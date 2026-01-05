from app.core.config import ENABLE_OPAQUE_IDS
from app.core.logger import logger
from app.services.base import BaseMongoService
from app.services.opaque_id_service import encode_opaque_id


class IndexService(BaseMongoService):
    async def list_indexes(self, db_name, col_name):
        """List all indexes for a collection"""
        logger.debug(f"IndexService.list_indexes: using db_name='{db_name}', col_name='{col_name}'")
        logger.debug("Listing indexes for collection")
        
        collection = self.client[db_name][col_name]
        indexes = []
        
        async for index in collection.list_indexes():
            # Convert key to a more readable format
            index_info = {
                "name": index["name"],
                "key": dict(index["key"]),
                "unique": index.get("unique", False),
                "sparse": index.get("sparse", False),
                "background": index.get("background", False),
                "partial_filter": index.get("partialFilterExpression"),
                "expire_after": index.get("expireAfterSeconds"),
                "text_weights": index.get("weights"),
                "text_default_language": index.get("default_language"),
                "version": index.get("v")
            }
            if ENABLE_OPAQUE_IDS:
                index_info["opaque_id"] = encode_opaque_id(index["name"])
            indexes.append(index_info)
        
        return {"indexes": indexes, "total": len(indexes)}

    async def create_index(self, db_name, col_name, keys, options=None):
        """Create an index on a collection"""
        logger.debug(f"IndexService.create_index: using db_name='{db_name}', col_name='{col_name}', keys={keys}")
        logger.info(f"Creating index on {db_name}.{col_name} with keys: {keys}")
        
        collection = self.client[db_name][col_name]
        
        # Build index options
        index_options = options or {}
        
        # Set defaults if not provided
        index_options.setdefault("unique", False)
        index_options.setdefault("sparse", False)
        index_options.setdefault("background", True)
        
        # Create index
        index_name = await collection.create_index(keys, **index_options)
        return index_name

    async def drop_index(self, db_name, col_name, index_name):
        """Drop an index from a collection"""
        logger.debug(f"IndexService.drop_index: using db_name='{db_name}', col_name='{col_name}', index_name='{index_name}'")
        logger.warning(f"Dropping index '{index_name}' from {db_name}.{col_name}")
        
        if index_name == "_id_":
            raise ValueError("Cannot drop the _id index")
        
        collection = self.client[db_name][col_name]
        await collection.drop_index(index_name)
        return {"message": f"Index '{index_name}' dropped successfully"}

    async def get_index_info(self, db_name, col_name, index_name):
        """Get detailed information about a specific index"""
        logger.debug(f"IndexService.get_index_info: using db_name='{db_name}', col_name='{col_name}', index_name='{index_name}'")
        logger.debug(f"Getting info for index '{index_name}' on {db_name}.{col_name}")
        
        collection = self.client[db_name][col_name]
        
        for index in await collection.list_indexes():
            if index["name"] == index_name:
                return {
                    "name": index["name"],
                    "key": dict(index["key"]),
                    "unique": index.get("unique", False),
                    "sparse": index.get("sparse", False),
                    "background": index.get("background", False),
                    "partial_filter": index.get("partialFilterExpression"),
                    "expire_after": index.get("expireAfterSeconds"),
                    "text_weights": index.get("weights"),
                    "text_default_language": index.get("default_language"),
                    "version": index.get("v"),
                    "size": index.get("size")
                }
        
        return None

    async def create_text_index(
        self, 
        db_name, 
        col_name, 
        fields, 
        name=None, 
        default_language="english",
        weights=None
    ):
        """Create a text index for full-text search"""
        logger.info(f"Creating text index on {db_name}.{col_name} for fields: {fields}")
        
        collection = self.client[db_name][col_name]
        
        # Build text index keys
        text_keys = [(field, "text") for field in fields]
        
        # Build index options
        index_options = {
            "default_language": default_language
        }
        
        if name:
            index_options["name"] = name
        if weights:
            index_options["weights"] = weights
        
        # Create text index
        index_name = await collection.create_index(text_keys, **index_options)
        return {"index_name": index_name, "message": "Text index created successfully"}

    async def get_index_stats(self, db_name, col_name):
        """Get statistics about all indexes for a collection"""
        logger.debug(f"Getting index statistics for {db_name}.{col_name}")
        
        try:
            # Use indexStats aggregation stage
            pipeline = [{"$indexStats": {}}]
            stats = await self.client[db_name][col_name].aggregate(pipeline).to_list()
            
            # Format the response
            index_stats = []
            for stat in stats:
                index_stats.append({
                    "name": stat["name"],
                    "key": stat["key"],
                    "accesses": stat["accesses"]["ops"],
                    "since": stat["accesses"]["since"]
                })
            
            return {"index_stats": index_stats, "total": len(index_stats)}
        except Exception as e:
            logger.warning(f"Could not get index stats: {e}")
            # Fallback to basic index list
            return self.list_indexes(db_name, col_name)


index_service = IndexService()