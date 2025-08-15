"""File operations and path handling utilities."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def safe_file_operation(
    operation: Callable[[], T],
    error_message: str,
    default: T | None = None,
    log_errors: bool = True,
) -> T | None:
    """Safely execute file operation with error handling.

    Args:
        operation: File operation to execute
        error_message: Error message for logging
        default: Default value if operation fails
        log_errors: Whether to log errors

    Returns:
        Operation result or default value
    """
    try:
        return operation()
    except Exception as e:
        if log_errors:
            logger.warning(f"{error_message}: {e}")
        return default


def ensure_directory_exists(directory_path: str | Path) -> bool:
    """Ensure directory exists, create if necessary.

    Args:
        directory_path: Path to directory

    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return False


def cleanup_file(file_path: str | Path, log_errors: bool = True) -> bool:
    """Safely remove file with error handling.

    Args:
        file_path: Path to file to remove
        log_errors: Whether to log errors

    Returns:
        True if file was removed or didn't exist
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up file: {path.name}")
        return True
    except Exception as e:
        if log_errors:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
        return False


def get_env_var(
    name: str,
    default: str | None = None,
    var_type: type = str,
) -> Any:
    """Get environment variable with type conversion.

    Args:
        name: Environment variable name
        default: Default value if not set
        var_type: Type to convert to (str, int, float, bool)

    Returns:
        Environment variable value converted to specified type
    """
    import os

    value = os.getenv(name, default)

    if value is None:
        return None

    if var_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    if var_type in (int, float):
        try:
            return var_type(value)
        except ValueError:
            logger.warning(f"Invalid {var_type.__name__} value for {name}: {value}")
            return default
    else:
        return var_type(value)
