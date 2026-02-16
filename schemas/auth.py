# schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from models.organization import OrganizationRoleType, MembershipStatus
from models.user import GlobalUserRole
from datetime import datetime
from typing import Optional


class RegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    #global_role: GlobalUserRole = Field(default=GlobalUserRole.user)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class LogoutResponse(BaseModel):
    message: str
    revoked: bool = True


class LogoutAllResponse(BaseModel):
    message: str
    tokens_revoked: int
    user_id: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    global_role: GlobalUserRole  # Changé de 'role' à 'global_role'
    is_active: bool
    created_at: datetime


class PromoteUserRequest(BaseModel):
    """Schema pour promouvoir un utilisateur en admin global"""
    user_id: int
    new_global_role: GlobalUserRole

class UserWithOrganizationsResponse(UserResponse):
    """Response avec les organisations de l'utilisateur"""
    organizations: list['OrganizationMembershipSummary'] = []


class OrganizationMembershipSummary(BaseModel):
    """Résumé d'une appartenance à une organisation"""
    model_config = ConfigDict(from_attributes=True)

    organization_id: int
    organization_name: str
    organization_slug: str
    role: 'OrganizationRoleType'
    status: 'MembershipStatus'
    joined_at: datetime