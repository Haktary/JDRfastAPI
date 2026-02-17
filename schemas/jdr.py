# schemas/jdr.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from models.jdr import JDRStatus, MembershipJDRStatus, ItemType, ItemRarity, BoardElementType

# ============================
# IMAGE EMBED (réutilisable)
# ============================

class ImageAssetEmbed(BaseModel):
    """Représentation légère d'un ImageAsset dans les réponses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    filename: str
    width: Optional[int]
    height: Optional[int]
    file_size: int


# ============================
# JDR Schemas
# ============================

class JDRCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    universe: Optional[str] = None
    max_players: int = Field(default=6, ge=1, le=50)
    is_public: bool = True
    settings: dict = {}

class JDRUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    universe: Optional[str] = None
    status: Optional[JDRStatus] = None
    max_players: Optional[int] = Field(None, ge=1, le=50)
    is_public: Optional[bool] = None
    settings: Optional[dict] = None

class JDRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    mj_id: Optional[int]
    name: str
    description: Optional[str]
    universe: Optional[str]
    status: JDRStatus
    max_players: int
    is_public: bool
    settings: dict
    created_at: datetime
    updated_at: datetime

class JDRDetailResponse(JDRResponse):
    player_count: Optional[int] = None
    is_member: Optional[bool] = None
    my_characters: Optional[list] = []


# ============================
# Membership JDR Schemas
# ============================

class JoinJDRRequest(BaseModel):
    join_message: Optional[str] = Field(None, max_length=500)

class JDRMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jdr_id: int
    user_id: int
    status: MembershipJDRStatus
    join_message: Optional[str]
    joined_at: datetime


# ============================
# Character Schemas
# ============================

class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    race: Optional[str] = None
    character_class: Optional[str] = None
    level: int = Field(default=1, ge=1)
    #   On passe l'ID de l'image uploadée, pas une URL
    avatar_image_id: Optional[int] = None
    stats: dict = {}
    gold: float = Field(default=0.0, ge=0)
    backstory: Optional[str] = None
    notes: Optional[str] = None

class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    race: Optional[str] = None
    character_class: Optional[str] = None
    level: Optional[int] = Field(None, ge=1)
    # On passe l'ID de l'image uploadée, pas une URL
    avatar_image_id: Optional[int] = None
    stats: Optional[dict] = None
    gold: Optional[float] = Field(None, ge=0)
    backstory: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_alive: Optional[bool] = None
    map_position: Optional[dict] = None

class MJCharacterUpdate(CharacterUpdate):
    """MJ peut modifier des champs supplémentaires"""
    experience: Optional[int] = Field(None, ge=0)

class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jdr_id: int
    owner_id: int
    name: str
    race: Optional[str]
    character_class: Optional[str]
    level: int
    # Retourne l'objet image complet ET l'url calculée via property
    avatar_image_id: Optional[int]
    avatar_image: Optional[ImageAssetEmbed] = None
    avatar_url: Optional[str] = None  # Calculée via la property du modèle
    stats: dict
    gold: float
    experience: int
    backstory: Optional[str]
    notes: Optional[str]
    is_active: bool
    is_alive: bool
    map_position: dict
    created_at: datetime
    updated_at: datetime


# ============================
# Item Schemas
# ============================

class ItemTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    item_type: ItemType = ItemType.misc
    rarity: ItemRarity = ItemRarity.common
    # On passe l'ID de l'image uploadée, pas une URL
    image_id: Optional[int] = None
    stats: dict = {}

class ItemTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    item_type: Optional[ItemType] = None
    rarity: Optional[ItemRarity] = None
    image_id: Optional[int] = None
    stats: Optional[dict] = None

class ItemTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    item_type: ItemType
    rarity: ItemRarity
    # Retourne l'objet image complet ET l'url calculée
    image_id: Optional[int]
    image: Optional[ImageAssetEmbed] = None
    image_url: Optional[str] = None  # Calculée via la property du modèle
    stats: dict
    is_global: bool
    created_at: datetime

class GameItemCreate(BaseModel):
    template_id: Optional[int] = None
    custom_name: Optional[str] = Field(None, max_length=255)
    custom_description: Optional[str] = None
    custom_stats: dict = {}
    # Image custom pour ce game item
    custom_image_id: Optional[int] = None
    quantity: int = Field(default=1, ge=1)

class GameItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jdr_id: int
    template_id: Optional[int]
    custom_name: Optional[str]
    custom_description: Optional[str]
    custom_stats: dict
    custom_image_id: Optional[int]
    custom_image: Optional[ImageAssetEmbed] = None
    # URL calculée (custom_image > template.image > None)
    image_url: Optional[str] = None
    display_name: Optional[str] = None  # Calculée via property du modèle
    quantity: int

class GiveItemRequest(BaseModel):
    """MJ donne un item à un personnage"""
    game_item_id: int
    character_id: int
    quantity: int = Field(default=1, ge=1)
    mj_notes: Optional[str] = None

class UpdateGoldRequest(BaseModel):
    """MJ modifie l'or d'un personnage"""
    amount: float
    reason: Optional[str] = None

class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    game_item_id: int
    # Inclut les infos de l'item avec son image
    game_item: Optional[GameItemResponse] = None
    quantity: int
    is_equipped: bool
    equipment_slot: Optional[str]
    mj_notes: Optional[str]
    obtained_at: datetime


# ============================
# Board Schemas
# ============================

class BoardUpdate(BaseModel):
    """MJ peut modifier le board"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    # Image de fond via ID
    background_image_id: Optional[int] = None
    dimensions: Optional[dict] = None

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: Optional[dict]) -> Optional[dict]:
        """Vérifie que les dimensions sont valides"""
        if v is None:
            return v
        allowed_keys = {
            "width", "height", "grid_size", "scale",
            "show_grid", "grid_color", "background_color"
        }
        invalid = set(v.keys()) - allowed_keys
        if invalid:
            raise ValueError(f"Invalid dimension keys: {invalid}")
        if "width" in v and not (100 <= v["width"] <= 8192):
            raise ValueError("Width must be between 100 and 8192")
        if "height" in v and not (100 <= v["height"] <= 8192):
            raise ValueError("Height must be between 100 and 8192")
        if "grid_size" in v and not (10 <= v["grid_size"] <= 500):
            raise ValueError("Grid size must be between 10 and 500")
        if "scale" in v and not (0.1 <= v["scale"] <= 10.0):
            raise ValueError("Scale must be between 0.1 and 10.0")
        return v


class BoardElementCreate(BaseModel):
    element_type: BoardElementType
    character_id: Optional[int] = None
    game_item_id: Optional[int] = None
    # Image via ID pour les éléments monster/image
    image_id: Optional[int] = None
    content: dict = {}
    position: dict = {}
    is_visible: bool = True
    visible_to: dict = {"all": True}

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: dict) -> dict:
        """Ajoute les valeurs par défaut de position"""
        defaults = {
            "x": 0.0, "y": 0.0, "z": 0.0,
            "width": 100, "height": 100,
            "rotation": 0.0,
            "scale": 1.0,
            "opacity": 1.0,
            "locked": False
        }
        return {**defaults, **v}

class BoardElementUpdate(BaseModel):
    # Peut changer l'image d'un élément
    image_id: Optional[int] = None
    content: Optional[dict] = None
    position: Optional[dict] = None
    is_visible: Optional[bool] = None
    visible_to: Optional[dict] = None

class BoardElementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    element_type: BoardElementType
    character_id: Optional[int]
    game_item_id: Optional[int]
    # Image de l'élément
    image_id: Optional[int]
    image: Optional[ImageAssetEmbed] = None
    # URL calculée (image directe > avatar perso > image item > None)
    image_url: Optional[str] = None
    content: dict
    position: dict
    is_visible: bool
    visible_to: dict
    created_at: datetime
    updated_at: datetime

class BoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jdr_id: int
    name: str
    # Image de fond avec ses infos complètes
    background_image_id: Optional[int]
    background_image: Optional[ImageAssetEmbed] = None
    background_url: Optional[str] = None  # Calculée via property du modèle
    dimensions: dict
    updated_at: datetime
    elements: list[BoardElementResponse] = []