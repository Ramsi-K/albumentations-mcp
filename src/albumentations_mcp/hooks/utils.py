"""Shared utilities for hook implementations.

This module contains common patterns and utilities used across multiple hooks
to reduce code duplication and improve maintainability.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Constants for validation thresholds
MIN_IMAGE_SIZE = 32
MAX_IMAGE_SIZE = 4096
MIN_ASPECT_RATIO = 0.1
MAX_ASPECT_RATIO = 10
MAX_TRANSFORMS_WARNING = 5
MIN_IMAGE_QUALITY = 50
MAX_PROMPT_LENGTH = 1000
HIGH_BLUR_LIMIT = 50
MAX_ROTATION_DEGREES = 45
HIGH_BRIGHTNESS_CONTRAST = 0.5
HIGH_NOISE_VARIANCE = 100
MIN_CROP_SIZE = 64
LOW_PROBABILITY_THRESHOLD = 0.1
HIGH_COMPLEXITY_THRESHOLD = 3
MAX_VERSION_ATTEMPTS = 1000

# Performance rating thresholds
EXCELLENT_TIME_THRESHOLD = 0.1
GOOD_TIME_THRESHOLD = 0.5
FAIR_TIME_THRESHOLD = 1.0

# File size constants
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
BYTES_PER_GB = 1024 * 1024 * 1024


def validate_image_format(image_format: str) -> bool:
    """Check if image format is supported."""
    return image_format in ["JPEG", "PNG", "WEBP", "TIFF"]


def validate_image_mode(image_mode: str) -> bool:
    """Check if image mode is recommended."""
    return image_mode in ["RGB", "RGBA", "L"]


def check_image_size_warnings(width: int, height: int) -> list[str]:
    """Generate warnings for problematic image sizes."""
    warnings = []

    if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
        warnings.append(
            f"Image is very small ({width}x{height}). "
            "Some transforms may not work properly.",
        )

    if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
        warnings.append(
            f"Image is very large ({width}x{height}). "
            "Processing may be slow or consume significant memory.",
        )

    # Check aspect ratio
    aspect_ratio = width / height
    if aspect_ratio > MAX_ASPECT_RATIO or aspect_ratio < MIN_ASPECT_RATIO:
        warnings.append(
            f"Extreme aspect ratio ({aspect_ratio:.2f}). "
            "Some transforms may produce unexpected results.",
        )

    return warnings


def sanitize_filename(text: str, max_length: int = 30) -> str:
    """Sanitize text for use in filename - delegates to validation.py."""
    from ..validation import sanitize_filename as _sanitize_filename

    try:
        return _sanitize_filename(text, max_length)
    except Exception:
        # Fallback for simple cases
        return "untitled" if not text else text[:max_length]


def categorize_transform(transform_name: str) -> str:
    """Categorize transform by type."""
    categories = {
        "blur": ["Blur", "GaussianBlur", "MotionBlur", "MedianBlur"],
        "color": [
            "RandomBrightnessContrast",
            "HueSaturationValue",
            "ColorJitter",
        ],
        "geometric": [
            "Rotate",
            "HorizontalFlip",
            "VerticalFlip",
            "RandomRotate90",
        ],
        "noise": ["GaussNoise", "ISONoise", "MultiplicativeNoise"],
        "crop": ["RandomCrop", "CenterCrop", "RandomResizedCrop"],
    }

    for category, transforms in categories.items():
        if transform_name in transforms:
            return category
    return "other"


def calculate_transform_complexity(
    transform_name: str,
    parameters: dict[str, Any],
) -> int:
    """Calculate complexity score for a transform (1-5 scale)."""
    base_complexity = {
        "HorizontalFlip": 1,
        "VerticalFlip": 1,
        "RandomRotate90": 1,
        "Blur": 2,
        "GaussianBlur": 2,
        "RandomBrightnessContrast": 2,
        "MotionBlur": 3,
        "HueSaturationValue": 3,
        "Rotate": 3,
        "GaussNoise": 3,
        "RandomCrop": 4,
        "RandomResizedCrop": 4,
    }.get(transform_name, 2)

    # Adjust based on parameters
    param_complexity = min(len(parameters), 3)  # Cap at 3

    return min(base_complexity + param_complexity, 5)


def check_transform_conflicts(transforms: list[dict[str, Any]]) -> list[str]:
    """Check for potentially conflicting transform combinations."""
    warnings = []
    transform_names = [t.get("name") for t in transforms]

    # Check for multiple blur transforms
    blur_transforms = [
        name for name in transform_names if categorize_transform(name) == "blur"
    ]
    if len(blur_transforms) > 1:
        warnings.append(
            f"Multiple blur transforms detected: {blur_transforms}. "
            "This may cause excessive blurring.",
        )

    # Check for conflicting flip transforms
    if "HorizontalFlip" in transform_names and "VerticalFlip" in transform_names:
        warnings.append(
            "Both horizontal and vertical flips detected. "
            "Consider using RandomRotate90 for similar effect.",
        )

    # Check for crop after resize
    crop_transforms = [name for name in transform_names if "Crop" in name]
    resize_transforms = [name for name in transform_names if "Resize" in name]
    if crop_transforms and resize_transforms:
        warnings.append(
            "Both crop and resize transforms detected. "
            "Order matters - consider using RandomResizedCrop instead.",
        )

    # Check for too many transforms
    if len(transforms) > MAX_TRANSFORMS_WARNING:
        warnings.append(
            f"Many transforms specified ({len(transforms)}). "
            "This may significantly slow processing and degrade quality.",
        )

    return warnings


def safe_file_operation(operation_func, *args, **kwargs):
    """Safely execute file operations with error handling."""
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"File operation failed: {e}")
        return None


def ensure_directory_exists(directory_path: Path) -> bool:
    """Ensure directory exists, create if necessary."""
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return False


def rate_performance(processing_time: float, transform_count: int) -> str:
    """Rate processing performance based on time per transform."""
    if transform_count == 0:
        return "unknown"

    time_per_transform = processing_time / transform_count

    if time_per_transform < EXCELLENT_TIME_THRESHOLD:
        return "excellent"
    if time_per_transform < GOOD_TIME_THRESHOLD:
        return "good"
    if time_per_transform < FAIR_TIME_THRESHOLD:
        return "fair"
    return "slow"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    if size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.1f} KB"
    if size_bytes < BYTES_PER_GB:
        return f"{size_bytes / BYTES_PER_MB:.1f} MB"
    return f"{size_bytes / BYTES_PER_GB:.1f} GB"


def extract_metadata_safely(context, key: str, default=None):
    """Safely extract metadata with fallback."""
    try:
        return context.metadata.get(key, default)
    except (AttributeError, KeyError):
        return default
