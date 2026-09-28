from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


ALLOWED_IMAGE_TYPES = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
}

MAX_IMAGE_UPLOAD_BYTES = (
    15 * 1024 * 1024
)

MAX_IMAGE_WIDTH = 8192
MAX_IMAGE_HEIGHT = 8192


class UploadValidationError(
    ValueError
):
    pass


def _detect_image_type(
    header,
):
    """
    Signature-based detection.

    We do not trust only the browser
    Content-Type or original extension.
    """

    if (
        len(header) >= 3
        and header[:3]
        == b"\xff\xd8\xff"
    ):
        return "jpeg"

    if (
        len(header) >= 8
        and header[:8]
        == b"\x89PNG\r\n\x1a\n"
    ):
        return "png"

    if (
        len(header) >= 12
        and header[:4] == b"RIFF"
        and header[8:12] == b"WEBP"
    ):
        return "webp"

    return None


def validate_uploaded_image(
    uploaded_file,
):
    size = int(
        getattr(
            uploaded_file,
            "size",
            0
        )
        or 0
    )

    if size <= 0:
        raise UploadValidationError(
            "El archivo esta vacio."
        )

    if size > MAX_IMAGE_UPLOAD_BYTES:
        raise UploadValidationError(
            "La imagen supera el limite "
            "de 15 MB."
        )

    original_position = (
        uploaded_file.tell()
        if hasattr(
            uploaded_file,
            "tell"
        )
        else 0
    )

    header = uploaded_file.read(
        32
    )

    if hasattr(
        uploaded_file,
        "seek"
    ):
        uploaded_file.seek(
            original_position
        )

    detected = _detect_image_type(
        header
    )

    if detected not in (
        ALLOWED_IMAGE_TYPES
    ):
        raise UploadValidationError(
            "Formato no permitido. "
            "Usa JPG, PNG o WebP."
        )

    content_type = (
        getattr(
            uploaded_file,
            "content_type",
            ""
        )
        or ""
    ).lower()

    allowed_mimes = {
        "jpeg": {
            "image/jpeg",
            "image/jpg",
            "",
        },
        "png": {
            "image/png",
            "",
        },
        "webp": {
            "image/webp",
            "",
        },
    }

    if (
        content_type
        not in allowed_mimes[
            detected
        ]
    ):
        raise UploadValidationError(
            "El tipo MIME no coincide "
            "con el contenido real."
        )

    # Optional stronger image parsing
    # if Pillow is available.
    try:
        from PIL import Image

        current = uploaded_file.tell()

        image = Image.open(
            uploaded_file
        )

        image.verify()

        uploaded_file.seek(
            current
        )

        image = Image.open(
            uploaded_file
        )

        width, height = image.size

        if (
            width > MAX_IMAGE_WIDTH
            or height > MAX_IMAGE_HEIGHT
        ):
            raise UploadValidationError(
                "La imagen supera las "
                "dimensiones permitidas."
            )

        uploaded_file.seek(
            0
        )

    except ImportError:
        if hasattr(
            uploaded_file,
            "seek"
        ):
            uploaded_file.seek(
                0
            )

    except UploadValidationError:
        raise

    except Exception:
        raise UploadValidationError(
            "El archivo no es una "
            "imagen valida."
        )

    return detected


def save_project_image(
    *,
    uploaded_file,
    project_id,
    scene_position,
):
    """
    Validate and persist a project image through Django
    default_storage.

    Local FileSystemStorage:
        path -> physical Path

    Remote storage:
        path -> None

    The public URL and storage name remain backend-agnostic.
    """

    detected = (
        validate_uploaded_image(
            uploaded_file
        )
    )

    extension = (
        ALLOWED_IMAGE_TYPES[
            detected
        ]
    )

    filename = (
        f"scene_{scene_position}_"
        f"{uuid4().hex[:16]}"
        f"{extension}"
    )

    storage_name = (
        generated_storage_name(
            category="uploads",
            filename=filename,
            project_id=project_id,
        )
    )

    if hasattr(
        uploaded_file,
        "seek"
    ):
        uploaded_file.seek(0)

    saved_name = (
        default_storage.save(
            storage_name,
            uploaded_file,
        )
    )

    try:

        public_url = (
            default_storage.url(
                saved_name
            )
        )

        size = (
            default_storage.size(
                saved_name
            )
        )

        local_path = (
            storage_local_path(
                saved_name
            )
        )

    except Exception:

        try:
            default_storage.delete(
                saved_name
            )
        except Exception:
            pass

        raise

    return {
        "name": saved_name,
        "path": local_path,
        "url": public_url,
        "format": detected,
        "size": size,
    }


# ============================================================================
# GINGAO V47H - unified generated storage
# ============================================================================

def generated_storage_name(
    *,
    category,
    filename,
    project_id=None,
):
    """
    Return a storage-relative path.

    This name is valid for both local FileSystemStorage
    and future remote/object storage backends.
    """

    category = str(
        category or ""
    ).strip().strip("/\\")

    filename = Path(
        str(filename or "")
    ).name

    if not category:
        raise ValueError(
            "Storage category is required."
        )

    if not filename:
        raise ValueError(
            "Storage filename is required."
        )

    parts = [
        "generated",
        category,
    ]

    if project_id is not None:
        parts.append(
            f"project_{int(project_id)}"
        )

    parts.append(
        filename
    )

    return "/".join(parts)


def save_generated_bytes(
    *,
    category,
    filename,
    content,
    project_id=None,
):
    """
    Save generated binary content through Django storage.
    """

    name = generated_storage_name(
        category=category,
        filename=filename,
        project_id=project_id,
    )

    if isinstance(
        content,
        memoryview,
    ):
        content = content.tobytes()

    if not isinstance(
        content,
        (bytes, bytearray),
    ):
        raise TypeError(
            "content must be bytes-like."
        )

    saved_name = default_storage.save(
        name,
        ContentFile(
            bytes(content)
        ),
    )

    return {
        "name":
            saved_name,

        "url":
            default_storage.url(
                saved_name
            ),

        "size":
            default_storage.size(
                saved_name
            ),
    }


def save_generated_text(
    *,
    category,
    filename,
    text,
    project_id=None,
    encoding="utf-8",
):
    """
    Save generated text through Django storage.
    """

    return save_generated_bytes(
        category=category,
        filename=filename,
        content=str(text).encode(
            encoding
        ),
        project_id=project_id,
    )


def generated_exists(
    storage_name,
):
    return default_storage.exists(
        storage_name
    )


def delete_generated(
    storage_name,
):
    if (
        storage_name
        and default_storage.exists(
            storage_name
        )
    ):
        default_storage.delete(
            storage_name
        )

        return True

    return False


def storage_url(
    storage_name,
):
    return default_storage.url(
        storage_name
    )


def storage_local_path(
    storage_name,
):
    """
    Return a filesystem path only when the active backend
    actually exposes one.

    Remote S3-compatible backends normally do not.
    """

    try:

        return Path(
            default_storage.path(
                storage_name
            )
        )

    except (
        NotImplementedError,
        AttributeError,
    ):

        return None

