"""Logging and error handling utilities."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


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
