# SPDX-License-Identifier: MIT
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class Grant(BaseModel):
    """Permission grant for a database (r=read, w=write, d=delete, a=admin)"""
    r: bool = False
    w: bool = False
    d: bool = False
    a: bool = False


class GroupGrant(BaseModel):
    """Permission grant for groups (r=read, w=write, d=delete - no admin)"""
    r: bool = False
    w: bool = False
    d: bool = False


class PermissionGroup(BaseModel):
    """Reusable permission template (role)"""
    name: str = Field(..., description="Group name")
    description: str = Field(..., description="Group description")
    grants: Dict[str, GroupGrant] = Field(..., description="Database-specific grants")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserPermission(BaseModel):
    """User permission assignment to groups with optional overrides"""
    email: EmailStr = Field(..., description="User email address")
    role: str = Field(default="user", description="User role: 'admin' for full access, 'user' for group-based access")
    groups: List[str] = Field(..., description="Assigned permission groups")
    custom_grants: Dict[str, Grant] = Field(default_factory=dict, description="Custom database grants (overrides)")
    isActive: bool = Field(default=True, description="Whether user is active")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        populate_by_name = True

    @property
    def is_active(self) -> bool:
        return self.isActive

    @is_active.setter
    def is_active(self, value: bool):
        self.isActive = value


class PermissionGroupCreate(BaseModel):
    """Model for creating permission groups"""
    name: str = Field(..., description="Group name")
    description: str = Field(..., description="Group description")
    grants: Dict[str, GroupGrant] = Field(..., description="Database grants")


class PermissionGroupUpdate(BaseModel):
    """Model for updating permission groups"""
    description: Optional[str] = Field(None, description="Group description")
    grants: Optional[Dict[str, GroupGrant]] = Field(None, description="Database grants")


class UserPermissionCreate(BaseModel):
    """Model for creating user permissions"""
    email: EmailStr = Field(..., description="User email address")
    role: str = Field(default="user", description="User role: 'admin' or 'user'")
    groups: List[str] = Field(..., description="Permission groups to assign")


class UserPermissionUpdate(BaseModel):
    """Model for updating user permissions"""
    role: Optional[str] = Field(None, description="User role: 'admin' or 'user'")
    groups: Optional[List[str]] = Field(None, description="Permission groups")
    custom_grants: Optional[Dict[str, Grant]] = Field(None, description="Custom grants")
    isActive: Optional[bool] = Field(None, description="Active status")


class PermissionCheck(BaseModel):
    """Model for checking permissions"""
    database: Optional[str] = None
    operation: Optional[str] = None


class PermissionResponse(BaseModel):
    """Response model for permission checks"""
    allowed: bool
    user_email: str
    role: str
    database: Optional[str] = None
    operation: Optional[str] = None
    reason: Optional[str] = None


# Permission presets for convenience
PERMISSION_PRESETS = {
    "VIEWER": Grant(r=True, w=False, d=False, a=False),
    "EDITOR": Grant(r=True, w=True, d=False, a=False),
    "MAINTAINER": Grant(r=True, w=True, d=True, a=False),
    "ADMIN": Grant(r=True, w=True, d=True, a=True)
}