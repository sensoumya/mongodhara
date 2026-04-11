# SPDX-License-Identifier: MIT
from app.core.config import ENABLE_AUDIT_LOGGING, ENABLE_OPAQUE_IDS
from app.core.exceptions import DatabaseExistsError
from app.core.logger import logger
from app.services.audit_service import audit_service
from app.services.base import BaseMongoService
from app.services.opaque_id_service import encode_opaque_id


class DatabaseService(BaseMongoService):
    """Service for database operations."""

    async def list_databases(
        self,
        search=None,
        sort="asc",
        page=1,
        page_size=10,
        sort_field=None,
        sort_order=1,
    ):
        logger.debug("Listing databases with filter and pagination")
        dbs = await self.client.list_database_names()

        if search:
            search_lower = search.lower()
            dbs = [db for db in dbs if search_lower in db.lower()]

        dbs.sort(reverse=(sort == "desc"))
        start = (page - 1) * page_size
        end = start + page_size
        
        # Build response with opaque IDs if enabled
        databases = []
        for db_name in dbs[start:end]:
            db_info = {"name": db_name}
            if ENABLE_OPAQUE_IDS:
                db_info["opaque_id"] = encode_opaque_id(db_name)
            databases.append(db_info)
        
        return {
            "databases": databases,
            "total": len(dbs),
            "page": page,
            "page_size": page_size,
        }

    async def create_database(self, db_name, collection_name, user=None, request=None):
        logger.debug(f"DatabaseService.create_database: using db_name='{db_name}', collection_name='{collection_name}'")
        # collection_name is raw from UI, no decryption
        logger.info("Creating database with initial collection")

        # Check if database already exists - if it does, this should be an error
        existing_dbs = await self.client.list_database_names()
        if db_name in existing_dbs:
            logger.error("Database already exists")
            if ENABLE_AUDIT_LOGGING and user:
                await audit_service.log_operation(
                    user_email=user.get("email"),
                    operation="create_database",
                    resource={"type": "database", "name": db_name},
                    status="failure",
                    error_message="Database already exists",
                    request=request
                )
            raise DatabaseExistsError("Database already exists")

        # Database doesn't exist, create collection (this will create the database too)
        logger.info("Creating new database with collection")
        await self.client[db_name].create_collection(collection_name)
        
        if ENABLE_AUDIT_LOGGING and user:
            await audit_service.log_operation(
                user_email=user.get("email"),
                operation="create_database",
                resource={"type": "database", "name": db_name},
                details={"initial_collection": collection_name},
                request=request
            )

    async def get_database_stats(self, db_name):
        # NOTE: db_name is already decoded by middleware
        logger.debug(f"DatabaseService.get_database_stats: using db_name='{db_name}'")
        logger.debug("Getting detailed database statistics")
        
        # Check if database exists
        existing_dbs = await self.client.list_database_names()
        if db_name not in existing_dbs:
            raise ValueError(f"Database '{db_name}' not found")
        
        db = self.client[db_name]
        
        # Get database stats using dbStats command
        db_stats = await db.command("dbStats", 1)  # scale=1 for bytes
        
        # Get collection count and details
        collections = await db.list_collection_names()
        # Filter out system collections and GridFS chunks/files
        user_collections = [
            c for c in collections
            if not (c.startswith("system.") or c.endswith((".files", ".chunks")))
        ]
        
        # Get total documents and indexes across all collections
        total_documents = 0
        total_indexes = 0
        total_index_size = 0
        
        for collection_name in user_collections:
            try:
                coll_stats = await db.command("collStats", collection_name)
                total_documents += coll_stats.get("count", 0)
                total_indexes += coll_stats.get("nindexes", 0)
                total_index_size += coll_stats.get("totalIndexSize", 0)
            except Exception as e:
                logger.warning(f"Could not get stats for collection {collection_name}: {e}")
                continue
        
        # Build comprehensive stats response
        stats = {
            "collections_count": len(user_collections),
            "total_documents": total_documents,
            "total_indexes": total_indexes,
            "total_index_size": total_index_size,
            "data_size": db_stats.get("dataSize", 0),
            "storage_size": db_stats.get("storageSize", 0),
            "index_size": db_stats.get("indexSize", 0),
            "total_size": db_stats.get("totalSize", 0),
            "fs_used_size": db_stats.get("fsUsedSize", 0),
            "fs_total_size": db_stats.get("fsTotalSize", 0),
        }
        
        return [
            {
                "database": {
                    "name": db_name,
                    "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
                },
                "stats": stats
            }
        ]

    async def delete_database(self, db_name, user=None, request=None, background_tasks=None):
        logger.warning(f"Dropping database: {db_name}")
        
        # Check if database exists
        existing_dbs = await self.client.list_database_names()
        if db_name not in existing_dbs:
            if ENABLE_AUDIT_LOGGING and user:
                if background_tasks:
                    background_tasks.add_task(
                        audit_service.log_operation,
                        user_email=user.get("email"),
                        operation="delete_database",
                        resource={"type": "database", "name": db_name},
                        status="failure",
                        error_message="Database not found",
                        request=request
                    )
                else:
                    await audit_service.log_operation(
                        user_email=user.get("email"),
                        operation="delete_database",
                        resource={"type": "database", "name": db_name},
                        status="failure",
                        error_message="Database not found",
                        request=request
                    )
            raise ValueError(f"Database '{db_name}' not found")
        
        await self.client.drop_database(db_name)
        
        if ENABLE_AUDIT_LOGGING and user:
            if background_tasks:
                background_tasks.add_task(
                    audit_service.log_operation,
                    user_email=user.get("email"),
                    operation="delete_database",
                    resource={"type": "database", "name": db_name},
                    request=request
                )
            else:
                await audit_service.log_operation(
                    user_email=user.get("email"),
                    operation="delete_database",
                    resource={"type": "database", "name": db_name},
                    request=request
                )
        return True


# Create a global instance
database_service = DatabaseService()