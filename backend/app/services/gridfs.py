# SPDX-License-Identifier: MIT
from bson import ObjectId
from bson.errors import InvalidId
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.core.config import ENABLE_OPAQUE_IDS
from app.core.logger import logger
from app.services.base import BaseMongoService
from app.services.opaque_id_service import encode_opaque_id


class GridFSService(BaseMongoService):
    async def list_gridfs_buckets(self, db_name, search=None, page=1, page_size=10):
        """List all GridFS buckets in a database"""
        logger.debug(f"GridFSService.list_gridfs_buckets: using db_name='{db_name}', search='{search}', page={page}, page_size={page_size}")
        logger.debug("Listing GridFS buckets in DB")

        db = self.client[db_name]
        collections = await db.list_collection_names()
        
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

        # Build response with minimal bucket info (no stats for performance)
        buckets = []
        for bucket_name in paginated_buckets:
            bucket_info = {"bucket_name": bucket_name}
            if ENABLE_OPAQUE_IDS:
                bucket_info["opaque_id"] = encode_opaque_id(bucket_name)
            buckets.append(bucket_info)

        return {
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "buckets": buckets,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_gridfs_bucket_stats(self, db_name, bucket_name):
        """Get detailed statistics for a specific GridFS bucket"""
        logger.debug(f"GridFSService.get_gridfs_bucket_stats: using db_name='{db_name}', bucket_name='{bucket_name}'")
        
        try:
            db = self.client[db_name]
            
            # Check if bucket exists (both .files and .chunks collections must exist)
            files_collection = f"{bucket_name}.files"
            chunks_collection = f"{bucket_name}.chunks"
            
            if files_collection not in await db.list_collection_names():
                raise ValueError(f"GridFS bucket '{bucket_name}' not found in database '{db_name}'")
            if chunks_collection not in await db.list_collection_names():
                raise ValueError(f"GridFS bucket '{bucket_name}' is corrupted (missing chunks collection)")
            
            # Get stats for files collection
            files_pipeline = [
                {"$collStats": {"storageStats": {}}},
                {"$project": {
                    "files_count": "$storageStats.count",
                    "files_size": "$storageStats.size",
                    "files_storage_size": "$storageStats.storageSize",
                    "files_indexes": "$storageStats.nindexes",
                    "files_index_size": "$storageStats.totalIndexSize"
                }}
            ]
            
            files_stats_result = await db[files_collection].aggregate(files_pipeline).to_list()
            files_stats = files_stats_result[0] if files_stats_result else {}
            
            # Get stats for chunks collection
            chunks_pipeline = [
                {"$collStats": {"storageStats": {}}},
                {"$project": {
                    "chunks_count": "$storageStats.count",
                    "chunks_size": "$storageStats.size",
                    "chunks_storage_size": "$storageStats.storageSize",
                    "chunks_indexes": "$storageStats.nindexes",
                    "chunks_index_size": "$storageStats.totalIndexSize"
                }}
            ]
            
            chunks_stats_result = await db[chunks_collection].aggregate(chunks_pipeline).to_list()
            chunks_stats = chunks_stats_result[0] if chunks_stats_result else {}
            
            # Calculate total stats
            total_files = files_stats.get("files_count", 0)
            total_chunks = chunks_stats.get("chunks_count", 0)
            total_data_size = files_stats.get("files_size", 0) + chunks_stats.get("chunks_size", 0)
            total_storage_size = files_stats.get("files_storage_size", 0) + chunks_stats.get("chunks_storage_size", 0)
            total_indexes = files_stats.get("files_indexes", 0) + chunks_stats.get("chunks_indexes", 0)
            total_index_size = files_stats.get("files_index_size", 0) + chunks_stats.get("chunks_index_size", 0)
            
            # Calculate average chunk size if we have chunks
            avg_chunk_size = 0
            if total_chunks > 0:
                avg_chunk_size = chunks_stats.get("chunks_size", 0) / total_chunks
            
            return {
                "database": {
                    "name": db_name,
                    "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
                },
                "bucket": {
                    "bucket_name": bucket_name,
                    "opaque_id": encode_opaque_id(bucket_name) if ENABLE_OPAQUE_IDS else None
                },
                "stats": {
                    "files_count": total_files,
                    "chunks_count": total_chunks,
                    "total_data_size": total_data_size,
                    "total_storage_size": total_storage_size,
                    "avg_chunk_size": avg_chunk_size,
                    "indexes_count": total_indexes,
                    "index_size": total_index_size
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get GridFS bucket stats for '{bucket_name}' in DB '{db_name}': {e}", exc_info=True)
            raise

    async def upload_file_to_bucket(
        self,
        db_name,
        bucket_name,
        file_content,
        filename,
        content_type=None,
        metadata=None,
    ):
        """Upload a file to a specific GridFS bucket"""
        logger.debug(f"GridFSService.upload_file_to_bucket: using db_name='{db_name}', bucket_name='{bucket_name}', filename='{filename}'")
        logger.debug(f"File content type: {content_type}, content length: {len(file_content) if file_content else 0} bytes")
        logger.debug(f"Metadata: {metadata}")
        # bucket_name is raw from UI, no decryption
        logger.info("Uploading file to GridFS bucket")
        fs = AsyncIOMotorGridFSBucket(self.client[db_name], bucket_name)
        logger.debug(f"GridFS object created for bucket '{bucket_name}' in database '{db_name}'")

        stream_metadata = metadata or {}
        if content_type:
            stream_metadata['contentType'] = content_type
        stream = fs.open_upload_stream(
            filename=filename,
            metadata=stream_metadata,
        )
            
        await stream.write(file_content)
        await stream.close()
        
        file_id = stream._id
        logger.debug(f"File uploaded successfully with ID: {file_id}")
        return str(file_id)

    async def download_file_from_bucket(self, db_name: str, bucket_name: str, file_id: str):
        """Download a file from a specific GridFS bucket by ID"""
        logger.debug(
            f"GridFSService.download_file_from_bucket: db='{db_name}', bucket='{bucket_name}', file_id='{file_id}'"
        )

        # Validate ObjectId
        try:
            _id = ObjectId(file_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId for file")

        fs = AsyncIOMotorGridFSBucket(self.client[db_name], bucket_name)

        try:
            # Don't await when opening a download stream - it returns synchronously
            stream = fs.open_download_stream(_id)
            content = await stream.read()  # Read the full file content as bytes

            logger.debug(f"File '{stream.filename}' downloaded successfully from GridFS")

            # Return only actual content and key metadata if desired
            return {
                "filename": stream.filename,
                "content_type": getattr(stream, "content_type", None),
                "content": content,  # <-- the actual file content as bytes
            }

        except NoFile:
            logger.warning(f"No file found in bucket '{bucket_name}' with id '{file_id}'")
            return None

    async def list_files_in_bucket(
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

        result = await collection.aggregate(pipeline).to_list()
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
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "bucket": {
                "bucket_name": bucket_name,
                "opaque_id": encode_opaque_id(bucket_name) if ENABLE_OPAQUE_IDS else None
            },
            "data": files,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def query_files_in_bucket(
        self,
        db_name: str,
        bucket_name: str,
        filter: dict | None = None,
        sort_field: str | None = None,
        sort_order: int = 1,
        page: int = 1,
        page_size: int = 10,
    ):
        """Query files in a GridFS bucket using a MongoDB filter with pagination and optional sorting.
        Supports matching on `filename`, `metadata.*`, and other fields present in the `.files` documents.
        """
        files_collection = f"{bucket_name}.files"
        collection = self.client[db_name][files_collection]

        match_stage = filter or {}

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        sort_stage = {"uploadDate": -1}
        if sort_field:
            sort_stage = {sort_field: sort_order}

        pipeline.append({
            "$facet": {
                "total": [{"$count": "count"}],
                "data": [
                    {"$sort": sort_stage},
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

        result = await collection.aggregate(pipeline).to_list()
        if result:
            total = result[0]["total"][0]["count"] if result[0]["total"] else 0
            files_data = result[0]["data"]
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
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "bucket": {
                "bucket_name": bucket_name,
                "opaque_id": encode_opaque_id(bucket_name) if ENABLE_OPAQUE_IDS else None
            },
            "data": files,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_file_metadata_from_bucket(self, db_name, bucket_name, file_id):
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
        
        result = await self.client[db_name][files_collection].aggregate(pipeline).to_list()
        
        if not result:
            return None

        file_doc = result[0]
        content_type = file_doc.get("contentType") or file_doc.get("metadata", {}).get("contentType")
        return {
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "bucket": {
                "bucket_name": bucket_name,
                "opaque_id": encode_opaque_id(bucket_name) if ENABLE_OPAQUE_IDS else None
            },
            "_id": file_doc["_id"],
            "filename": file_doc.get("filename"),
            "content_type": content_type,
            "length": file_doc.get("length"),
            "upload_date": file_doc.get("uploadDate"),
            "metadata": file_doc.get("metadata", {}),
        }

    async def delete_file_from_bucket(self, db_name, bucket_name, file_id):
        """Delete a file from a specific GridFS bucket by ID"""
        try:
            _id = ObjectId(file_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId for file")

        logger.warning(
            f"Deleting file with ID '{file_id}' from GridFS bucket '{bucket_name}' in DB '{db_name}'"
        )

        try:
            fs = AsyncIOMotorGridFSBucket(self.client[db_name], bucket_name)
        except Exception as e:
            logger.error(f"Failed to create GridFS object for bucket '{bucket_name}' in DB '{db_name}': {e}")
            raise ValueError(f"Invalid GridFS bucket '{bucket_name}'")

        # Check if file exists before attempting deletion
        try:
            exists = await fs.find({"_id": _id}).to_list(length=1)
            if not exists:
                return False
        except Exception as e:
            logger.error(f"Failed to check if file exists in bucket '{bucket_name}': {e}")
            raise ValueError(f"Error checking file existence in bucket '{bucket_name}'")

        try:
            await fs.delete(_id)
            return True
        except NoFile:
            # This shouldn't happen since we checked exists() above, but just in case
            return False
        except Exception as e:
            logger.error(f"Failed to delete file from GridFS: {e}")
            raise

    async def delete_bucket(self, db_name, bucket_name):
        """Delete an entire GridFS bucket (both .files and .chunks collections)"""
        logger.warning(
            f"Deleting entire GridFS bucket '{bucket_name}' from DB '{db_name}'"
        )

        db = self.client[db_name]
        files_collection = f"{bucket_name}.files"
        chunks_collection = f"{bucket_name}.chunks"

        # Check if bucket exists (both collections must exist)
        collections = await db.list_collection_names()
        if files_collection not in collections:
            raise ValueError(f"GridFS bucket '{bucket_name}' not found in database '{db_name}'")
        if chunks_collection not in collections:
            raise ValueError(f"GridFS bucket '{bucket_name}' is corrupted (missing chunks collection)")

        # Drop both collections
        await db.drop_collection(files_collection)
        await db.drop_collection(chunks_collection)
        return True

gridfs_service = GridFSService()