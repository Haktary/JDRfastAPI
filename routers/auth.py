from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from dependencies import get_db, require_global_admin
from services.auth_service import (
    register_user,
    authenticate_user,
    renew_token,
    revoke_token,
    revoke_all_user_tokens
)
from schemas.auth import (
    RegisterSchema,
    LoginSchema,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    LogoutAllResponse,
    LogoutResponse, PromoteUserRequest
)
from models.user import User
from services.auth_service import promote_user
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    """Enregistre un nouvel utilisateur"""
    user = register_user(db, data.email, data.password)
    return user

@router.post("/login", response_model=TokenResponse)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    """Connexion et obtention des tokens"""
    return authenticate_user(db, data.email, data.password)

@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Renouvelle les tokens"""
    return renew_token(db, data.refresh_token)

@router.post("/logout", response_model=LogoutResponse)
def logout(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Déconnexion (révoque le refresh token)"""
    return revoke_token(db, data.refresh_token)

@router.post("/logout-all", response_model=LogoutAllResponse)
def logout_all(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Déconnexion de tous les appareils"""
    return revoke_all_user_tokens(db, data.refresh_token)

@router.post("/promote", response_model=UserResponse)
def promote_user_role(
    data: PromoteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_global_admin)
):
    """Promouvoir un utilisateur en admin global (réservé aux admins)"""
    return promote_user(db, data.user_id, data.new_global_role)