# SPDX-License-Identifier: MIT
import fnmatch
import re
from datetime import datetime
from typing import Dict, List, Optional

from app.core.config import ENABLE_AUDIT_LOGGING
from app.core.logger import logger
from app.dependencies.models.permission import (
    Grant,
    GroupGrant,
    PermissionCheck,
    PermissionGroup,
    PermissionGroupCreate,
    PermissionGroupUpdate,
    PermissionResponse,
    UserPermission,
    UserPermissionCreate,
    UserPermissionUpdate,
)
from app.services.audit_service import audit_service
from app.services.base import BaseMongoService


class PermissionService(BaseMongoService):
    """Service for managing group-based permissions with custom overrides"""

    def __init__(self):
        super().__init__()
        self.permission_groups = self.get_database("mongodhara")["permission_groups"]
        self.user_permissions = self.get_database("mongodhara")["user_permissions"]

    # ============================================================================
    # PERMISSION GROUP MANAGEMENT
    # ============================================================================

    async def create_permission_group(self, group: PermissionGroupCreate, user=None, request=None, background_tasks=None) -> PermissionGroup:
        """Create new permission group"""
        logger.info(f"Creating permission group: {group.name}")

        # Check if group already exists
        existing = await self.permission_groups.find_one({"name": group.name})
        if existing:
            if ENABLE_AUDIT_LOGGING and user:
                if background_tasks:
                    background_tasks.add_task(
                        audit_service.log_operation,
                        user_email=user.get("email"),
                        operation="create_permission_group",
                        resource={"type": "permission_group", "name": group.name},
                        status="failure",
                        error_message="Permission group already exists",
                        request=request
                    )
                else:
                    await audit_service.log_operation(
                        user_email=user.get("email"),
                        operation="create_permission_group",
                        resource={"type": "permission_group", "name": group.name},
                        status="failure",
                        error_message="Permission group already exists",
                        request=request
                    )
            raise ValueError(f"Permission group already exists: {group.name}")

        # Create group document
        group_doc = PermissionGroup(
            name=group.name,
            description=group.description,
            grants=group.grants
        )

        # Insert into database
        await self.permission_groups.insert_one(group_doc.dict())

        if ENABLE_AUDIT_LOGGING and user:
            if background_tasks:
                background_tasks.add_task(
                    audit_service.log_operation,
                    user_email=user.get("email"),
                    operation="create_permission_group",
                    resource={"type": "permission_group", "name": group.name},
                    details={"description": group.description, "grants": {db: g.dict() for db, g in group.grants.items()}},
                    request=request
                )
            else:
                await audit_service.log_operation(
                    user_email=user.get("email"),
                    operation="create_permission_group",
                    resource={"type": "permission_group", "name": group.name},
                    details={"description": group.description, "grants": {db: g.dict() for db, g in group.grants.items()}},
                    request=request
                )

        logger.info(f"Created permission group: {group.name}")
        return group_doc

    async def get_permission_group(self, name: str) -> Optional[PermissionGroup]:
        """Get permission group by name"""
        doc = await self.permission_groups.find_one({"name": name})
        if doc:
            return PermissionGroup(**doc)
        return None

    async def list_permission_groups(self, skip: int = 0, limit: int = 100) -> List[PermissionGroup]:
        """List all permission groups"""
        docs = await self.permission_groups.find().skip(skip).limit(limit).to_list(length=None)
        return [PermissionGroup(**doc) for doc in docs]

    async def update_permission_group(self, name: str, update: PermissionGroupUpdate) -> Optional[PermissionGroup]:
        """Update permission group"""
        logger.info(f"Updating permission group: {name}")

        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        if update.description is not None:
            update_doc["description"] = update.description
        if update.grants is not None:
            update_doc["grants"] = {db: g.dict() for db, g in update.grants.items()}

        # Update in database
        result = await self.permission_groups.update_one(
            {"name": name},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return None

        # Return updated group
        return await self.get_permission_group(name)

    async def delete_permission_group(self, name: str) -> bool:
        """Delete permission group"""
        logger.info(f"Deleting permission group: {name}")

        result = await self.permission_groups.delete_one({"name": name})
        return result.deleted_count > 0

    # ============================================================================
    # USER PERMISSION MANAGEMENT
    # ============================================================================

    async def create_user_permission(self, permission: UserPermissionCreate, user=None, request=None, background_tasks=None) -> UserPermission:
        """Create new user permission assignment"""
        logger.info(f"Creating user permission for: {permission.email}")

        # Check if permission already exists
        existing = await self.user_permissions.find_one({"email": permission.email.lower()})
        if existing:
            if ENABLE_AUDIT_LOGGING and user:
                if background_tasks:
                    background_tasks.add_task(
                        audit_service.log_operation,
                        user_email=user.get("email"),
                        operation="create_user_permission",
                        resource={"type": "user_permission", "email": permission.email},
                        status="failure",
                        error_message="User permission already exists",
                        request=request
                    )
                else:
                    await audit_service.log_operation(
                        user_email=user.get("email"),
                        operation="create_user_permission",
                        resource={"type": "user_permission", "email": permission.email},
                        status="failure",
                        error_message="User permission already exists",
                        request=request
                    )
            raise ValueError(f"User permission already exists for: {permission.email}")

        # Create permission document
        perm_doc = UserPermission(
            email=permission.email,
            role=permission.role,
            groups=permission.groups
        )

        # Insert into database
        await self.user_permissions.insert_one(perm_doc.dict())

        if ENABLE_AUDIT_LOGGING and user:
            if background_tasks:
                background_tasks.add_task(
                    audit_service.log_operation,
                    user_email=user.get("email"),
                    operation="create_user_permission",
                    resource={"type": "user_permission", "email": permission.email},
                    details={"groups": permission.groups},
                    request=request
                )
            else:
                await audit_service.log_operation(
                    user_email=user.get("email"),
                    operation="create_user_permission",
                    resource={"type": "user_permission", "email": permission.email},
                    details={"groups": permission.groups},
                    request=request
                )

        logger.info(f"Created user permission for: {permission.email}")
        return perm_doc

    async def get_user_permission(self, email: str) -> Optional[UserPermission]:
        """Get user permission by email"""
        doc = await self.user_permissions.find_one({
            "email": email.lower()
        })
        if doc:
            return UserPermission(**doc)
        return None

    async def list_user_permissions(self, skip: int = 0, limit: int = 100) -> List[UserPermission]:
        """List all user permissions"""
        docs = await self.user_permissions.find({}).skip(skip).limit(limit).to_list(length=None)
        return [UserPermission(**doc) for doc in docs]

    async def update_user_permission(self, email: str, update: UserPermissionUpdate) -> Optional[UserPermission]:
        """Update user permission"""
        logger.info(f"Updating user permission for: {email}")

        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        if update.role is not None:
            update_doc["role"] = update.role
        if update.groups is not None:
            update_doc["groups"] = update.groups
        if update.custom_grants is not None:
            update_doc["custom_grants"] = {db: g.dict() for db, g in update.custom_grants.items()}
        if update.isActive is not None:
            update_doc["isActive"] = update.isActive

        # Update in database
        result = await self.user_permissions.update_one(
            {"email": email.lower()},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return None

        # Return updated permission
        return await self.get_user_permission(email)

    async def delete_user_permission(self, email: str) -> bool:
        """Delete user permission (hard delete)"""
        logger.info(f"Deleting user permission for: {email}")

        result = await self.user_permissions.delete_one(
            {"email": email.lower()}
        )
        return result.deleted_count > 0

    # ============================================================================
    # PERMISSION CHECKING (CORE LOGIC)
    # ============================================================================

    async def check_permission(self, user_email: str, database: Optional[str] = None, operation: Optional[str] = None) -> PermissionResponse:
        """Check if user has permission for operation on database"""
        user_perm = await self.get_user_permission(user_email)

        if not user_perm:
            return PermissionResponse(
                allowed=False,
                user_email=user_email,
                role="user",
                database=database,
                operation=operation,
                reason="No permissions found for user"
            )

        # If no database/operation specified, return user info
        if database is None or operation is None:
            return PermissionResponse(
                allowed=True,  # User exists and is active
                user_email=user_email,
                role=user_perm.role,
                database=database,
                operation=operation,
                reason="User permissions retrieved"
            )

        # Check if user has admin role - grant all permissions
        if user_perm.role == "admin":
            return PermissionResponse(
                allowed=True,
                user_email=user_email,
                role=user_perm.role,
                database=database,
                operation=operation,
                reason="User has admin role"
            )

        # For non-admin users, check permissions as usual
        # Resolve final grants by merging groups + custom grants
        final_grants = await self._resolve_user_grants(user_perm)

        # Map operation to grant attribute
        op_map = {"read": "r", "write": "w", "delete": "d", "admin": "a"}
        grant_attr = op_map.get(operation)
        if not grant_attr:
            return PermissionResponse(
                allowed=False,
                user_email=user_email,
                role=user_perm.role,
                database=database,
                operation=operation,
                reason=f"Unknown operation: {operation}"
            )

        # Check wildcard admin (super admin)
        if "*" in final_grants and getattr(final_grants["*"], grant_attr):
            return PermissionResponse(
                allowed=True,
                user_email=user_email,
                role=user_perm.role,
                database=database,
                operation=operation
            )

        # Check database-specific grant
        if database in final_grants:
            has_perm = getattr(final_grants[database], grant_attr)
            if has_perm:
                return PermissionResponse(
                    allowed=True,
                    user_email=user_email,
                    role=user_perm.role,
                    database=database,
                    operation=operation
                )

        # Check pattern-based grants
        for db_pattern, grant in final_grants.items():
            if fnmatch.fnmatch(database, db_pattern):
                has_perm = getattr(grant, grant_attr)
                if has_perm:
                    return PermissionResponse(
                        allowed=True,
                        user_email=user_email,
                        role=user_perm.role,
                        database=database,
                        operation=operation
                    )

        # Permission denied
        accessible_dbs = [
            db for db, grant in final_grants.items()
            if getattr(grant, grant_attr)
        ]
        return PermissionResponse(
            allowed=False,
            user_email=user_email,
            role=user_perm.role,
            database=database,
            operation=operation,
            reason=f"No '{operation}' permission on database '{database}'. Accessible databases: {accessible_dbs}"
        )

    async def _resolve_user_grants(self, user_perm: UserPermission) -> Dict[str, Grant]:
        """Resolve final grants by merging all groups + custom grants"""
        final_grants = {}

        # Load all assigned groups
        if user_perm.groups:
            groups = await self.permission_groups.find({
                "name": {"$in": user_perm.groups}
            }).to_list(length=None)

            # Merge group permissions (OR logic - most permissive wins)
            for group_doc in groups:
                for db, grant_dict in group_doc["grants"].items():
                    # Groups now use GroupGrant (no 'a' permission)
                    group_grant = GroupGrant(**grant_dict)
                    if db not in final_grants:
                        # Convert GroupGrant to Grant for final result
                        final_grants[db] = Grant(r=group_grant.r, w=group_grant.w, d=group_grant.d, a=False)
                    else:
                        # Merge with OR - if any group grants permission, user gets it
                        final_grants[db].r = final_grants[db].r or group_grant.r
                        final_grants[db].w = final_grants[db].w or group_grant.w
                        final_grants[db].d = final_grants[db].d or group_grant.d
                        # 'a' permission is never granted by groups

        # Apply custom overrides (highest priority)
        for db, grant in user_perm.custom_grants.items():
            final_grants[db] = grant

        return final_grants

    # ============================================================================
    # LEGACY COMPATIBILITY METHODS
    # ============================================================================

    def create_permission(self, permission, user=None, request=None, background_tasks=None):
        """Legacy method - convert to new format"""
        # This would need conversion logic from old format to new
        raise NotImplementedError("Use create_user_permission() instead")

    def get_permission(self, user_email: str):
        """Legacy method - convert to async"""
        # This would need to be converted to async in calling code
        raise NotImplementedError("Use get_user_permission() instead")

    def list_permissions(self, skip: int = 0, limit: int = 100):
        """Legacy method - convert to async"""
        raise NotImplementedError("Use list_user_permissions() instead")

    def update_permission(self, user_email: str, update):
        """Legacy method - convert to async"""
        raise NotImplementedError("Use update_user_permission() instead")

    def delete_permission(self, user_email: str):
        """Legacy method - convert to async"""
        raise NotImplementedError("Use delete_user_permission() instead")

    def get_user_permissions_dict(self, user_email: str):
        """Legacy method - convert to async"""
        raise NotImplementedError("Use get_user_permission() instead")

    def _matches_database_pattern(self, database: str, patterns: List[str]) -> bool:
        """Legacy method - kept for compatibility but not used in new system"""
        for pattern in patterns:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace('*', '.*')
            if re.match(f"^{regex_pattern}$", database):
                return True
        return False


# Global permission service instance
permission_service = PermissionService()