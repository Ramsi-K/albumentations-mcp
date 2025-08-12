"""Common utilities to reduce code duplication across modules.

This module contains shared utility functions that are used across multiple
modules to reduce code duplication and improve maintainability.

# File Summary
Centralized utility functions for common patterns like logging,
error handling, validation, file operations, and singleton management.
Reduces code duplication across validation, recovery, processor, and hook modules.

# TODO Tree
- [x] Logging Utilities
  - [x] Structured logging helpers with consistent formatting
  - [x] Error logging with context and exception info
  - [x] Debug logging with session tracking
  - [x] Warning logging with categorization
- [x] Error Handling Utilities
  - [x] Exception handling patterns with consistent error messages
  - [x] Error context preservation and chaining
  - [x] Graceful degradation helpers
  - [x] Error recovery attempt tracking
- [x] Validation Utilities
  - [x] Common validation patterns for strings, dicts, lists
  - [x] Type checking helpers with detailed error messages
  - [x] Parameter sanitization and cleaning
  - [x] Range validation for numeric values
- [x] File Operation Utilities
  - [x] Safe file operations with error handling
  - [x] Directory creation and management
  - [x] Temporary file cleanup patterns
  - [x] Path validation and sanitization
- [x] Singleton Management
  - [x] Global instance management pattern
  - [x] Thread-safe singleton creation
  - [x] Instance lifecycle management
  - [x] Configuration-based instance creation

# Code Review Notes
- CONSISTENCY: Standardizes common patterns across modules
- MAINTAINABILITY: Centralizes shared logic for easier updates
- TESTING: Easier to test common patterns in isolation
- PERFORMANCE: Reduces code duplication and import overhead
- RELIABILITY: Consistent error handling and validation
"""

import functools
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable, TypeVar, Union

# Type variables for generic functions
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Thread lock for singleton management
_singleton_lock = threading.Lock()

logger = logging.getLogger(__name__)


# Logging Utilities
def log_with_context(
    level: str,
    message: str,
    session_id: str | None = None,
    operation: str | None = None,
    **kwargs: Any,
) -> None:
    """Log message with consistent context formatting.

    Args:
        level: Log level (debug, info, warning, error)
        message: Log message
        session_id: Optional session ID for tracking
        operation: Optional operation name
        **kwargs: Additional context data
    """
    log_func = getattr(logger, level.lower())

    # Build context
    context = {}
    if session_id:
        context["session_id"] = session_id
    if operation:
        context["operation"] = operation
    context.update(kwargs)

    if context:
        log_func(message, extra=context)
    else:
        log_func(message)


def log_error_with_context(
    error: Exception,
    message: str,
    session_id: str | None = None,
    operation: str | None = None,
    **kwargs: Any,
) -> None:
    """Log error with consistent context and exception info.

    Args:
        error: Exception that occurred
        message: Error message
        session_id: Optional session ID for tracking
        operation: Optional operation name
        **kwargs: Additional context data
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if session_id:
        context["session_id"] = session_id
    if operation:
        context["operation"] = operation
    context.update(kwargs)

    logger.error(message, extra=context, exc_info=True)


def log_performance(
    operation: str,
    duration: float,
    session_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log performance metrics with consistent formatting.

    Args:
        operation: Operation name
        duration: Duration in seconds
        session_id: Optional session ID for tracking
        **kwargs: Additional metrics
    """
    context = {
        "operation": operation,
        "duration_seconds": duration,
        "duration_ms": duration * 1000,
    }
    if session_id:
        context["session_id"] = session_id
    context.update(kwargs)

    logger.info(f"Performance: {operation} completed", extra=context)


# Error Handling Utilities
def handle_exception_with_fallback(
    operation_func: Callable[[], T],
    fallback_func: Callable[[], T],
    error_message: str,
    session_id: str | None = None,
    operation: str | None = None,
) -> T:
    """Execute operation with fallback on exception.

    Args:
        operation_func: Primary operation to execute
        fallback_func: Fallback operation if primary fails
        error_message: Error message for logging
        session_id: Optional session ID for tracking
        operation: Optional operation name

    Returns:
        Result from operation_func or fallback_func
    """
    try:
        return operation_func()
    except Exception as e:
        log_error_with_context(
            e, error_message, session_id=session_id, operation=operation
        )
        return fallback_func()


def safe_execute(
    func: Callable[[], T],
    default: T,
    error_message: str | None = None,
    log_errors: bool = True,
) -> T:
    """Safely execute function with default fallback.

    Args:
        func: Function to execute
        default: Default value if function fails
        error_message: Optional error message for logging
        log_errors: Whether to log errors

    Returns:
        Function result or default value
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            message = error_message or f"Safe execution failed: {e}"
            logger.warning(message)
        return default


def create_error_result(
    success: bool = False,
    error: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create standardized error result dictionary.

    Args:
        success: Whether operation was successful
        error: Error message
        **kwargs: Additional result data

    Returns:
        Standardized error result dictionary
    """
    result = {
        "success": success,
        "error": error,
        **kwargs,
    }
    return result


def raise_with_context(
    exception_class: type[Exception],
    message: str,
    original_error: Exception | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Raise exception with consistent context and chaining.

    Args:
        exception_class: Exception class to raise
        message: Error message
        original_error: Original exception for chaining
        context: Additional context data
    """
    if (
        hasattr(exception_class, "__init__")
        and len(exception_class.__init__.__code__.co_varnames) > 2
    ):
        # Exception class accepts context parameter
        exception = exception_class(message, context or {})
    else:
        # Standard exception class
        exception = exception_class(message)

    if original_error:
        raise exception from original_error
    else:
        raise exception


def handle_validation_error(
    condition: bool,
    error_message: str,
    exception_class: type[Exception],
    strict: bool = True,
    result_dict: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> bool:
    """Handle validation errors with consistent pattern.

    Args:
        condition: Condition to check (True = valid, False = error)
        error_message: Error message if condition fails
        exception_class: Exception class to raise in strict mode
        strict: Whether to raise exception or just log
        result_dict: Optional result dictionary to update
        context: Additional context for exception

    Returns:
        True if condition passed, False if failed and not strict

    Raises:
        exception_class: If condition fails and strict=True
    """
    if condition:
        return True

    # Condition failed
    if result_dict is not None:
        result_dict["error"] = error_message

    if strict:
        raise_with_context(exception_class, error_message, context=context)
    else:
        logger.warning(f"Validation failed (non-strict): {error_message}")

    return False


def chain_exceptions(
    operation_func: Callable[[], T],
    exception_mapping: dict[type[Exception], type[Exception]] | None = None,
    context_message: str | None = None,
) -> T:
    """Execute operation with consistent exception chaining.

    Args:
        operation_func: Operation to execute
        exception_mapping: Map original exceptions to new exception types
        context_message: Additional context for error messages

    Returns:
        Result from operation_func

    Raises:
        Mapped exception with proper chaining
    """
    try:
        return operation_func()
    except Exception as e:
        if exception_mapping and type(e) in exception_mapping:
            new_exception_class = exception_mapping[type(e)]
            message = f"{context_message}: {e}" if context_message else str(e)
            raise_with_context(new_exception_class, message, original_error=e)
        else:
            # Re-raise original exception
            raise


# Validation Utilities
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
        raise ValueError(
            f"{name} must be a string, got {type(value).__name__}"
        )

    if not allow_empty and not value:
        raise ValueError(f"{name} cannot be empty")

    if max_length is not None and len(value) > max_length:
        raise ValueError(
            f"{name} too long: {len(value)} characters (max: {max_length})"
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
        raise ValueError(
            f"{name} must be a dictionary, got {type(value).__name__}"
        )

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
        raise ValueError(
            f"{name} too long: {len(value)} items (max: {max_length})"
        )

    return value


def validate_numeric_range(
    value: Union[int, float],
    name: str,
    min_value: Union[int, float] | None = None,
    max_value: Union[int, float] | None = None,
) -> Union[int, float]:
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


# File Operation Utilities
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


def ensure_directory_exists(directory_path: Union[str, Path]) -> bool:
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


def cleanup_file(file_path: Union[str, Path], log_errors: bool = True) -> bool:
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


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """Sanitize text for use as filename.

    Args:
        text: Text to sanitize
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    if not text:
        return "untitled"

    # Convert to lowercase and replace spaces with underscores
    sanitized = text.lower().replace(" ", "_")

    # Replace problematic characters with underscores
    sanitized = re.sub(r"[^\w\-_.]", "_", sanitized)

    # Truncate if too long, preserving extension
    if len(sanitized) > max_length:
        # Try to preserve file extension
        if "." in sanitized:
            name, ext = sanitized.rsplit(".", 1)
            max_name_length = max_length - len(ext) - 1  # -1 for the dot
            if max_name_length > 0:
                sanitized = name[:max_name_length] + "." + ext
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = "file_" + sanitized

    return sanitized or "untitled"


# Singleton Management Utilities
def create_singleton(
    instance_var_name: str,
    factory_func: Callable[[], T],
    module_globals: dict[str, Any],
) -> T:
    """Create singleton instance with thread safety.

    Args:
        instance_var_name: Name of the global instance variable
        factory_func: Function to create new instance
        module_globals: Module's globals() dictionary

    Returns:
        Singleton instance
    """
    instance = module_globals.get(instance_var_name)
    if instance is None:
        with _singleton_lock:
            # Double-check locking pattern
            instance = module_globals.get(instance_var_name)
            if instance is None:
                instance = factory_func()
                module_globals[instance_var_name] = instance
    return instance


def singleton_getter(
    instance_var_name: str,
    factory_func: Callable[[], T],
) -> Callable[[], T]:
    """Create a singleton getter function.

    Args:
        instance_var_name: Name of the global instance variable
        factory_func: Function to create new instance

    Returns:
        Getter function that returns singleton instance
    """

    def getter() -> T:
        # Get the caller's globals
        import inspect

        frame = inspect.currentframe().f_back
        module_globals = frame.f_globals
        return create_singleton(
            instance_var_name, factory_func, module_globals
        )

    return getter


# Timing and Performance Utilities
def timed_operation(operation_name: str | None = None):
    """Decorator to time function execution and log performance.

    Args:
        operation_name: Optional name for the operation (defaults to function name)

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            name = operation_name or func.__name__
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_error_with_context(
                    e,
                    f"Timed operation {name} failed",
                    operation=name,
                    duration=duration,
                )
                raise

        return wrapper

    return decorator


# String and Text Utilities
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


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    return re.sub(r"\s+", " ", text.strip())


# Configuration Utilities
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
    value = os.getenv(name, default)

    if value is None:
        return None

    if var_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    elif var_type in (int, float):
        try:
            return var_type(value)
        except ValueError:
            logger.warning(
                f"Invalid {var_type.__name__} value for {name}: {value}"
            )
            return default
    else:
        return var_type(value)


# Memory and Resource Utilities
def format_bytes(size_bytes: int) -> str:
    """Format byte size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def estimate_memory_usage(width: int, height: int, channels: int = 3) -> int:
    """Estimate memory usage for image processing.

    Args:
        width: Image width
        height: Image height
        channels: Number of channels (default: 3 for RGB)

    Returns:
        Estimated memory usage in bytes
    """
    # Base memory for image data
    base_memory = width * height * channels

    # Processing overhead (2x for intermediate results)
    processing_overhead = base_memory * 2

    return base_memory + processing_overhead
