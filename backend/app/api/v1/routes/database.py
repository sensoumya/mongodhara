# SPDX-License-Identifier: MIT
import fnmatch
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pymongo.errors import OperationFailure

from app.core.config import ENABLE_AUTHZ, ENABLE_OPAQUE_IDS
from app.core.logger import logger
from app.core.validators import validate_database_name_for_write
from app.dependencies.auth import require_read, require_role_admin
from app.dependencies.models.responses import (
    DatabaseListResponse,
    DatabaseStatsListResponse,
    MessageResponse,
)
from app.services.database import database_service as mongo
from app.services.opaque_id_service import encode_opaque_id

router = APIRouter()

@router.get(
    "/db",
    summary="List databases with pagination and filter",
    tags=["Database Management"],
    response_model=DatabaseListResponse,
)
async def list_databases(
    search: Optional[str] = Query(
        None, description="Search databases whose name contains this string"
    ),
    sort: Optional[str] = Query(
        "asc", pattern="^(asc|desc)$", description="Sort direction"
    ),
    sort_field: Optional[str] = Query(
        None, description="(Unused for now) Field to sort by"
    ),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(
        10, le=100, description="Number of databases per page (max 100)"
    ),
    user = Depends(require_read),  # RBAC: Require read permission
):
    try:
        # Get all databases from MongoDB
        all_databases = await mongo.client.list_database_names()

        # Filter databases based on user permissions
        from app.services.permission_service import permission_service

        if not ENABLE_AUTHZ:
            # When authorization is disabled, show all databases
            filtered_databases = all_databases
            filtered_by_permissions = False
        else:
            # Get user permissions and resolved grants in one call
            user_perm, final_grants = await permission_service.get_resolved_grants(user["email"])

            if not user_perm:
                # No permissions found, return empty list
                filtered_databases = []
                filtered_by_permissions = True
            elif user_perm.role == "admin":
                # Admin role users can see all databases
                filtered_databases = all_databases
                filtered_by_permissions = False
            else:
                # Regular users only see databases they have permissions for
                # Optimize: Check wildcard first to avoid iterating through all databases
                if "*" in final_grants and final_grants["*"].r:
                    # User has wildcard read access - show all databases
                    filtered_databases = all_databases
                    filtered_by_permissions = False
                else:
                    # Pre-separate exact grants from patterns for performance
                    exact_grants = {k: v for k, v in final_grants.items() if '*' not in k and '?' not in k}
                    pattern_grants = {k: v for k, v in final_grants.items() if '*' in k or '?' in k}
                    
                    filtered_databases = []
                    for db_name in all_databases:
                        # Check exact match first (O(1) hash lookup)
                        if db_name in exact_grants and exact_grants[db_name].r:
                            filtered_databases.append(db_name)
                        # Only check patterns if no exact match found
                        elif pattern_grants:
                            for pattern, grant in pattern_grants.items():
                                if grant.r and fnmatch.fnmatch(db_name, pattern):
                                    filtered_databases.append(db_name)
                                    break
                    filtered_by_permissions = True
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            filtered_databases = [db for db in filtered_databases if search_lower in db.lower()]
        
        # Apply sorting
        filtered_databases.sort(reverse=(sort == "desc"))
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        # Build response with opaque IDs if enabled
        databases = []
        for db_name in filtered_databases[start:end]:
            db_info = {"name": db_name}
            if ENABLE_OPAQUE_IDS:
                db_info["opaque_id"] = encode_opaque_id(db_name)
            databases.append(db_info)

        return {
            "databases": databases,
            "total": len(filtered_databases),
            "page": page,
            "page_size": page_size,
            "filtered_by_permissions": filtered_by_permissions
        }
    except Exception as e:
        logger.error(f"Failed to list databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list databases")


@router.delete("/db/{db}", summary="Delete a database", tags=["Database Management"], response_model=MessageResponse)
async def delete_database(db: str, background_tasks: BackgroundTasks, request: Request, user = Depends(require_role_admin)):  # RBAC: Require admin role
    # NOTE: Validation removed - now handled by OpaqueIDDecodingMiddleware
    # The db parameter is already decoded and validated
    validate_database_name_for_write(db)

    try:
        await mongo.delete_database(db, user, request, background_tasks)
        return {"message": f"Database '{db}' deleted successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except OperationFailure as e:
        # Handle MongoDB specific errors with user-friendly messages
        error_msg = str(e)
        if "prohibited" in error_msg.lower():
            logger.error(f"Attempted to delete prohibited database '{db}': {e}")
            raise HTTPException(
                status_code=403,
                detail="Unauthorized action!",
            )
        elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        else:
            logger.error(f"MongoDB operation failed for database '{db}': {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to delete database '{db}': {e.details.get('errmsg', str(e))}",
            )
    except Exception as e:
        logger.error(f"Failed to delete database '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete database")


@router.get(
    "/db/{db}/stats",
    summary="Get database statistics",
    tags=["Database Management"],
    response_model=DatabaseStatsListResponse,
)
async def get_database_stats(db: str, user = Depends(require_read),  # RBAC: Require read permission
):
    """Get detailed statistics for a database"""
    # NOTE: Validation removed - now handled by OpaqueIDDecodingMiddleware
    try:
        stats = await mongo.get_database_stats(db)
        return stats
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get database stats for '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get database statistics")