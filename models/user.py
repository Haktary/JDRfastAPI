# models/user.py (mise à jour)
import enum
from sqlalchemy import String, Enum, ForeignKey, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from datetime import datetime

from models.organization import OrganizationRoleType, MembershipStatus, OrganizationMembership


class GlobalUserRole(str, enum.Enum):
    """Rôle global de l'utilisateur dans l'application"""
    admin = "admin"  # Admin avec certains privilèges
    user = "user"  # Utilisateur standard


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Rôle GLOBAL (dans toute l'app, pas dans une orga spécifique)
    global_role: Mapped[GlobalUserRole] = mapped_column(
        Enum(GlobalUserRole),
        default=GlobalUserRole.user,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    organization_memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="user",
        foreign_keys="OrganizationMembership.user_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"

    # Méthodes utiles
    def get_organization_role(self, organization_id: int) -> OrganizationRoleType | None:
        """Récupère le rôle de l'utilisateur dans une organisation"""
        membership = next(
            (m for m in self.organization_memberships
             if m.organization_id == organization_id and m.status == MembershipStatus.active),
            None
        )
        return membership.role if membership else None

    def is_member_of(self, organization_id: int) -> bool:
        """Vérifie si l'utilisateur est membre d'une organisation"""
        return any(
            m.organization_id == organization_id and m.status == MembershipStatus.active
            for m in self.organization_memberships
        )

    def has_permission_in_org(self, organization_id: int, min_role: OrganizationRoleType) -> bool:
        """Vérifie si l'utilisateur a au moins un certain rôle dans une org"""
        role_hierarchy = {
            OrganizationRoleType.guest: 0,
            OrganizationRoleType.member: 1,
            OrganizationRoleType.mj: 2,
            OrganizationRoleType.admin: 3,
            OrganizationRoleType.owner: 4
        }

        user_role = self.get_organization_role(organization_id)
        if not user_role:
            return False

        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(min_role, 0)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")