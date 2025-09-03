"""Comprehensive input validation and edge case handling.

This module provides robust validation for all inputs to the albumentations-mcp
system, including Base64 images, natural language prompts, and transform parameters.
Handles edge cases like corrupted data, memory limits, and malformed inputs.

Centralized validation system that protects against invalid inputs,
memory exhaustion, and security vulnerabilities. Provides detailed
error messages and graceful degradation strategies.

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

from .errors import (
    ImageValidationError,
    PromptValidationError,
    ResourceLimitError,
    SecurityValidationError,
    ValidationError,
)

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
# Enhanced security patterns with ReDoS protection
SUSPICIOUS_PATTERNS = [
    # Script injection patterns
    r"<script[^>]{0,100}>.*?</script>",  # Script tags (limited quantifier)
    r"javascript:[^\s]{0,200}",  # JavaScript URLs (limited length)
    r"data:text/html[^\s]{0,200}",  # HTML data URLs (limited length)
    r"vbscript:[^\s]{0,200}",  # VBScript URLs (limited length)
    # File system access patterns
    r"file://[^\s]{0,200}",  # File URLs (limited length)
    r"\\\\[^\s]{0,100}",  # UNC paths (limited length)
    # Path traversal patterns (with limits to prevent ReDoS)
    r"(?:\.\./){1,10}",  # Unix path traversal (limited repetition)
    r"(?:\.\.\\){1,10}",  # Windows path traversal (limited repetition)
    # Command injection patterns
    r"[;&|`$(){}[\]]{2,}",  # Multiple shell metacharacters
    r"(?:cmd|powershell|bash|sh)\s+[/\-]",  # Command execution attempts
    # SQL injection patterns
    r"(?:union|select|insert|update|delete|drop)\s+",  # SQL keywords
    r"['\"];?\s*(?:--|\#|/\*)",  # SQL comment patterns
    # LDAP injection patterns
    r"[()&|!*][\w\s]{0,50}[()&|!*]",  # LDAP filter metacharacters
    # XML/XXE patterns
    r"<!(?:DOCTYPE|ENTITY)[^>]{0,200}>",  # XML entity declarations
    r"&[a-zA-Z][a-zA-Z0-9]{0,20};",  # XML entity references
    # Server-side template injection
    r"\{\{[^}]{0,100}\}\}",  # Template expressions (limited length)
    r"\{%[^%]{0,100}%\}",  # Template blocks (limited length)
]

# Compile patterns for performance with timeout protection
SUSPICIOUS_REGEX = []
for pattern in SUSPICIOUS_PATTERNS:
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        # Test pattern with a potentially problematic string to catch ReDoS
        test_string = "a" * 1000
        compiled.search(test_string)
        SUSPICIOUS_REGEX.append(compiled)
    except (re.error, Exception) as e:
        logger.warning(f"Skipping problematic regex pattern {pattern}: {e}")

# Additional security constants
SECURITY_TIMEOUT_SECONDS = 1.0  # Timeout for regex operations


# Get configurable security check length
def _get_max_security_check_length() -> int:
    """Get the maximum security check length from configuration."""
    try:
        from .config import get_max_security_check_length

        return get_max_security_check_length()
    except Exception:
        # Fallback to default if config is not available
        return int(os.getenv("MAX_SECURITY_CHECK_LENGTH", "2000000"))


# Exception classes are now imported from errors.py module


def validate_base64_image(
    image_b64: str,
    strict: bool = True,
    skip_security_length_check: bool = False,
) -> dict[str, Any]:
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
    validation_result: dict[str, Any] = {
        "valid": False,
        "error": None,
        "warnings": [],
        "metadata": {},
        "sanitized_data": None,
    }

    try:
        # Step 1: Basic input validation
        if not _validate_basic_input(image_b64, validation_result, strict):
            return validation_result

        # Step 2: Security validation (can skip length check for image data)
        _validate_security(image_b64, skip_length_check=skip_security_length_check)

        # Step 3: Sanitize and decode Base64 input
        decoded_data = _sanitize_and_decode_base64(image_b64, validation_result, strict)
        if decoded_data is None:
            return validation_result

        # Step 4: Check file size limits
        if not _validate_file_size(decoded_data, validation_result, strict):
            return validation_result

        # Step 5: Validate image format and structure
        if not _validate_image_structure(decoded_data, validation_result, strict):
            return validation_result

        # Step 6: Memory usage estimation and final checks
        _add_memory_estimation(validation_result)

        validation_result["valid"] = True
        logger.debug(f"Image validation passed: {validation_result['metadata']}")

    except (
        SecurityValidationError,
        ResourceLimitError,
        ImageValidationError,
    ) as e:
        validation_result["error"] = str(e)
        if strict:
            raise
    except Exception as e:
        error = f"Unexpected error during image validation: {e!s}"
        validation_result["error"] = error
        logger.error(error, exc_info=True)
        if strict:
            raise ImageValidationError(error, {"original_error": str(e)})

    return validation_result


def _validate_basic_input(
    image_b64: str,
    validation_result: dict[str, Any],
    strict: bool,
) -> bool:
    """Validate basic input requirements."""
    if not image_b64 or not isinstance(image_b64, str):
        error = "Image data must be a non-empty string"
        validation_result["error"] = error
        if strict:
            raise ImageValidationError(error)
        return False
    return True


def _sanitize_and_decode_base64(
    image_b64: str,
    validation_result: dict[str, Any],
    strict: bool,
) -> bytes | None:
    """Sanitize Base64 input and decode to bytes."""
    try:
        from .utils.validation_utils import sanitize_base64_input

        clean_b64 = sanitize_base64_input(image_b64)
        validation_result["sanitized_data"] = clean_b64
    except ImageValidationError as e:
        validation_result["error"] = str(e)
        if strict:
            raise
        return None

    try:
        decoded_data = base64.b64decode(clean_b64, validate=True)
    except (binascii.Error, ValueError) as e:
        error = f"Invalid Base64 encoding: {e!s}"
        validation_result["error"] = error
        validation_result["metadata"]["encoding_error"] = str(e)
        if strict:
            raise ImageValidationError(error, {"original_error": str(e)})
        return None

    # Check for corrupted data that passes base64 decoding
    if len(decoded_data) < 10:  # Too small to be a valid image
        error = "Decoded data too small to be a valid image"
        validation_result["error"] = error
        if strict:
            raise ImageValidationError(error)
        return None

    return decoded_data


def _validate_file_size(
    decoded_data: bytes,
    validation_result: dict[str, Any],
    strict: bool,
) -> bool:
    """Validate file size limits."""
    file_size = len(decoded_data)
    validation_result["metadata"]["file_size_bytes"] = file_size

    if file_size > MAX_FILE_SIZE:
        error = f"Image file too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
        validation_result["error"] = error
        if strict:
            raise ResourceLimitError(
                error,
                {"file_size": file_size, "max_size": MAX_FILE_SIZE},
            )
        return False
    return True


def _validate_image_structure(
    decoded_data: bytes,
    validation_result: dict[str, Any],
    strict: bool,
) -> bool:
    """Validate image format and structure."""
    try:
        # Set decompression bomb protection
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

        with io.BytesIO(decoded_data) as buffer:
            with Image.open(buffer) as img:
                # Force image loading to detect corruption
                img.load()

                # Collect image metadata
                _collect_image_metadata(img, validation_result)

                # Validate dimensions and pixel count
                if not _validate_image_dimensions(img, validation_result, strict):
                    return False

                # Add format and quality warnings
                _add_image_warnings(img, validation_result, len(decoded_data))

    except OSError as e:
        error = f"Cannot open image: {e!s}"
        validation_result["error"] = error
        validation_result["metadata"]["image_error"] = str(e)
        if strict:
            raise ImageValidationError(error, {"original_error": str(e)})
        return False

    except Image.DecompressionBombError as e:
        error = f"Image too large (decompression bomb): {e!s}"
        validation_result["error"] = error
        if strict:
            raise ResourceLimitError(error, {"original_error": str(e)})
        return False

    return True


def _collect_image_metadata(
    img: Image.Image,
    validation_result: dict[str, Any],
) -> None:
    """Collect image metadata."""
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


def _validate_image_dimensions(
    img: Image.Image,
    validation_result: dict[str, Any],
    strict: bool,
) -> bool:
    """Validate image dimensions and pixel count."""
    width, height = img.size

    if width <= 0 or height <= 0:
        error = f"Invalid image dimensions: {width}x{height}"
        validation_result["error"] = error
        if strict:
            raise ImageValidationError(error)
        return False

    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        error = (
            f"Image too large: {width}x{height} "
            f"(max: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT})"
        )
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
        return False

    # Check pixel count for decompression bomb protection
    pixel_count = width * height
    if pixel_count > MAX_IMAGE_PIXELS:
        error = (
            f"Image has too many pixels: {pixel_count} " f"(max: {MAX_IMAGE_PIXELS})"
        )
        validation_result["error"] = error
        if strict:
            raise ResourceLimitError(
                error,
                {
                    "pixel_count": pixel_count,
                    "max_pixels": MAX_IMAGE_PIXELS,
                },
            )
        return False

    return True


def _add_image_warnings(
    img: Image.Image,
    validation_result: dict[str, Any],
    file_size: int,
) -> None:
    """Add warnings for image format and quality issues."""
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


def _add_memory_estimation(validation_result: dict[str, Any]) -> None:
    """Add memory usage estimation to validation result."""
    estimated_memory = _estimate_memory_usage(validation_result["metadata"])
    validation_result["metadata"]["estimated_memory_mb"] = estimated_memory

    if estimated_memory > 500:  # 500MB threshold
        validation_result["warnings"].append(
            f"High memory usage estimated: {estimated_memory:.1f}MB",
        )


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
    validation_result: dict[str, Any] = {
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
            error = (
                f"Prompt too long: {prompt_length} characters "
                f"(max: {MAX_PROMPT_LENGTH})"
            )
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
    transform_name: str,
    parameters: dict[str, Any],
    strict: bool = True,
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
    validation_result: dict[str, Any] = {
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


# Security validation functions


def _validate_security(input_data: str, skip_length_check: bool = False) -> None:
    """Validate input for security issues with comprehensive protection."""
    import time

    # Early length check to prevent DoS (can be skipped for image data)
    if not skip_length_check:
        max_security_length = _get_max_security_check_length()
        if len(input_data) > max_security_length:
            raise SecurityValidationError(
                f"Input too large for security check: {len(input_data)} chars "
                f"(max: {max_security_length})",
            )

    # Check for null bytes and control characters
    if "\x00" in input_data:
        raise SecurityValidationError("Null bytes detected in input")

    # Check for excessive control characters
    control_chars = sum(1 for c in input_data if ord(c) < 32 and c not in "\t\n\r")
    if control_chars > len(input_data) * 0.1:  # More than 10% control chars
        raise SecurityValidationError("Excessive control characters detected")

    # Check for suspicious patterns with timeout protection
    start_time = time.time()
    for pattern in SUSPICIOUS_REGEX:
        # Check if we're taking too long
        if time.time() - start_time > SECURITY_TIMEOUT_SECONDS:
            logger.warning("Security validation timeout, skipping remaining patterns")
            break

        try:
            if pattern.search(input_data):
                raise SecurityValidationError(
                    f"Suspicious pattern detected: {pattern.pattern[:50]}...",
                )
        except SecurityValidationError:
            # Re-raise security validation errors
            raise
        except Exception as e:
            # Log regex errors but don't fail validation
            logger.warning(f"Regex pattern error: {e}")
            continue

    # Check for repeated suspicious characters
    suspicious_chars = [
        "<",
        ">",
        "{",
        "}",
        "(",
        ")",
        "[",
        "]",
        "&",
        "|",
        ";",
        "`",
        "$",
    ]
    for char in suspicious_chars:
        if input_data.count(char) > 20:  # Arbitrary threshold
            raise SecurityValidationError(
                f"Excessive suspicious character '{char}' detected",
            )

    # Check for encoding attacks
    try:
        # Try to detect double-encoding or unusual encodings
        encoded_variants = [
            input_data.encode("utf-8").decode("utf-8"),
            input_data.encode("latin-1", errors="ignore").decode("latin-1"),
        ]
        for variant in encoded_variants:
            if variant != input_data and len(variant) > len(input_data) * 1.5:
                raise SecurityValidationError("Potential encoding attack detected")
    except (UnicodeError, UnicodeDecodeError):
        raise SecurityValidationError("Invalid character encoding detected")


def _estimate_memory_usage(metadata: dict[str, Any]) -> float:
    """Estimate memory usage in MB for image processing."""
    width = metadata.get("width", 0)
    height = metadata.get("height", 0)

    if width <= 0 or height <= 0:
        return 0.0

    # Estimate memory for RGB image (3 bytes per pixel)
    # plus processing overhead
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


def validate_file_path(file_path: str, allowed_dirs: list[str] | None = None) -> str:
    """Validate file path for security issues.

    Args:
        file_path: File path to validate
        allowed_dirs: List of allowed directory prefixes

    Returns:
        Normalized safe file path

    Raises:
        SecurityValidationError: If path is unsafe
    """
    import os
    from pathlib import Path

    if not file_path or not isinstance(file_path, str):
        raise SecurityValidationError("File path must be a non-empty string")

    # Check for path traversal attempts
    if ".." in file_path or "~" in file_path:
        raise SecurityValidationError("Path traversal detected in file path")

    # Check for absolute paths (should be relative)
    if os.path.isabs(file_path):
        raise SecurityValidationError("Absolute paths not allowed")

    # Normalize path
    try:
        normalized_path = os.path.normpath(file_path)
        path_obj = Path(normalized_path)

        # Check for suspicious path components
        for part in path_obj.parts:
            if part.startswith(".") and part not in [".", ".."]:
                raise SecurityValidationError(
                    f"Hidden file/directory not allowed: {part}",
                )

            # Check for reserved names on Windows
            reserved_names = {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                "COM1",
                "COM2",
                "COM3",
                "COM4",
                "COM5",
                "COM6",
                "COM7",
                "COM8",
                "COM9",
                "LPT1",
                "LPT2",
                "LPT3",
                "LPT4",
                "LPT5",
                "LPT6",
                "LPT7",
                "LPT8",
                "LPT9",
            }
            if part.upper() in reserved_names:
                raise SecurityValidationError(f"Reserved filename not allowed: {part}")

        # Check allowed directories if specified
        if allowed_dirs:
            path_str = str(path_obj)
            if not any(
                path_str.startswith(allowed_dir) for allowed_dir in allowed_dirs
            ):
                raise SecurityValidationError(
                    f"Path not in allowed directories: {path_str}",
                )

        return normalized_path

    except (OSError, ValueError) as e:
        raise SecurityValidationError(f"Invalid file path: {e}")


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe file system operations.

    Args:
        filename: Original filename
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename

    Raises:
        SecurityValidationError: If filename cannot be sanitized
    """
    if not filename or not isinstance(filename, str):
        raise SecurityValidationError("Filename must be a non-empty string")

    # Remove or replace dangerous characters
    dangerous_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")

    # Remove control characters
    sanitized = "".join(c for c in sanitized if ord(c) >= 32)

    # Trim whitespace and dots from ends
    sanitized = sanitized.strip(" .")

    # Check length
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext

    # Ensure we have a valid filename
    if not sanitized or sanitized in [".", ".."]:
        sanitized = "file"

    return sanitized
