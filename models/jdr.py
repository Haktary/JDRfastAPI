# models/jdr.py
import enum
from sqlalchemy import String, Enum, ForeignKey, DateTime, Boolean, Integer, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from datetime import datetime
from typing import Optional

# ============================
# ENUMS
# ============================

class JDRStatus(str, enum.Enum):
    """Statut d'une partie JDR"""
    draft = "draft"
    open = "open"
    in_progress = "in_progress"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"

class MembershipJDRStatus(str, enum.Enum):
    """Statut d'un joueur dans un JDR"""
    pending = "pending"
    active = "active"
    rejected = "rejected"
    kicked = "kicked"
    left = "left"

class ItemType(str, enum.Enum):
    """Type d'item"""
    weapon = "weapon"
    armor = "armor"
    potion = "potion"
    spell = "spell"
    tool = "tool"
    treasure = "treasure"
    misc = "misc"
    quest = "quest"

class ItemRarity(str, enum.Enum):
    """Rareté d'un item"""
    common = "common"
    uncommon = "uncommon"
    rare = "rare"
    epic = "epic"
    legendary = "legendary"

class BoardElementType(str, enum.Enum):
    """Type d'élément sur le board"""
    character = "character"
    monster = "monster"
    item = "item"
    map = "map"
    note = "note"
    image = "image"


# ============================
# JDR (Partie)
# ============================

class JDR(Base):
    __tablename__ = "jdrs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mj_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Informations générales
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    universe: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[JDRStatus] = mapped_column(Enum(JDRStatus), default=JDRStatus.draft, nullable=False)

    # Configuration
    max_players: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Métadonnées évolutives
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relations
    organization: Mapped["Organization"] = relationship("Organization", back_populates="jdrs")
    mj: Mapped["User"] = relationship("User", foreign_keys=[mj_id])
    memberships: Mapped[list["JDRMembership"]] = relationship(
        "JDRMembership", back_populates="jdr", cascade="all, delete-orphan"
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character", back_populates="jdr", cascade="all, delete-orphan"
    )
    board: Mapped["Board"] = relationship(
        "Board", back_populates="jdr", uselist=False, cascade="all, delete-orphan"
    )
    game_items: Mapped[list["GameItem"]] = relationship(
        "GameItem", back_populates="jdr", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<JDR {self.name} ({self.status})>"


# ============================
# MEMBERSHIP JDR (Joueurs)
# ============================

class JDRMembership(Base):
    __tablename__ = "jdr_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jdr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jdrs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[MembershipJDRStatus] = mapped_column(
        Enum(MembershipJDRStatus), default=MembershipJDRStatus.pending, nullable=False
    )
    join_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    jdr: Mapped["JDR"] = relationship("JDR", back_populates="memberships")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    approved_by: Mapped["User"] = relationship("User", foreign_keys=[approved_by_id])

    def __repr__(self):
        return f"<JDRMembership jdr={self.jdr_id} user={self.user_id} status={self.status}>"


# ============================
# CHARACTER (Fiche Personnage)
# ============================

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jdr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jdrs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Informations de base
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    race: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    character_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Remplace avatar_url par une FK vers ImageAsset
    avatar_image_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("image_assets.id", ondelete="SET NULL"), nullable=True
    )

    # Stats évolutives
    stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Ressources
    gold: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Notes
    backstory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # État
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Position sur la map (coordonnées évolutives)
    map_position: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # {"map_id": 1, "x": 100.5, "y": 200.3, "z": 0.0, "rotation": 45.0}

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    jdr: Mapped["JDR"] = relationship("JDR", back_populates="characters")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    avatar_image: Mapped[Optional["ImageAsset"]] = relationship(
        "ImageAsset", foreign_keys=[avatar_image_id]
    )
    inventory: Mapped[list["CharacterInventory"]] = relationship(
        "CharacterInventory", back_populates="character", cascade="all, delete-orphan"
    )

    @property
    def avatar_url(self) -> Optional[str]:
        """URL de l'avatar calculée depuis l'ImageAsset"""
        return self.avatar_image.url if self.avatar_image else None

    def __repr__(self):
        return f"<Character {self.name} (lvl {self.level})>"


# ============================
# ITEMS (Bibliothèque d'items)
# ============================

class ItemTemplate(Base):
    __tablename__ = "item_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Informations
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), default=ItemType.misc, nullable=False)
    rarity: Mapped[ItemRarity] = mapped_column(Enum(ItemRarity), default=ItemRarity.common, nullable=False)

    # Remplace image_url par une FK vers ImageAsset
    image_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("image_assets.id", ondelete="SET NULL"), nullable=True
    )

    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    image: Mapped[Optional["ImageAsset"]] = relationship(
        "ImageAsset", foreign_keys=[image_id]
    )

    @property
    def image_url(self) -> Optional[str]:
        """URL de l'image calculée depuis l'ImageAsset"""
        return self.image.url if self.image else None

    def __repr__(self):
        return f"<ItemTemplate {self.name} ({self.item_type})>"


class GameItem(Base):
    __tablename__ = "game_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jdr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jdrs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("item_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Override du template
    custom_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Image custom pour cet item (override du template)
    custom_image_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("image_assets.id", ondelete="SET NULL"), nullable=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relations
    jdr: Mapped["JDR"] = relationship("JDR", back_populates="game_items")
    template: Mapped[Optional["ItemTemplate"]] = relationship("ItemTemplate")
    custom_image: Mapped[Optional["ImageAsset"]] = relationship(
        "ImageAsset", foreign_keys=[custom_image_id]
    )
    inventory_entries: Mapped[list["CharacterInventory"]] = relationship(
        "CharacterInventory", back_populates="game_item"
    )

    @property
    def image_url(self) -> Optional[str]:
        """
        URL de l'image dans cet ordre de priorité :
        1. Image custom du GameItem
        2. Image du template
        3. None
        """
        if self.custom_image:
            return self.custom_image.url
        if self.template and self.template.image:
            return self.template.image.url
        return None

    @property
    def display_name(self) -> str:
        """Nom affiché : custom_name > template.name"""
        return self.custom_name or (self.template.name if self.template else "Unknown")

    def __repr__(self):
        return f"<GameItem {self.display_name} in JDR {self.jdr_id}>"


class CharacterInventory(Base):
    __tablename__ = "character_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    equipment_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # "main_hand", "off_hand", "head", "body", "legs", "feet", "ring"

    mj_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    obtained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    character: Mapped["Character"] = relationship("Character", back_populates="inventory")
    game_item: Mapped["GameItem"] = relationship("GameItem", back_populates="inventory_entries")

    def __repr__(self):
        return f"<Inventory char={self.character_id} item={self.game_item_id} x{self.quantity}>"


# ============================
# BOARD (Tableau de jeu)
# ============================

class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jdr_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jdrs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), default="Board principal", nullable=False)

    # ✅ Remplace background_url par une FK vers ImageAsset
    background_image_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("image_assets.id", ondelete="SET NULL"), nullable=True
    )

    # Dimensions et config du canvas
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # {
    #   "width": 1920, "height": 1080,    <- dimensions du canvas
    #   "grid_size": 50,                   <- taille d'une case
    #   "scale": 1.0,                      <- zoom actuel
    #   "show_grid": true,                 <- afficher la grille
    #   "grid_color": "#CCCCCC",           <- couleur de la grille
    #   "background_color": "#1a1a2e"      <- couleur de fond fallback
    # }

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relations
    jdr: Mapped["JDR"] = relationship("JDR", back_populates="board")
    background_image: Mapped[Optional["ImageAsset"]] = relationship(
        "ImageAsset", foreign_keys=[background_image_id]
    )
    elements: Mapped[list["BoardElement"]] = relationship(
        "BoardElement", back_populates="board", cascade="all, delete-orphan"
    )

    @property
    def background_url(self) -> Optional[str]:
        """URL du background calculée depuis l'ImageAsset"""
        return self.background_image.url if self.background_image else None

    def __repr__(self):
        return f"<Board JDR={self.jdr_id}>"


class BoardElement(Base):
    __tablename__ = "board_elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    element_type: Mapped[BoardElementType] = mapped_column(Enum(BoardElementType), nullable=False)

    # Références optionnelles
    character_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    game_item_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("game_items.id"), nullable=True)

    # ✅ Référence directe à une image pour les éléments de type "image" ou "monster"
    image_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("image_assets.id", ondelete="SET NULL"), nullable=True
    )

    # Contenu libre (infos supplémentaires)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # monster:   {"name": "Dragon", "hp": 500, "description": "..."}
    # note:      {"text": "Bienvenue!", "color": "#FFD700", "font_size": 16}
    # image:     {"alt": "Carte du donjon", "opacity": 1.0}
    # character: {"display_name": "Thorin", "token_color": "#0000FF"}

    # Position sur le canvas (coordonnées précises pour les maps)
    position: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # {
    #   "x": 150.5, "y": 300.0, "z": 0.0,     <- position sur le canvas
    #   "width": 100, "height": 100,            <- dimensions de l'élément
    #   "rotation": 0.0,                        <- rotation en degrés
    #   "scale": 1.0,                           <- zoom de l'élément
    #   "opacity": 1.0,                         <- transparence
    #   "locked": false                         <- verrouillé par le MJ
    # }

    # Visibilité
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    visible_to: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # {"all": True}
    # {"player_ids": [1, 2]}
    # {"character_ids": [3, 4]}

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    board: Mapped["Board"] = relationship("Board", back_populates="elements")
    character: Mapped[Optional["Character"]] = relationship("Character")
    game_item: Mapped[Optional["GameItem"]] = relationship("GameItem")
    image: Mapped[Optional["ImageAsset"]] = relationship(
        "ImageAsset", foreign_keys=[image_id]
    )

    @property
    def image_url(self) -> Optional[str]:
        """
        URL de l'image dans cet ordre de priorité :
        1. image directement liée à l'élément
        2. avatar du personnage lié
        3. image du game_item lié
        4. None
        """
        if self.image:
            return self.image.url
        if self.character and self.character.avatar_image:
            return self.character.avatar_image.url
        if self.game_item and self.game_item.image_url:
            return self.game_item.image_url
        return None

    def __repr__(self):
        return f"<BoardElement {self.element_type} on Board={self.board_id}>"