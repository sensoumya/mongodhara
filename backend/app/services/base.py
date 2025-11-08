import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import MONGO_URI
from app.core.logger import logger


class BaseMongoService:
    """Base MongoDB service with shared connection and utilities."""
    
    def __init__(self):
        self._client = None
        self._loop = None
    
    @property
    def client(self):
        """Get the MongoDB client with optimized connection pooling."""
        current_loop = asyncio.get_event_loop()
        if self._client is None or self._loop is not current_loop:
            if self._client is not None:
                logger.debug("Event loop changed, recreating MongoDB client")
            
            # Optimized connection pool for 100MB max file transfers
            self._client = AsyncIOMotorClient(
                MONGO_URI,
                maxPoolSize=25,           # Max 25 connections (handles 20 RPS uploads)
                minPoolSize=5,            # Keep 5 warm connections
                maxIdleTimeMS=30000,      # 30s idle timeout
                serverSelectionTimeoutMS=5000,    # 5s server selection timeout
                connectTimeoutMS=10000,   # 10s connection timeout
                socketTimeoutMS=120000,   # 2 minutes (matches worker timeout)
                waitQueueTimeoutMS=10000  # 10s wait for connection from pool
            )
            self._loop = current_loop
            logger.debug("MongoDB client initialized with optimized connection pool (maxPoolSize=25, minPoolSize=5)")
        return self._client
    
    def get_database(self, db_name: str):
        """Get a database instance."""
        return self.client[db_name]
    
    def get_collection(self, db_name: str, col_name: str):
        """Get a collection instance."""
        return self.client[db_name][col_name]