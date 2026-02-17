# schemas/image.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    category: str
    url: str
    width: Optional[int]
    height: Optional[int]
    file_size: int
    is_global: bool
    created_at: datetime


class ImageResizeRequest(BaseModel):
    filename: str
    category: str
    width: int = Field(..., ge=1, le=4096)
    height: int = Field(..., ge=1, le=4096)
    quality: int = Field(default=85, ge=1, le=100)
    keep_ratio: bool = True


class ImageResizeResponse(BaseModel):
    original_filename: str
    resized_filename: str
    url: str
    original_size: dict
    final_size: dict
    file_size: int
    keep_ratio: bool


class BoardCanvasRequest(BaseModel):
    """Requête pour placer une image sur le canvas du board"""
    filename: str
    category: str
    canvas_width: int = Field(..., ge=100, le=8192)
    canvas_height: int = Field(..., ge=100, le=8192)
    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    img_width: Optional[int] = Field(None, ge=1, le=4096)
    img_height: Optional[int] = Field(None, ge=1, le=4096)
    quality: int = Field(default=85, ge=1, le=100)


class BoardCanvasResponse(BaseModel):
    filename: str
    url: str
    canvas_size: dict
    image_position: dict
    image_size: dict
    file_size: int


class ImageInfoResponse(BaseModel):
    filename: str
    category: str
    url: str
    size: dict
    file_size: int
    format: Optional[str]
    mode: Optional[str]