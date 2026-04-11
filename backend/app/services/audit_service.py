# SPDX-License-Identifier: MIT
from datetime import datetime

from app.services.base import BaseMongoService


class AuditService(BaseMongoService):
    """Service for logging audit events to MongoDB."""

    def __init__(self):
        super().__init__()
        self._indexes_setup = False

    @property
    def collection(self):
        """Get the audit logs collection, ensuring we use the current client."""
        return self.get_database("mongodhara")["audit_logs"]

    async def _ensure_indexes(self):
        """Ensure indexes are created (called lazily)."""
        if not self._indexes_setup:
            await self._setup_indexes()
            self._indexes_setup = True

    async def _setup_indexes(self):
        """Create necessary indexes for audit_logs collection."""
        try:
            # TTL index for automatic expiration (1 year)
            await self.collection.create_index("timestamp", expireAfterSeconds=365 * 24 * 3600)
            # Indexes for efficient queries
            await self.collection.create_index("user_email")
            await self.collection.create_index("operation")
            await self.collection.create_index([("timestamp", 1), ("user_email", 1)])
        except Exception as e:
            # Log but don't fail if indexes already exist
            print(f"Warning: Could not create audit indexes: {e}")

    async def log_operation(
        self,
        user_email: str,
        operation: str,
        resource: dict,
        details: dict = None,
        status: str = "success",
        error_message: str = None,
        request=None
    ):
        """Log an audit event to the audit_logs collection."""
        # Ensure indexes are set up before logging
        await self._ensure_indexes()
        
        doc = {
            "user_email": user_email,
            "operation": operation,
            "resource": resource,
            "details": details or {},
            "timestamp": datetime.utcnow(),
            "status": status,
            "ip": request.client.host if request and request.client else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
            "error_message": error_message
        }
        await self.collection.insert_one(doc)


# Global instance
audit_service = AuditService()