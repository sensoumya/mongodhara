from app.core.config import ENABLE_AUDIT_LOGGING, ENABLE_OPAQUE_IDS
from app.core.exceptions import CollectionExistsError
from app.core.logger import logger
from app.services.audit_service import audit_service
from app.services.base import BaseMongoService
from app.services.opaque_id_service import encode_opaque_id


class CollectionService(BaseMongoService):
    """Service for collection operations."""

    async def list_collections(
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
            
            db = self.get_database(db_name)
            collection_names = await db.list_collection_names()

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
            
            # Build response with opaque IDs if enabled
            collections = []
            for collection_name in filtered_names[start:end]:
                col_info = {"name": collection_name}
                if ENABLE_OPAQUE_IDS:
                    col_info["opaque_id"] = encode_opaque_id(collection_name)
                collections.append(col_info)

            return {
                "database": {
                    "name": db_name,
                    "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
                },
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

    async def get_collection_stats(self, db_name, col_name):
        """Get detailed statistics for a specific collection"""
        
        try:
            logger.debug(f"Getting stats for collection '{col_name}' in DB '{db_name}'")
            
            db = self.get_database(db_name)
            
            # Check if collection exists
            if col_name not in await db.list_collection_names():
                raise ValueError(f"Collection '{col_name}' not found in database '{db_name}'")
            
            # Use $collStats aggregation to get comprehensive collection info
            pipeline = [
                {"$collStats": {"storageStats": {}}},
                {"$project": {
                    "count": "$storageStats.count",
                    "size": "$storageStats.size",
                    "avgObjSize": "$storageStats.avgObjSize",
                    "storageSize": "$storageStats.storageSize",
                    "indexes": "$storageStats.nindexes",
                    "indexSize": "$storageStats.totalIndexSize"
                }}
            ]
            
            stats_result = await db[col_name].aggregate(pipeline).to_list()
            
            if stats_result:
                stats = stats_result[0]
                return {
                    "database": {
                        "name": db_name,
                        "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
                    },
                    "collection": {
                        "name": col_name,
                        "opaque_id": encode_opaque_id(col_name) if ENABLE_OPAQUE_IDS else None
                    },
                    "stats": {
                        "documents_count": stats.get("count", 0),
                        "total_size": stats.get("size", 0),
                        "avg_document_size": stats.get("avgObjSize", 0),
                        "storage_size": stats.get("storageSize", 0),
                        "indexes_count": stats.get("indexes", 0),
                        "index_size": stats.get("indexSize", 0)
                    }
                }
            else:
                # Fallback if aggregation fails
                coll_stats = await db.command("collStats", col_name)
                return {
                    "database": {
                        "name": db_name,
                        "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
                    },
                    "collection": {
                        "name": col_name,
                        "opaque_id": encode_opaque_id(col_name) if ENABLE_OPAQUE_IDS else None
                    },
                    "stats": {
                        "documents_count": await db[col_name].estimated_document_count(),
                        "total_size": coll_stats.get("size", 0),
                        "avg_document_size": 0,
                        "storage_size": coll_stats.get("storageSize", 0),
                        "indexes_count": coll_stats.get("nindexes", 0),
                        "index_size": coll_stats.get("totalIndexSize", 0)
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get collection stats for '{col_name}' in DB '{db_name}': {e}", exc_info=True)
            raise

    async def create_collection(self, db_name, col_name, user=None, request=None, background_tasks=None):
        logger.info(f"Creating collection '{col_name}' in database '{db_name}'")
        db = self.get_database(db_name)

        # Check if collection already exists - if it does, this should be an error
        existing_cols = await db.list_collection_names()
        if col_name in existing_cols:
            logger.error(f"Collection '{col_name}' already exists in database '{db_name}'")
            if ENABLE_AUDIT_LOGGING and user:
                if background_tasks:
                    background_tasks.add_task(
                        audit_service.log_operation,
                        user_email=user.get("email"),
                        operation="create_collection",
                        resource={"type": "collection", "database": db_name, "name": col_name},
                        status="failure",
                        error_message="Collection already exists",
                        request=request
                    )
                else:
                    await audit_service.log_operation(
                        user_email=user.get("email"),
                        operation="create_collection",
                        resource={"type": "collection", "database": db_name, "name": col_name},
                        status="failure",
                        error_message="Collection already exists",
                        request=request
                    )
            raise CollectionExistsError(f"Collection '{col_name}' already exists in database '{db_name}'")

        # Collection doesn't exist, create it
        await db.create_collection(col_name)
        logger.info(f"Collection '{col_name}' created successfully in database '{db_name}'")
        
        if ENABLE_AUDIT_LOGGING and user:
            if background_tasks:
                background_tasks.add_task(
                    audit_service.log_operation,
                    user_email=user.get("email"),
                    operation="create_collection",
                    resource={"type": "collection", "database": db_name, "name": col_name},
                    request=request
                )
            else:
                await audit_service.log_operation(
                    user_email=user.get("email"),
                    operation="create_collection",
                    resource={"type": "collection", "database": db_name, "name": col_name},
                    request=request
                )

    async def delete_collection(self, db_name, col_name):
        logger.warning(f"Dropping collection '{col_name}' from database '{db_name}'")
        db = self.get_database(db_name)
        
        # Check if collection exists
        if col_name not in await db.list_collection_names():
            raise ValueError(f"Collection '{col_name}' not found in database '{db_name}'")
        
        await db.drop_collection(col_name)
        return True


collection_service = CollectionService()