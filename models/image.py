# models/image.py
from sqlalchemy import String, ForeignKey, DateTime, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from datetime import datetime
from typing import Optional


class ImageAsset(Base):
    """Référence d'une image stockée sur le serveur"""
    __tablename__ = "image_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Qui a uploadé l'image
    uploaded_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Contexte (optionnel - peut être global)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    jdr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jdrs.id", ondelete="CASCADE"), nullable=True
    )

    # Infos fichier
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dimensions
    width: Mapped[int] = mapped_column(Integer, nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=True)

    # Global = fourni par l'app (items/monstres par défaut)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Tags pour recherche
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Exemple: {"type": "monster", "name": "Dragon", "theme": "fantasy"}

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    uploaded_by: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<ImageAsset {self.filename} ({self.category})>"