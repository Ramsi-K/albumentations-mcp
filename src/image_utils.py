"""Image handling utilities for Base64 ↔ PIL Image conversion.

This module provides robust image conversion utilities with comprehensive error handling
and validation for the albumentations-mcp server.
"""

import base64
import binascii
import io
import logging
import os
from typing import List, Dict, Any
from PIL import Image, ImageFile
import numpy as np

# Enable loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)

# Configuration - can be overridden by environment variables
SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG", "WEBP", "TIFF", "BMP"}
MAX_IMAGE_SIZE = (
    int(os.getenv("MAX_IMAGE_WIDTH", "8192")),
    int(os.getenv("MAX_IMAGE_HEIGHT", "8192")),
)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
MAX_PIXELS = int(os.getenv("MAX_PIXELS", str(89_478_485)))  # PIL default


class ImageConversionError(Exception):
    """Raised when image conversion fails."""

    pass


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    pass


def _sanitize_base64_input(image_b64: str) -> str:
    """Sanitize and validate base64 input string.

    Args:
        image_b64: Raw base64 input string

    Returns:
        Clean base64 string without data URL prefix

    Raises:
        ImageConversionError: If input is invalid
    """
    if not image_b64 or not isinstance(image_b64, str):
        raise ImageConversionError("Image data must be a non-empty string")

    # Remove data URL prefix if present
    if image_b64.startswith("data:image/"):
        if "," not in image_b64:
            raise ImageConversionError("Invalid data URL format")
        image_b64 = image_b64.split(",", 1)[1]

    # Validate base64 string
    clean_b64 = image_b64.strip()
    if not clean_b64:
        raise ImageConversionError("Empty base64 data")

    # Add padding if missing
    missing_padding = len(clean_b64) % 4
    if missing_padding:
        clean_b64 += "=" * (4 - missing_padding)

    return clean_b64


def _decode_image_data(image_b64: str) -> bytes:
    """Safely decode base64 image data with size validation.

    Args:
        image_b64: Clean base64 string

    Returns:
        Decoded image bytes

    Raises:
        ImageConversionError: If decoding fails
        ImageValidationError: If data is too large
    """
    try:
        image_data = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ImageConversionError(f"Invalid base64 encoding: {str(e)}")

    # Check file size before processing
    if len(image_data) > MAX_FILE_SIZE:
        raise ImageValidationError(
            f"Image file too large: {len(image_data)} bytes "
            f"(max: {MAX_FILE_SIZE})"
        )

    return image_data


def _load_image_safely(image_data: bytes) -> Image.Image:
    """Safely load PIL Image with decompression bomb protection.

    Args:
        image_data: Raw image bytes

    Returns:
        Loaded PIL Image

    Raises:
        ImageConversionError: If image cannot be loaded
    """
    try:
        # Set decompression bomb protection
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS

        image = Image.open(io.BytesIO(image_data))

        # Verify image before loading
        if hasattr(image, "size") and image.size:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise ImageConversionError(
                    f"Image too large: {width}x{height} pixels "
                    f"(max: {MAX_PIXELS})"
                )

        # Force loading to catch truncated/corrupted images
        image.load()
        return image

    except (OSError, IOError) as e:
        raise ImageConversionError(f"Cannot open image: {str(e)}")
    except Image.DecompressionBombError as e:
        raise ImageConversionError(
            f"Image too large (decompression bomb): {str(e)}"
        )


def _normalize_image_mode(image: Image.Image) -> Image.Image:
    """Normalize image mode to RGB or RGBA.

    Args:
        image: PIL Image to normalize

    Returns:
        Image in RGB or RGBA mode

    Raises:
        ImageConversionError: If mode conversion fails
    """
    if image.mode in ("RGB", "RGBA"):
        return image

    if image.mode in ("P", "L", "LA"):
        # Convert palette and grayscale images to RGB
        return image.convert("RGB")

    # For other modes, try to convert to RGB
    try:
        return image.convert("RGB")
    except Exception as e:
        raise ImageConversionError(
            f"Cannot convert image mode '{image.mode}' to RGB: {str(e)}"
        )


def base64_to_pil(image_b64: str) -> Image.Image:
    """Convert Base64 string to PIL Image with comprehensive error handling.

    Args:
        image_b64: Base64 encoded image string (with or without data URL prefix)

    Returns:
        PIL Image object in RGB or RGBA mode

    Raises:
        ImageConversionError: If image data is invalid or conversion fails
        ImageValidationError: If image doesn't meet validation criteria
    """
    try:
        # Step 1: Sanitize input
        clean_b64 = _sanitize_base64_input(image_b64)

        # Step 2: Decode safely
        image_data = _decode_image_data(clean_b64)

        # Step 3: Load image with protection
        image = _load_image_safely(image_data)

        # Step 4: Validate image
        validate_image(image)

        # Step 5: Normalize mode
        image = _normalize_image_mode(image)

        logger.debug(
            f"Successfully converted base64 to PIL image: "
            f"{image.size}, mode: {image.mode}"
        )
        return image

    except (ImageConversionError, ImageValidationError):
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Unexpected error during image conversion: {str(e)}"
        )


def pil_to_base64(
    image: Image.Image, format: str = "PNG", quality: int = 95
) -> str:
    """Convert PIL Image to Base64 string with format validation.

    Args:
        image: PIL Image object
        format: Output format (PNG, JPEG, WEBP, etc.)
        quality: JPEG quality (1-100, ignored for PNG)

    Returns:
        Base64 encoded image string

    Raises:
        ImageConversionError: If conversion fails
        ImageValidationError: If image or format is invalid
    """
    if not isinstance(image, Image.Image):
        raise ImageConversionError("Input must be a PIL Image object")

    # Validate format
    format = format.upper()
    if format not in SUPPORTED_FORMATS:
        raise ImageValidationError(
            f"Unsupported format '{format}'. "
            f"Supported: {SUPPORTED_FORMATS}"
        )

    # Validate image
    validate_image(image)

    try:
        buffer = io.BytesIO()

        # Handle format-specific options
        save_kwargs = {"format": format}
        if format == "JPEG":
            save_kwargs["quality"] = max(1, min(100, quality))
            save_kwargs["optimize"] = True
            # Convert RGBA to RGB for JPEG
            if image.mode == "RGBA":
                # Create white background
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(
                    image, mask=image.split()[-1]
                )  # Use alpha channel as mask
                image = background
        elif format == "PNG":
            save_kwargs["optimize"] = True

        image.save(buffer, **save_kwargs)
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.debug(
            f"Successfully converted PIL image to base64: "
            f"format={format}, size={len(base64_data)}"
        )
        return base64_data

    except Exception as e:
        raise ImageConversionError(
            f"Failed to convert image to base64: {str(e)}"
        )


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image with validation.

    Args:
        array: Numpy array representing image (H, W, C) or (H, W)

    Returns:
        PIL Image object

    Raises:
        ImageConversionError: If conversion fails
        ImageValidationError: If array format is invalid
    """
    if not isinstance(array, np.ndarray):
        raise ImageConversionError("Input must be a numpy array")

    try:
        # Validate array dimensions
        if array.ndim not in (2, 3):
            raise ImageValidationError(
                f"Array must be 2D or 3D, got {array.ndim}D"
            )

        if array.ndim == 3 and array.shape[2] not in (1, 3, 4):
            raise ImageValidationError(
                f"3D array must have 1, 3, or 4 channels, "
                f"got {array.shape[2]}"
            )

        # Handle different data types
        if array.dtype == np.float32 or array.dtype == np.float64:
            # Assume values are in [0, 1] range
            if array.max() <= 1.0 and array.min() >= 0.0:
                array = (array * 255).astype(np.uint8)
            else:
                raise ImageValidationError(
                    "Float arrays must have values in [0, 1] range"
                )
        elif array.dtype != np.uint8:
            # Try to convert to uint8
            array = array.astype(np.uint8)

        # Convert to PIL Image
        if array.ndim == 2:
            image = Image.fromarray(array)
        elif array.shape[2] == 1:
            image = Image.fromarray(array.squeeze(2))
        elif array.shape[2] == 3:
            image = Image.fromarray(array)
        elif array.shape[2] == 4:
            image = Image.fromarray(array)

        # Validate resulting image
        validate_image(image)

        logger.debug(
            f"Successfully converted numpy array to PIL image: "
            f"{image.size}, mode: {image.mode}"
        )
        return image

    except (ImageConversionError, ImageValidationError):
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Failed to convert numpy array to PIL image: {str(e)}"
        )


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array.

    Args:
        image: PIL Image object

    Returns:
        Numpy array (H, W, C) with uint8 dtype

    Raises:
        ImageConversionError: If conversion fails
    """
    if not isinstance(image, Image.Image):
        raise ImageConversionError("Input must be a PIL Image object")

    try:
        validate_image(image)
        array = np.array(image)

        # Ensure 3D array for consistency
        if array.ndim == 2:
            array = np.expand_dims(array, axis=2)

        logger.debug(
            f"Successfully converted PIL image to numpy array: "
            f"{array.shape}, dtype: {array.dtype}"
        )
        return array

    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Failed to convert PIL image to numpy array: {str(e)}"
        )


def validate_image(image: Image.Image) -> None:
    """Validate PIL Image format and properties.

    Args:
        image: PIL Image to validate

    Raises:
        ImageValidationError: If image is invalid
    """
    if not isinstance(image, Image.Image):
        raise ImageValidationError("Input must be a PIL Image object")

    try:
        # Check if image is loaded
        if not hasattr(image, "size") or not image.size:
            raise ImageValidationError("Image has no size information")

        width, height = image.size

        # Check dimensions
        if width <= 0 or height <= 0:
            raise ImageValidationError(
                f"Invalid image dimensions: {width}x{height}"
            )

        if width > MAX_IMAGE_SIZE[0] or height > MAX_IMAGE_SIZE[1]:
            raise ImageValidationError(
                f"Image too large: {width}x{height} "
                f"(max: {MAX_IMAGE_SIZE[0]}x{MAX_IMAGE_SIZE[1]})"
            )

        # Check if image data is accessible
        try:
            image.getpixel((0, 0))
        except Exception:
            raise ImageValidationError("Cannot access image pixel data")

        # Verify image can be converted to array
        try:
            np.array(image)
        except Exception as e:
            raise ImageValidationError(
                f"Cannot convert image to numpy array: {str(e)}"
            )

        logger.debug(
            f"Image validation passed: {width}x{height}, mode: {image.mode}"
        )

    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageValidationError(
            f"Unexpected error during image validation: {str(e)}"
        )


def get_image_info(image: Image.Image) -> Dict[str, Any]:
    """Get comprehensive information about a PIL Image.

    Args:
        image: PIL Image object

    Returns:
        Dictionary with image information

    Raises:
        ImageValidationError: If image is invalid
    """
    validate_image(image)

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


def is_supported_format(format_name: str) -> bool:
    """Check if image format is supported.

    Args:
        format_name: Format name (e.g., "PNG", "JPEG")

    Returns:
        True if format is supported
    """
    return format_name.upper() in SUPPORTED_FORMATS


def get_supported_formats() -> List[str]:
    """Get list of supported image formats.

    Returns:
        List of supported format names
    """
    return list(SUPPORTED_FORMATS)
