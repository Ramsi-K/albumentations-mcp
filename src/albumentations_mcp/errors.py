"""Standardized error handling and exception definitions.

This module provides consistent error handling patterns and exception
definitions used throughout the albumentations-mcp system.

# File Summary
Centralized error handling system with consistent exception hierarchy,
error message formatting, and recovery strategies. Provides standardized
patterns for validation errors, processing failures, and graceful degradation.

# TODO Tree
- [x] Exception Hierarchy
  - [x] Base exception classes with consistent interfaces
  - [x] Specialized exceptions for different error types
  - [x] Context preservation and error chaining
  - [x] Error code enumeration for programmatic handling
- [x] Error Message Formatting
  - [x] Consistent error message templates
  - [x] Context-aware error descriptions
  - [x] User-friendly error messages
  - [x] Developer debugging information
- [x] Error Recovery Patterns
  - [x] Graceful degradation strategies
  - [x] Fallback value providers
  - [x] Error aggregation and reporting
  - [x] Recovery attempt tracking
- [x] Validation Error Handling
  - [x] Strict vs non-strict validation modes
  - [x] Validation result standardization
  - [x] Warning collection and reporting
  - [x] Parameter sanitization helpers

# Code Review Notes
- CONSISTENCY: All errors follow the same pattern and interface
- DEBUGGING: Rich context information for troubleshooting
- RECOVERY: Built-in fallback and recovery mechanisms
- USABILITY: Clear, actionable error messages for users
- MAINTAINABILITY: Centralized error handling logic
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for programmatic error handling."""

    # Validation errors (1000-1999)
    VALIDATION_ERROR = 1000
    IMAGE_VALIDATION_ERROR = 1001
    PROMPT_VALIDATION_ERROR = 1002
    PARAMETER_VALIDATION_ERROR = 1003
    SECURITY_VALIDATION_ERROR = 1004

    # Resource errors (2000-2999)
    RESOURCE_LIMIT_ERROR = 2000
    MEMORY_LIMIT_ERROR = 2001
    FILE_SIZE_LIMIT_ERROR = 2002
    PROCESSING_TIMEOUT_ERROR = 2003

    # Processing errors (3000-3999)
    PROCESSING_ERROR = 3000
    IMAGE_CONVERSION_ERROR = 3001
    TRANSFORM_ERROR = 3002
    PIPELINE_ERROR = 3003

    # Recovery errors (4000-4999)
    RECOVERY_ERROR = 4000
    TRANSFORM_RECOVERY_ERROR = 4001
    MEMORY_RECOVERY_ERROR = 4002

    # System errors (5000-5999)
    SYSTEM_ERROR = 5000
    CONFIGURATION_ERROR = 5001
    DEPENDENCY_ERROR = 5002


class BaseAlbumentationsMCPError(Exception):
    """Base exception class for all albumentations-mcp errors.

    Provides consistent error handling with context preservation,
    error codes, and recovery information.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None,
        user_message: Optional[str] = None,
    ):
        """Initialize base error with context and recovery information.

        Args:
            message: Technical error message for developers
            error_code: Standardized error code
            context: Additional context data for debugging
            recovery_suggestion: Suggestion for error recovery
            user_message: User-friendly error message
        """
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.recovery_suggestion = recovery_suggestion
        self.user_message = user_message or message

        # Add error metadata
        self.context.update(
            {
                "error_code": error_code.value,
                "error_name": error_code.name,
                "exception_type": self.__class__.__name__,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error": True,
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": str(self),
            "user_message": self.user_message,
            "recovery_suggestion": self.recovery_suggestion,
            "context": self.context,
            "exception_type": self.__class__.__name__,
        }

    def log_error(
        self, logger_instance: Optional[logging.Logger] = None
    ) -> None:
        """Log error with full context."""
        log = logger_instance or logger
        log.error(
            f"{self.__class__.__name__}: {self}",
            extra={
                "error_code": self.error_code.value,
                "context": self.context,
                "recovery_suggestion": self.recovery_suggestion,
            },
            exc_info=True,
        )


class ValidationError(BaseAlbumentationsMCPError):
    """Base class for validation errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        field_name: Optional[str] = None,
        field_value: Any = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            recovery_suggestion="Check input parameters and try again",
        )

        if field_name:
            self.context["field_name"] = field_name
        if field_value is not None:
            self.context["field_value"] = str(field_value)


class ImageValidationError(ValidationError):
    """Raised when image validation fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        image_info: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.error_code = ErrorCode.IMAGE_VALIDATION_ERROR
        self.recovery_suggestion = "Check image format, size, and encoding"

        if image_info:
            self.context["image_info"] = image_info


class PromptValidationError(ValidationError):
    """Raised when prompt validation fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        prompt_info: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.error_code = ErrorCode.PROMPT_VALIDATION_ERROR
        self.recovery_suggestion = (
            "Simplify prompt or check for invalid characters"
        )

        if prompt_info:
            self.context["prompt_info"] = prompt_info


class SecurityValidationError(ValidationError):
    """Raised when security validation fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        security_issue: Optional[str] = None,
    ):
        super().__init__(message, context)
        self.error_code = ErrorCode.SECURITY_VALIDATION_ERROR
        self.recovery_suggestion = "Remove suspicious content and try again"
        self.user_message = "Input contains potentially unsafe content"

        if security_issue:
            self.context["security_issue"] = security_issue


class ResourceLimitError(BaseAlbumentationsMCPError):
    """Raised when resource limits are exceeded."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        limit_type: Optional[str] = None,
        current_value: Optional[Union[int, float]] = None,
        limit_value: Optional[Union[int, float]] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_LIMIT_ERROR,
            context=context,
            recovery_suggestion="Reduce input size or complexity",
            user_message="Input exceeds system limits",
        )

        if limit_type:
            self.context["limit_type"] = limit_type
        if current_value is not None:
            self.context["current_value"] = current_value
        if limit_value is not None:
            self.context["limit_value"] = limit_value


class ProcessingError(BaseAlbumentationsMCPError):
    """Base class for processing errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            context=context,
            recovery_suggestion="Try with different parameters or simpler transforms",
        )

        if operation:
            self.context["operation"] = operation


class ImageConversionError(ProcessingError):
    """Raised when image conversion fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context, operation="image_conversion")
        self.error_code = ErrorCode.IMAGE_CONVERSION_ERROR
        self.recovery_suggestion = "Check image format and encoding"


class TransformError(ProcessingError):
    """Raised when transform application fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        transform_name: Optional[str] = None,
        transform_params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context, operation="transform_application")
        self.error_code = ErrorCode.TRANSFORM_ERROR
        self.recovery_suggestion = "Try with safer transform parameters"

        if transform_name:
            self.context["transform_name"] = transform_name
        if transform_params:
            self.context["transform_params"] = transform_params


class RecoveryError(BaseAlbumentationsMCPError):
    """Base class for recovery-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_strategy: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.RECOVERY_ERROR,
            context=context,
            recovery_suggestion="System will attempt alternative approaches",
        )

        if recovery_strategy:
            self.context["recovery_strategy"] = recovery_strategy


class ValidationResult:
    """Standardized validation result with consistent interface."""

    def __init__(
        self,
        valid: bool = False,
        error: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sanitized_data: Any = None,
    ):
        """Initialize validation result.

        Args:
            valid: Whether validation passed
            error: Error message if validation failed
            warnings: List of warning messages
            metadata: Additional metadata
            sanitized_data: Cleaned/sanitized version of input data
        """
        self.valid = valid
        self.error = error
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.sanitized_data = sanitized_data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "valid": self.valid,
            "error": self.error,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "sanitized_data": self.sanitized_data,
        }

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata entry."""
        self.metadata[key] = value

    def fail(self, error: str) -> None:
        """Mark validation as failed with error message."""
        self.valid = False
        self.error = error


def handle_strict_validation(
    condition: bool,
    error_message: str,
    exception_class: Type[BaseAlbumentationsMCPError],
    strict: bool = True,
    result: Optional[ValidationResult] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Handle validation with strict/non-strict modes.

    Args:
        condition: Validation condition (True = valid)
        error_message: Error message if validation fails
        exception_class: Exception to raise in strict mode
        strict: Whether to raise exception or just log
        result: Optional validation result to update
        context: Additional context for exception

    Returns:
        True if validation passed, False if failed in non-strict mode

    Raises:
        exception_class: If validation fails and strict=True
    """
    if condition:
        return True

    # Validation failed
    if result:
        result.fail(error_message)

    if strict:
        raise exception_class(error_message, context=context)
    else:
        logger.warning(f"Validation failed (non-strict): {error_message}")
        return False


def create_error_response(
    error: Union[BaseAlbumentationsMCPError, Exception, str],
    success: bool = False,
    **additional_data: Any,
) -> Dict[str, Any]:
    """Create standardized error response dictionary.

    Args:
        error: Error object, exception, or error message
        success: Success flag (usually False for errors)
        **additional_data: Additional response data

    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, BaseAlbumentationsMCPError):
        response = error.to_dict()
        response["success"] = success
        response.update(additional_data)
        return response
    elif isinstance(error, Exception):
        return {
            "success": success,
            "error": True,
            "message": str(error),
            "exception_type": type(error).__name__,
            **additional_data,
        }
    else:
        return {
            "success": success,
            "error": True,
            "message": str(error),
            **additional_data,
        }


def log_error_with_recovery(
    error: Exception,
    operation: str,
    recovery_attempted: bool = False,
    recovery_successful: bool = False,
    session_id: Optional[str] = None,
) -> None:
    """Log error with recovery information.

    Args:
        error: Exception that occurred
        operation: Operation that failed
        recovery_attempted: Whether recovery was attempted
        recovery_successful: Whether recovery was successful
        session_id: Optional session ID for tracking
    """
    context = {
        "operation": operation,
        "error_type": type(error).__name__,
        "recovery_attempted": recovery_attempted,
        "recovery_successful": recovery_successful,
    }

    if session_id:
        context["session_id"] = session_id

    if isinstance(error, BaseAlbumentationsMCPError):
        context.update(error.context)

    if recovery_successful:
        logger.info(
            f"Operation {operation} recovered from error: {error}",
            extra=context,
        )
    elif recovery_attempted:
        logger.warning(
            f"Operation {operation} recovery failed: {error}", extra=context
        )
    else:
        logger.error(
            f"Operation {operation} failed: {error}",
            extra=context,
            exc_info=True,
        )


# Exception mapping for consistent error conversion
EXCEPTION_MAPPING = {
    ValueError: ValidationError,
    TypeError: ValidationError,
    OSError: ProcessingError,
    MemoryError: ResourceLimitError,
}


def convert_exception(
    original_error: Exception,
    context_message: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> BaseAlbumentationsMCPError:
    """Convert standard exceptions to albumentations-mcp exceptions.

    Args:
        original_error: Original exception to convert
        context_message: Additional context message
        additional_context: Additional context data

    Returns:
        Converted albumentations-mcp exception
    """
    error_type = type(original_error)

    if isinstance(original_error, BaseAlbumentationsMCPError):
        return original_error

    if error_type in EXCEPTION_MAPPING:
        new_exception_class = EXCEPTION_MAPPING[error_type]
        message = (
            f"{context_message}: {original_error}"
            if context_message
            else str(original_error)
        )

        if new_exception_class == ValidationError:
            return ValidationError(message, context=additional_context)
        elif new_exception_class == ProcessingError:
            return ProcessingError(message, context=additional_context)
        elif new_exception_class == ResourceLimitError:
            return ResourceLimitError(message, context=additional_context)

    # Fallback to generic processing error
    message = (
        f"{context_message}: {original_error}"
        if context_message
        else str(original_error)
    )
    return ProcessingError(message, context=additional_context)
