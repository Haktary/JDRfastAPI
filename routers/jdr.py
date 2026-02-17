# routers/jdr.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from config.database import get_session
from services.jdr_service import (
    create_jdr, get_organization_jdrs, update_jdr,
    join_jdr, approve_player,
    create_character, update_character, get_jdr_characters,
    create_game_item, give_item_to_character, update_character_gold,
    get_board, update_board, add_board_element, update_board_element, delete_board_element
)
from schemas.jdr import (
    JDRCreate, JDRUpdate, JDRResponse,
    JoinJDRRequest, JDRMembershipResponse,
    CharacterCreate, CharacterUpdate, MJCharacterUpdate, CharacterResponse,
    GameItemCreate, GameItemResponse,
    GiveItemRequest, UpdateGoldRequest, InventoryResponse,
    BoardUpdate, BoardElementCreate, BoardElementUpdate,
    BoardElementResponse, BoardResponse
)
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/organizations/{organization_id}/jdrs", tags=["JDR"])


# ============================
# JDR CRUD
# ============================

@router.post("/", response_model=JDRResponse, status_code=status.HTTP_201_CREATED)
def create_new_jdr(
    organization_id: int,
    data: JDRCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée un JDR - le créateur devient automatiquement MJ"""
    return create_jdr(db, current_user, organization_id, data)


@router.get("/", response_model=list[JDRResponse])
def list_jdrs(
    organization_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste les JDRs de l'organisation"""
    return get_organization_jdrs(db, current_user, organization_id)


@router.patch("/{jdr_id}", response_model=JDRResponse)
def update_jdr_route(
    organization_id: int,
    jdr_id: int,
    data: JDRUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Met à jour un JDR (MJ seulement)"""
    return update_jdr(db, current_user, jdr_id, data)


# ============================
# MEMBERSHIP
# ============================

@router.post("/{jdr_id}/join", response_model=JDRMembershipResponse)
def join_jdr_route(
    organization_id: int,
    jdr_id: int,
    data: JoinJDRRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Demande à rejoindre un JDR"""
    return join_jdr(db, current_user, jdr_id, data.join_message)


@router.post("/{jdr_id}/members/{membership_id}/approve", response_model=JDRMembershipResponse)
def approve_player_route(
    organization_id: int,
    jdr_id: int,
    membership_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ approuve un joueur"""
    return approve_player(db, current_user, jdr_id, membership_id)


# ============================
# CHARACTERS
# ============================

@router.post("/{jdr_id}/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
def create_character_route(
    organization_id: int,
    jdr_id: int,
    data: CharacterCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée une fiche personnage"""
    return create_character(db, current_user, jdr_id, data)


@router.get("/{jdr_id}/characters", response_model=list[CharacterResponse])
def list_characters(
    organization_id: int,
    jdr_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste les personnages du JDR"""
    return get_jdr_characters(db, current_user, jdr_id)


@router.patch("/{jdr_id}/characters/{character_id}", response_model=CharacterResponse)
def update_character_route(
    organization_id: int,
    jdr_id: int,
    character_id: int,
    data: CharacterUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Met à jour un personnage (joueur)"""
    return update_character(db, current_user, character_id, data, is_mj=False)


@router.patch("/{jdr_id}/characters/{character_id}/mj", response_model=CharacterResponse)
def mj_update_character(
    organization_id: int,
    jdr_id: int,
    character_id: int,
    data: MJCharacterUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ met à jour un personnage (stats, xp...)"""
    return update_character(db, current_user, character_id, data, is_mj=True)


@router.patch("/{jdr_id}/characters/{character_id}/gold", response_model=CharacterResponse)
def update_gold(
    organization_id: int,
    jdr_id: int,
    character_id: int,
    data: UpdateGoldRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ modifie l'or d'un personnage"""
    return update_character_gold(db, current_user, jdr_id, character_id, data.amount)


# ============================
# ITEMS & INVENTORY
# ============================

@router.post("/{jdr_id}/items", response_model=GameItemResponse, status_code=status.HTTP_201_CREATED)
def create_game_item_route(
    organization_id: int,
    jdr_id: int,
    data: GameItemCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ crée un item dans le JDR"""
    return create_game_item(db, current_user, jdr_id, data)


@router.post("/{jdr_id}/inventory/give", response_model=InventoryResponse)
def give_item(
    organization_id: int,
    jdr_id: int,
    data: GiveItemRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ donne un item à un personnage"""
    return give_item_to_character(db, current_user, jdr_id, data)


# ============================
# BOARD
# ============================

@router.get("/{jdr_id}/board", response_model=BoardResponse)
def get_board_route(
    organization_id: int,
    jdr_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupère le board du JDR"""
    return get_board(db, current_user, jdr_id)


@router.patch("/{jdr_id}/board", response_model=BoardResponse)
def update_board_route(
    organization_id: int,
    jdr_id: int,
    data: BoardUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ configure le board (dimensions, background...)"""
    return update_board(db, current_user, jdr_id, data)


@router.post("/{jdr_id}/board/elements", response_model=BoardElementResponse, status_code=status.HTTP_201_CREATED)
def add_element(
    organization_id: int,
    jdr_id: int,
    data: BoardElementCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ ajoute un élément sur le board"""
    return add_board_element(db, current_user, jdr_id, data)


@router.patch("/{jdr_id}/board/elements/{element_id}", response_model=BoardElementResponse)
def update_element(
    organization_id: int,
    jdr_id: int,
    element_id: int,
    data: BoardElementUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ met à jour un élément du board"""
    return update_board_element(db, current_user, jdr_id, element_id, data)


@router.delete("/{jdr_id}/board/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(
    organization_id: int,
    jdr_id: int,
    element_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """MJ supprime un élément du board"""
    delete_board_element(db, current_user, jdr_id, element_id)
    return None