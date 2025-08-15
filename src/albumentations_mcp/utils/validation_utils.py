"""Input validation and sanitization utilities."""

import re
from typing import Any


def sanitize_base64_input(image_b64: str) -> str:
    """Master function for base64 sanitization - eliminates duplicates.

    Sanitizes and validates base64 input string, removing data URL prefixes
    and adding proper padding.

    Args:
        image_b64: Raw base64 input string

    Returns:
        Clean base64 string without data URL prefix

    Raises:
        ValueError: If input is invalid
    """
    if not image_b64 or not isinstance(image_b64, str):
        raise ValueError("Image data must be a non-empty string")

    # Remove data URL prefix if present
    if image_b64.startswith("data:image/"):
        if "," not in image_b64:
            raise ValueError("Invalid data URL format")
        image_b64 = image_b64.split(",", 1)[1]

    # Validate base64 string
    clean_b64 = image_b64.strip()
    if not clean_b64:
        raise ValueError("Empty base64 data")

    # Add padding if missing
    missing_padding = len(clean_b64) % 4
    if missing_padding:
        clean_b64 += "=" * (4 - missing_padding)

    return clean_b64


def validate_string_input(
    value: Any,
    name: str,
    allow_empty: bool = False,
    max_length: int | None = None,
) -> str:
    """Validate string input with consistent error messages.

    Args:
        value: Value to validate
        name: Name of the parameter for error messages
        allow_empty: Whether to allow empty strings
        max_length: Maximum allowed length

    Returns:
        Validated string

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")

    if not allow_empty and not value:
        raise ValueError(f"{name} cannot be empty")

    if max_length is not None and len(value) > max_length:
        raise ValueError(
            f"{name} too long: {len(value)} characters (max: {max_length})",
        )

    return value


def validate_dict_input(
    value: Any,
    name: str,
    allow_empty: bool = True,
) -> dict[str, Any]:
    """Validate dictionary input with consistent error messages.

    Args:
        value: Value to validate
        name: Name of the parameter for error messages
        allow_empty: Whether to allow empty dictionaries

    Returns:
        Validated dictionary

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a dictionary, got {type(value).__name__}")

    if not allow_empty and not value:
        raise ValueError(f"{name} cannot be empty")

    return value


def validate_list_input(
    value: Any,
    name: str,
    allow_empty: bool = True,
    max_length: int | None = None,
) -> list[Any]:
    """Validate list input with consistent error messages.

    Args:
        value: Value to validate
        name: Name of the parameter for error messages
        allow_empty: Whether to allow empty lists
        max_length: Maximum allowed length

    Returns:
        Validated list

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list, got {type(value).__name__}")

    if not allow_empty and not value:
        raise ValueError(f"{name} cannot be empty")

    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{name} too long: {len(value)} items (max: {max_length})")

    return value


def validate_numeric_range(
    value: float,
    name: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> int | float:
    """Validate numeric value within range.

    Args:
        value: Value to validate
        name: Name of the parameter for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated numeric value

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}")

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} too small: {value} (min: {min_value})")

    if max_value is not None and value > max_value:
        raise ValueError(f"{name} too large: {value} (max: {max_value})")

    return value


def sanitize_parameters(
    parameters: dict[str, Any],
    allowed_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Sanitize parameters dictionary by removing None values and invalid keys.

    Args:
        parameters: Parameters to sanitize
        allowed_keys: Set of allowed parameter keys (None = allow all)

    Returns:
        Sanitized parameters dictionary
    """
    sanitized = {}

    for key, value in parameters.items():
        # Skip None values
        if value is None:
            continue

        # Skip non-string keys
        if not isinstance(key, str):
            continue

        # Skip disallowed keys
        if allowed_keys is not None and key not in allowed_keys:
            continue

        sanitized[key] = value

    return sanitized


# sanitize_filename moved to validation.py for security-focused implementation


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    return re.sub(r"\s+", " ", text.strip())


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]

    return text[:truncate_length] + suffix
