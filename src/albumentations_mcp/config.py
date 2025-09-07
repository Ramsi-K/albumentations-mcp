"""Configuration management and validation for albumentations-mcp.

This module handles environment variable validation and provides
configuration defaults for the MCP server.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_environment_variables() -> dict[str, Any]:
    """Validate all environment variables and return validated configuration.

    Returns:
        Dictionary with validated configuration values

    Raises:
        ConfigurationError: If any environment variable has an invalid value
    """
    config = {}
    errors = []

    # Validate STRICT_MODE
    strict_mode_str = os.getenv("STRICT_MODE", "false").lower()
    if strict_mode_str in ("true", "1", "yes", "on"):
        config["STRICT_MODE"] = True
    elif strict_mode_str in ("false", "0", "no", "off"):
        config["STRICT_MODE"] = False
    else:
        errors.append(f"STRICT_MODE must be true/false, got: {strict_mode_str}")

    # Validate MAX_IMAGE_SIZE
    try:
        max_image_size = int(os.getenv("MAX_IMAGE_SIZE", "4096"))
        if max_image_size < 32:
            errors.append("MAX_IMAGE_SIZE must be at least 32 pixels")
        elif max_image_size > 32768:
            errors.append("MAX_IMAGE_SIZE must be at most 32768 pixels")
        else:
            config["MAX_IMAGE_SIZE"] = max_image_size
    except ValueError:
        errors.append(
            f"MAX_IMAGE_SIZE must be an integer, got: {os.getenv('MAX_IMAGE_SIZE')}",
        )

    # Validate MAX_PIXELS_IN
    try:
        max_pixels = int(os.getenv("MAX_PIXELS_IN", "16000000"))
        if max_pixels < 1024:
            errors.append("MAX_PIXELS_IN must be at least 1024 pixels")
        elif max_pixels > 1000000000:  # 1 billion pixels
            errors.append("MAX_PIXELS_IN must be at most 1 billion pixels")
        else:
            config["MAX_PIXELS_IN"] = max_pixels
    except ValueError:
        errors.append(
            f"MAX_PIXELS_IN must be an integer, got: {os.getenv('MAX_PIXELS_IN')}",
        )

    # Validate MAX_BYTES_IN
    try:
        max_bytes = int(os.getenv("MAX_BYTES_IN", "50000000"))
        if max_bytes < 1024:  # 1KB minimum
            errors.append("MAX_BYTES_IN must be at least 1024 bytes")
        elif max_bytes > 1073741824:  # 1GB maximum
            errors.append("MAX_BYTES_IN must be at most 1GB (1073741824 bytes)")
        else:
            config["MAX_BYTES_IN"] = max_bytes
    except ValueError:
        errors.append(
            f"MAX_BYTES_IN must be an integer, got: {os.getenv('MAX_BYTES_IN')}",
        )

    # Validate OUTPUT_DIR
    output_dir = os.getenv("OUTPUT_DIR", "outputs")
    if not output_dir or not output_dir.strip():
        errors.append("OUTPUT_DIR cannot be empty")
    else:
        config["OUTPUT_DIR"] = output_dir.strip()

    # Validate MCP_LOG_LEVEL
    log_level = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in valid_levels:
        errors.append(f"MCP_LOG_LEVEL must be one of {valid_levels}, got: {log_level}")
    else:
        config["MCP_LOG_LEVEL"] = log_level

    # Validate DEFAULT_SEED
    default_seed_str = os.getenv("DEFAULT_SEED")
    if default_seed_str is not None:
        try:
            default_seed = int(default_seed_str)
            if default_seed < 0 or default_seed > 4294967295:  # 2^32 - 1
                errors.append("DEFAULT_SEED must be between 0 and 4294967295")
            else:
                config["DEFAULT_SEED"] = default_seed
        except ValueError:
            errors.append(f"DEFAULT_SEED must be an integer, got: {default_seed_str}")

    # Validate ENABLE_VISION_VERIFICATION
    vision_verify_str = os.getenv("ENABLE_VISION_VERIFICATION", "true").lower()
    if vision_verify_str in ("true", "1", "yes", "on"):
        config["ENABLE_VISION_VERIFICATION"] = True
    elif vision_verify_str in ("false", "0", "no", "off"):
        config["ENABLE_VISION_VERIFICATION"] = False
    else:
        errors.append(
            f"ENABLE_VISION_VERIFICATION must be true/false, got: {vision_verify_str}",
        )

    # Validate MAX_SECURITY_CHECK_LENGTH
    try:
        max_security_length = int(os.getenv("MAX_SECURITY_CHECK_LENGTH", "10000000"))
        if max_security_length < 1000:
            errors.append("MAX_SECURITY_CHECK_LENGTH must be at least 1000 characters")
        elif max_security_length > 10000000:  # 10MB limit
            errors.append(
                "MAX_SECURITY_CHECK_LENGTH must be at most 10MB (10000000 characters)",
            )
        else:
            config["MAX_SECURITY_CHECK_LENGTH"] = max_security_length
    except ValueError:
        errors.append(
            f"MAX_SECURITY_CHECK_LENGTH must be an integer, got: {os.getenv('MAX_SECURITY_CHECK_LENGTH')}",
        )

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        raise ConfigurationError(error_msg)

    return config


def get_validated_config() -> dict[str, Any]:
    """Get validated configuration with helpful error messages.

    Returns:
        Dictionary with validated configuration values

    Raises:
        ConfigurationError: If validation fails with detailed error message
    """
    try:
        return validate_environment_variables()
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise


def validate_config_on_startup() -> None:
    """Validate configuration on startup and log results.

    This function should be called during server initialization to catch
    configuration errors early.
    """
    try:
        config = get_validated_config()
        logger.info("Configuration validation passed")
        logger.debug(f"Active configuration: {config}")
    except ConfigurationError as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.error("Please check your environment variables and try again")
        raise


def get_config_summary() -> str:
    """Get a human-readable summary of current configuration.

    Returns:
        Formatted string with configuration summary
    """
    try:
        config = get_validated_config()

        summary_lines = [
            "🔧 Configuration Summary:",
            f"  • Image Size Handling: {'Strict (reject)' if config['STRICT_MODE'] else 'Permissive (auto-resize)'}",
            f"  • Max Image Size: {config['MAX_IMAGE_SIZE']}px",
            f"  • Max Total Pixels: {config['MAX_PIXELS_IN']:,}",
            f"  • Max File Size: {config['MAX_BYTES_IN']:,} bytes ({config['MAX_BYTES_IN'] / 1024 / 1024:.1f}MB)",
            f"  • Output Directory: {config['OUTPUT_DIR']}",
            f"  • Log Level: {config['MCP_LOG_LEVEL']}",
            f"  • Vision Verification: {'Enabled' if config['ENABLE_VISION_VERIFICATION'] else 'Disabled'}",
            f"  • Max Security Check Length: {config['MAX_SECURITY_CHECK_LENGTH']:,} chars ({config['MAX_SECURITY_CHECK_LENGTH'] / 1024:.1f}KB)",
        ]

        if "DEFAULT_SEED" in config:
            summary_lines.append(f"  • Default Seed: {config['DEFAULT_SEED']}")

        return "\n".join(summary_lines)

    except ConfigurationError as e:
        return f"❌ Configuration Error: {e}"


# Export commonly used configuration values
def get_max_image_size() -> int:
    """Get validated MAX_IMAGE_SIZE value."""
    return get_validated_config()["MAX_IMAGE_SIZE"]


def get_max_pixels_in() -> int:
    """Get validated MAX_PIXELS_IN value."""
    return get_validated_config()["MAX_PIXELS_IN"]


def get_max_bytes_in() -> int:
    """Get validated MAX_BYTES_IN value."""
    return get_validated_config()["MAX_BYTES_IN"]


def is_strict_mode() -> bool:
    """Get validated STRICT_MODE value."""
    return get_validated_config()["STRICT_MODE"]


def get_max_security_check_length() -> int:
    """Get validated MAX_SECURITY_CHECK_LENGTH value."""
    return get_validated_config()["MAX_SECURITY_CHECK_LENGTH"]


# --- VLM (Vision Language Model) configuration helpers ---


def is_vlm_enabled() -> bool:
    """Check if VLM features are enabled (file-first, env fallback)."""
    try:
        from .vlm.config import load_vlm_config

        return bool(load_vlm_config().get("enabled", False))
    except Exception:
        # Fallback to env-only if loader fails
        val = os.getenv("ENABLE_VLM", "false").strip().lower()
        return val in ("true", "1", "yes", "on")


def get_vlm_provider() -> str | None:
    """Get the configured VLM provider identifier (file-first)."""
    try:
        from .vlm.config import load_vlm_config

        provider = load_vlm_config().get("provider")
        return provider or None
    except Exception:
        provider = os.getenv("VLM_PROVIDER") or os.getenv("VLM_BACKEND")
        provider = (provider or "").strip()
        return provider or None


def get_vlm_model() -> str | None:
    """Get the configured VLM model name (file-first)."""
    try:
        from .vlm.config import load_vlm_config

        model = load_vlm_config().get("model")
        return model or None
    except Exception:
        model = os.getenv("VLM_MODEL") or os.getenv("GEMINI_MODEL")
        model = (model or "").strip()
        return model or None


def get_vlm_config_path() -> str | None:
    """Optional path to a local VLM config file (reported by loader)."""
    try:
        from .vlm.config import load_vlm_config

        return load_vlm_config().get("config_path") or None
    except Exception:
        path = os.getenv("VLM_CONFIG_PATH", "").strip()
        return path or None


def has_vlm_api_key() -> bool:
    """Return True if a VLM API key is available (file-first, env fallback)."""
    try:
        from .vlm.config import load_vlm_config

        return bool(load_vlm_config().get("api_key_present", False))
    except Exception:
        candidates = [
            "NANO_BANANA_API_KEY",
            "VLM_API_KEY",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
        ]
        return any((os.getenv(name) or "").strip() for name in candidates)
