# SPDX-License-Identifier: MIT
from typing import Any, Dict

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from app.core.config import (
    AUTH_EMAIL_HEADER,
    ENABLE_AUTHZ,
)
from app.core.logger import logger
from app.services.permission_service import permission_service

# Security scheme for documentation
oauth_email = APIKeyHeader(
    name=AUTH_EMAIL_HEADER,
    description="User email from OAuth proxy authentication (required for protected endpoints)"
)


def get_current_user(
    request: Request
) -> Dict[str, Any]:
    """Extract user information from OAuth proxy headers"""
    
    # If authorization is disabled, return anonymous user
    if not ENABLE_AUTHZ:
        return {
            "username": "anonymous",
            "email": "anonymous@example.com",
            "groups": []
        }
    
    # Check for required authentication header
    email_from_header = request.headers.get(AUTH_EMAIL_HEADER)
    if not email_from_header:
        logger.warning(f"Missing {AUTH_EMAIL_HEADER} header")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing email header."
        )

    user_info = {
        "email": email_from_header,
    }
    
    logger.debug(f"Auth.get_current_user: authenticated user '{user_info['email']}'")
    return user_info


def require_permission(operation: str, database_param: str = None):
    """
    Dependency factory to check user permissions

    Args:
        operation: The operation to check (read, write, delete, admin)
        database_param: Path parameter name for database (e.g., 'db', 'database')
    """

    async def permission_checker(
        request: Request,
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Check if user has permission for the operation"""

        # Check if authorization is enabled
        if not ENABLE_AUTHZ:
            return user

        # Extract database name from path parameters
        # NOTE: If opaque IDs are enabled, the value is already decoded by middleware
        database = None
        if database_param:
            database = request.path_params.get(database_param)
            if not database:
                # Try to extract from path
                path_parts = request.url.path.strip('/').split('/')
                try:
                    db_index = path_parts.index('db') + 1
                    database = path_parts[db_index]
                except (ValueError, IndexError):
                    database = None
            if not database:
                # Try to extract from request body
                try:
                    body = await request.json()
                    database = body.get(database_param)
                except Exception:
                    # If body parsing fails, continue without database
                    pass
        else:
            # For routes without database parameter, allow if user has any permissions
            database = "*"

        # NOTE: Validation removed - now handled by OpaqueIDDecodingMiddleware
        # The middleware validates and decodes BEFORE this dependency runs
        # Database name here is already decoded and validated

        if database and database != "*":
            logger.debug(f"Auth.require_permission: checking access for user '{user['email']}' on database '{database}' for operation '{operation}'")

        if not database or database == "*":
            logger.debug(f"Auth.require_permission: checking wildcard permissions for user '{user['email']}' (no specific database)")
            # Check if user has admin role or any permissions at all
            user_perms = await permission_service.get_user_permission(user["email"])
            if user_perms and user_perms.role == "admin":
                # Admin role has access to everything
                return user
            if not user_perms or not user_perms.groups:
                logger.warning(f"User {user['email']} has no permissions")
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized action!"
                )
            return user

        # Check specific permission
        result = await permission_service.check_permission(
            user_email=user["email"],
            database=database,
            operation=operation
        )
        logger.debug(f"Auth.require_permission: permission check result - allowed={result.allowed}, reason='{result.reason}'")

        if not result.allowed:
            logger.warning(f"Permission denied: {result.reason}")
            raise HTTPException(
                status_code=403,
                detail="Unauthorized action!"
            )

        logger.debug(f"Permission granted: {user['email']} can {operation}")
        return user

    return permission_checker


# Convenience dependencies for common operations
require_read = require_permission("read")
require_write = require_permission("write")
require_delete = require_permission("delete")
require_admin = require_permission("admin")

async def require_role_admin(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if user has admin role"""
    # Check if authorization is enabled
    if not ENABLE_AUTHZ:
        logger.debug("Auth.require_role_admin: authorization disabled - allowing access")
        return user
    
    logger.debug(f"Auth.require_role_admin: checking admin access for user '{user['email']}'")
    
    # Get user permissions
    permission = await permission_service.get_user_permission(user["email"])
    if not permission:
        logger.warning(f"User {user['email']} has no permissions configured")
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action!"
        )
    
    # Check if user has admin role - grants full access regardless of groups
    if permission.role == "admin":
        logger.debug(f"Auth.require_role_admin: user '{user['email']}' has admin role")
        logger.info(f"Admin role access granted for user: {user['email']}")
        return user
    
    # For non-admin role users, check if they belong to admin group
    logger.debug(f"Auth.require_role_admin: user '{user['email']}' has groups '{permission.groups}'")
    
    if "admin" not in permission.groups:
        logger.warning(f"User {user['email']} does not have admin role or admin group (role: {permission.role}, groups: {permission.groups})")
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action!"
        )
    
    logger.debug(f"Auth.require_role_admin: admin group access granted for user '{user['email']}'")
    logger.info(f"Admin group access granted for user: {user['email']}")
    return user

# Dependencies that specify database parameter
def require_read_db(db_param: str):
    return require_permission("read", db_param)

def require_write_db(db_param: str):
    return require_permission("write", db_param)

def require_delete_db(db_param: str):
    return require_permission("delete", db_param)

def require_admin_db(db_param: str):
    return require_permission("admin", db_param)