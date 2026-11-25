"""
Стиснення зображень при імпорті / обслуговуванні медіа.
Мета: менший диск і трафік без помітної втрати якості в каталозі.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

MAX_SIDE = 1200
JPEG_QUALITY = 82


def optimize_image_bytes(
    data: bytes,
    *,
    max_side: int = MAX_SIDE,
    quality: int = JPEG_QUALITY,
) -> tuple[bytes, str]:
    """
    Повертає (байти, розширення без крапки).
    Невдале декодування — оригінал як jpeg-байтів fallback (caller лишає як є).
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return data, "bin"

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        logger.debug("optimize_image_bytes: open failed: %s", exc)
        return data, "bin"

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > max_side:
        scale = max_side / float(longest)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
    optimized = out.getvalue()
    # Якщо стиснення не виграло — лишаємо оригінал
    if len(optimized) >= len(data) and longest <= max_side:
        return data, "bin"
    return optimized, "jpg"


def content_file_from_image_bytes(data: bytes, *, name_stem: str = "photo") -> ContentFile:
    optimized, ext = optimize_image_bytes(data)
    if ext == "bin":
        return ContentFile(data)
    return ContentFile(optimized, name=f"{name_stem}.jpg")


def optimize_file_on_disk(path: Path, *, max_side: int = MAX_SIDE, quality: int = JPEG_QUALITY) -> bool:
    """
    Перезаписує JPEG на місці (шлях у БД не змінюється).
    PNG/WebP пропускаємо тут — інакше зламається розширення у FileField.
    """
    if path.suffix.lower() not in (".jpg", ".jpeg"):
        return False
    try:
        raw = path.read_bytes()
    except OSError:
        return False
    optimized, ext = optimize_image_bytes(raw, max_side=max_side, quality=quality)
    if ext == "bin" or len(optimized) >= len(raw):
        return False
    try:
        path.write_bytes(optimized)
        return True
    except OSError:
        return False
