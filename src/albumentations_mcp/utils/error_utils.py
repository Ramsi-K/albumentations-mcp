"""Error handling and exception management utilities."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
        from .logging_utils import log_error_with_context

        log_error_with_context(
            e,
            error_message,
            session_id=session_id,
            operation=operation,
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
