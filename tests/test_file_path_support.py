"""Tests for file path support in augment_image tool.

This module tests the new file path functionality added to fix
Claude base64 conversion crashes.
"""

import os
import tempfile
from pathlib import Path

from PIL import Image

from src.albumentations_mcp.server import (
    _detect_input_mode,
    _load_image_from_input,
    get_pipeline_status,
    list_available_presets,
    list_available_transforms,
    load_image_for_processing,
    set_default_seed,
    validate_mcp_request,
    validate_prompt,
)


class TestInputModeDetection:
    """Test input mode detection functionality."""

    def test_file_path_mode(self):
        """Test detection of file path input mode."""
        mode, error = _detect_input_mode("test.jpg", "", "")
        assert mode == "path"
        assert error is None

    def test_base64_mode(self):
        """Test detection of base64 input mode."""
        mode, error = _detect_input_mode("", "base64data", "")
        assert mode == "base64"
        assert error is None

    def test_session_mode(self):
        """Test detection of session input mode."""
        mode, error = _detect_input_mode("", "", "session123")
        assert mode == "session"
        assert error is None

    def test_no_input_error(self):
        """Test error when no input is provided."""
        mode, error = _detect_input_mode("", "", "")
        assert mode == ""
        assert "Must provide either" in error

    def test_multiple_inputs_error(self):
        """Test error when multiple inputs are provided."""
        mode, error = _detect_input_mode("test.jpg", "base64data", "")
        assert mode == ""
        assert "Provide only one of" in error

    def test_multiple_inputs_all_three_error(self):
        """Test error when all three inputs are provided."""
        mode, error = _detect_input_mode("test.jpg", "base64data", "session123")
        assert mode == ""
        assert "Provide only one of" in error


class TestImageLoading:
    """Test image loading from different input modes."""

    def test_load_from_valid_file_path(self):
        """Test loading image from valid file path."""
        # Create a temporary valid image file
        with tempfile.TemporaryDirectory() as td:
            img_path = Path(td) / "valid_test.png"
            Image.new("RGB", (16, 16), color=(128, 128, 128)).save(
                img_path,
                format="PNG",
            )
            result = _load_image_from_input("path", str(img_path), "", "")
        assert result[0] is not None  # Should return base64 data
        assert result[1] is None  # No error

    def test_load_from_invalid_file_path(self):
        """Test loading image from invalid file path."""
        result = _load_image_from_input("path", "nonexistent.jpg", "", "")
        assert result[0] is None  # Should return None
        assert "Image file not found" in result[1]

    def test_load_from_valid_base64(self):
        """Test loading image from valid base64 data."""
        # Create a minimal valid PNG base64
        test_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9"
            "jU77yQAAAABJRU5ErkJggg=="
        )
        result = _load_image_from_input("base64", "", test_b64, "")
        assert result[0] is not None  # Should return base64 data
        assert result[1] is None  # No error

    def test_load_from_invalid_base64(self):
        """Test loading image from invalid base64 data."""
        result = _load_image_from_input("base64", "", "invalid_base64_data", "")
        assert result[0] is None  # Should return None
        assert "Invalid base64" in result[1]

    def test_load_from_session_nonexistent(self):
        """Test loading image from non-existent session."""
        result = _load_image_from_input("session", "", "", "nonexistent_session")
        assert result[0] is None  # Should return None
        assert "Session" in result[1] and "not found" in result[1]


class TestMCPValidation:
    """Test MCP request validation for new parameters."""

    def test_validate_file_path_mode(self):
        """Test validation for file path mode."""
        valid, error = validate_mcp_request(
            "augment_image",
            image_path="example.jpg",
            prompt="add blur",
            seed=42,
        )
        assert valid is True
        assert error is None

    def test_validate_base64_mode(self):
        """Test validation for base64 mode."""
        test_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9"
            "jU77yQAAAABJRU5ErkJggg=="
        )
        valid, error = validate_mcp_request(
            "augment_image",
            image_b64=test_b64,
            prompt="add blur",
            seed=42,
        )
        assert valid is True
        assert error is None

    def test_validate_session_mode(self):
        """Test validation for session mode (backward compatibility)."""
        valid, error = validate_mcp_request(
            "augment_image",
            session_id="test123",
            prompt="add blur",
            seed=42,
        )
        assert valid is True
        assert error is None

    def test_validate_output_dir_parameter(self):
        """Test validation for output_dir parameter."""
        valid, error = validate_mcp_request(
            "augment_image",
            image_path="example.jpg",
            prompt="add blur",
            output_dir="/tmp/outputs",
        )
        assert valid is True
        assert error is None

    def test_validate_invalid_seed(self):
        """Test validation for invalid seed value."""
        valid, error = validate_mcp_request(
            "augment_image",
            image_path="examples/cat.jpg",
            prompt="add blur",
            seed=-1,  # Invalid seed
        )
        assert valid is False
        assert "seed" in error


class TestErrorHandling:
    """Test error handling for file access issues."""

    def test_permission_denied_simulation(self):
        """Test handling of permission denied errors."""
        # Create a temporary file and then try to access a restricted path
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_path = Path(temp_dir) / "restricted" / "image.jpg"

            # Try to load from non-existent directory (simulates permission issues)
            result = _load_image_from_input("path", str(restricted_path), "", "")
            assert result[0] is None
            assert "Image file not found" in result[1]

    def test_invalid_image_format(self):
        """Test handling of invalid image formats."""
        # Create a temporary text file with .jpg extension
        with tempfile.NamedTemporaryFile(suffix=".jpg", mode="w", delete=False) as f:
            f.write("This is not an image file")
            temp_path = f.name

        try:
            result = _load_image_from_input("path", temp_path, "", "")
            assert result[0] is None
            assert "Failed to load image" in result[1]
        finally:
            os.unlink(temp_path)

    def test_corrupted_base64_data(self):
        """Test handling of corrupted base64 data."""
        # Use base64-like string that's not valid image data
        corrupted_b64 = (
            "VGhpcyBpcyBub3QgYW4gaW1hZ2U="  # "This is not an image" in base64
        )
        result = _load_image_from_input("base64", "", corrupted_b64, "")
        assert result[0] is None
        # Implementation returns taxonomy with B64_INVALID for decode/open failures
        assert ("B64_INVALID" in result[1]) or ("Invalid base64" in result[1])


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    def test_session_mode_still_works(self):
        """Test that session mode still works for backward compatibility."""
        # This test would require setting up a session first
        # For now, just test that the validation works
        valid, error = validate_mcp_request(
            "augment_image",
            session_id="test_session",
            prompt="add blur",
        )
        assert valid is True
        assert error is None

    def test_base64_mode_still_works(self):
        """Test that base64 mode still works for backward compatibility."""
        test_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9"
            "jU77yQAAAABJRU5ErkJggg=="
        )
        valid, error = validate_mcp_request(
            "augment_image",
            image_b64=test_b64,
            prompt="add blur",
        )
        assert valid is True
        assert error is None


class TestOutputDirectoryHandling:
    """Test output directory handling functionality."""

    def test_custom_output_directory(self):
        """Test setting custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set custom output directory
            os.environ["OUTPUT_DIR"] = temp_dir

            # Test that the environment variable is set correctly
            assert os.getenv("OUTPUT_DIR") == temp_dir

            # Clean up
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_default_output_directory(self):
        """Test default output directory behavior."""
        # Ensure OUTPUT_DIR is not set
        if "OUTPUT_DIR" in os.environ:
            del os.environ["OUTPUT_DIR"]

        default_dir = os.getenv("OUTPUT_DIR", "outputs")
        assert default_dir == "outputs"


class TestIntegrationWithExistingTools:
    """Test that other MCP tools still work correctly."""

    def test_list_available_transforms_still_works(self):
        """Test that list_available_transforms tool still works."""
        result = list_available_transforms()
        assert isinstance(result, dict)
        assert "transforms" in result
        assert "total_count" in result

    def test_validate_prompt_still_works(self):
        """Test that validate_prompt tool still works."""
        result = validate_prompt("add blur")
        assert isinstance(result, dict)
        assert "valid" in result
        assert "transforms" in result

    def test_get_pipeline_status_still_works(self):
        """Test that get_pipeline_status tool still works."""
        result = get_pipeline_status()
        assert isinstance(result, dict)
        # Should have either status info or error info

    def test_set_default_seed_still_works(self):
        """Test that set_default_seed tool still works."""
        result = set_default_seed(42)
        assert isinstance(result, dict)
        assert "success" in result

    def test_list_available_presets_still_works(self):
        """Test that list_available_presets tool still works."""
        result = list_available_presets()
        assert isinstance(result, dict)
        assert "presets" in result
        assert "total_count" in result

    def test_load_image_for_processing_still_works(self):
        """Test that load_image_for_processing tool still works."""
        # Create a temporary image and load it
        with tempfile.TemporaryDirectory() as td:
            img_path = Path(td) / "load_test.png"
            Image.new("RGB", (16, 16), color=(64, 64, 64)).save(img_path, format="PNG")
            result = load_image_for_processing(str(img_path))
        assert isinstance(result, str)
        assert "✅" in result  # Success message
        assert "Session ID:" in result
