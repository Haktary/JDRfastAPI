# models/organization.py
import enum
from sqlalchemy import String, Enum, ForeignKey, DateTime, Boolean, Integer, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from datetime import datetime


# ============================
# ENUMS
# ============================

class OrganizationVisibility(str, enum.Enum):
    """Visibilité de l'organisation"""
    public = "public"  # Visible par tous
    private = "private"  # Visible uniquement par les membres


class OrganizationJoinMode(str, enum.Enum):
    """Mode de rejointe d'une organisation"""
    open = "open"  # N'importe qui peut rejoindre directement
    approval = "approval"  # Nécessite l'approbation d'un admin
    invite_only = "invite_only"  # Uniquement sur invitation
    closed = "closed"  # Fermé, personne ne peut rejoindre


class OrganizationRoleType(str, enum.Enum):
    """Rôles au sein d'une organisation"""
    owner = "owner"  # Créateur de l'orga, tous les droits
    admin = "admin"  # Administrateur, peut gérer l'orga
    mj = "mj"  # Maître du jeu
    member = "member"  # Membre standard
    guest = "guest"  # Invité (accès limité)


class MembershipStatus(str, enum.Enum):
    """Statut d'appartenance à une organisation"""
    active = "active"  # Membre actif
    pending = "pending"  # En attente d'approbation
    invited = "invited"  # Invité mais pas encore accepté
    suspended = "suspended"  # Suspendu temporairement
    banned = "banned"  # Banni


# ============================
# TABLES
# ============================

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Configuration
    visibility: Mapped[OrganizationVisibility] = mapped_column(
        Enum(OrganizationVisibility),
        default=OrganizationVisibility.public,
        nullable=False
    )
    join_mode: Mapped[OrganizationJoinMode] = mapped_column(
        Enum(OrganizationJoinMode),
        default=OrganizationJoinMode.approval,
        nullable=False
    )

    # Métadonnées
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                                                 nullable=False)

    # Relations
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"


class OrganizationMembership(Base):
    """Table de liaison entre User et Organization avec rôle"""
    __tablename__ = "organization_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Relations
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Rôle et statut
    role: Mapped[OrganizationRoleType] = mapped_column(
        Enum(OrganizationRoleType),
        default=OrganizationRoleType.member,
        nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus),
        default=MembershipStatus.pending,
        nullable=False
    )

    # Métadonnées
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    invited_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relations
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    invited_by: Mapped["User"] = relationship("User", foreign_keys=[invited_by_id])
    approved_by: Mapped["User"] = relationship("User", foreign_keys=[approved_by_id])

    def __repr__(self):
        return f"<Membership user={self.user_id} org={self.organization_id} role={self.role}>"


class OrganizationInvitation(Base):
    """Invitations en attente pour rejoindre une organisation"""
    __tablename__ = "organization_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Peut inviter par email (même si pas encore inscrit) ou user_id
    email: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Invitation
    invited_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[OrganizationRoleType] = mapped_column(
        Enum(OrganizationRoleType),
        default=OrganizationRoleType.member,
        nullable=False
    )

    # Token unique pour accepter l'invitation
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relations
    organization: Mapped["Organization"] = relationship("Organization")
    invited_by: Mapped["User"] = relationship("User", foreign_keys=[invited_by_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Invitation org={self.organization_id} email={self.email}>"