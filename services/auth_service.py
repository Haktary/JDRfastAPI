# services/auth_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.testing.suite.test_reflection import users

from models.user import User, RefreshToken, GlobalUserRole
from config.settings import (
    hash_password,
    verify_password,
    create_access_token,
    create_random_refresh_token,
    settings
)
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Dict


def register_user(db: Session, email: str, password: str) -> User:
    """Enregistre un nouvel utilisateur"""
    email = email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        global_role=GlobalUserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Dict[str, str]:
    """Authentifie un utilisateur et retourne les tokens"""
    email = email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    _cleanup_expired_tokens(db, user.id)

    access_token = create_access_token({
        "sub": user.email,
        "role": user.global_role.value,
        "user_id": user.id
    })

    refresh_token = create_random_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_db = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(refresh_db)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def renew_token(db: Session, refresh_token: str) -> Dict[str, str]:
    """Renouvelle les tokens à partir d'un refresh token valide"""
    token_db = db.query(RefreshToken).filter(
        and_(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False
        )
    ).first()

    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Utiliser datetime.utcnow() pour rester cohérent avec la DB
    if token_db.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    user = token_db.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    token_db.revoked = True
    token_db.revoked_at = datetime.utcnow()

    new_refresh = create_random_refresh_token()
    new_refresh_db = RefreshToken(
        token=new_refresh,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_refresh_db)

    _cleanup_expired_tokens(db, user.id)

    db.commit()

    new_access = create_access_token({
        "sub": user.email,
        "role": user.global_role.value,
        "user_id": user.id
    })

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


def revoke_token(db: Session, refresh_token: str) -> Dict[str, any]:
    """Révoque un refresh token (logout)"""
    token_db = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found"
        )

    if token_db.revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already revoked"
        )

    token_db.revoked = True
    token_db.revoked_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Successfully logged out",
        "revoked": True
    }


def revoke_all_user_tokens(db: Session, refresh_token: str) -> Dict[str, any]:
    """Révoque tous les tokens d'un utilisateur (logout de tous les appareils)"""
    token_db = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found"
        )

    if token_db.revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already revoked"
        )

    if token_db.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    user_id = token_db.user_id
    now = datetime.utcnow()

    tokens_to_revoke = db.query(RefreshToken).filter(
        and_(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        )
    ).count()

    db.query(RefreshToken).filter(
        and_(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        )
    ).update({
        "revoked": True,
        "revoked_at": now
    }, synchronize_session=False)

    db.commit()

    return {
        "message": "Successfully logged out from all devices",
        "tokens_revoked": tokens_to_revoke,
        "user_id": user_id
    }

def _cleanup_expired_tokens(db: Session, user_id: int) -> None:
    """Supprime les tokens expirés ou révoqués depuis plus de 7 jours"""
    cutoff_date = datetime.utcnow() - timedelta(days=7)

    db.query(RefreshToken).filter(
        and_(
            RefreshToken.user_id == user_id,
            (
                    (RefreshToken.expires_at < datetime.utcnow()) |
                    (RefreshToken.revoked_at < cutoff_date)
            )
        )
    ).delete(synchronize_session=False)
    db.commit()

def promote_user(db: Session, user_id: int, new_role: GlobalUserRole) -> User:
    """Promouvoir un utilisateur (admin global seulement)"""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.global_role = new_role
    db.commit()
    db.refresh(user)

    return user