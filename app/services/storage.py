from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


async def save_product_image(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    if upload.content_type not in settings.allowed_image_types or upload.content_type not in EXTENSIONS:
        raise ValueError("Only JPG, PNG and WEBP images are allowed.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"Image must be smaller than {settings.MAX_UPLOAD_SIZE_MB} MB.")

    try:
        check_image = Image.open(BytesIO(content))
        check_image.verify()
        image = Image.open(BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc

    if image.width > 4000 or image.height > 4000:
        image.thumbnail((4000, 4000))
    if upload.content_type == "image/jpeg" and image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{EXTENSIONS[upload.content_type]}"
    destination = settings.upload_dir / filename
    save_options = {"optimize": True}
    if upload.content_type in {"image/jpeg", "image/webp"}:
        save_options["quality"] = 88
    image.save(destination, format=FORMATS[upload.content_type], **save_options)
    return f"/uploads/{filename}"


def delete_local_image(image_path: str | None) -> None:
    if not image_path or not image_path.startswith("/uploads/"):
        return
    filename = Path(image_path).name
    target = (settings.upload_dir / filename).resolve()
    upload_root = settings.upload_dir.resolve()
    if target.parent == upload_root and target.exists():
        target.unlink()
