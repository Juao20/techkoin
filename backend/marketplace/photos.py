"""Photo processing: validation, EXIF removal, WebP conversion, resizing, perceptual hash."""

import io

import imagehash
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 1600
THUMB_SIDE = 480
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidPhoto(ValueError):
    pass


def _webp(img: Image.Image, side: int, quality: int) -> ContentFile:
    copy = img.copy()
    copy.thumbnail((side, side), Image.LANCZOS)
    buf = io.BytesIO()
    copy.save(buf, format="WEBP", quality=quality, method=4)  # re-encoding drops EXIF
    return ContentFile(buf.getvalue())


def process_upload(upload) -> tuple[ContentFile, ContentFile, str]:
    if upload.size > MAX_BYTES:
        raise InvalidPhoto("La photo dépasse 10 Mo. Réduisez sa taille et réessayez.")
    try:
        img = Image.open(upload)
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidPhoto("Ce fichier n'est pas une image valide.") from exc
    if img.format not in ALLOWED_FORMATS:
        raise InvalidPhoto("Format non accepté. Utilisez une photo JPEG, PNG ou WebP.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    phash = str(imagehash.phash(img))
    return _webp(img, MAX_SIDE, 82), _webp(img, THUMB_SIDE, 78), phash
