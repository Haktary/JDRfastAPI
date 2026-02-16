# routers/organizations.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from config.database import get_engine, get_session
from models.organization import Organization
from services.organization_service import (
    create_organization,
    get_user_organizations,
    join_organization,
    update_member_role,
    approve_membership, update_organization
)
from schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    JoinOrganizationRequest,
    MembershipResponse,
    UpdateMemberRoleRequest, OrganizationUpdate
)
from dependencies import (
    get_current_user,
    require_global_admin,
    require_org_admin,
    require_org_member
)
from models.user import User

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ============================
# Routes PUBLIQUES (avec auth)
# ============================

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_org(
        data: OrganizationCreate,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)  # Juste authentifié
):
    """Crée une nouvelle organisation (tout utilisateur authentifié peut créer une org)"""
    org = create_organization(
        db,
        current_user,
        data.name,
        data.slug,
        data.description,
        data.visibility,
        data.join_mode
    )
    return org


@router.get("/my", response_model=list[OrganizationResponse])
def get_my_organizations(
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)  # Juste authentifié
):
    """Récupère mes organisations"""
    return get_user_organizations(db, current_user.id)


@router.post("/{organization_id}/join", response_model=MembershipResponse)
def join_org(
        organization_id: int,
        data: JoinOrganizationRequest,
        db: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)  # Juste authentifié
):
    """Demande à rejoindre une organisation"""
    return join_organization(db, current_user, organization_id, data.message)


# ============================
# Routes réservées aux MEMBRES
# ============================

@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
        organization_id: int,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_org_member)  # Doit être membre
):
    """Récupère les détails d'une organisation (réservé aux membres)"""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ============================
# Routes réservées aux ADMINS
# ============================


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_org(
        organization_id: int,
        data: OrganizationUpdate,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_org_admin)  # Doit être admin de l'org
):
    """Met à jour une organisation (réservé aux admins)"""
    return update_organization(db, current_user, organization_id, data)

@router.patch("/{organization_id}/members/{user_id}/role", response_model=MembershipResponse)
def change_member_role(
        organization_id: int,
        user_id: int,
        data: UpdateMemberRoleRequest,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_org_admin)  # Doit être admin de l'org
):
    """Change le rôle d'un membre (réservé aux admins)"""
    return update_member_role(db, current_user, organization_id, user_id, data.role)


@router.post("/{organization_id}/members/{membership_id}/approve", response_model=MembershipResponse)
def approve_member(
        organization_id: int,
        membership_id: int,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_org_admin)  # Doit être admin de l'org
):
    """Approuve une demande d'adhésion (réservé aux admins)"""
    return approve_membership(db, current_user, organization_id, membership_id)


@router.delete("/{organization_id}/members/{user_id}")
def remove_member(
        organization_id: int,
        user_id: int,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_org_admin)  # Doit être admin de l'org
):
    """Retire un membre de l'organisation (réservé aux admins)"""
    # TODO: implémenter
    pass


# ============================
# Routes réservées aux SUPER ADMINS (global)
# ============================

@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
        organization_id: int,
        db: Session = Depends(get_session),
        current_user: User = Depends(require_global_admin)  # Doit être admin global
):
    """Supprime une organisation (réservé aux admins globaux)"""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    db.delete(org)
    db.commit()
    return None