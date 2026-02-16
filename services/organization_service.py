# services/organization_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.user import User
from models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    OrganizationVisibility,
    OrganizationJoinMode,
    OrganizationRoleType,
    MembershipStatus
)
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
import secrets


def create_organization(
        db: Session,
        user: User,
        name: str,
        slug: str,
        description: Optional[str] = None,
        visibility: OrganizationVisibility = OrganizationVisibility.public,
        join_mode: OrganizationJoinMode = OrganizationJoinMode.approval
) -> Organization:
    """Crée une nouvelle organisation"""

    # Vérifie si le slug existe déjà
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists"
        )

    # Crée l'organisation
    org = Organization(
        name=name,
        slug=slug,
        description=description,
        visibility=visibility,
        join_mode=join_mode
    )
    db.add(org)
    db.flush()  # Pour obtenir l'ID

    # IMPORTANT: Le créateur devient OWNER automatiquement
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role=OrganizationRoleType.owner,  # OWNER, pas admin
        status=MembershipStatus.active  # Directement actif
    )
    db.add(membership)
    db.commit()
    db.refresh(org)

    return org


def get_user_organizations(db: Session, user_id: int) -> List[Organization]:
    """Récupère toutes les organisations d'un utilisateur"""
    return db.query(Organization).join(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == MembershipStatus.active
        )
    ).all()


def join_organization(
        db: Session,
        user: User,
        organization_id: int,
        message: Optional[str] = None
) -> OrganizationMembership:
    """Demande à rejoindre une organisation"""

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is not active"
        )

    # Vérifie si l'utilisateur est déjà membre
    existing = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status.in_([MembershipStatus.active, MembershipStatus.pending])
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member or pending approval"
        )

    # Vérifie le mode de rejointe
    if org.join_mode == OrganizationJoinMode.closed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is closed"
        )

    if org.join_mode == OrganizationJoinMode.invite_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is invite-only"
        )

    # Détermine le statut initial
    if org.join_mode == OrganizationJoinMode.open:
        initial_status = MembershipStatus.active
    else:  # approval
        initial_status = MembershipStatus.pending

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=organization_id,
        role=OrganizationRoleType.member,  # Nouveau membre = "member"
        status=initial_status
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


def update_member_role(
        db: Session,
        requester: User,
        organization_id: int,
        target_user_id: int,
        new_role: OrganizationRoleType
) -> OrganizationMembership:
    """Change le rôle d'un membre (nécessite admin/owner)"""

    # Vérifie les permissions du requester (doit être au moins admin)
    if not requester.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions - Admin role required"
        )

    # Récupère le membership cible
    membership = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == target_user_id,
            OrganizationMembership.organization_id == organization_id
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )

    # 🔥 RÈGLE IMPORTANTE: On ne peut pas modifier le rôle d'un owner
    if membership.role == OrganizationRoleType.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )

    # 🔥 RÈGLE: Seul un owner peut promouvoir quelqu'un en owner
    if new_role == OrganizationRoleType.owner:
        if not requester.has_permission_in_org(organization_id, OrganizationRoleType.owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can promote to owner role"
            )

    membership.role = new_role
    db.commit()
    db.refresh(membership)

    return membership


def approve_membership(
        db: Session,
        requester: User,
        organization_id: int,
        membership_id: int
) -> OrganizationMembership:
    """Approuve une demande d'adhésion (nécessite admin/owner)"""

    # Vérifie les permissions
    if not requester.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions - Admin role required"
        )

    membership = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.pending
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending membership not found"
        )

    membership.status = MembershipStatus.active
    membership.approved_by_id = requester.id
    membership.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(membership)

    return membership


def update_organization(
        db: Session,
        user: User,
        organization_id: int,
        data
) -> Organization:
    """Met à jour une organisation (admin/owner seulement)"""

    # Vérifie les permissions (au moins admin)
    if not user.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions - Admin role required"
        )

    # Récupère l'organisation
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Met à jour les champs fournis
    update_data = data.model_dump(exclude_unset=True)

    # Vérifie si le slug change et s'il est déjà utilisé
    if "slug" in update_data and update_data["slug"] != org.slug:
        existing_slug = db.query(Organization).filter(
            and_(
                Organization.slug == update_data["slug"],
                Organization.id != organization_id
            )
        ).first()
        if existing_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug already in use"
            )

    # Applique les modifications
    for field, value in update_data.items():
        setattr(org, field, value)

    org.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(org)

    return org

def get_user_organizations(db: Session, user_id: int) -> List[Organization]:
    """Récupère toutes les organisations d'un utilisateur"""
    return db.query(Organization).join(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == MembershipStatus.active
        )
    ).all()


def join_organization(
        db: Session,
        user: User,
        organization_id: int,
        message: Optional[str] = None
) -> OrganizationMembership:
    """Demande à rejoindre une organisation"""

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is not active"
        )

    # Vérifie si l'utilisateur est déjà membre
    existing = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status.in_([MembershipStatus.active, MembershipStatus.pending])
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member or pending approval"
        )

    # Vérifie le mode de rejointe
    if org.join_mode == OrganizationJoinMode.closed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is closed"
        )

    if org.join_mode == OrganizationJoinMode.invite_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is invite-only"
        )

    # Détermine le statut initial
    if org.join_mode == OrganizationJoinMode.open:
        initial_status = MembershipStatus.active
    else:  # approval
        initial_status = MembershipStatus.pending

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=organization_id,
        role=OrganizationRoleType.member,
        status=initial_status
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


def update_member_role(
        db: Session,
        requester: User,
        organization_id: int,
        target_user_id: int,
        new_role: OrganizationRoleType
) -> OrganizationMembership:
    """Change le rôle d'un membre (nécessite admin/owner)"""

    # Vérifie les permissions du requester
    if not requester.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    # Récupère le membership cible
    membership = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == target_user_id,
            OrganizationMembership.organization_id == organization_id
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )

    # On ne peut pas changer le rôle du owner (pour éviter de perdre le contrôle)
    if membership.role == OrganizationRoleType.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )

    membership.role = new_role
    db.commit()
    db.refresh(membership)

    return membership


def approve_membership(
        db: Session,
        requester: User,
        organization_id: int,
        membership_id: int
) -> OrganizationMembership:
    """Approuve une demande d'adhésion (nécessite admin/owner)"""

    if not requester.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    membership = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.pending
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending membership not found"
        )

    membership.status = MembershipStatus.active
    membership.approved_by_id = requester.id
    membership.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(membership)

    return membership


def invite_user_to_organization(
        db: Session,
        requester: User,
        organization_id: int,
        email: str,
        role: OrganizationRoleType = OrganizationRoleType.member
) -> OrganizationInvitation:
    """Invite un utilisateur à rejoindre l'organisation"""

    if not requester.has_permission_in_org(organization_id, OrganizationRoleType.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    # Génère un token unique
    token = secrets.token_urlsafe(32)

    invitation = OrganizationInvitation(
        organization_id=organization_id,
        email=email.lower().strip(),
        invited_by_id=requester.id,
        role=role,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation