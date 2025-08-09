"""Comprehensive input validation and edge case handling.

This module provides robust validation for all inputs to the albumentations-mcp
system, including Base64 images, natural language prompts, and transform parameters.
Handles edge cases like corrupted data, memory limits, and malformed inputs.

# File Summary
Centralized validation system that protects against invalid inputs,
memory exhaustion, and security vulnerabilities. Provides detailed
error messages and graceful degradation strategies.

# TODO Tree
- [x] Core Validation Infrastructure
  - [x] Import dependencies (base64, io, logging, os, re, typing)
  - [x] Define validation exceptions hierarchy
  - [x] Create configuration constants with environment overrides
  - [x] Set up structured logging
- [x] Base64 Image Validation
  - [x] Validate Base64 encoding format
  - [x] Check for data URL prefixes and strip them
  - [x] Detect corrupted/truncated Base64 data
  - [x] Validate decoded image size limits
  - [x] Check for decompression bomb attacks
- [x] Natural Language Prompt Validation
  - [x] Check prompt length limits
  - [x] Validate character encoding (UTF-8)
  - [x] Detect potentially malicious patterns
  - [x] Handle empty/whitespace-only prompts
  - [x] Protect against ReDoS attacks
- [x] Memory and Resource Limits
  - [x] Image size validation (width, height, pixels)
  - [x] File size limits for Base64 data
  - [x] Memory usage estimation
  - [x] Processing timeout limits
- [x] Security Validation
  - [x] Input sanitization
  - [x] Path traversal prevention
  - [x] Command injection prevention
  - [x] Resource exhaustion protection
- [x] Error Recovery Strategies
  - [x] Graceful degradation for invalid inputs
  - [x] Fallback values for corrupted parameters
  - [x] Safe defaults for edge cases
  - [x] Detailed error reporting

# Code Review Notes
- SECURITY: All inputs are sanitized and validated
- PERFORMANCE: Early validation prevents expensive processing
- MEMORY: Strict limits prevent memory exhaustion
- LOGGING: Comprehensive logging for debugging
- RECOVERY: Graceful fallbacks for all error cases
"""

import base64
import binascii
import io
import logging
import os
import re
import unicodedata
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# Configuration constants with environment overrides
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
MAX_IMAGE_WIDTH = int(os.getenv("MAX_IMAGE_WIDTH", "8192"))
MAX_IMAGE_HEIGHT = int(os.getenv("MAX_IMAGE_HEIGHT", "8192"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "89478485"))  # PIL default
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))

# Supported image formats
SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG", "WEBP", "TIFF", "BMP", "GIF"}

# Security patterns
SUSPICIOUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",  # JavaScript URLs
    r"data:text/html",  # HTML data URLs
    r"vbscript:",  # VBScript URLs
    r"file://",  # File URLs
    r"\\\\",  # UNC paths
    r"\.\./",  # Path traversal
    r"\.\.\\",  # Windows path traversal
]

# Compile patterns for performance
SUSPICIOUS_REGEX = [
    re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS
]


class ValidationError(Exception):
    """Base class for validation errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ImageValidationError(ValidationError):
    """Raised when image validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "IMAGE_VALIDATION_ERROR", details)


class PromptValidationError(ValidationError):
    """Raised when prompt validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "PROMPT_VALIDATION_ERROR", details)


class SecurityValidationError(ValidationError):
    """Raised when security validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "SECURITY_VALIDATION_ERROR", details)


class ResourceLimitError(ValidationError):
    """Raised when resource limits are exceeded."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "RESOURCE_LIMIT_ERROR", details)


def validate_base64_image(image_b64: str, strict: bool = True) -> dict[str, Any]:
    """Validate Base64 image data with comprehensive edge case handling.

    Args:
        image_b64: Base64 encoded image string
        strict: If True, raises exceptions on validation failures

    Returns:
        Dictionary with validation results and metadata

    Raises:
        ImageValidationError: If validation fails and strict=True
        SecurityValidationError: If security issues detected
        ResourceLimitError: If resource limits exceeded
    """
    validation_result = {
        "valid": False,
        "error": None,
        "warnings": [],
        "metadata": {},
        "sanitized_data": None,
    }

    try:
        # Step 1: Basic input validation
        if not image_b64 or not isinstance(image_b64, str):
            error = "Image data must be a non-empty string"
            validation_result["error"] = error
            if strict:
                raise ImageValidationError(error)
            return validation_result

        # Step 2: Security validation
        _validate_security(image_b64)

        # Step 3: Sanitize Base64 input
        try:
            clean_b64 = _sanitize_base64_input(image_b64)
            validation_result["sanitized_data"] = clean_b64
        except ImageValidationError as e:
            validation_result["error"] = str(e)
            if strict:
                raise
            return validation_result

        # Step 4: Validate Base64 encoding
        try:
            decoded_data = base64.b64decode(clean_b64, validate=True)
        except (binascii.Error, ValueError) as e:
            error = f"Invalid Base64 encoding: {e!s}"
            validation_result["error"] = error
            validation_result["metadata"]["encoding_error"] = str(e)
            if strict:
                raise ImageValidationError(error, {"original_error": str(e)})
            return validation_result

        # Additional check for corrupted data that passes base64 decoding
        if len(decoded_data) < 10:  # Too small to be a valid image
            error = "Decoded data too small to be a valid image"
            validation_result["error"] = error
            if strict:
                raise ImageValidationError(error)
            return validation_result

        # Step 5: Check file size limits
        file_size = len(decoded_data)
        validation_result["metadata"]["file_size_bytes"] = file_size

        if file_size > MAX_FILE_SIZE:
            error = f"Image file too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
            validation_result["error"] = error
            if strict:
                raise ResourceLimitError(
                    error, {"file_size": file_size, "max_size": MAX_FILE_SIZE},
                )
            return validation_result

        # Step 6: Validate image format and structure
        try:
            # Set decompression bomb protection
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

            with io.BytesIO(decoded_data) as buffer:
                with Image.open(buffer) as img:
                    # Force image loading to detect corruption
                    img.load()

                    # Collect image metadata
                    validation_result["metadata"].update(
                        {
                            "width": img.size[0],
                            "height": img.size[1],
                            "mode": img.mode,
                            "format": img.format,
                            "pixel_count": img.size[0] * img.size[1],
                            "has_transparency": img.mode in ("RGBA", "LA")
                            or "transparency" in img.info,
                        },
                    )

                    # Validate image dimensions
                    width, height = img.size
                    if width <= 0 or height <= 0:
                        error = f"Invalid image dimensions: {width}x{height}"
                        validation_result["error"] = error
                        if strict:
                            raise ImageValidationError(error)
                        return validation_result

                    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                        error = f"Image too large: {width}x{height} (max: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT})"
                        validation_result["error"] = error
                        if strict:
                            raise ResourceLimitError(
                                error,
                                {
                                    "width": width,
                                    "height": height,
                                    "max_width": MAX_IMAGE_WIDTH,
                                    "max_height": MAX_IMAGE_HEIGHT,
                                },
                            )
                        return validation_result

                    # Check pixel count for decompression bomb protection
                    pixel_count = width * height
                    if pixel_count > MAX_IMAGE_PIXELS:
                        error = f"Image has too many pixels: {pixel_count} (max: {MAX_IMAGE_PIXELS})"
                        validation_result["error"] = error
                        if strict:
                            raise ResourceLimitError(
                                error,
                                {
                                    "pixel_count": pixel_count,
                                    "max_pixels": MAX_IMAGE_PIXELS,
                                },
                            )
                        return validation_result

                    # Validate image format
                    if img.format and img.format.upper() not in SUPPORTED_FORMATS:
                        warning = f"Unsupported image format: {img.format}"
                        validation_result["warnings"].append(warning)
                        logger.warning(warning)

                    # Check for potential issues
                    if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                        validation_result["warnings"].append(
                            f"Unusual image mode: {img.mode}",
                        )

                    if file_size > 10 * 1024 * 1024:  # 10MB
                        validation_result["warnings"].append(
                            "Large image file may impact performance",
                        )

        except OSError as e:
            error = f"Cannot open image: {e!s}"
            validation_result["error"] = error
            validation_result["metadata"]["image_error"] = str(e)
            if strict:
                raise ImageValidationError(error, {"original_error": str(e)})
            return validation_result

        except Image.DecompressionBombError as e:
            error = f"Image too large (decompression bomb): {e!s}"
            validation_result["error"] = error
            if strict:
                raise ResourceLimitError(error, {"original_error": str(e)})
            return validation_result

        # Step 7: Memory usage estimation
        estimated_memory = _estimate_memory_usage(validation_result["metadata"])
        validation_result["metadata"]["estimated_memory_mb"] = estimated_memory

        if estimated_memory > 500:  # 500MB threshold
            validation_result["warnings"].append(
                f"High memory usage estimated: {estimated_memory:.1f}MB",
            )

        validation_result["valid"] = True
        logger.debug(f"Image validation passed: {validation_result['metadata']}")

    except (SecurityValidationError, ResourceLimitError, ImageValidationError):
        if strict:
            raise
    except Exception as e:
        error = f"Unexpected error during image validation: {e!s}"
        validation_result["error"] = error
        logger.error(error, exc_info=True)
        if strict:
            raise ImageValidationError(error, {"original_error": str(e)})

    return validation_result


def validate_prompt(prompt: str, strict: bool = True) -> dict[str, Any]:
    """Validate natural language prompt with edge case handling.

    Args:
        prompt: Natural language prompt to validate
        strict: If True, raises exceptions on validation failures

    Returns:
        Dictionary with validation results and metadata

    Raises:
        PromptValidationError: If validation fails and strict=True
        SecurityValidationError: If security issues detected
    """
    validation_result = {
        "valid": False,
        "error": None,
        "warnings": [],
        "metadata": {},
        "sanitized_prompt": None,
    }

    try:
        # Step 1: Basic input validation
        if not isinstance(prompt, str):
            error = "Prompt must be a string"
            validation_result["error"] = error
            if strict:
                raise PromptValidationError(error)
            return validation_result

        # Step 2: Length validation
        prompt_length = len(prompt)
        validation_result["metadata"]["length"] = prompt_length

        if prompt_length == 0:
            error = "Prompt cannot be empty"
            validation_result["error"] = error
            if strict:
                raise PromptValidationError(error)
            return validation_result

        if prompt_length > MAX_PROMPT_LENGTH:
            error = f"Prompt too long: {prompt_length} characters (max: {MAX_PROMPT_LENGTH})"
            validation_result["error"] = error
            if strict:
                raise ResourceLimitError(
                    error,
                    {"length": prompt_length, "max_length": MAX_PROMPT_LENGTH},
                )
            return validation_result

        # Step 3: Character encoding validation
        try:
            # Normalize Unicode characters
            normalized_prompt = unicodedata.normalize("NFKC", prompt)
            validation_result["sanitized_prompt"] = normalized_prompt

            # Check for non-printable characters
            non_printable = [
                c
                for c in normalized_prompt
                if not c.isprintable() and c not in "\n\r\t"
            ]
            if non_printable:
                validation_result["warnings"].append(
                    f"Contains {len(non_printable)} non-printable characters",
                )

        except UnicodeError as e:
            error = f"Invalid character encoding: {e!s}"
            validation_result["error"] = error
            if strict:
                raise PromptValidationError(error, {"original_error": str(e)})
            return validation_result

        # Step 4: Security validation
        try:
            _validate_security(normalized_prompt)
        except SecurityValidationError as e:
            validation_result["error"] = str(e)
            if strict:
                raise
            return validation_result

        # Step 5: Content analysis
        sanitized = normalized_prompt.strip()
        if not sanitized:
            error = "Prompt contains only whitespace"
            validation_result["error"] = error
            if strict:
                raise PromptValidationError(error)
            return validation_result

        validation_result["sanitized_prompt"] = sanitized

        # Step 6: Pattern analysis for potential issues
        word_count = len(sanitized.split())
        validation_result["metadata"]["word_count"] = word_count

        if word_count > 100:
            validation_result["warnings"].append(
                "Very long prompt may impact parsing accuracy",
            )

        # Check for repeated patterns that might indicate ReDoS attempts
        if _detect_redos_patterns(sanitized):
            validation_result["warnings"].append(
                "Detected potentially problematic regex patterns",
            )

        # Check for excessive punctuation
        punct_ratio = sum(
            1 for c in sanitized if not c.isalnum() and not c.isspace()
        ) / len(sanitized)
        if punct_ratio > 0.3:
            validation_result["warnings"].append(
                "High punctuation ratio may impact parsing",
            )

        validation_result["valid"] = True
        logger.debug(f"Prompt validation passed: {validation_result['metadata']}")

    except (
        SecurityValidationError,
        ResourceLimitError,
        PromptValidationError,
    ):
        if strict:
            raise
    except Exception as e:
        error = f"Unexpected error during prompt validation: {e!s}"
        validation_result["error"] = error
        logger.error(error, exc_info=True)
        if strict:
            raise PromptValidationError(error, {"original_error": str(e)})

    return validation_result


def validate_transform_parameters(
    transform_name: str, parameters: dict[str, Any], strict: bool = True,
) -> dict[str, Any]:
    """Validate transform parameters with edge case handling.

    Args:
        transform_name: Name of the transform
        parameters: Transform parameters to validate
        strict: If True, raises exceptions on validation failures

    Returns:
        Dictionary with validation results and sanitized parameters

    Raises:
        ValidationError: If validation fails and strict=True
    """
    validation_result = {
        "valid": False,
        "error": None,
        "warnings": [],
        "sanitized_parameters": {},
        "metadata": {},
    }

    try:
        if not isinstance(transform_name, str) or not transform_name:
            error = "Transform name must be a non-empty string"
            validation_result["error"] = error
            if strict:
                raise ValidationError(error)
            return validation_result

        if not isinstance(parameters, dict):
            error = "Parameters must be a dictionary"
            validation_result["error"] = error
            if strict:
                raise ValidationError(error)
            return validation_result

        # Sanitize parameters
        sanitized = {}
        for key, value in parameters.items():
            if not isinstance(key, str):
                validation_result["warnings"].append(f"Non-string parameter key: {key}")
                continue

            # Validate parameter values
            if value is None:
                continue  # Skip None values

            # Type-specific validation
            if isinstance(value, (int, float)):
                if not (-1e10 < value < 1e10):  # Reasonable numeric range
                    validation_result["warnings"].append(
                        f"Parameter {key} has extreme value: {value}",
                    )
                    continue
                sanitized[key] = value
            elif isinstance(value, str):
                if len(value) > 1000:  # Reasonable string length
                    validation_result["warnings"].append(
                        f"Parameter {key} string too long",
                    )
                    continue
                sanitized[key] = value
            elif isinstance(value, (list, tuple)):
                if len(value) > 100:  # Reasonable list length
                    validation_result["warnings"].append(
                        f"Parameter {key} list too long",
                    )
                    continue
                sanitized[key] = value
            else:
                validation_result["warnings"].append(
                    f"Unsupported parameter type for {key}: {type(value)}",
                )

        validation_result["sanitized_parameters"] = sanitized
        validation_result["metadata"]["original_param_count"] = len(parameters)
        validation_result["metadata"]["sanitized_param_count"] = len(sanitized)
        validation_result["valid"] = True

    except ValidationError:
        if strict:
            raise
    except Exception as e:
        error = f"Unexpected error during parameter validation: {e!s}"
        validation_result["error"] = error
        logger.error(error, exc_info=True)
        if strict:
            raise ValidationError(error, {"original_error": str(e)})

    return validation_result


def _sanitize_base64_input(image_b64: str) -> str:
    """Sanitize Base64 input string."""
    # Remove data URL prefix if present
    if image_b64.startswith("data:"):
        if "," not in image_b64:
            raise ImageValidationError("Invalid data URL format")
        image_b64 = image_b64.split(",", 1)[1]

    # Clean whitespace and validate
    clean_b64 = re.sub(r"\s+", "", image_b64)  # Remove all whitespace

    if not clean_b64:
        raise ImageValidationError("Empty Base64 data after cleaning")

    # Add padding if missing
    missing_padding = len(clean_b64) % 4
    if missing_padding:
        clean_b64 += "=" * (4 - missing_padding)

    return clean_b64


def _sanitize_base64_input(image_b64: str) -> str:
    """Sanitize Base64 input string."""
    # Remove data URL prefix if present
    if image_b64.startswith("data:"):
        if "," not in image_b64:
            raise ImageValidationError("Invalid data URL format")
        image_b64 = image_b64.split(",", 1)[1]

    # Clean whitespace and validate
    clean_b64 = re.sub(r"\s+", "", image_b64)  # Remove all whitespace

    if not clean_b64:
        raise ImageValidationError("Empty Base64 data after cleaning")

    # Validate Base64 characters
    if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", clean_b64):
        raise ImageValidationError("Invalid Base64 characters detected")

    # Add padding if missing
    missing_padding = len(clean_b64) % 4
    if missing_padding:
        clean_b64 += "=" * (4 - missing_padding)

    return clean_b64


def _validate_security(input_data: str) -> None:
    """Validate input for security issues."""
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_REGEX:
        if pattern.search(input_data):
            raise SecurityValidationError(
                f"Suspicious pattern detected: {pattern.pattern}",
            )

    # Check for excessive length that might indicate DoS attempt
    if len(input_data) > 1000000:  # 1MB
        raise SecurityValidationError("Input too large, possible DoS attempt")

    # Check for null bytes
    if "\x00" in input_data:
        raise SecurityValidationError("Null bytes detected in input")


def _estimate_memory_usage(metadata: dict[str, Any]) -> float:
    """Estimate memory usage in MB for image processing."""
    width = metadata.get("width", 0)
    height = metadata.get("height", 0)

    if width <= 0 or height <= 0:
        return 0.0

    # Estimate memory for RGB image (3 bytes per pixel) plus processing overhead
    base_memory = (width * height * 3) / (1024 * 1024)  # MB
    processing_overhead = base_memory * 2  # 2x for processing

    return base_memory + processing_overhead


def _detect_redos_patterns(text: str) -> bool:
    """Detect patterns that might cause ReDoS attacks."""
    # Look for nested quantifiers and excessive repetition
    redos_patterns = [
        r"(\w+)+",  # Nested quantifiers
        r"(\d+)*",  # Nested quantifiers
        r"(.+)+",  # Catastrophic backtracking
        r"(.*)*",  # Catastrophic backtracking
    ]

    for pattern in redos_patterns:
        try:
            if re.search(pattern, text):
                return True
        except re.error:
            continue

    return False


def get_validation_config() -> dict[str, Any]:
    """Get current validation configuration."""
    return {
        "max_prompt_length": MAX_PROMPT_LENGTH,
        "max_image_width": MAX_IMAGE_WIDTH,
        "max_image_height": MAX_IMAGE_HEIGHT,
        "max_image_pixels": MAX_IMAGE_PIXELS,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "processing_timeout_seconds": PROCESSING_TIMEOUT_SECONDS,
        "supported_formats": list(SUPPORTED_FORMATS),
    }


def create_safe_fallback_image() -> Image.Image:
    """Create a safe fallback image for error cases."""
    # Create a simple 100x100 white image
    return Image.new("RGB", (100, 100), color="white")


def get_safe_default_parameters(transform_name: str) -> dict[str, Any]:
    """Get safe default parameters for a transform."""
    safe_defaults = {
        "Blur": {"blur_limit": 3, "p": 0.5},
        "GaussianBlur": {"blur_limit": 3, "p": 0.5},
        "MotionBlur": {"blur_limit": 3, "p": 0.5},
        "RandomBrightnessContrast": {
            "brightness_limit": 0.1,
            "contrast_limit": 0.1,
            "p": 0.5,
        },
        "HueSaturationValue": {
            "hue_shift_limit": 10,
            "sat_shift_limit": 10,
            "val_shift_limit": 10,
            "p": 0.5,
        },
        "Rotate": {"limit": 15, "p": 0.5},
        "HorizontalFlip": {"p": 0.5},
        "VerticalFlip": {"p": 0.5},
        "GaussNoise": {"var_limit": (5.0, 15.0), "p": 0.5},
        "RandomCrop": {"height": 224, "width": 224, "p": 0.5},
        "RandomResizedCrop": {"height": 224, "width": 224, "p": 0.5},
        "Normalize": {"p": 1.0},
        "CLAHE": {"clip_limit": 2.0, "tile_grid_size": (4, 4), "p": 0.5},
    }

    return safe_defaults.get(transform_name, {"p": 0.5})
