"""Utility modules organized by functionality.

This package contains utility functions organized into focused modules:
- async_utils: Async execution helpers
- validation_utils: Input validation and sanitization
- file_utils: File operations and path handling
- memory_utils: Memory management and resource utilities
- logging_utils: Logging and error handling utilities
- singleton_utils: Singleton pattern management
"""

# Import commonly used functions for backward compatibility
from .async_utils import run_async_safely
from .error_utils import (
    chain_exceptions,
    create_error_result,
    handle_exception_with_fallback,
    handle_validation_error,
    raise_with_context,
    safe_execute,
)
from .file_utils import (
    cleanup_file,
    ensure_directory_exists,
    get_env_var,
    safe_file_operation,
)
from .logging_utils import (
    log_error_with_context,
    log_performance,
    log_with_context,
)
from .memory_utils import (
    estimate_memory_usage,
    format_bytes,
)
from .singleton_utils import (
    create_singleton,
    singleton_getter,
)
from .validation_utils import (
    normalize_whitespace,
    sanitize_base64_input,
    sanitize_parameters,
    truncate_string,
    validate_dict_input,
    validate_list_input,
    validate_numeric_range,
    validate_string_input,
)

__all__ = [
    # Async utilities
    "run_async_safely",
    # Validation utilities
    "sanitize_base64_input",
    "validate_string_input",
    "validate_dict_input",
    "validate_list_input",
    "validate_numeric_range",
    "sanitize_parameters",
    # Validation utilities (continued)
    "sanitize_filename",
    "normalize_whitespace",
    "truncate_string",
    # File utilities
    "safe_file_operation",
    "ensure_directory_exists",
    "cleanup_file",
    "get_env_var",
    # Error utilities
    "handle_exception_with_fallback",
    "safe_execute",
    "create_error_result",
    "raise_with_context",
    "handle_validation_error",
    "chain_exceptions",
    # Singleton utilities
    "create_singleton",
    "singleton_getter",
    # Memory utilities
    "format_bytes",
    "estimate_memory_usage",
    # Logging utilities
    "log_with_context",
    "log_error_with_context",
    "log_performance",
]
