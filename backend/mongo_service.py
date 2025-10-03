from datetime import datetime

import gridfs
from bson import ObjectId
from bson.errors import InvalidId
from gridfs.errors import NoFile
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure

from config import MONGO_URI
from logger import logger


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
            dbs = [db for db in dbs if search.lower() in db.lower()]

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
            collection_names = self.client[db_name].list_collection_names()

            # Filter out MongoDB system collections and GridFS collections
            collection_names = [
                c
                for c in collection_names
                if not c.startswith("system.")
                and not c.endswith(".files")
                and not c.endswith(".chunks")
            ]

            # Build detailed collection info similar to GridFS buckets
            collections = []
            for collection_name in collection_names:
                try:
                    # Get document count for this collection
                    documents_count = self.client[db_name][
                        collection_name
                    ].count_documents({})

                    # Calculate collection size (estimated)
                    stats = self.client[db_name].command("collStats", collection_name)
                    total_size = stats.get("size", 0)

                    collections.append(
                        {
                            "collection_name": collection_name,
                            "documents_count": documents_count,
                            "total_size": total_size,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not get stats for collection '{collection_name}': {e}"
                    )
                    # Include collection with basic info if stats fail
                    collections.append(
                        {
                            "collection_name": collection_name,
                            "documents_count": 0,
                            "total_size": 0,
                        }
                    )

            # Apply search filter
            if search:
                collections = [
                    c
                    for c in collections
                    if search.lower() in c["collection_name"].lower()
                ]

            # Sort collections by name
            collections.sort(
                key=lambda x: x["collection_name"], reverse=(sort == "desc")
            )

            total = len(collections)
            start = (page - 1) * page_size
            end = start + page_size

            return {
                "collections": collections[start:end],
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

        db = self.client[db_name]
        collection = db[col_name]
        query_filter = filter or {}

        # 👇 Convert _id from string to ObjectId if present
        if "_id" in query_filter and isinstance(query_filter["_id"], str):
            try:
                query_filter["_id"] = ObjectId(query_filter["_id"])
            except Exception:
                raise ValueError("Invalid ObjectId format for _id")

        total = collection.count_documents(query_filter)
        cursor = collection.find(query_filter)

        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)

        cursor = cursor.skip((page - 1) * page_size).limit(page_size)

        data = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            data.append(doc)

        return {"data": data, "total": total, "page": page, "page_size": page_size}

    def get_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        doc = self.client[db_name][col_name].find_one({"_id": _id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def update_document(self, db_name, col_name, doc_id, update_data: dict):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = self.client[db_name][col_name].update_one(
            {"_id": _id}, {"$set": update_data}
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
        docs = self.client[db_name][col_name].find()
        exported = []
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            exported.append(doc)
        return exported

    def import_documents(self, db_name, col_name, documents: list):
        if len(documents) > 500:
            raise ValueError("Too many documents to import (max 500)")

        # Always remove _id fields to avoid conflicts and let MongoDB generate new ones
        cleaned_documents = []
        for doc in documents:
            cleaned_doc = dict(doc)  # Create a copy
            if "_id" in cleaned_doc:
                del cleaned_doc["_id"]  # Always remove existing _id
            cleaned_documents.append(cleaned_doc)

        result = self.client[db_name][col_name].insert_many(cleaned_documents)
        return [str(_id) for _id in result.inserted_ids]

    # --------- GridFS Bucket Operations ---------

    def list_gridfs_buckets(self, db_name, search=None, page=1, page_size=10):
        """List all GridFS buckets in a database"""
        logger.debug(f"Listing GridFS buckets in DB: {db_name}")

        # Find all collections that end with .files (GridFS convention)
        collections = self.client[db_name].list_collection_names()
        buckets = []

        for collection in collections:
            if collection.endswith(".files"):
                bucket_name = collection[:-6]  # Remove .files suffix
                # Verify corresponding .chunks collection exists
                chunks_collection = f"{bucket_name}.chunks"
                if chunks_collection in collections:
                    # Get file count and total size for this bucket
                    files_count = self.client[db_name][collection].count_documents({})

                    # Calculate total size by summing length field
                    pipeline = [
                        {"$group": {"_id": None, "total_size": {"$sum": "$length"}}}
                    ]
                    size_result = list(
                        self.client[db_name][collection].aggregate(pipeline)
                    )
                    total_size = size_result[0]["total_size"] if size_result else 0

                    buckets.append(
                        {
                            "bucket_name": bucket_name,
                            "files_count": files_count,
                            "total_size": total_size,
                        }
                    )

        # Apply search filter
        if search:
            buckets = [b for b in buckets if search.lower() in b["bucket_name"].lower()]

        # Sort buckets by name
        buckets.sort(key=lambda x: x["bucket_name"])

        # Apply pagination
        total = len(buckets)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "buckets": buckets[start:end],
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

        # Build query filter
        query = {}
        if search:
            query["filename"] = {"$regex": search, "$options": "i"}

        # Get total count
        files_collection = f"{bucket_name}.files"
        total = self.client[db_name][files_collection].count_documents(query)

        # Apply pagination
        skip = (page - 1) * page_size
        cursor = (
            self.client[db_name][files_collection]
            .find(query)
            .skip(skip)
            .limit(page_size)
            .sort("uploadDate", -1)
        )

        files = []
        for file_doc in cursor:
            files.append(
                {
                    "_id": str(file_doc["_id"]),
                    "filename": file_doc.get("filename"),
                    "content_type": file_doc.get("contentType"),
                    "length": file_doc.get("length"),
                    "upload_date": file_doc.get("uploadDate"),
                    "metadata": file_doc.get("metadata", {}),
                }
            )

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
        file_doc = self.client[db_name][files_collection].find_one({"_id": _id})

        if not file_doc:
            return None

        return {
            "_id": str(file_doc["_id"]),
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

        # Find all files with this filename in the specific bucket
        files_collection = f"{bucket_name}.files"
        file_docs = self.client[db_name][files_collection].find({"filename": filename})
        deleted_count = 0

        fs = gridfs.GridFS(self.client[db_name], collection=bucket_name)
        for file_doc in file_docs:
            try:
                fs.delete(file_doc["_id"])
                deleted_count += 1
            except NoFile:
                continue

        return deleted_count

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
