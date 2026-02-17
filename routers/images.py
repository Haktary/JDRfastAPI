# routers/images.py
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
from config.database import get_session
from dependencies import get_current_user
from models.user import User
from models.image import ImageAsset
from models.jdr import JDR
from services.image_service import (
    save_image,
    resize_existing_image,
    process_board_image,
    delete_image,
    get_image_info,
    UPLOAD_DIRS
)
from schemas.image import (
    ImageUploadResponse,
    ImageResizeRequest,
    ImageResizeResponse,
    BoardCanvasRequest,
    BoardCanvasResponse,
    ImageInfoResponse
)

router = APIRouter(prefix="/images", tags=["Images"])


# ============================
# SERVIR LES IMAGES (PUBLIC)
# ============================

@router.get("/uploads/{category}/{filename}")
def serve_image(category: str, filename: str):
    """Sert une image publiquement - pas d'auth requise"""
    file_path = UPLOAD_DIRS.get(category, UPLOAD_DIRS["misc"]) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        path=str(file_path),
        media_type="image/*",
        headers={"Cache-Control": "public, max-age=86400"}  # Cache 24h
    )


# ============================
# UPLOAD
# ============================

@router.post("/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    category: str = Form(default="misc"),
    jdr_id: Optional[int] = Form(default=None),
    organization_id: Optional[int] = Form(default=None),
    tags: Optional[str] = Form(default="{}"),
    resize_width: Optional[int] = Form(default=None),
    resize_height: Optional[int] = Form(default=None),
    quality: int = Form(default=85),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload une image.
    Catégories: characters, items, monsters, maps, boards, misc
    """

    # Parse les tags
    import json
    try:
        tags_dict = json.loads(tags) if tags else {}
    except:
        tags_dict = {}

    # Redimensionne si demandé
    resize = None
    if resize_width and resize_height:
        resize = (resize_width, resize_height)

    # Sauvegarde l'image
    result = await save_image(file, category, resize=resize, quality=quality)

    # Enregistre en DB
    asset = ImageAsset(
        uploaded_by_id=current_user.id,
        organization_id=organization_id,
        jdr_id=jdr_id,
        filename=result["filename"],
        original_filename=file.filename,
        category=category,
        url=result["url"],
        content_type=result["content_type"],
        file_size=result["file_size"],
        width=result["final_size"]["width"],
        height=result["final_size"]["height"],
        is_global=False,
        tags=tags_dict
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


# ============================
# RESIZE (MJ seulement)
# ============================

@router.post("/resize", response_model=ImageResizeResponse)
def resize_image(
    data: ImageResizeRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Redimensionne une image existante (crée une nouvelle version)"""
    result = resize_existing_image(
        filename=data.filename,
        category=data.category,
        width=data.width,
        height=data.height,
        quality=data.quality,
        keep_ratio=data.keep_ratio
    )

    # Enregistre la nouvelle version en DB
    source_asset = db.query(ImageAsset).filter(
        ImageAsset.filename == data.filename
    ).first()

    new_asset = ImageAsset(
        uploaded_by_id=current_user.id,
        organization_id=source_asset.organization_id if source_asset else None,
        jdr_id=source_asset.jdr_id if source_asset else None,
        filename=result["resized_filename"],
        original_filename=result["original_filename"],
        category=data.category,
        url=result["url"],
        content_type=source_asset.content_type if source_asset else "image/jpeg",
        file_size=result["file_size"],
        width=result["final_size"]["width"],
        height=result["final_size"]["height"],
        is_global=False,
        tags={}
    )
    db.add(new_asset)
    db.commit()

    return result


# ============================
# CANVAS BOARD (MJ seulement)
# ============================

@router.post("/board-canvas/{jdr_id}", response_model=BoardCanvasResponse)
def create_board_canvas(
    jdr_id: int,
    data: BoardCanvasRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Place une image sur un canvas aux dimensions du board.
    Réservé au MJ du JDR.
    """
    # Vérifie que l'user est MJ du JDR
    jdr = db.query(JDR).filter(JDR.id == jdr_id).first()
    if not jdr:
        raise HTTPException(status_code=404, detail="JDR not found")
    if jdr.mj_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the MJ can manage board canvas")

    result = process_board_image(
        filename=data.filename,
        category=data.category,
        canvas_width=data.canvas_width,
        canvas_height=data.canvas_height,
        position_x=data.position_x,
        position_y=data.position_y,
        img_width=data.img_width,
        img_height=data.img_height,
        quality=data.quality
    )

    # Enregistre en DB
    source_asset = db.query(ImageAsset).filter(
        ImageAsset.filename == data.filename
    ).first()

    new_asset = ImageAsset(
        uploaded_by_id=current_user.id,
        organization_id=jdr.organization_id,
        jdr_id=jdr_id,
        filename=result["filename"],
        original_filename=data.filename,
        category="boards",
        url=result["url"],
        content_type="image/png",
        file_size=result["file_size"],
        width=result["canvas_size"]["width"],
        height=result["canvas_size"]["height"],
        is_global=False,
        tags={"type": "board_canvas", "jdr_id": jdr_id}
    )
    db.add(new_asset)
    db.commit()

    return result


# ============================
# LISTING ET INFO
# ============================

@router.get("/jdr/{jdr_id}", response_model=list[ImageUploadResponse])
def list_jdr_images(
    jdr_id: int,
    category: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste toutes les images d'un JDR"""
    query = db.query(ImageAsset).filter(ImageAsset.jdr_id == jdr_id)
    if category:
        query = query.filter(ImageAsset.category == category)
    return query.all()


@router.get("/info/{category}/{filename}", response_model=ImageInfoResponse)
def image_info(
    category: str,
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Récupère les infos d'une image"""
    return get_image_info(filename, category)


# ============================
# SUPPRESSION
# ============================

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image_route(
    image_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprime une image (uploader ou admin seulement)"""
    asset = db.query(ImageAsset).filter(ImageAsset.id == image_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")

    # Vérifie les permissions
    if asset.uploaded_by_id != current_user.id:
        from models.user import GlobalUserRole
        if current_user.global_role != GlobalUserRole.admin:
            raise HTTPException(status_code=403, detail="Not your image")

    # Supprime le fichier
    delete_image(asset.filename, asset.category)

    # Supprime de la DB
    db.delete(asset)
    db.commit()
    return None