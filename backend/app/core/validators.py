# SPDX-License-Identifier: MIT
from fastapi import HTTPException


def validate_database_name_for_access(db_name: str) -> None:
    """Validate MongoDB database name for READ/ACCESS operations - permissive for existing data but secure."""
    if not db_name or db_name.strip() == "":
        raise HTTPException(status_code=400, detail="Database name cannot be empty")

    # Check for potentially dangerous characters that could indicate injection attempts
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
    for char_seq in dangerous_chars:
        if char_seq in db_name:
            raise HTTPException(
                status_code=400,
                detail=f"Database name contains invalid characters: {char_seq}"
            )

    # Only check if it's not empty - allow existing databases with other naming


def validate_collection_name_for_access(col_name: str) -> None:
    """Validate MongoDB collection name for READ/ACCESS operations - permissive for existing data."""
    if not col_name or col_name.strip() == "":
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")


def validate_index_name(index_name: str) -> None:
    """Validate MongoDB index name for access operations."""
    if not index_name or index_name.strip() == "":
        raise HTTPException(status_code=400, detail="Index name cannot be empty")
    
    # Check length (reasonable limit)
    if len(index_name.encode("utf-8")) > 128:
        raise HTTPException(
            status_code=400,
            detail="Index name cannot exceed 128 bytes when UTF-8 encoded"
        )
    
    # Check for potentially dangerous characters
    dangerous_chars = ["..", "/", "\\", "\x00", "'", '"', ";"]
    for char_seq in dangerous_chars:
        if char_seq in index_name:
            raise HTTPException(
                status_code=400,
                detail=f"Index name contains invalid characters: {char_seq}"
            )


def validate_email_format(email: str) -> None:
    """Validate email format for admin permission management operations."""
    import re
    
    if not email or email.strip() == "":
        raise HTTPException(status_code=400, detail="Email cannot be empty")
    
    email = email.strip()
    
    # Check length
    if len(email) > 255:
        raise HTTPException(
            status_code=400,
            detail="Email address cannot exceed 255 characters"
        )
    
    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    # Prevent injection attacks
    dangerous_chars = ["'", '"', ";", "<", ">", "\\", "\x00", "\n", "\r"]
    for char in dangerous_chars:
        if char in email:
            raise HTTPException(
                status_code=400,
                detail="Email contains invalid characters"
            )


def validate_database_name_for_access(db_name: str) -> None:
    """Validate MongoDB database name for READ/ACCESS operations - permissive for existing data but secure."""
    if not db_name or db_name.strip() == "":
        raise HTTPException(status_code=400, detail="Database name cannot be empty")

    # Check for potentially dangerous characters that could indicate injection attempts
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
    for char_seq in dangerous_chars:
        if char_seq in db_name:
            raise HTTPException(
                status_code=400,
                detail=f"Database name contains invalid characters: {char_seq}"
            )

    # Only check if it's not empty - allow existing databases with other naming


def validate_collection_name_for_create(col_name: str) -> None:
    """Validate MongoDB collection name for CREATE operations - strict MongoDB naming conventions."""
    if not col_name or col_name.strip() == "":
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")

    col_name = col_name.strip()

    # Check length (MongoDB doesn't have a strict limit, but 120 is reasonable)
    if len(col_name.encode("utf-8")) > 120:
        raise HTTPException(
            status_code=400,
            detail="Collection name cannot exceed 120 bytes when UTF-8 encoded",
        )

    # Cannot start with 'system.' (reserved for MongoDB internal collections)
    if col_name.startswith("system."):
        raise HTTPException(
            status_code=400,
            detail="Collection name cannot start with 'system.' (reserved prefix)",
        )

    # Cannot contain '$' character
    if "$" in col_name:
        raise HTTPException(
            status_code=400, detail="Collection name cannot contain '$' character"
        )

    # Cannot contain spaces
    if " " in col_name:
        raise HTTPException(
            status_code=400, detail="Collection name cannot contain spaces"
        )

    # Cannot contain dots
    if "." in col_name:
        raise HTTPException(
            status_code=400, detail="Collection name cannot contain dots"
        )

    # Cannot contain null character
    if "\x00" in col_name:
        raise HTTPException(
            status_code=400, detail="Collection name cannot contain null character"
        )

    # Cannot be empty string after stripping
    if not col_name:
        raise HTTPException(
            status_code=400, detail="Collection name cannot be empty or only whitespace"
        )


def validate_database_name_for_write(db_name: str) -> None:
    """Validate database name for write operations, blocking system databases."""
    validate_database_name_for_access(db_name)  # Existing checks
    
    system_databases = {"admin", "local", "config", "mongodhara"}
    if db_name in system_databases:
        raise HTTPException(
            status_code=403, 
            detail=f"Operations on system database '{db_name}' are not allowed"
        )
