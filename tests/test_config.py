#!/usr/bin/env python3
"""
Unit tests for configuration validation.

This module tests the environment variable validation and configuration
management functionality.
"""

import os
from unittest.mock import patch

import pytest

from src.albumentations_mcp.config import (
    ConfigurationError,
    get_config_summary,
    get_validated_config,
    validate_environment_variables,
)


class TestConfigurationValidation:
    """Test configuration validation functionality."""

    def test_default_configuration_valid(self):
        """Test that default configuration is valid."""
        # Clear environment to test defaults
        with patch.dict(os.environ, {}, clear=True):
            config = validate_environment_variables()

            assert config["STRICT_MODE"] is False
            assert config["MAX_IMAGE_SIZE"] == 4096
            assert config["MAX_PIXELS_IN"] == 16000000
            assert config["MAX_BYTES_IN"] == 50000000
            assert config["OUTPUT_DIR"] == "outputs"
            assert config["MCP_LOG_LEVEL"] == "INFO"
            assert config["ENABLE_VISION_VERIFICATION"] is True

    def test_strict_mode_validation(self):
        """Test STRICT_MODE validation."""
        # Test valid values
        valid_true_values = ["true", "1", "yes", "on", "TRUE", "Yes"]
        for value in valid_true_values:
            with patch.dict(os.environ, {"STRICT_MODE": value}):
                config = validate_environment_variables()
                assert config["STRICT_MODE"] is True

        valid_false_values = ["false", "0", "no", "off", "FALSE", "No"]
        for value in valid_false_values:
            with patch.dict(os.environ, {"STRICT_MODE": value}):
                config = validate_environment_variables()
                assert config["STRICT_MODE"] is False

        # Test invalid value
        with patch.dict(os.environ, {"STRICT_MODE": "maybe"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "STRICT_MODE must be true/false" in str(exc_info.value)

    def test_max_image_size_validation(self):
        """Test MAX_IMAGE_SIZE validation."""
        # Test valid value
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "2048"}):
            config = validate_environment_variables()
            assert config["MAX_IMAGE_SIZE"] == 2048

        # Test too small
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "16"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_IMAGE_SIZE must be at least 32 pixels" in str(exc_info.value)

        # Test too large
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "50000"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_IMAGE_SIZE must be at most 32768 pixels" in str(exc_info.value)

        # Test non-integer
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_IMAGE_SIZE must be an integer" in str(exc_info.value)

    def test_max_pixels_validation(self):
        """Test MAX_PIXELS_IN validation."""
        # Test valid value
        with patch.dict(os.environ, {"MAX_PIXELS_IN": "20000000"}):
            config = validate_environment_variables()
            assert config["MAX_PIXELS_IN"] == 20000000

        # Test too small
        with patch.dict(os.environ, {"MAX_PIXELS_IN": "500"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_PIXELS_IN must be at least 1024 pixels" in str(exc_info.value)

        # Test too large
        with patch.dict(os.environ, {"MAX_PIXELS_IN": "2000000000"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_PIXELS_IN must be at most 1 billion pixels" in str(
                exc_info.value,
            )

    def test_max_bytes_validation(self):
        """Test MAX_BYTES_IN validation."""
        # Test valid value
        with patch.dict(os.environ, {"MAX_BYTES_IN": "100000000"}):
            config = validate_environment_variables()
            assert config["MAX_BYTES_IN"] == 100000000

        # Test too small
        with patch.dict(os.environ, {"MAX_BYTES_IN": "500"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_BYTES_IN must be at least 1024 bytes" in str(exc_info.value)

        # Test too large
        with patch.dict(os.environ, {"MAX_BYTES_IN": "2000000000"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MAX_BYTES_IN must be at most 1GB" in str(exc_info.value)

    def test_log_level_validation(self):
        """Test MCP_LOG_LEVEL validation."""
        # Test valid values
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            with patch.dict(os.environ, {"MCP_LOG_LEVEL": level}):
                config = validate_environment_variables()
                assert config["MCP_LOG_LEVEL"] == level

        # Test case insensitive
        with patch.dict(os.environ, {"MCP_LOG_LEVEL": "debug"}):
            config = validate_environment_variables()
            assert config["MCP_LOG_LEVEL"] == "DEBUG"

        # Test invalid value
        with patch.dict(os.environ, {"MCP_LOG_LEVEL": "INVALID"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "MCP_LOG_LEVEL must be one of" in str(exc_info.value)

    def test_default_seed_validation(self):
        """Test DEFAULT_SEED validation."""
        # Test valid value
        with patch.dict(os.environ, {"DEFAULT_SEED": "12345"}):
            config = validate_environment_variables()
            assert config["DEFAULT_SEED"] == 12345

        # Test boundary values
        with patch.dict(os.environ, {"DEFAULT_SEED": "0"}):
            config = validate_environment_variables()
            assert config["DEFAULT_SEED"] == 0

        with patch.dict(os.environ, {"DEFAULT_SEED": "4294967295"}):
            config = validate_environment_variables()
            assert config["DEFAULT_SEED"] == 4294967295

        # Test out of range
        with patch.dict(os.environ, {"DEFAULT_SEED": "-1"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "DEFAULT_SEED must be between 0 and 4294967295" in str(
                exc_info.value,
            )

        with patch.dict(os.environ, {"DEFAULT_SEED": "4294967296"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "DEFAULT_SEED must be between 0 and 4294967295" in str(
                exc_info.value,
            )

        # Test non-integer
        with patch.dict(os.environ, {"DEFAULT_SEED": "not_a_number"}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "DEFAULT_SEED must be an integer" in str(exc_info.value)

    def test_output_dir_validation(self):
        """Test OUTPUT_DIR validation."""
        # Test valid value
        with patch.dict(os.environ, {"OUTPUT_DIR": "/custom/output"}):
            config = validate_environment_variables()
            assert config["OUTPUT_DIR"] == "/custom/output"

        # Test empty value
        with patch.dict(os.environ, {"OUTPUT_DIR": ""}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "OUTPUT_DIR cannot be empty" in str(exc_info.value)

        # Test whitespace only
        with patch.dict(os.environ, {"OUTPUT_DIR": "   "}):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()
            assert "OUTPUT_DIR cannot be empty" in str(exc_info.value)

    def test_multiple_errors_reported(self):
        """Test that multiple configuration errors are reported together."""
        with patch.dict(
            os.environ,
            {
                "STRICT_MODE": "maybe",
                "MAX_IMAGE_SIZE": "not_a_number",
                "MCP_LOG_LEVEL": "INVALID",
            },
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_environment_variables()

            error_message = str(exc_info.value)
            assert "STRICT_MODE must be true/false" in error_message
            assert "MAX_IMAGE_SIZE must be an integer" in error_message
            assert "MCP_LOG_LEVEL must be one of" in error_message

    def test_config_summary_generation(self):
        """Test configuration summary generation."""
        with patch.dict(
            os.environ,
            {
                "STRICT_MODE": "true",
                "MAX_IMAGE_SIZE": "2048",
                "DEFAULT_SEED": "42",
            },
        ):
            summary = get_config_summary()

            assert "Configuration Summary" in summary
            assert "Strict (reject)" in summary
            assert "2048px" in summary
            assert "Default Seed: 42" in summary

    def test_config_summary_with_error(self):
        """Test configuration summary when validation fails."""
        with patch.dict(os.environ, {"STRICT_MODE": "invalid"}):
            summary = get_config_summary()
            assert "Configuration Error" in summary

    def test_get_validated_config_wrapper(self):
        """Test the get_validated_config wrapper function."""
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "2048"}):
            config = get_validated_config()
            assert config["MAX_IMAGE_SIZE"] == 2048

        with (
            patch.dict(os.environ, {"STRICT_MODE": "invalid"}),
            pytest.raises(ConfigurationError),
        ):
            get_validated_config()
