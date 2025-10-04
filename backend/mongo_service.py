from datetime import datetime

import gridfs
from bson import ObjectId
from bson.errors import InvalidId
from config import MONGO_URI
from gridfs.errors import NoFile
from logger import logger
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure


class DatabaseExistsError(Exception):
    """Custom exception for database already exists scenarios"""

    pass


class MongoService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)

    # --------- Database Operations ---------

    def list_databases(
        self,
        search=None,
        sort="asc",
        page=1,
        page_size=10,
        sort_field=None,
        sort_order=1,
    ):
        logger.debug("Listing databases with filter and pagination")
        dbs = self.client.list_database_names()

        if search:
            search_lower = search.lower()
            dbs = [db for db in dbs if search_lower in db.lower()]

        dbs.sort(reverse=(sort == "desc"))
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "databases": dbs[start:end],
            "total": len(dbs),
            "page": page,
            "page_size": page_size,
        }

    def create_database(self, db_name, collection_name):
        logger.info(
            f"Creating database '{db_name}' with initial collection '{collection_name}'"
        )

        # Check if database already exists - if it does, this should be an error
        existing_dbs = self.client.list_database_names()
        if db_name in existing_dbs:
            logger.error(f"Database '{db_name}' already exists")
            raise DatabaseExistsError(f"Database '{db_name}' already exists")

        # Database doesn't exist, create collection (this will create the database too)
        logger.info(
            f"Creating new database '{db_name}' with collection '{collection_name}'"
        )
        self.client[db_name].create_collection(collection_name)

    def delete_database(self, db_name):
        logger.warning(f"Dropping database: {db_name}")
        self.client.drop_database(db_name)
        return True

    # --------- Collection Operations ---------

    def list_collections(
        self,
        db_name,
        search=None,
        sort="asc",
        page=1,
        page_size=10,
        sort_field=None,
        sort_order=1,
    ):
        try:
            logger.debug(
                f"Listing collections in DB: {db_name} with filter and pagination"
            )
            
            db = self.client[db_name]
            collection_names = db.list_collection_names()

            # Filter out MongoDB system collections and GridFS collections
            filtered_names = [
                c for c in collection_names
                if not (c.startswith("system.") or c.endswith((".files", ".chunks")))
            ]

            # Apply search filter early
            if search:
                search_lower = search.lower()
                filtered_names = [
                    c for c in filtered_names
                    if search_lower in c.lower()
                ]

            # Sort collection names
            filtered_names.sort(reverse=(sort == "desc"))

            # Calculate pagination
            total = len(filtered_names)
            start = (page - 1) * page_size
            end = start + page_size
            
            # Only fetch stats for paginated collections
            paginated_names = filtered_names[start:end]

            # Use aggregation to get stats efficiently (MongoDB does the work)
            collections = []
            for collection_name in paginated_names:
                try:
                    # Use $collStats aggregation - single MongoDB operation
                    pipeline = [
                        {"$collStats": {"storageStats": {}}},
                        {"$project": {
                            "count": "$storageStats.count",
                            "size": "$storageStats.size"
                        }}
                    ]
                    
                    stats_result = list(db[collection_name].aggregate(pipeline))
                    
                    if stats_result:
                        stats = stats_result[0]
                        documents_count = stats.get("count", 0)
                        total_size = stats.get("size", 0)
                    else:
                        # Fallback only if aggregation returns nothing
                        documents_count = db[collection_name].estimated_document_count()
                        coll_stats = db.command("collStats", collection_name)
                        total_size = coll_stats.get("size", 0)

                    collections.append({
                        "collection_name": collection_name,
                        "documents_count": documents_count,
                        "total_size": total_size,
                    })
                except Exception as e:
                    logger.warning(
                        f"Could not get stats for collection '{collection_name}': {e}"
                    )
                    collections.append({
                        "collection_name": collection_name,
                        "documents_count": 0,
                        "total_size": 0,
                    })

            return {
                "collections": collections,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as e:
            logger.error(
                f"Error listing collections for DB '{db_name}': {e}", exc_info=True
            )
            raise

    def create_collection(self, db_name, col_name):
        logger.info(f"Creating collection '{col_name}' in DB '{db_name}'")
        db = self.client[db_name]
        if col_name in db.list_collection_names():
            raise CollectionInvalid(
                f"Collection '{col_name}' already exists in '{db_name}'"
            )
        db.create_collection(col_name)

    def delete_collection(self, db_name, col_name):
        logger.warning(f"Dropping collection '{col_name}' from DB '{db_name}'")
        self.client[db_name].drop_collection(col_name)
        return True

    # --------- Document Operations ---------

    def insert_document(self, db_name, col_name, document: dict):
        logger.debug(f"Inserting document into {db_name}.{col_name}")
        result = self.client[db_name][col_name].insert_one(document)
        return str(result.inserted_id)

    def query_collection(
        self,
        db_name,
        col_name,
        filter=None,
        sort_field=None,
        sort_order=1,
        page=1,
        page_size=10,
    ):
        if page_size > 100:
            raise ValueError("Page size exceeds max limit of 100")

        logger.debug(
            f"Querying {db_name}.{col_name} | filter={filter} | page={page} | size={page_size}"
        )

        collection = self.client[db_name][col_name]
        query_filter = filter or {}

        # Convert _id from string to ObjectId if present
        if "_id" in query_filter and isinstance(query_filter["_id"], str):
            try:
                query_filter["_id"] = ObjectId(query_filter["_id"])
            except Exception:
                raise ValueError("Invalid ObjectId format for _id")

        # Use aggregation pipeline for better performance
        pipeline = [{"$match": query_filter}]
        
        if sort_field:
            pipeline.append({"$sort": {sort_field: sort_order}})
        
        # Use $facet to get count and data in single query
        pipeline.append({
            "$facet": {
                "total": [{"$count": "count"}],
                "data": [
                    {"$skip": (page - 1) * page_size},
                    {"$limit": page_size}
                ]
            }
        })

        result = list(collection.aggregate(pipeline))
        
        if result:
            total = result[0]["total"][0]["count"] if result[0]["total"] else 0
            data = result[0]["data"]
            
            # Convert ObjectId to string
            for doc in data:
                doc["_id"] = str(doc["_id"])
        else:
            total = 0
            data = []

        return {"data": data, "total": total, "page": page, "page_size": page_size}

    def get_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        doc = self.client[db_name][col_name].find_one(
            {"_id": _id},
            session=None
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def update_document(self, db_name, col_name, doc_id, update_data: dict):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = self.client[db_name][col_name].update_one(
            {"_id": _id}, 
            {"$set": update_data}
        )
        return result.modified_count

    def delete_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = self.client[db_name][col_name].delete_one({"_id": _id})
        return result.deleted_count

    # --------- Bulk Operations ---------

    def export_collection(self, db_name, col_name):
        logger.info(f"Exporting collection: {db_name}.{col_name}")
        
        # Use aggregation with projection to convert _id on MongoDB side
        pipeline = [
            {"$project": {
                "_id": {"$toString": "$_id"},
                "doc": "$$ROOT"
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$project": {"doc": 0}}
        ]
        
        # Stream results for memory efficiency
        exported = []
        for doc in self.client[db_name][col_name].aggregate(pipeline, allowDiskUse=True):
            doc["_id"] = str(doc["_id"])
            exported.append(doc)
        
        return exported

    def import_documents(self, db_name, col_name, documents: list):
        if len(documents) > 500:
            raise ValueError("Too many documents to import (max 500)")

        # Remove _id in list comprehension (more efficient)
        cleaned_documents = [
            {k: v for k, v in doc.items() if k != "_id"}
            for doc in documents
        ]

        result = self.client[db_name][col_name].insert_many(
            cleaned_documents,
            ordered=False  # Faster bulk insert
        )
        return [str(_id) for _id in result.inserted_ids]

    # --------- GridFS Bucket Operations ---------

    def list_gridfs_buckets(self, db_name, search=None, page=1, page_size=10):
        """List all GridFS buckets in a database"""
        logger.debug(f"Listing GridFS buckets in DB: {db_name}")

        db = self.client[db_name]
        collections = db.list_collection_names()
        
        # Find .files collections and verify .chunks exist
        bucket_names = set()
        files_collections = [c for c in collections if c.endswith(".files")]
        
        for files_col in files_collections:
            bucket_name = files_col[:-6]
            chunks_col = f"{bucket_name}.chunks"
            if chunks_col in collections:
                bucket_names.add(bucket_name)

        # Apply search filter early
        if search:
            search_lower = search.lower()
            bucket_names = {b for b in bucket_names if search_lower in b.lower()}

        # Sort bucket names
        sorted_buckets = sorted(bucket_names)

        # Calculate pagination
        total = len(sorted_buckets)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_buckets = sorted_buckets[start:end]

        # Use aggregation to get stats for paginated buckets only
        buckets = []
        for bucket_name in paginated_buckets:
            files_collection = f"{bucket_name}.files"
            
            # Single aggregation to get both count and total size
            pipeline = [
                {
                    "$facet": {
                        "count": [{"$count": "total"}],
                        "size": [{"$group": {"_id": None, "total_size": {"$sum": "$length"}}}]
                    }
                }
            ]
            
            result = list(db[files_collection].aggregate(pipeline))
            
            if result:
                files_count = result[0]["count"][0]["total"] if result[0]["count"] else 0
                total_size = result[0]["size"][0]["total_size"] if result[0]["size"] else 0
            else:
                files_count = 0
                total_size = 0

            buckets.append({
                "bucket_name": bucket_name,
                "files_count": files_count,
                "total_size": total_size,
            })

        return {
            "buckets": buckets,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def upload_file_to_bucket(
        self,
        db_name,
        bucket_name,
        file_content,
        filename,
        content_type=None,
        metadata=None,
    ):
        """Upload a file to a specific GridFS bucket"""
        logger.info(
            f"Uploading file '{filename}' to GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )
        fs = gridfs.GridFS(self.client[db_name], collection=bucket_name)

        file_id = fs.put(
            file_content,
            filename=filename,
            contentType=content_type,
            metadata=metadata or {},
            uploadDate=datetime.utcnow(),
        )
        return str(file_id)

    def download_file_from_bucket(self, db_name, bucket_name, file_id):
        """Download a file from a specific GridFS bucket by ID"""
        try:
            _id = ObjectId(file_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId for file")

        logger.debug(
            f"Downloading file with ID '{file_id}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )
        fs = gridfs.GridFS(self.client[db_name], collection=bucket_name)

        try:
            grid_file = fs.get(_id)
            return {
                "content": grid_file.read(),
                "filename": grid_file.filename,
                "content_type": grid_file.content_type,
                "length": grid_file.length,
                "upload_date": grid_file.upload_date,
                "metadata": grid_file.metadata,
            }
        except NoFile:
            return None

    def download_file_by_name_from_bucket(self, db_name, bucket_name, filename):
        """Download the latest version of a file from a specific GridFS bucket by filename"""
        logger.debug(
            f"Downloading file '{filename}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )
        fs = gridfs.GridFS(self.client[db_name], collection=bucket_name)

        try:
            grid_file = fs.get_last_version(filename)
            return {
                "content": grid_file.read(),
                "filename": grid_file.filename,
                "content_type": grid_file.content_type,
                "length": grid_file.length,
                "upload_date": grid_file.upload_date,
                "metadata": grid_file.metadata,
                "file_id": str(grid_file._id),
            }
        except NoFile:
            return None

    def list_files_in_bucket(
        self, db_name, bucket_name, search=None, page=1, page_size=10
    ):
        """List files in a specific GridFS bucket with pagination and search"""
        logger.debug(
            f"Listing GridFS files in bucket '{bucket_name}' in DB '{db_name}' with pagination"
        )

        files_collection = f"{bucket_name}.files"
        collection = self.client[db_name][files_collection]
        
        # Build match stage
        match_stage = {}
        if search:
            match_stage["filename"] = {"$regex": search, "$options": "i"}

        # Use aggregation with $facet to get count and data in one query
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        pipeline.append({
            "$facet": {
                "total": [{"$count": "count"}],
                "data": [
                    {"$sort": {"uploadDate": -1}},
                    {"$skip": (page - 1) * page_size},
                    {"$limit": page_size},
                    {"$project": {
                        "_id": {"$toString": "$_id"},
                        "filename": 1,
                        "contentType": 1,
                        "length": 1,
                        "uploadDate": 1,
                        "metadata": 1
                    }}
                ]
            }
        })

        result = list(collection.aggregate(pipeline))
        
        if result:
            total = result[0]["total"][0]["count"] if result[0]["total"] else 0
            files_data = result[0]["data"]
            
            # Reformat field names for consistency
            files = [
                {
                    "_id": f["_id"],
                    "filename": f.get("filename"),
                    "content_type": f.get("contentType"),
                    "length": f.get("length"),
                    "upload_date": f.get("uploadDate"),
                    "metadata": f.get("metadata", {}),
                }
                for f in files_data
            ]
        else:
            total = 0
            files = []

        return {
            "data": files,
            "total": total,
            "page": page,
            "page_size": page_size,
            "bucket_name": bucket_name,
        }

    def get_file_metadata_from_bucket(self, db_name, bucket_name, file_id):
        """Get file metadata from a specific bucket without downloading the content"""
        try:
            _id = ObjectId(file_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId for file")

        logger.debug(
            f"Getting metadata for file ID '{file_id}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )
        
        files_collection = f"{bucket_name}.files"
        
        # Use aggregation for consistent string conversion
        pipeline = [
            {"$match": {"_id": _id}},
            {"$project": {
                "_id": {"$toString": "$_id"},
                "filename": 1,
                "contentType": 1,
                "length": 1,
                "uploadDate": 1,
                "metadata": 1
            }},
            {"$limit": 1}
        ]
        
        result = list(self.client[db_name][files_collection].aggregate(pipeline))
        
        if not result:
            return None

        file_doc = result[0]
        return {
            "_id": file_doc["_id"],
            "filename": file_doc.get("filename"),
            "content_type": file_doc.get("contentType"),
            "length": file_doc.get("length"),
            "upload_date": file_doc.get("uploadDate"),
            "metadata": file_doc.get("metadata", {}),
            "bucket_name": bucket_name,
        }

    def delete_file_from_bucket(self, db_name, bucket_name, file_id):
        """Delete a file from a specific GridFS bucket by ID"""
        try:
            _id = ObjectId(file_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId for file")

        logger.warning(
            f"Deleting file with ID '{file_id}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )
        fs = gridfs.GridFS(self.client[db_name], collection=bucket_name)

        try:
            fs.delete(_id)
            return True
        except NoFile:
            return False

    def delete_files_by_name_from_bucket(self, db_name, bucket_name, filename):
        """Delete all files with the given filename from a specific GridFS bucket"""
        logger.warning(
            f"Deleting all files named '{filename}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )

        files_collection = f"{bucket_name}.files"
        chunks_collection = f"{bucket_name}.chunks"
        
        # Get all file IDs matching the filename
        file_ids = [
            doc["_id"] 
            for doc in self.client[db_name][files_collection].find(
                {"filename": filename}, 
                {"_id": 1}
            )
        ]
        
        if not file_ids:
            return 0

        # Bulk delete from both collections
        self.client[db_name][files_collection].delete_many({"_id": {"$in": file_ids}})
        self.client[db_name][chunks_collection].delete_many({"files_id": {"$in": file_ids}})
        
        return len(file_ids)

    def delete_bucket(self, db_name, bucket_name):
        """Delete an entire GridFS bucket (both .files and .chunks collections)"""
        logger.warning(
            f"Deleting entire GridFS bucket '{bucket_name}' from DB '{db_name}'"
        )

        files_collection = f"{bucket_name}.files"
        chunks_collection = f"{bucket_name}.chunks"

        # Drop both collections
        self.client[db_name].drop_collection(files_collection)
        self.client[db_name].drop_collection(chunks_collection)

        return True