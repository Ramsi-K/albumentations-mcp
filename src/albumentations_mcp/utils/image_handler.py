"""Low-level image processing and handling utilities.

This module contains the core image processing logic that supports
the main image conversion operations. It handles the actual PIL Image
operations, format validation, and low-level conversions.
"""

import base64
import binascii
import io
import logging
import os
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# Configuration - can be overridden by environment variables
SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG", "WEBP", "TIFF", "BMP"}
MAX_IMAGE_SIZE = (
    int(os.getenv("MAX_IMAGE_WIDTH", "8192")),
    int(os.getenv("MAX_IMAGE_HEIGHT", "8192")),
)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
MAX_PIXELS = int(os.getenv("MAX_PIXELS", str(89_478_485)))  # PIL default


def decode_image_data(image_b64: str) -> bytes:
    """Safely decode base64 image data with size validation."""
    try:
        image_data = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as e:
        from ..errors import ImageConversionError

        raise ImageConversionError(f"Invalid base64 encoding: {e!s}")

    # Check file size before processing
    if len(image_data) > MAX_FILE_SIZE:
        from ..errors import ImageValidationError

        raise ImageValidationError(
            f"Image file too large: {len(image_data)} bytes (max: {MAX_FILE_SIZE})",
        )

    return image_data


def load_image_safely(image_data: bytes) -> Image.Image:
    """Safely load PIL Image with decompression bomb protection."""
    try:
        # Set decompression bomb protection
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS

        # Use BytesIO context manager for proper cleanup
        with io.BytesIO(image_data) as buffer:
            image = Image.open(buffer)

            # Verify image before loading
            if hasattr(image, "size") and image.size:
                width, height = image.size
                if width * height > MAX_PIXELS:
                    from ..errors import ImageConversionError

                    raise ImageConversionError(
                        f"Image too large: {width}x{height} pixels (max: {MAX_PIXELS})",
                    )

            # Force loading to catch truncated/corrupted images
            image.load()
            image_copy = image.copy()

        return image_copy

    except OSError as e:
        from ..errors import ImageConversionError

        raise ImageConversionError(f"Cannot open image: {e!s}")
    except Image.DecompressionBombError as e:
        from ..errors import ImageConversionError

        raise ImageConversionError(f"Image too large (decompression bomb): {e!s}")


def normalize_image_mode(image: Image.Image) -> Image.Image:
    """Normalize image mode to RGB or RGBA."""
    if image.mode in ("RGB", "RGBA"):
        return image

    if image.mode in ("P", "L", "LA"):
        return image.convert("RGB")

    try:
        return image.convert("RGB")
    except Exception as e:
        from ..errors import ImageConversionError

        raise ImageConversionError(
            f"Cannot convert image mode '{image.mode}' to RGB: {e!s}",
        )


def is_supported_format(format_name: str) -> bool:
    """Check if image format is supported."""
    return format_name.upper() in SUPPORTED_FORMATS


def get_supported_formats() -> list[str]:
    """Get list of supported image formats."""
    return list(SUPPORTED_FORMATS)


def get_image_info(image: Image.Image) -> dict[str, Any]:
    """Get comprehensive information about a PIL Image."""
    # Basic validation without circular dependency
    if not isinstance(image, Image.Image):
        from ..errors import ImageValidationError

        raise ImageValidationError("Input must be a PIL Image object")

    if not hasattr(image, "size") or not image.size:
        from ..errors import ImageValidationError

        raise ImageValidationError("Image has no size information")

    info = {
        "width": image.size[0],
        "height": image.size[1],
        "mode": image.mode,
        "format": getattr(image, "format", None),
        "has_transparency": image.mode in ("RGBA", "LA")
        or "transparency" in image.info,
        "channels": len(image.getbands()),
        "pixel_count": image.size[0] * image.size[1],
    }

    return info


def validate_image_dimensions(image: Image.Image) -> None:
    """Validate image dimensions without full validation chain."""
    if not isinstance(image, Image.Image):
        from ..errors import ImageValidationError

        raise ImageValidationError("Input must be a PIL Image object")

    if not hasattr(image, "size") or not image.size:
        from ..errors import ImageValidationError

        raise ImageValidationError("Image has no size information")

    width, height = image.size
    if width <= 0 or height <= 0:
        from ..errors import ImageValidationError

        raise ImageValidationError(f"Invalid image dimensions: {width}x{height}")

    if width > MAX_IMAGE_SIZE[0] or height > MAX_IMAGE_SIZE[1]:
        from ..errors import ImageValidationError

        raise ImageValidationError(
            f"Image too large: {width}x{height} "
            f"(max: {MAX_IMAGE_SIZE[0]}x{MAX_IMAGE_SIZE[1]})",
        )


def load_image_from_source(
    image_source: str, session_dir: str = None, temp_paths: list = None
) -> Image.Image:
    """Load PIL Image from various sources (URL, file path, or base64).

    Args:
        image_source: Image source - can be:
                     - URL (http://example.com/image.jpg)
                     - Local file path (/path/to/image.jpg)
                     - Base64 data (data:image/jpeg;base64,... or raw base64)
        session_dir: Optional session directory for saving temporary files
        temp_paths: Optional list to track temporary file paths

    Returns:
        PIL Image object

    Raises:
        ImageConversionError: If image cannot be loaded
        ImageValidationError: If image is invalid
    """
    import urllib.request
    from pathlib import Path

    source = image_source.strip()

    # Check if it's a URL
    if source.startswith(("http://", "https://")):
        try:
            logger.info(f"Loading image from URL: {source}")
            with urllib.request.urlopen(source) as response:
                image_data = response.read()

            with io.BytesIO(image_data) as buffer:
                image = Image.open(buffer)
                image.load()

            # Save URL-loaded image to session temp directory if provided
            if session_dir and temp_paths is not None:
                temp_path = _save_temp_image_to_session(
                    image, session_dir, "url_download", temp_paths
                )
                logger.debug(f"Saved URL image to temp: {temp_path}")

        except Exception as e:
            from ..errors import ImageConversionError

            raise ImageConversionError(f"Failed to load image from URL: {e}")

    # Check if it's a file path
    elif Path(source).exists():
        try:
            logger.info(f"Loading image from file: {source}")

            # Validate path security
            if not _validate_path_security(source, session_dir):
                from ..errors import ImageValidationError

                raise ImageValidationError(f"Invalid or unsafe file path: {source}")

            image = Image.open(source)
            image.load()

            # For pasted/external files, save copy to session temp directory if provided
            if (
                session_dir
                and temp_paths is not None
                and not _is_user_original_file(source, session_dir)
            ):
                temp_path = _save_temp_image_to_session(
                    image, session_dir, "pasted_file", temp_paths
                )
                logger.debug(f"Saved pasted image to temp: {temp_path}")

        except Exception as e:
            from ..errors import ImageConversionError

            raise ImageConversionError(f"Failed to load image from file: {e}")

    # Assume it's base64 data
    else:
        logger.info("Loading image from base64 data")
        # Use the main conversion function
        from ..image_conversions import base64_to_pil

        image = base64_to_pil(source)

    # Basic validation
    validate_image_dimensions(image)

    # Convert to RGB if needed
    if image.mode not in ("RGB", "RGBA"):
        logger.debug(f"Converting image from {image.mode} to RGB")
        image = image.convert("RGB")

    return image


def validate_image(image: Image.Image) -> None:
    """Full image validation with comprehensive checks.

    Args:
        image: PIL Image to validate

    Raises:
        ImageValidationError: If image is invalid
    """
    validate_image_dimensions(image)

    try:
        # Check if image data is accessible
        image.getpixel((0, 0))
    except Exception:
        from ..errors import ImageValidationError

        raise ImageValidationError("Cannot access image pixel data")

    # Verify image can be converted to array
    try:
        import numpy as np

        np.array(image)
    except Exception as e:
        from ..errors import ImageValidationError

        raise ImageValidationError(f"Cannot convert image to numpy array: {e!s}")

    logger.debug(
        f"Image validation passed: {image.size[0]}x{image.size[1]}, mode: {image.mode}"
    )


def _save_temp_image_to_session(
    image: Image.Image, session_dir: str, prefix: str, temp_paths: list
) -> str | None:
    """Save image to session temp directory with proper format preservation."""
    try:
        from pathlib import Path

        # Create session temp directory
        temp_dir = Path(session_dir) / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Determine format and extension
        original_format = image.format or "PNG"
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "TIFF": "tiff"}
        extension = ext_map.get(original_format.upper(), "png")

        # Generate unique filename
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}_{unique_id}.{extension}"
        temp_path = temp_dir / filename

        # Save with format-specific options
        save_kwargs = {"format": original_format}
        if original_format.upper() == "JPEG":
            save_kwargs["quality"] = 85
            save_kwargs["optimize"] = True
            # Convert RGBA to RGB for JPEG
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
        elif original_format.upper() == "PNG":
            save_kwargs["optimize"] = True
        elif original_format.upper() == "WEBP":
            save_kwargs["lossless"] = True
            save_kwargs["quality"] = 100

        image.save(temp_path, **save_kwargs)

        # Track temp file
        temp_paths.append(str(temp_path))

        logger.debug(f"Saved temp image: {temp_path}")
        return str(temp_path)

    except Exception as e:
        logger.warning(f"Failed to save temp image: {e}")
        return None


def _validate_path_security(path: str, session_dir: str = None) -> bool:
    """Validate path for security (prevent path traversal, symlinks)."""
    try:
        from pathlib import Path

        path_obj = Path(path)

        # Reject symlinks
        if path_obj.is_symlink():
            return False

        # If session_dir provided, ensure path is not outside it (for relative paths)
        if session_dir and not os.path.isabs(path):
            session_path = Path(session_dir)
            try:
                # Resolve to check if it's within session directory
                resolved_path = (session_path / path).resolve()
                if not str(resolved_path).startswith(str(session_path.resolve())):
                    return False
            except Exception:
                return False

        # Reject paths with '..' segments
        if ".." in path_obj.parts:
            return False

        return True
    except Exception:
        return False


def _is_user_original_file(path: str, session_dir: str) -> bool:
    """Check if file is a user original (not a temp file that should be copied)."""
    try:
        from pathlib import Path

        path_obj = Path(path)
        session_path = Path(session_dir)

        # If file is already within session directory, it's likely a temp file
        try:
            path_obj.resolve().relative_to(session_path.resolve())
            return False  # It's within session dir, so it's a temp file
        except ValueError:
            return True  # It's outside session dir, so it's a user original

    except Exception:
        return True  # Default to treating as user original for safety
