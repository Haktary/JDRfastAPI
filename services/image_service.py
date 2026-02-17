# services/image_service.py
import os
import uuid
import shutil
from pathlib import Path
from PIL import Image as PILImage
from fastapi import HTTPException, UploadFile, status
from typing import Optional

# ============================
# CONFIGURATION
# ============================

UPLOAD_DIR = Path("uploads/")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Sous-dossiers par catégorie
UPLOAD_DIRS = {
    "characters": UPLOAD_DIR / "characters",
    "items":      UPLOAD_DIR / "items",
    "monsters":   UPLOAD_DIR / "monsters",
    "maps":       UPLOAD_DIR / "maps",
    "boards":     UPLOAD_DIR / "boards",
    "misc":       UPLOAD_DIR / "misc",
}

def init_upload_dirs():
    """Crée les dossiers d'upload au démarrage"""
    for path in UPLOAD_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)
    print("✅ Upload directories initialized")


def _get_upload_path(category: str) -> Path:
    if category not in UPLOAD_DIRS:
        category = "misc"
    return UPLOAD_DIRS[category]


def _generate_filename(original_filename: str) -> str:
    """Génère un nom de fichier unique"""
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


async def save_image(
    file: UploadFile,
    category: str = "misc",
    resize: Optional[tuple[int, int]] = None,
    quality: int = 85
) -> dict:
    """
    Sauvegarde une image uploadée.
    Retourne les infos de l'image sauvegardée.
    """

    # Vérifie le type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    # Lit le contenu
    content = await file.read()

    # Vérifie la taille
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # Génère le nom et le path
    filename = _generate_filename(file.filename)
    upload_path = _get_upload_path(category)
    file_path = upload_path / filename

    # Sauvegarde avec PIL pour traitement
    try:
        from io import BytesIO
        img = PILImage.open(BytesIO(content))

        # Convertit en RGB si nécessaire (PNG avec transparence -> JPEG)
        if img.mode in ("RGBA", "P") and not filename.endswith(".png"):
            img = img.convert("RGB")

        # Récupère les dimensions originales
        original_width, original_height = img.size

        # Redimensionne si demandé
        if resize:
            img = img.resize(resize, PILImage.LANCZOS)

        # Sauvegarde
        save_kwargs = {}
        if filename.endswith((".jpg", ".jpeg")):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif filename.endswith(".png"):
            save_kwargs["optimize"] = True
        elif filename.endswith(".webp"):
            save_kwargs["quality"] = quality

        img.save(file_path, **save_kwargs)

        final_width, final_height = img.size

        return {
            "filename": filename,
            "category": category,
            "url": f"/uploads/{category}/{filename}",
            "original_size": {"width": original_width, "height": original_height},
            "final_size": {"width": final_width, "height": final_height},
            "file_size": os.path.getsize(file_path),
            "content_type": file.content_type
        }

    except Exception as e:
        # Nettoie si erreur
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )


def resize_existing_image(
    filename: str,
    category: str,
    width: int,
    height: int,
    quality: int = 85,
    keep_ratio: bool = True
) -> dict:
    """
    Redimensionne une image existante.
    Crée une nouvelle version sans écraser l'originale.
    """
    source_path = _get_upload_path(category) / filename

    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    try:
        img = PILImage.open(source_path)
        original_width, original_height = img.size

        if keep_ratio:
            # Calcule les dimensions en gardant le ratio
            ratio = min(width / original_width, height / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
        else:
            new_width, new_height = width, height

        img_resized = img.resize((new_width, new_height), PILImage.LANCZOS)

        # Nouveau filename pour la version redimensionnée
        stem = Path(filename).stem
        ext = Path(filename).suffix
        new_filename = f"{stem}_{new_width}x{new_height}{ext}"
        new_path = _get_upload_path(category) / new_filename

        save_kwargs = {}
        if ext in (".jpg", ".jpeg"):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif ext == ".webp":
            save_kwargs["quality"] = quality

        img_resized.save(new_path, **save_kwargs)

        return {
            "original_filename": filename,
            "resized_filename": new_filename,
            "url": f"/uploads/{category}/{new_filename}",
            "original_size": {"width": original_width, "height": original_height},
            "final_size": {"width": new_width, "height": new_height},
            "file_size": os.path.getsize(new_path),
            "keep_ratio": keep_ratio
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resizing image: {str(e)}"
        )


def process_board_image(
    filename: str,
    category: str,
    canvas_width: int,
    canvas_height: int,
    position_x: int = 0,
    position_y: int = 0,
    img_width: Optional[int] = None,
    img_height: Optional[int] = None,
    quality: int = 85
) -> dict:
    """
    Place une image sur un canvas aux dimensions spécifiées.
    Utile pour le board du MJ.
    """
    source_path = _get_upload_path(category) / filename

    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    try:
        img = PILImage.open(source_path)

        # Redimensionne l'image si des dimensions sont spécifiées
        if img_width and img_height:
            img = img.resize((img_width, img_height), PILImage.LANCZOS)

        # Crée le canvas
        canvas = PILImage.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

        # Convertit l'image en RGBA pour coller sur le canvas
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        canvas.paste(img, (position_x, position_y), img)

        # Sauvegarde
        stem = Path(filename).stem
        new_filename = f"{stem}_canvas_{canvas_width}x{canvas_height}.png"
        new_path = _get_upload_path("boards") / new_filename
        canvas.save(new_path, optimize=True)

        return {
            "filename": new_filename,
            "url": f"/uploads/boards/{new_filename}",
            "canvas_size": {"width": canvas_width, "height": canvas_height},
            "image_position": {"x": position_x, "y": position_y},
            "image_size": {"width": img.width, "height": img.height},
            "file_size": os.path.getsize(new_path)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing board image: {str(e)}"
        )


def delete_image(filename: str, category: str) -> bool:
    """Supprime une image"""
    file_path = _get_upload_path(category) / filename
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def get_image_info(filename: str, category: str) -> dict:
    """Récupère les infos d'une image"""
    file_path = _get_upload_path(category) / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    img = PILImage.open(file_path)
    width, height = img.size

    return {
        "filename": filename,
        "category": category,
        "url": f"/uploads/{category}/{filename}",
        "size": {"width": width, "height": height},
        "file_size": os.path.getsize(file_path),
        "format": img.format,
        "mode": img.mode
    }