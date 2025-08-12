"""Tests for the standardized error handling system."""

import pytest
from src.albumentations_mcp.errors import (
    BaseAlbumentationsMCPError,
    ErrorCode,
    ImageValidationError,
    PromptValidationError,
    ResourceLimitError,
    SecurityValidationError,
    ValidationError,
    ValidationResult,
    convert_exception,
    create_error_response,
    handle_strict_validation,
    log_error_with_recovery,
)


class TestErrorCode:
    """Test error code enumeration."""

    def test_error_codes_exist(self):
        """Test that all expected error codes exist."""
        expected_codes = [
            "VALIDATION_ERROR",
            "IMAGE_VALIDATION_ERROR",
            "PROMPT_VALIDATION_ERROR",
            "SECURITY_VALIDATION_ERROR",
            "RESOURCE_LIMIT_ERROR",
            "PROCESSING_ERROR",
            "RECOVERY_ERROR",
        ]

        for code_name in expected_codes:
            assert hasattr(ErrorCode, code_name)
            assert isinstance(getattr(ErrorCode, code_name), ErrorCode)


class TestBaseAlbumentationsMCPError:
    """Test base error class functionality."""

    def test_basic_error_creation(self):
        """Test creating basic error."""
        error = BaseAlbumentationsMCPError(
            "Test error",
            ErrorCode.VALIDATION_ERROR,
        )

        assert str(error) == "Test error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.user_message == "Test error"
        assert isinstance(error.context, dict)

    def test_error_with_context(self):
        """Test error with additional context."""
        context = {"field": "test_field", "value": "test_value"}
        error = BaseAlbumentationsMCPError(
            "Test error",
            ErrorCode.VALIDATION_ERROR,
            context=context,
            recovery_suggestion="Try again",
            user_message="User-friendly message",
        )

        assert error.context["field"] == "test_field"
        assert error.recovery_suggestion == "Try again"
        assert error.user_message == "User-friendly message"

    def test_to_dict(self):
        """Test error serialization to dictionary."""
        error = BaseAlbumentationsMCPError(
            "Test error",
            ErrorCode.VALIDATION_ERROR,
            context={"test": "value"},
        )

        error_dict = error.to_dict()

        assert error_dict["error"] is True
        assert error_dict["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert error_dict["message"] == "Test error"
        assert error_dict["context"]["test"] == "value"


class TestSpecializedErrors:
    """Test specialized error classes."""

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = ValidationError(
            "Validation failed",
            field_name="test_field",
            field_value="invalid_value",
        )

        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.context["field_name"] == "test_field"
        assert error.context["field_value"] == "invalid_value"

    def test_image_validation_error(self):
        """Test ImageValidationError creation."""
        image_info = {"width": 100, "height": 100}
        error = ImageValidationError(
            "Invalid image",
            image_info=image_info,
        )

        assert error.error_code == ErrorCode.IMAGE_VALIDATION_ERROR
        assert error.context["image_info"] == image_info

    def test_prompt_validation_error(self):
        """Test PromptValidationError creation."""
        prompt_info = {"length": 1000, "word_count": 200}
        error = PromptValidationError(
            "Invalid prompt",
            prompt_info=prompt_info,
        )

        assert error.error_code == ErrorCode.PROMPT_VALIDATION_ERROR
        assert error.context["prompt_info"] == prompt_info

    def test_security_validation_error(self):
        """Test SecurityValidationError creation."""
        error = SecurityValidationError(
            "Security issue detected",
            security_issue="script_injection",
        )

        assert error.error_code == ErrorCode.SECURITY_VALIDATION_ERROR
        assert error.context["security_issue"] == "script_injection"
        assert "unsafe content" in error.user_message

    def test_resource_limit_error(self):
        """Test ResourceLimitError creation."""
        error = ResourceLimitError(
            "Resource limit exceeded",
            limit_type="memory",
            current_value=1000,
            limit_value=500,
        )

        assert error.error_code == ErrorCode.RESOURCE_LIMIT_ERROR
        assert error.context["limit_type"] == "memory"
        assert error.context["current_value"] == 1000
        assert error.context["limit_value"] == 500


class TestValidationResult:
    """Test ValidationResult class."""

    def test_basic_validation_result(self):
        """Test basic validation result creation."""
        result = ValidationResult(
            valid=True,
            metadata={"test": "value"},
        )

        assert result.valid is True
        assert result.error is None
        assert result.warnings == []
        assert result.metadata["test"] == "value"

    def test_failed_validation_result(self):
        """Test failed validation result."""
        result = ValidationResult(
            valid=False,
            error="Validation failed",
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.valid is False
        assert result.error == "Validation failed"
        assert len(result.warnings) == 2

    def test_add_warning(self):
        """Test adding warnings to result."""
        result = ValidationResult()
        result.add_warning("Test warning")

        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"

    def test_add_metadata(self):
        """Test adding metadata to result."""
        result = ValidationResult()
        result.add_metadata("key", "value")

        assert result.metadata["key"] == "value"

    def test_fail(self):
        """Test marking result as failed."""
        result = ValidationResult(valid=True)
        result.fail("Test error")

        assert result.valid is False
        assert result.error == "Test error"

    def test_to_dict(self):
        """Test result serialization."""
        result = ValidationResult(
            valid=True,
            warnings=["Warning"],
            metadata={"key": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["valid"] is True
        assert result_dict["warnings"] == ["Warning"]
        assert result_dict["metadata"]["key"] == "value"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_handle_strict_validation_success(self):
        """Test strict validation with successful condition."""
        result = ValidationResult()

        success = handle_strict_validation(
            condition=True,
            error_message="Test error",
            exception_class=ValidationError,
            strict=True,
            result=result,
        )

        assert success is True
        assert result.valid is False  # Default state

    def test_handle_strict_validation_failure_strict(self):
        """Test strict validation with failed condition in strict mode."""
        result = ValidationResult()

        with pytest.raises(ValidationError):
            handle_strict_validation(
                condition=False,
                error_message="Test error",
                exception_class=ValidationError,
                strict=True,
                result=result,
            )

    def test_handle_strict_validation_failure_non_strict(self):
        """Test strict validation with failed condition in non-strict mode."""
        result = ValidationResult()

        success = handle_strict_validation(
            condition=False,
            error_message="Test error",
            exception_class=ValidationError,
            strict=False,
            result=result,
        )

        assert success is False
        assert result.error == "Test error"

    def test_create_error_response_with_custom_error(self):
        """Test creating error response with custom error."""
        error = ValidationError("Test error")
        response = create_error_response(error)

        assert response["success"] is False
        assert response["error"] is True
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value

    def test_create_error_response_with_exception(self):
        """Test creating error response with standard exception."""
        error = ValueError("Test error")
        response = create_error_response(error)

        assert response["success"] is False
        assert response["error"] is True
        assert response["message"] == "Test error"
        assert response["exception_type"] == "ValueError"

    def test_create_error_response_with_string(self):
        """Test creating error response with string."""
        response = create_error_response("Test error")

        assert response["success"] is False
        assert response["error"] is True
        assert response["message"] == "Test error"

    def test_convert_exception_known_type(self):
        """Test converting known exception types."""
        original_error = ValueError("Test error")
        converted = convert_exception(original_error, "Context message")

        assert isinstance(converted, ValidationError)
        assert "Context message: Test error" in str(converted)

    def test_convert_exception_unknown_type(self):
        """Test converting unknown exception types."""
        original_error = RuntimeError("Test error")
        converted = convert_exception(original_error)

        # Should fallback to ProcessingError
        assert isinstance(converted, BaseAlbumentationsMCPError)
        assert "Test error" in str(converted)

    def test_convert_exception_already_converted(self):
        """Test converting already converted exception."""
        original_error = ValidationError("Test error")
        converted = convert_exception(original_error)

        assert converted is original_error


class TestErrorLogging:
    """Test error logging functionality."""

    def test_log_error_with_recovery_success(self, caplog):
        """Test logging error with successful recovery."""
        import logging

        error = ValidationError("Test error")

        with caplog.at_level(logging.INFO):
            log_error_with_recovery(
                error=error,
                operation="test_operation",
                recovery_attempted=True,
                recovery_successful=True,
                session_id="test_session",
            )

        assert "recovered from error" in caplog.text
        assert "test_operation" in caplog.text

    def test_log_error_with_recovery_failure(self, caplog):
        """Test logging error with failed recovery."""
        error = ValidationError("Test error")

        log_error_with_recovery(
            error=error,
            operation="test_operation",
            recovery_attempted=True,
            recovery_successful=False,
        )

        assert "recovery failed" in caplog.text

    def test_log_error_no_recovery(self, caplog):
        """Test logging error without recovery."""
        error = ValidationError("Test error")

        log_error_with_recovery(
            error=error,
            operation="test_operation",
            recovery_attempted=False,
            recovery_successful=False,
        )

        assert "failed" in caplog.text
