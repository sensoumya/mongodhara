class DatabaseExistsError(Exception):
    """Custom exception for database already exists scenarios"""
    pass


class CollectionExistsError(Exception):
    """Custom exception for collection already exists scenarios"""
    pass


class InvalidOpaqueIDError(Exception):
    """Custom exception for invalid or tampered opaque IDs"""
    pass
