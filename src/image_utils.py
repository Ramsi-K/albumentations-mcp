"""Image handling utilities for Base64 ↔ PIL Image conversion."""

import base64
import io
from typing import Optional
from PIL import Image
import numpy as np


def base64_to_pil(image_b64: str) -> Image.Image:
    """Convert Base64 string to PIL Image.

    Args:
        image_b64: Base64 encoded image string

    Returns:
        PIL Image object

    Raises:
        ValueError: If image data is invalid
    """
    try:
        # Remove data URL prefix if present
        if image_b64.startswith("data:image/"):
            image_b64 = image_b64.split(",", 1)[1]

        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        return image
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")


def pil_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to Base64 string.

    Args:
        image: PIL Image object
        format: Output format (PNG, JPEG, etc.)

    Returns:
        Base64 encoded image string
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image.

    Args:
        array: Numpy array representing image

    Returns:
        PIL Image object
    """
    # Ensure array is in correct format
    if array.dtype != np.uint8:
        array = (array * 255).astype(np.uint8)

    return Image.fromarray(array)


def validate_image_format(image: Image.Image) -> bool:
    """Validate image format and properties.

    Args:
        image: PIL Image to validate

    Returns:
        True if image is valid
    """
    try:
        # Check basic properties
        if image.size[0] == 0 or image.size[1] == 0:
            return False

        # Check if image can be converted to array
        np.array(image)
        return True
    except Exception:
        return False
