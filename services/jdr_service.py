# services/jdr_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from models.jdr import (
    JDR, JDRMembership, Character, ItemTemplate,
    GameItem, CharacterInventory, Board, BoardElement,
    JDRStatus, MembershipJDRStatus, BoardElementType
)
from models.image import ImageAsset
from models.user import User
from models.organization import OrganizationMembership, MembershipStatus, OrganizationRoleType
from fastapi import HTTPException, status
from datetime import datetime
from typing import Optional


# ============================
# HELPERS / CHECKS
# ============================

def _check_org_membership(db: Session, user_id: int, organization_id: int):
    """Vérifie que l'user est membre actif de l'organisation"""
    membership = db.query(OrganizationMembership).filter(
        and_(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.active
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this organization"
        )
    return membership


def _check_is_mj(db: Session, user: User, jdr_id: int) -> JDR:
    """Vérifie que l'user est MJ du JDR"""
    jdr = db.query(JDR).filter(JDR.id == jdr_id).first()
    if not jdr:
        raise HTTPException(status_code=404, detail="JDR not found")
    if jdr.mj_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the MJ can perform this action"
        )
    return jdr


def _check_is_player(db: Session, user_id: int, jdr_id: int) -> JDRMembership:
    """Vérifie que l'user est joueur actif du JDR"""
    membership = db.query(JDRMembership).filter(
        and_(
            JDRMembership.user_id == user_id,
            JDRMembership.jdr_id == jdr_id,
            JDRMembership.status == MembershipJDRStatus.active
        )
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an active player in this JDR"
        )
    return membership


def _check_image_exists(db: Session, image_id: int) -> ImageAsset:
    """Vérifie qu'une image existe en DB"""
    image = db.query(ImageAsset).filter(ImageAsset.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id {image_id} not found"
        )
    return image


# ============================
# JDR CRUD
# ============================

def create_jdr(db: Session, user: User, organization_id: int, data) -> JDR:
    """Crée un JDR - le créateur devient automatiquement MJ"""
    _check_org_membership(db, user.id, organization_id)

    jdr = JDR(
        organization_id=organization_id,
        mj_id=user.id,
        name=data.name,
        description=data.description,
        universe=data.universe,
        max_players=data.max_players,
        is_public=data.is_public,
        settings=data.settings,
        status=JDRStatus.draft
    )
    db.add(jdr)
    db.flush()

    # Crée le board automatiquement avec config canvas complète
    board = Board(
        jdr_id=jdr.id,
        dimensions={
            "width": 1920,
            "height": 1080,
            "grid_size": 50,
            "scale": 1.0,
            "show_grid": True,
            "grid_color": "#CCCCCC",
            "background_color": "#1a1a2e"
        }
    )
    db.add(board)
    db.commit()
    db.refresh(jdr)
    return jdr


def get_organization_jdrs(db: Session, user: User, organization_id: int) -> list[JDR]:
    """Récupère tous les JDRs d'une organisation"""
    _check_org_membership(db, user.id, organization_id)
    return db.query(JDR).filter(JDR.organization_id == organization_id).all()


def update_jdr(db: Session, user: User, jdr_id: int, data) -> JDR:
    """Met à jour un JDR (MJ seulement)"""
    jdr = _check_is_mj(db, user, jdr_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(jdr, field, value)

    jdr.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(jdr)
    return jdr


# ============================
# MEMBERSHIP JDR
# ============================

def join_jdr(db: Session, user: User, jdr_id: int, join_message: Optional[str]) -> JDRMembership:
    """Rejoindre un JDR (demande d'approbation au MJ)"""
    jdr = db.query(JDR).filter(JDR.id == jdr_id).first()
    if not jdr:
        raise HTTPException(status_code=404, detail="JDR not found")

    if jdr.status not in [JDRStatus.open, JDRStatus.in_progress]:
        raise HTTPException(status_code=400, detail="This JDR is not accepting new players")

    _check_org_membership(db, user.id, jdr.organization_id)

    existing = db.query(JDRMembership).filter(
        and_(
            JDRMembership.user_id == user.id,
            JDRMembership.jdr_id == jdr_id,
            JDRMembership.status.in_([MembershipJDRStatus.active, MembershipJDRStatus.pending])
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member or pending approval")

    active_count = db.query(JDRMembership).filter(
        and_(JDRMembership.jdr_id == jdr_id, JDRMembership.status == MembershipJDRStatus.active)
    ).count()
    if active_count >= jdr.max_players:
        raise HTTPException(status_code=400, detail="JDR is full")

    membership = JDRMembership(
        jdr_id=jdr_id,
        user_id=user.id,
        status=MembershipJDRStatus.pending,
        join_message=join_message
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def approve_player(db: Session, mj: User, jdr_id: int, membership_id: int) -> JDRMembership:
    """MJ approuve un joueur"""
    _check_is_mj(db, mj, jdr_id)

    membership = db.query(JDRMembership).filter(
        and_(
            JDRMembership.id == membership_id,
            JDRMembership.jdr_id == jdr_id,
            JDRMembership.status == MembershipJDRStatus.pending
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Pending membership not found")

    membership.status = MembershipJDRStatus.active
    membership.approved_by_id = mj.id
    membership.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(membership)
    return membership


# ============================
# CHARACTERS
# ============================

def create_character(db: Session, user: User, jdr_id: int, data) -> Character:
    """Créer une fiche personnage"""
    _check_is_player(db, user.id, jdr_id)

    #  Vérifie l'image si fournie
    if data.avatar_image_id:
        _check_image_exists(db, data.avatar_image_id)

    character = Character(
        jdr_id=jdr_id,
        owner_id=user.id,
        name=data.name,
        race=data.race,
        character_class=data.character_class,
        level=data.level,
        avatar_image_id=data.avatar_image_id,  #  FK image
        stats=data.stats,
        gold=data.gold,
        backstory=data.backstory,
        notes=data.notes
    )
    db.add(character)
    db.commit()

    #  Reload avec les relations images
    return _get_character_with_images(db, character.id)


def update_character(
    db: Session, user: User, character_id: int, data, is_mj: bool = False
) -> Character:
    """Met à jour une fiche personnage"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if not is_mj and character.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your character")

    if is_mj:
        _check_is_mj(db, user, character.jdr_id)

    update_data = data.model_dump(exclude_unset=True)

    #  Vérifie l'image si elle change
    if "avatar_image_id" in update_data and update_data["avatar_image_id"]:
        _check_image_exists(db, update_data["avatar_image_id"])

    for field, value in update_data.items():
        setattr(character, field, value)

    character.updated_at = datetime.utcnow()
    db.commit()

    #  Reload avec les relations images
    return _get_character_with_images(db, character.id)


def get_jdr_characters(db: Session, user: User, jdr_id: int) -> list[Character]:
    """Récupère tous les personnages d'un JDR"""
    jdr = db.query(JDR).filter(JDR.id == jdr_id).first()
    if not jdr:
        raise HTTPException(status_code=404, detail="JDR not found")

    is_mj = jdr.mj_id == user.id
    if not is_mj:
        _check_is_player(db, user.id, jdr_id)

    #  Charge les images avec joinedload
    return (
        db.query(Character)
        .options(joinedload(Character.avatar_image))
        .filter(Character.jdr_id == jdr_id)
        .all()
    )


def _get_character_with_images(db: Session, character_id: int) -> Character:
    """Récupère un personnage avec toutes ses images chargées"""
    return (
        db.query(Character)
        .options(joinedload(Character.avatar_image))
        .filter(Character.id == character_id)
        .first()
    )


# ============================
# ITEMS & INVENTORY
# ============================

def create_game_item(db: Session, mj: User, jdr_id: int, data) -> GameItem:
    """MJ crée un item dans le JDR"""
    _check_is_mj(db, mj, jdr_id)

    #  Vérifie l'image custom si fournie
    if data.custom_image_id:
        _check_image_exists(db, data.custom_image_id)

    # Vérifie le template si fourni
    if data.template_id:
        template = db.query(ItemTemplate).filter(ItemTemplate.id == data.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Item template not found")

    game_item = GameItem(
        jdr_id=jdr_id,
        template_id=data.template_id,
        custom_name=data.custom_name,
        custom_description=data.custom_description,
        custom_stats=data.custom_stats,
        custom_image_id=data.custom_image_id,  #  FK image
        quantity=data.quantity
    )
    db.add(game_item)
    db.commit()

    return _get_game_item_with_images(db, game_item.id)


def _get_game_item_with_images(db: Session, game_item_id: int) -> GameItem:
    """Récupère un GameItem avec toutes ses images chargées"""
    return (
        db.query(GameItem)
        .options(
            joinedload(GameItem.custom_image),
            joinedload(GameItem.template).joinedload(ItemTemplate.image)
        )
        .filter(GameItem.id == game_item_id)
        .first()
    )


def give_item_to_character(db: Session, mj: User, jdr_id: int, data) -> CharacterInventory:
    """MJ donne un item à un personnage"""
    _check_is_mj(db, mj, jdr_id)

    character = db.query(Character).filter(
        and_(Character.id == data.character_id, Character.jdr_id == jdr_id)
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found in this JDR")

    game_item = db.query(GameItem).filter(
        and_(GameItem.id == data.game_item_id, GameItem.jdr_id == jdr_id)
    ).first()
    if not game_item:
        raise HTTPException(status_code=404, detail="Item not found in this JDR")

    # Stack si déjà dans l'inventaire
    existing = db.query(CharacterInventory).filter(
        and_(
            CharacterInventory.character_id == data.character_id,
            CharacterInventory.game_item_id == data.game_item_id
        )
    ).first()

    if existing:
        existing.quantity += data.quantity
        if data.mj_notes:
            existing.mj_notes = data.mj_notes
        db.commit()
        return _get_inventory_with_images(db, existing.id)

    inventory = CharacterInventory(
        character_id=data.character_id,
        game_item_id=data.game_item_id,
        quantity=data.quantity,
        mj_notes=data.mj_notes
    )
    db.add(inventory)
    db.commit()

    return _get_inventory_with_images(db, inventory.id)


def _get_inventory_with_images(db: Session, inventory_id: int) -> CharacterInventory:
    """Récupère une entrée d'inventaire avec toutes ses images chargées"""
    return (
        db.query(CharacterInventory)
        .options(
            joinedload(CharacterInventory.game_item)
            .joinedload(GameItem.custom_image),
            joinedload(CharacterInventory.game_item)
            .joinedload(GameItem.template)
            .joinedload(ItemTemplate.image)
        )
        .filter(CharacterInventory.id == inventory_id)
        .first()
    )


def update_character_gold(
    db: Session, mj: User, jdr_id: int, character_id: int, amount: float
) -> Character:
    """MJ modifie l'or d'un personnage"""
    _check_is_mj(db, mj, jdr_id)

    character = db.query(Character).filter(
        and_(Character.id == character_id, Character.jdr_id == jdr_id)
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    character.gold = max(0.0, character.gold + amount)
    db.commit()

    return _get_character_with_images(db, character.id)


# ============================
# BOARD
# ============================

def get_board(db: Session, user: User, jdr_id: int) -> Board:
    """Récupère le board d'un JDR avec tous les éléments et images"""
    jdr = db.query(JDR).filter(JDR.id == jdr_id).first()
    if not jdr:
        raise HTTPException(status_code=404, detail="JDR not found")

    is_mj = jdr.mj_id == user.id
    if not is_mj:
        _check_is_player(db, user.id, jdr_id)

    #  Charge toutes les images en une seule requête
    board = (
        db.query(Board)
        .options(
            joinedload(Board.background_image),
            joinedload(Board.elements).joinedload(BoardElement.image),
            joinedload(Board.elements).joinedload(BoardElement.character)
                .joinedload(Character.avatar_image),
            joinedload(Board.elements).joinedload(BoardElement.game_item)
                .joinedload(GameItem.custom_image),
            joinedload(Board.elements).joinedload(BoardElement.game_item)
                .joinedload(GameItem.template)
                .joinedload(ItemTemplate.image),
        )
        .filter(Board.jdr_id == jdr_id)
        .first()
    )

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    #  Filtre les éléments invisibles pour les joueurs
    if not is_mj:
        board.elements = [
            el for el in board.elements
            if el.is_visible and _is_visible_to_user(el, user.id)
        ]

    return board


def update_board(db: Session, mj: User, jdr_id: int, data) -> Board:
    """MJ met à jour la configuration du board (canvas, background...)"""
    _check_is_mj(db, mj, jdr_id)

    board = db.query(Board).filter(Board.jdr_id == jdr_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    update_data = data.model_dump(exclude_unset=True)

    #  Vérifie l'image de fond si elle change
    if "background_image_id" in update_data and update_data["background_image_id"]:
        _check_image_exists(db, update_data["background_image_id"])

    #  Merge des dimensions (pas d'écrasement total)
    if "dimensions" in update_data:
        current_dimensions = board.dimensions or {}
        board.dimensions = {**current_dimensions, **update_data.pop("dimensions")}

    for field, value in update_data.items():
        setattr(board, field, value)

    board.updated_at = datetime.utcnow()
    db.commit()

    return _get_board_with_images(db, jdr_id)


def add_board_element(db: Session, mj: User, jdr_id: int, data) -> BoardElement:
    """MJ ajoute un élément sur le board"""
    _check_is_mj(db, mj, jdr_id)

    board = db.query(Board).filter(Board.jdr_id == jdr_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    #  Vérifie l'image si fournie
    if data.image_id:
        _check_image_exists(db, data.image_id)

    #  Vérifie le personnage si fourni
    if data.character_id:
        character = db.query(Character).filter(
            and_(Character.id == data.character_id, Character.jdr_id == jdr_id)
        ).first()
        if not character:
            raise HTTPException(status_code=404, detail="Character not found in this JDR")

    #  Vérifie le game item si fourni
    if data.game_item_id:
        game_item = db.query(GameItem).filter(
            and_(GameItem.id == data.game_item_id, GameItem.jdr_id == jdr_id)
        ).first()
        if not game_item:
            raise HTTPException(status_code=404, detail="Game item not found in this JDR")

    element = BoardElement(
        board_id=board.id,
        element_type=data.element_type,
        character_id=data.character_id,
        game_item_id=data.game_item_id,
        image_id=data.image_id,  # FK image
        content=data.content,
        position=data.position,
        is_visible=data.is_visible,
        visible_to=data.visible_to
    )
    db.add(element)
    board.updated_at = datetime.utcnow()
    db.commit()

    return _get_board_element_with_images(db, element.id)


def update_board_element(
    db: Session, mj: User, jdr_id: int, element_id: int, data
) -> BoardElement:
    """MJ met à jour un élément du board"""
    _check_is_mj(db, mj, jdr_id)

    board = db.query(Board).filter(Board.jdr_id == jdr_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    element = db.query(BoardElement).filter(
        and_(BoardElement.id == element_id, BoardElement.board_id == board.id)
    ).first()
    if not element:
        raise HTTPException(status_code=404, detail="Board element not found")

    update_data = data.model_dump(exclude_unset=True)

    # Vérifie l'image si elle change
    if "image_id" in update_data and update_data["image_id"]:
        _check_image_exists(db, update_data["image_id"])

    # Merge de position (pas d'écrasement total)
    if "position" in update_data:
        current_position = element.position or {}
        element.position = {**current_position, **update_data.pop("position")}

    # Merge de content (pas d'écrasement total)
    if "content" in update_data:
        current_content = element.content or {}
        element.content = {**current_content, **update_data.pop("content")}

    for field, value in update_data.items():
        setattr(element, field, value)

    element.updated_at = datetime.utcnow()
    board.updated_at = datetime.utcnow()
    db.commit()

    return _get_board_element_with_images(db, element.id)


def delete_board_element(db: Session, mj: User, jdr_id: int, element_id: int) -> None:
    """MJ supprime un élément du board"""
    _check_is_mj(db, mj, jdr_id)

    board = db.query(Board).filter(Board.jdr_id == jdr_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    element = db.query(BoardElement).filter(
        and_(BoardElement.id == element_id, BoardElement.board_id == board.id)
    ).first()
    if not element:
        raise HTTPException(status_code=404, detail="Board element not found")

    db.delete(element)
    board.updated_at = datetime.utcnow()
    db.commit()


# ============================
# HELPERS IMAGES
# ============================

def _get_board_with_images(db: Session, jdr_id: int) -> Board:
    """Récupère un board avec toutes ses images chargées"""
    return (
        db.query(Board)
        .options(
            joinedload(Board.background_image),
            joinedload(Board.elements).joinedload(BoardElement.image),
            joinedload(Board.elements).joinedload(BoardElement.character)
                .joinedload(Character.avatar_image),
            joinedload(Board.elements).joinedload(BoardElement.game_item)
                .joinedload(GameItem.custom_image),
            joinedload(Board.elements).joinedload(BoardElement.game_item)
                .joinedload(GameItem.template)
                .joinedload(ItemTemplate.image),
        )
        .filter(Board.jdr_id == jdr_id)
        .first()
    )


def _get_board_element_with_images(db: Session, element_id: int) -> BoardElement:
    """Récupère un élément du board avec toutes ses images"""
    return (
        db.query(BoardElement)
        .options(
            joinedload(BoardElement.image),
            joinedload(BoardElement.character).joinedload(Character.avatar_image),
            joinedload(BoardElement.game_item).joinedload(GameItem.custom_image),
            joinedload(BoardElement.game_item).joinedload(GameItem.template)
                .joinedload(ItemTemplate.image),
        )
        .filter(BoardElement.id == element_id)
        .first()
    )


def _is_visible_to_user(element: BoardElement, user_id: int) -> bool:
    """
    Vérifie si un élément est visible pour un utilisateur.
    visible_to examples:
        {"all": True}
        {"player_ids": [1, 2, 3]}
        {"character_ids": [4, 5]}
    """
    visible_to = element.visible_to

    if not visible_to:
        return True

    # Visible par tous
    if visible_to.get("all"):
        return True

    # Visible par certains joueurs
    if "player_ids" in visible_to:
        return user_id in visible_to["player_ids"]

    # Visible par certains personnages
    if "character_ids" in visible_to:
        if element.character_id and element.character:
            return element.character.owner_id == user_id
        return False

    return False