# schemas/organization.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from models.organization import (
    OrganizationVisibility,
    OrganizationJoinMode,
    OrganizationRoleType,
    MembershipStatus
)


# ============================
# Organization Schemas
# ============================

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=3, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    visibility: OrganizationVisibility = OrganizationVisibility.public
    join_mode: OrganizationJoinMode = OrganizationJoinMode.approval

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return v.lower().strip()


class OrganizationUpdate(BaseModel):
    """Schema pour mettre à jour une organisation"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    visibility: Optional[OrganizationVisibility] = None
    join_mode: Optional[OrganizationJoinMode] = None
    is_active: Optional[bool] = None

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.lower().strip()
        return v


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    visibility: OrganizationVisibility
    join_mode: OrganizationJoinMode
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationDetailResponse(OrganizationResponse):
    member_count: Optional[int] = None
    user_role: Optional[OrganizationRoleType] = None
    user_status: Optional[MembershipStatus] = None


# ============================
# Membership Schemas
# ============================

class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    organization_id: int
    role: OrganizationRoleType
    status: MembershipStatus
    joined_at: datetime


class MemberDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_email: str
    role: OrganizationRoleType
    status: MembershipStatus
    joined_at: datetime


class JoinOrganizationRequest(BaseModel):
    message: Optional[str] = Field(None, max_length=500)


class UpdateMemberRoleRequest(BaseModel):
    role: OrganizationRoleType


class UpdateMemberStatusRequest(BaseModel):
    status: MembershipStatus


# ============================
# Invitation Schemas
# ============================

class InviteUserRequest(BaseModel):
    email: str
    role: OrganizationRoleType = OrganizationRoleType.member


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    email: Optional[str]
    role: OrganizationRoleType
    created_at: datetime
    expires_at: datetime