"""Tests for the common utilities module."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.albumentations_mcp.utils import (
    cleanup_file,
    create_error_result,
    ensure_directory_exists,
    estimate_memory_usage,
    format_bytes,
    get_env_var,
    handle_exception_with_fallback,
    log_with_context,
    normalize_whitespace,
    safe_execute,
    safe_file_operation,
    sanitize_filename,
    sanitize_parameters,
    timed_operation,
    truncate_string,
    validate_dict_input,
    validate_list_input,
    validate_numeric_range,
    validate_string_input,
)


class TestLoggingUtilities:
    """Test logging utility functions."""

    def test_log_with_context(self, caplog):
        """Test logging with context."""
        import logging

        with caplog.at_level(logging.INFO):
            log_with_context(
                level="info",
                message="Test message",
                session_id="test_session",
                operation="test_op",
                custom_field="custom_value",
            )

        assert "Test message" in caplog.text

    def test_log_with_context_no_context(self, caplog):
        """Test logging without context."""
        import logging

        with caplog.at_level(logging.INFO):
            log_with_context(level="info", message="Simple message")

        assert "Simple message" in caplog.text


class TestErrorHandlingUtilities:
    """Test error handling utility functions."""

    def test_handle_exception_with_fallback_success(self):
        """Test exception handling with successful operation."""

        def operation():
            return "success"

        def fallback():
            return "fallback"

        result = handle_exception_with_fallback(operation, fallback, "Test error")

        assert result == "success"

    def test_handle_exception_with_fallback_failure(self):
        """Test exception handling with failed operation."""

        def operation():
            raise ValueError("Test error")

        def fallback():
            return "fallback"

        result = handle_exception_with_fallback(operation, fallback, "Test error")

        assert result == "fallback"

    def test_safe_execute_success(self):
        """Test safe execution with successful function."""

        def success_func():
            return "success"

        result = safe_execute(success_func, "default")
        assert result == "success"

    def test_safe_execute_failure(self):
        """Test safe execution with failing function."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, "default")
        assert result == "default"

    def test_safe_execute_no_logging(self):
        """Test safe execution without error logging."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, "default", log_errors=False)
        assert result == "default"

    def test_create_error_result(self):
        """Test creating standardized error result."""
        result = create_error_result(
            success=False,
            error="Test error",
            additional_field="value",
        )

        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["additional_field"] == "value"


class TestValidationUtilities:
    """Test validation utility functions."""

    def test_validate_string_input_valid(self):
        """Test string validation with valid input."""
        result = validate_string_input("test", "field_name")
        assert result == "test"

    def test_validate_string_input_invalid_type(self):
        """Test string validation with invalid type."""
        with pytest.raises(ValueError, match="must be a string"):
            validate_string_input(123, "field_name")

    def test_validate_string_input_empty_not_allowed(self):
        """Test string validation with empty string when not allowed."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_string_input("", "field_name", allow_empty=False)

    def test_validate_string_input_too_long(self):
        """Test string validation with too long string."""
        with pytest.raises(ValueError, match="too long"):
            validate_string_input("x" * 100, "field_name", max_length=50)

    def test_validate_dict_input_valid(self):
        """Test dictionary validation with valid input."""
        test_dict = {"key": "value"}
        result = validate_dict_input(test_dict, "field_name")
        assert result == test_dict

    def test_validate_dict_input_invalid_type(self):
        """Test dictionary validation with invalid type."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            validate_dict_input("not_dict", "field_name")

    def test_validate_dict_input_empty_not_allowed(self):
        """Test dictionary validation with empty dict when not allowed."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_dict_input({}, "field_name", allow_empty=False)

    def test_validate_list_input_valid(self):
        """Test list validation with valid input."""
        test_list = [1, 2, 3]
        result = validate_list_input(test_list, "field_name")
        assert result == test_list

    def test_validate_list_input_invalid_type(self):
        """Test list validation with invalid type."""
        with pytest.raises(ValueError, match="must be a list"):
            validate_list_input("not_list", "field_name")

    def test_validate_list_input_too_long(self):
        """Test list validation with too long list."""
        with pytest.raises(ValueError, match="too long"):
            validate_list_input([1] * 100, "field_name", max_length=50)

    def test_validate_numeric_range_valid(self):
        """Test numeric validation with valid input."""
        result = validate_numeric_range(5, "field_name", min_value=0, max_value=10)
        assert result == 5

    def test_validate_numeric_range_invalid_type(self):
        """Test numeric validation with invalid type."""
        with pytest.raises(ValueError, match="must be numeric"):
            validate_numeric_range("not_numeric", "field_name")

    def test_validate_numeric_range_too_small(self):
        """Test numeric validation with too small value."""
        with pytest.raises(ValueError, match="too small"):
            validate_numeric_range(-5, "field_name", min_value=0)

    def test_validate_numeric_range_too_large(self):
        """Test numeric validation with too large value."""
        with pytest.raises(ValueError, match="too large"):
            validate_numeric_range(15, "field_name", max_value=10)

    def test_sanitize_parameters(self):
        """Test parameter sanitization."""
        params = {
            "valid_key": "valid_value",
            "none_value": None,
            123: "invalid_key",
            "empty_string": "",
        }

        result = sanitize_parameters(params)

        assert "valid_key" in result
        assert "none_value" not in result
        assert 123 not in result
        assert "empty_string" in result  # Empty strings are kept

    def test_sanitize_parameters_with_allowed_keys(self):
        """Test parameter sanitization with allowed keys."""
        params = {
            "allowed_key": "value",
            "disallowed_key": "value",
        }

        result = sanitize_parameters(params, allowed_keys={"allowed_key"})

        assert "allowed_key" in result
        assert "disallowed_key" not in result


class TestFileOperationUtilities:
    """Test file operation utility functions."""

    def test_safe_file_operation_success(self):
        """Test safe file operation with successful operation."""

        def operation():
            return "success"

        result = safe_file_operation(operation, "Test operation")
        assert result == "success"

    def test_safe_file_operation_failure(self):
        """Test safe file operation with failing operation."""

        def operation():
            raise OSError("File error")

        result = safe_file_operation(operation, "Test operation")
        assert result is None

    def test_safe_file_operation_with_default(self):
        """Test safe file operation with default value."""

        def operation():
            raise OSError("File error")

        result = safe_file_operation(operation, "Test operation", default="default")
        assert result == "default"

    def test_ensure_directory_exists_new_dir(self):
        """Test creating new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"

            result = ensure_directory_exists(new_dir)

            assert result is True
            assert new_dir.exists()

    def test_ensure_directory_exists_existing_dir(self):
        """Test with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = ensure_directory_exists(temp_dir)
            assert result is True

    def test_cleanup_file_existing(self):
        """Test cleaning up existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # File should exist
        assert Path(temp_path).exists()

        result = cleanup_file(temp_path)

        assert result is True
        assert not Path(temp_path).exists()

    def test_cleanup_file_nonexistent(self):
        """Test cleaning up non-existent file."""
        result = cleanup_file("nonexistent_file.txt")
        assert result is True  # Should succeed silently

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("test<>file.txt")
        assert result == "test__file.txt"

    def test_sanitize_filename_empty(self):
        """Test sanitizing empty filename."""
        result = sanitize_filename("")
        assert result == "untitled"

    def test_sanitize_filename_too_long(self):
        """Test sanitizing too long filename."""
        long_name = "x" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=50)

        assert len(result) <= 50
        assert result.endswith(".txt")

    def test_sanitize_filename_starts_with_number(self):
        """Test sanitizing filename that starts with number."""
        result = sanitize_filename("123file.txt")
        assert result.startswith("file_")


class TestTimingUtilities:
    """Test timing and performance utilities."""

    def test_timed_operation_decorator(self):
        """Test timed operation decorator."""

        @timed_operation("test_operation")
        def test_function():
            time.sleep(0.01)  # Small delay
            return "result"

        result = test_function()
        assert result == "result"

    def test_timed_operation_with_exception(self):
        """Test timed operation decorator with exception."""

        @timed_operation("test_operation")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()


class TestStringUtilities:
    """Test string and text utilities."""

    def test_truncate_string_no_truncation(self):
        """Test string truncation when no truncation needed."""
        result = truncate_string("short", 10)
        assert result == "short"

    def test_truncate_string_with_truncation(self):
        """Test string truncation when truncation needed."""
        result = truncate_string("very long string", 10)
        assert result == "very lo..."
        assert len(result) == 10

    def test_truncate_string_suffix_too_long(self):
        """Test string truncation when suffix is too long."""
        result = truncate_string("test", 2, suffix="...")
        assert result == ".."

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        result = normalize_whitespace("  multiple   spaces  \n\t  ")
        assert result == "multiple spaces"


class TestConfigurationUtilities:
    """Test configuration utility functions."""

    def test_get_env_var_string_default(self):
        """Test getting environment variable with string default."""
        result = get_env_var("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"

    def test_get_env_var_int_conversion(self):
        """Test getting environment variable with int conversion."""
        with patch.dict(os.environ, {"TEST_INT_VAR": "42"}):
            result = get_env_var("TEST_INT_VAR", 0, var_type=int)
            assert result == 42

    def test_get_env_var_bool_conversion(self):
        """Test getting environment variable with bool conversion."""
        with patch.dict(os.environ, {"TEST_BOOL_VAR": "true"}):
            result = get_env_var("TEST_BOOL_VAR", False, var_type=bool)
            assert result is True

    def test_get_env_var_bool_false_values(self):
        """Test bool conversion with false values."""
        false_values = ["false", "0", "no", "off"]

        for false_val in false_values:
            with patch.dict(os.environ, {"TEST_BOOL_VAR": false_val}):
                result = get_env_var("TEST_BOOL_VAR", True, var_type=bool)
                assert result is False

    def test_get_env_var_invalid_int(self):
        """Test getting environment variable with invalid int."""
        with patch.dict(os.environ, {"TEST_INT_VAR": "not_a_number"}):
            result = get_env_var("TEST_INT_VAR", 42, var_type=int)
            assert result == 42  # Should return default


class TestMemoryUtilities:
    """Test memory and resource utilities."""

    def test_format_bytes_bytes(self):
        """Test formatting bytes."""
        result = format_bytes(512)
        assert result == "512 B"

    def test_format_bytes_kb(self):
        """Test formatting kilobytes."""
        result = format_bytes(1536)  # 1.5 KB
        assert result == "1.5 KB"

    def test_format_bytes_mb(self):
        """Test formatting megabytes."""
        result = format_bytes(1572864)  # 1.5 MB
        assert result == "1.5 MB"

    def test_format_bytes_gb(self):
        """Test formatting gigabytes."""
        result = format_bytes(1610612736)  # 1.5 GB
        assert result == "1.5 GB"

    def test_estimate_memory_usage(self):
        """Test memory usage estimation."""
        result = estimate_memory_usage(1920, 1080, 3)  # Full HD RGB

        assert result > 0
        assert isinstance(result, int)

        # Should be roughly 1920 * 1080 * 3 * 3 (base + overhead)
        expected_base = 1920 * 1080 * 3
        expected_total = expected_base * 3

        assert result >= expected_base
        assert result <= expected_total * 1.1  # Allow some variance
