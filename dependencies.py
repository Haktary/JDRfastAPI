# dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from config.settings import settings
from config.database import get_session
from models.user import User, GlobalUserRole
from models.organization import OrganizationRoleType

security = HTTPBearer()


def get_db():
    """Dépendance pour obtenir une session DB"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur courant à partir du JWT"""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        token_type = payload.get("type")

        # Vérifie que c'est bien un access token
        if token_type and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# ============================
# Permissions GLOBALES
# ============================

def require_global_admin(current_user: User = Depends(get_current_user)) -> User:
    """Vérifie que l'utilisateur est admin global de l'application"""
    if current_user.global_role != GlobalUserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_global_roles(allowed_roles: list[GlobalUserRole]):
    """Vérifie que l'utilisateur a un des rôles globaux autorisés"""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.global_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user

    return role_checker


# ============================
# Permissions dans les ORGANISATIONS
# ============================

class RequireOrgRole:
    """Dépendance pour vérifier le rôle dans une organisation"""

    def __init__(self, min_role: OrganizationRoleType):
        self.min_role = min_role

    def __call__(
            self,
            organization_id: int,
            current_user: User = Depends(get_current_user)
    ) -> User:
        """Vérifie que l'utilisateur a au moins le rôle requis dans l'org"""
        if not current_user.has_permission_in_org(organization_id, self.min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least {self.min_role.value} role in this organization"
            )
        return current_user


class RequireOrgMember:
    """Vérifie que l'utilisateur est membre de l'organisation"""

    def __call__(
            self,
            organization_id: int,
            current_user: User = Depends(get_current_user)
    ) -> User:
        """Vérifie que l'utilisateur est membre actif de l'org"""
        if not current_user.is_member_of(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization"
            )
        return current_user


# Raccourcis pratiques pour les organisations
require_org_owner = RequireOrgRole(OrganizationRoleType.owner)
require_org_admin = RequireOrgRole(OrganizationRoleType.admin)
require_org_mj = RequireOrgRole(OrganizationRoleType.mj)
require_org_member = RequireOrgMember()