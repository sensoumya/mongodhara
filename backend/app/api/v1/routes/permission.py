from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from app.core.logger import logger
from app.dependencies.auth import get_current_user, require_role_admin
from app.dependencies.models.permission import (
    PermissionCheck,
    PermissionGroup,
    PermissionGroupCreate,
    PermissionGroupUpdate,
    PermissionResponse,
    UserPermission,
    UserPermissionCreate,
    UserPermissionUpdate,
)
from app.dependencies.models.responses import MessageResponse
from app.services.permission_service import permission_service

router = APIRouter()

# -------------------- Permission Group Management APIs --------------------

@router.post(
    "/admin/groups",
    response_model=PermissionGroup,
    summary="Create permission group",
    tags=["Admin - Permission Groups"],
)
async def create_permission_group(
    background_tasks: BackgroundTasks,
    request: Request,
    group: PermissionGroupCreate,
    user=Depends(require_role_admin)
):
    """Create a new permission group"""
    try:
        return await permission_service.create_permission_group(group, user, request, background_tasks)
    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to create permission group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create permission group")


@router.get(
    "/admin/groups",
    response_model=List[PermissionGroup],
    summary="List all permission groups",
    tags=["Admin - Permission Groups"],
)
async def list_permission_groups(
    skip: int = Query(0, ge=0, description="Number of groups to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of groups to return"),
    user=Depends(require_role_admin)
):
    """List all permission groups with pagination"""
    try:
        return await permission_service.list_permission_groups(skip, limit)
    except Exception as e:
        logger.error(f"Failed to list permission groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list permission groups")


@router.get(
    "/admin/groups/{name}",
    response_model=PermissionGroup,
    summary="Get permission group",
    tags=["Admin - Permission Groups"],
)
async def get_permission_group(name: str, user=Depends(require_role_admin)):
    """Get a specific permission group"""
    try:
        group = await permission_service.get_permission_group(name)
        if not group:
            raise HTTPException(status_code=404, detail=f"No permission group found: {name}")
        return group
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission group {name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get permission group")


@router.put(
    "/admin/groups/{name}",
    response_model=PermissionGroup,
    summary="Update permission group",
    tags=["Admin - Permission Groups"],
)
async def update_permission_group(name: str, update: PermissionGroupUpdate, user=Depends(require_role_admin)):
    """Update a permission group"""
    try:
        group = await permission_service.update_permission_group(name, update)
        if not group:
            raise HTTPException(status_code=404, detail=f"No permission group found: {name}")
        return group
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update permission group {name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update permission group")


@router.delete(
    "/admin/groups/{name}",
    summary="Delete permission group",
    tags=["Admin - Permission Groups"],
    response_model=MessageResponse,
)
async def delete_permission_group(name: str, user=Depends(require_role_admin)):
    """Delete a permission group"""
    try:
        deleted = await permission_service.delete_permission_group(name)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No permission group found: {name}")
        return {"message": f"Permission group deleted: {name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete permission group {name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete permission group")

# -------------------- User Permission Management APIs --------------------

@router.post(
    "/admin/users",
    response_model=UserPermission,
    summary="Create user permissions",
    tags=["Admin - User Permissions"],
)
async def create_user_permission(
    background_tasks: BackgroundTasks,
    request: Request,
    permission: UserPermissionCreate,
    user=Depends(require_role_admin)
):
    """Create permissions for a user"""
    try:
        return await permission_service.create_user_permission(permission, user, request, background_tasks)
    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to create user permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create user permission")


@router.get(
    "/admin/users",
    response_model=List[UserPermission],
    summary="List all user permissions",
    tags=["Admin - User Permissions"],
)
async def list_user_permissions(
    skip: int = Query(0, ge=0, description="Number of permissions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of permissions to return"),
    user=Depends(require_role_admin)
):
    """List all user permissions with pagination"""
    try:
        return await permission_service.list_user_permissions(skip, limit)
    except Exception as e:
        logger.error(f"Failed to list user permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list user permissions")


@router.get(
    "/admin/users/{user_email}",
    response_model=UserPermission,
    summary="Get user permissions",
    tags=["Admin - User Permissions"],
)
async def get_user_permission(user_email: str, user=Depends(require_role_admin)):
    """Get permissions for a specific user"""
    try:
        permission = await permission_service.get_user_permission(user_email)
        if not permission:
            raise HTTPException(status_code=404, detail=f"No permissions found for user: {user_email}")
        return permission
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user permission for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get user permission")


@router.put(
    "/admin/users/{user_email}",
    response_model=UserPermission,
    summary="Update user permissions",
    tags=["Admin - User Permissions"],
)
async def update_user_permission(user_email: str, update: UserPermissionUpdate, user=Depends(require_role_admin)):
    """Update permissions for a user"""
    try:
        # Check if user being deactivated or removed from admin is the only admin
        needs_admin_check = False
        
        if update.isActive is False:
            needs_admin_check = True
        elif update.role is not None and update.role != "admin":
            # Check if user is currently an admin and being demoted
            user_perm = await permission_service.get_user_permission(user_email)
            if user_perm and user_perm.role == "admin":
                needs_admin_check = True
        elif update.groups is not None and "admin" not in update.groups:
            # Check if user is currently in admin group and being removed
            user_perm = await permission_service.get_user_permission(user_email)
            if user_perm and "admin" in user_perm.groups:
                needs_admin_check = True
        
        if needs_admin_check:
            # Count active admin users (excluding the one being modified)
            # Count both role="admin" and group="admin" users
            admin_count = await permission_service.user_permissions.count_documents({
                "$or": [
                    {"role": "admin"},
                    {"groups": "admin"}
                ],
                "isActive": True,
                "email": {"$ne": user_email}
            })
            if admin_count == 0:
                action = "deactivate" if update.isActive is False else "remove from admin group"
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot {action} the last active admin user. At least one admin user must remain."
                )
        
        permission = await permission_service.update_user_permission(user_email, update)
        if not permission:
            raise HTTPException(status_code=404, detail=f"No permissions found for user: {user_email}")
        return permission
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user permission for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user permission")


@router.delete(
    "/admin/users/{user_email}",
    summary="Delete user permissions",
    tags=["Admin - User Permissions"],
    response_model=MessageResponse,
)
async def delete_user_permission(user_email: str, user=Depends(require_role_admin)):
    """Delete permissions for a user"""
    try:
        # Check if user being deleted is an admin and if they're the only admin
        user_perm = await permission_service.get_user_permission(user_email)
        if user_perm and (user_perm.role == "admin" or "admin" in user_perm.groups):
            # Count active admin users (excluding the one being deleted)
            # Count both role="admin" and group="admin" users
            admin_count = await permission_service.user_permissions.count_documents({
                "$or": [
                    {"role": "admin"},
                    {"groups": "admin"}
                ],
                "isActive": True,
                "email": {"$ne": user_email}
            })
            if admin_count == 0:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete the last active admin user. At least one admin user must remain."
                )
        
        deleted = await permission_service.delete_user_permission(user_email)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No permissions found for user: {user_email}")
        return {"message": f"Permissions deleted for user: {user_email}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user permission for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete user permission")


@router.post(
    "/permissions/check",
    response_model=PermissionResponse,
    summary="Check user permissions",
    tags=["Permission Management"],
)
async def check_permission(
    check: Optional[PermissionCheck] = None,
    user=Depends(get_current_user)
):
    """Check if a user has permission for a specific operation on a database, or get user role if no params"""
    try:
        user_email = user["email"]
        
        # Validate that if check is provided, both database and operation are present
        if check:
            if (check.database is None) != (check.operation is None):
                raise HTTPException(
                    status_code=400,
                    detail="Both database and operation must be provided together, or neither"
                )
        
        database = check.database if check else None
        operation = check.operation if check else None
        
        return await permission_service.check_permission(user_email, database, operation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check permission")