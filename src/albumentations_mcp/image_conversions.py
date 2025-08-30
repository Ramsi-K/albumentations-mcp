"""Core image conversion functions for the MCP server.

This module provides the essential image conversion functions needed by the
albumentations-mcp server: Base64 ↔ PIL and PIL ↔ NumPy conversions.
These are the only conversions actually used by the MCP tools.
"""

import base64
import io
import logging
from typing import Any

import numpy as np
from PIL import Image, ImageFile

# Enable loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)

# Import configuration and exceptions
from .errors import ImageConversionError, ImageValidationError
from .utils.image_handler import MAX_IMAGE_SIZE, SUPPORTED_FORMATS


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
        # Use comprehensive validation system
        from .validation import ValidationError, validate_base64_image

        try:
            validation_result = validate_base64_image(image_b64, strict=True)
            clean_b64 = validation_result["sanitized_data"]
        except ValidationError as e:
            # Convert validation errors to image conversion errors for compatibility
            raise ImageConversionError(f"Image validation failed: {e}")

        # Decode the validated Base64 data
        image_data = base64.b64decode(clean_b64)

        # Load image with protection
        from .utils.image_handler import (
            load_image_safely,
            normalize_image_mode,
        )

        image = load_image_safely(image_data)

        # Normalize mode
        image = normalize_image_mode(image)

        logger.debug(
            f"Successfully converted base64 to PIL image: "
            f"{image.size}, mode: {image.mode}",
        )
        return image

    except (ImageConversionError, ImageValidationError):
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Unexpected error during image conversion: {e!s}",
        )


def pil_to_base64(image: Image.Image, format: str = "PNG", quality: int = 95) -> str:
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
            f"Unsupported format '{format}'. Supported: {SUPPORTED_FORMATS}",
        )

    # Validate image using image_handler
    from .utils.image_handler import validate_image_dimensions

    validate_image_dimensions(image)

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
                background.paste(image, mask=image.split()[-1])
                image = background
        elif format == "PNG":
            save_kwargs["optimize"] = True

        image.save(buffer, **save_kwargs)
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.debug(
            f"Successfully converted PIL image to base64: "
            f"format={format}, size={len(base64_data)}",
        )
        return base64_data

    except Exception as e:
        raise ImageConversionError(f"Failed to convert image to base64: {e!s}")


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image for Albumentations processing.

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
            raise ImageValidationError(f"Array must be 2D or 3D, got {array.ndim}D")

        if array.ndim == 3 and array.shape[2] not in (1, 3, 4):
            raise ImageValidationError(
                f"3D array must have 1, 3, or 4 channels, got {array.shape[2]}",
            )

        # Handle different data types
        if array.dtype == np.float32 or array.dtype == np.float64:
            # Assume values are in [0, 1] range
            if array.max() <= 1.0 and array.min() >= 0.0:
                array = (array * 255).astype(np.uint8)
            else:
                raise ImageValidationError(
                    "Float arrays must have values in [0, 1] range",
                )
        elif array.dtype != np.uint8:
            # Try to convert to uint8
            array = array.astype(np.uint8)

        # Convert to PIL Image
        if array.ndim == 2:
            image = Image.fromarray(array)
        elif array.shape[2] == 1:
            image = Image.fromarray(array.squeeze(2))
        elif array.shape[2] == 3 or array.shape[2] == 4:
            image = Image.fromarray(array)

        # Basic validation using image_handler
        from .utils.image_handler import validate_image_dimensions

        validate_image_dimensions(image)

        logger.debug(
            f"Successfully converted numpy array to PIL image: "
            f"{image.size}, mode: {image.mode}",
        )
        return image

    except (ImageConversionError, ImageValidationError):
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Failed to convert numpy array to PIL image: {e!s}",
        )


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array for Albumentations processing.

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
        # Basic validation using image_handler
        from .utils.image_handler import validate_image_dimensions

        validate_image_dimensions(image)

        array = np.array(image)

        # Ensure 3D array for consistency
        if array.ndim == 2:
            array = np.expand_dims(array, axis=2)

        logger.debug(
            f"Successfully converted PIL image to numpy array: "
            f"{array.shape}, dtype: {array.dtype}",
        )
        return array

    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageConversionError(
            f"Failed to convert PIL image to numpy array: {e!s}",
        )


def load_image_from_source(
    image_source: str, session_dir: str = None, temp_paths: list = None
) -> Image.Image:
    """Load PIL Image from various sources - delegates to image handler."""
    from .utils.image_handler import load_image_from_source

    return load_image_from_source(image_source, session_dir, temp_paths)


def validate_image(image: Image.Image) -> None:
    """Full image validation with comprehensive checks - delegates to image handler."""
    from .utils.image_handler import validate_image

    return validate_image(image)
