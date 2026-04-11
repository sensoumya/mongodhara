# SPDX-License-Identifier: MIT
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
)
from pymongo.errors import CollectionInvalid, OperationFailure

from app.core.exceptions import CollectionExistsError
from app.core.logger import logger
from app.core.validators import validate_database_name_for_write
from app.dependencies.auth import get_current_user, require_admin_db, require_read_db
from app.dependencies.models.responses import (
    CollectionListResponse,
    CollectionStatsResponse,
    MessageResponse,
)
from app.services.collection import collection_service as mongo
from app.services.permission_service import permission_service

router=APIRouter()

@router.get(
    "/db/{db}/col",
    summary="List collections with pagination and filter",
    tags=["Collection Management"],
    response_model=CollectionListResponse,
)
async def list_collections(
    db: str,
    search: Optional[str] = Query(None, description="Search collection name contains"),
    sort: Optional[str] = Query(
        "asc", pattern="^(asc|desc)$", description="Sort direction"
    ),
    sort_field: Optional[str] = Query(
        None, description="(Unused for now) Field to sort by"
    ),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(
        10, le=100, description="Number of collections per page (max 100)"
    ),
    user = Depends(require_read_db("db")),  # RBAC: Require read permission for database
):
    # NOTE: Validation removed - now handled by OpaqueIDDecodingMiddleware

    try:
        return await mongo.list_collections(
            db, search, sort, page, page_size, sort_field, sort_order
        )
    except Exception as e:
        logger.error(f"Failed to list collections for DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list collections")


@router.post(
    "/db/col",
    summary="Create a new collection",
    tags=["Collection Management"],
    response_model=MessageResponse,
)
async def create_collection(
    background_tasks: BackgroundTasks,
    request: Request,
    body: dict = Body(..., examples=[{"db": "my_database", "name": "my_collection"}]),
    user = Depends(get_current_user)  # Get user first, check permissions inside function
):
    db = body.get("db")
    if not db:
        raise HTTPException(status_code=400, detail="Database name is required")
    
    # Check permissions based on whether database exists
    from app.core.config import ENABLE_AUTHZ
    if ENABLE_AUTHZ:
        # Check if database already exists
        existing_databases = await mongo.client.list_database_names()
        db_exists = db in existing_databases
        
        if not db_exists:
            # New database creation - require admin role
            user_permissions = await permission_service.get_user_permission(user["email"])
            if not user_permissions or user_permissions.role != "admin":
                raise HTTPException(status_code=403, detail="Unauthorized action!")
        else:
            # Existing database - check write permission
            permission_check = await permission_service.check_permission(
                user_email=user["email"],
                database=db,
                operation="write"
            )
            if not permission_check.allowed:
                raise HTTPException(status_code=403, detail="Unauthorized action!")
    
    validate_database_name_for_write(db)
    
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required")

    # NOTE: db validation removed - handled by middleware if opaque ID
    # For creation, db comes from body (not path), so not encrypted

    # NOTE: Collection name validation removed - now handled by OpaqueIDDecodingMiddleware

    try:
        await mongo.create_collection(db, name, user, request, background_tasks)
        return {"message": f"Collection '{name}' created successfully in DB '{db}'"}
    except CollectionExistsError as e:
        logger.error(f"Collection '{name}' already exists in DB '{db}': {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Collection '{name}' already exists in database '{db}'",
        )
    except CollectionInvalid as e:
        # Handle collection already exists or validation errors
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            logger.error(f"Collection '{name}' already exists in DB '{db}': {e}")
            raise HTTPException(
                status_code=409,
                detail=f"Collection '{name}' already exists in database '{db}'",
            )
        else:
            logger.error(f"Collection validation error for '{name}' in DB '{db}': {e}")
            raise HTTPException(
                status_code=400, detail=f"Invalid collection name '{name}': {str(e)}"
            )
    except OperationFailure as e:
        # Handle MongoDB specific errors (collection existence is handled by CollectionInvalid)
        error_msg = str(e)
        if (
            "database does not exist" in error_msg.lower()
            or "not found" in error_msg.lower()
        ):
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        elif "invalid" in error_msg.lower() and "name" in error_msg.lower():
            logger.error(f"Invalid collection name '{name}': {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid collection name '{name}': {e.details.get('errmsg', str(e))}",
            )
        else:
            logger.error(
                f"MongoDB operation failed for collection creation '{name}' in DB '{db}': {e}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create collection '{name}': {e.details.get('errmsg', str(e))}",
            )
    except Exception as e:
        logger.error(
            f"Failed to create collection '{name}' in DB '{db}': {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to create collection")


@router.delete(
    "/db/{db}/col/{col}", summary="Delete a collection", tags=["Collection Management"], response_model=MessageResponse
)
async def delete_collection(db: str, col: str, user = Depends(require_admin_db("db"))):  # RBAC: Require admin permission
    # Validate database name for write operations
    validate_database_name_for_write(db)
    # NOTE: Collection validation removed - now handled by OpaqueIDDecodingMiddleware

    try:
        await mongo.delete_collection(db, col)
        return {"message": f"Collection '{col}' deleted successfully from DB '{db}'"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except OperationFailure as e:
        # Handle MongoDB specific errors
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"Collection '{col}' not found in DB '{db}': {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{col}' not found in database '{db}'",
            )
        elif "database does not exist" in error_msg.lower():
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        else:
            logger.error(
                f"MongoDB operation failed for collection deletion '{col}' in DB '{db}': {e}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to delete collection '{col}': {e.details.get('errmsg', str(e))}",
            )
    except Exception as e:
        logger.error(
            f"Failed to delete collection '{col}' from DB '{db}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete collection '{col}' from DB '{db}'",
        )


@router.get(
    "/db/{db}/col/{col}/stats",
    summary="Get collection statistics",
    tags=["Collection Management"],
    response_model=CollectionStatsResponse,
)
async def get_collection_stats(db: str, col: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    """Get detailed statistics for a collection"""
    # NOTE: Validation removed - now handled by OpaqueIDDecodingMiddleware

    try:
        stats = await mongo.get_collection_stats(db, col)
        return stats
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get collection stats for '{col}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get collection statistics")

