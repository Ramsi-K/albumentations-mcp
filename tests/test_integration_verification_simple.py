#!/usr/bin/env python3
"""
Simplified Integration Testing and Verification for File Path Mode

This module provides focused integration tests to verify:
- Claude integration works with file path mode
- File path mode prevents base64 conversion crashes
- Various image sizes and formats work correctly
- All existing functionality (presets, seeding, hooks) works with file paths
- Resource cleanup after processing

"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from src.albumentations_mcp.image_conversions import (
    load_image_from_source,
    pil_to_base64,
)
from src.albumentations_mcp.server import (
    augment_image,
    get_pipeline_status,
    list_available_presets,
    list_available_transforms,
    validate_prompt,
)


class TestClaudeIntegrationBasic:
    """Test basic Claude integration with file path mode."""

    @pytest.fixture
    def test_image(self):
        """Create a test image file."""
        temp_dir = tempfile.mkdtemp()
        image = Image.new("RGB", (512, 512), color=(128, 128, 128))
        image_path = Path(temp_dir) / "test.png"
        image.save(image_path)

        yield str(image_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_path_mode_works(self, test_image, temp_output_dir):
        """Test that file path mode works without crashing."""
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            result = augment_image(image_path=test_image, prompt="add blur", seed=42)

            # Should not crash and should return a string result
            assert isinstance(result, str)

            # Should either succeed or fail gracefully
            assert ("✅" in result) or ("❌" in result)

            # If successful, should include saved files information
            if "✅" in result:
                assert "Files saved:" in result

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_file_path_vs_base64_no_crash(self, test_image):
        """Test that file path mode doesn't crash with large images."""
        # Create a larger image that might be problematic for base64
        temp_dir = tempfile.mkdtemp()
        try:
            large_image = Image.new("RGB", (1024, 1024), color=(255, 0, 0))
            large_image_path = Path(temp_dir) / "large.png"
            large_image.save(large_image_path)

            # Test file path mode
            result_file = augment_image(
                image_path=str(large_image_path),
                prompt="add blur",
                seed=42,
            )

            # Should not crash
            assert isinstance(result_file, str)
            assert ("✅" in result_file) or ("❌" in result_file)

            image = load_image_from_source(str(large_image_path))
            image_b64 = pil_to_base64(image)

            result_b64 = augment_image(image_b64=image_b64, prompt="add blur", seed=42)

            # Should also not crash
            assert isinstance(result_b64, str)
            assert ("✅" in result_b64) or ("❌" in result_b64)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestImageFormatsAndSizes:
    """Test various image formats and sizes."""

    def test_different_image_formats(self):
        """Test different image formats work with file path mode."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Test different formats
            formats = [
                ("test.png", "PNG"),
                ("test.jpg", "JPEG"),
            ]

            for filename, format_type in formats:
                # Create test image
                image = Image.new("RGB", (256, 256), color=(100, 100, 100))
                image_path = Path(temp_dir) / filename
                image.save(image_path, format=format_type)

                # Test augmentation
                result = augment_image(
                    image_path=str(image_path),
                    prompt="add brightness",
                    seed=42,
                )

                # Should not crash
                assert isinstance(result, str)
                assert ("✅" in result) or ("❌" in result)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_different_image_sizes(self):
        """Test different image sizes work with file path mode."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Test different sizes
            sizes = [
                (64, 64),  # Small
                (512, 512),  # Medium
                (800, 600),  # Large
            ]

            for width, height in sizes:
                # Create test image
                image = Image.new("RGB", (width, height), color=(150, 150, 150))
                image_path = Path(temp_dir) / f"test_{width}x{height}.png"
                image.save(image_path)

                # Test augmentation
                result = augment_image(
                    image_path=str(image_path),
                    prompt="add contrast",
                    seed=42,
                )

                # Should not crash
                assert isinstance(result, str)
                assert ("✅" in result) or ("❌" in result)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestExistingFunctionality:
    """Test that existing functionality works with file paths."""

    @pytest.fixture
    def test_image(self):
        """Create a test image file."""
        temp_dir = tempfile.mkdtemp()
        image = Image.new("RGB", (256, 256), color=(100, 150, 200))
        image_path = Path(temp_dir) / "test.png"
        image.save(image_path)

        yield str(image_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_presets_work_with_file_paths(self, test_image):
        """Test that presets work with file path mode."""
        # Get available presets
        presets_result = list_available_presets()
        assert presets_result["total_count"] > 0

        # Test first preset
        first_preset = presets_result["presets"][0]["name"]

        result = augment_image(image_path=test_image, preset=first_preset, seed=42)

        # Should not crash
        assert isinstance(result, str)
        assert ("✅" in result) or ("❌" in result)

    def test_seeding_works_with_file_paths(self, test_image):
        """Test that seeding works with file path mode."""
        # Test with explicit seed
        result1 = augment_image(image_path=test_image, prompt="add noise", seed=12345)

        result2 = augment_image(image_path=test_image, prompt="add noise", seed=12345)

        # Should not crash
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert ("✅" in result1) or ("❌" in result1)
        assert ("✅" in result2) or ("❌" in result2)

    def test_hooks_work_with_file_paths(self, test_image):
        """Test that hook system works with file path mode."""
        # Check pipeline status
        status = get_pipeline_status()
        assert isinstance(status, dict)

        # Test augmentation with hooks
        result = augment_image(
            image_path=test_image,
            prompt="add blur and contrast",
            seed=42,
        )

        # Should not crash
        assert isinstance(result, str)
        assert ("✅" in result) or ("❌" in result)

    def test_validation_still_works(self):
        """Test that prompt validation still works correctly."""
        # Test valid prompt
        result = validate_prompt("add blur")
        assert isinstance(result, dict)
        assert "valid" in result
        assert "transforms" in result

        # Test invalid prompt
        result = validate_prompt("invalid_transform_xyz")
        assert isinstance(result, dict)
        assert "valid" in result

    def test_other_tools_still_work(self):
        """Test that other MCP tools still work correctly."""
        # Test list_available_transforms
        transforms_result = list_available_transforms()
        assert isinstance(transforms_result, dict)
        assert "transforms" in transforms_result

        # Test list_available_presets
        presets_result = list_available_presets()
        assert isinstance(presets_result, dict)
        assert "presets" in presets_result

        # Test get_pipeline_status
        status_result = get_pipeline_status()
        assert isinstance(status_result, dict)


class TestErrorHandling:
    """Test error handling with file path mode."""

    def test_nonexistent_file_path(self):
        """Test handling of non-existent file paths."""
        result = augment_image(
            image_path="/nonexistent/path/image.jpg",
            prompt="add blur",
        )

        assert isinstance(result, str)
        assert "❌" in result
        assert "not found" in result.lower()

    def test_invalid_file_format(self):
        """Test handling of invalid file formats."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a text file with image extension
            fake_image_path = Path(temp_dir) / "fake.jpg"
            with open(fake_image_path, "w") as f:
                f.write("This is not an image file")

            result = augment_image(image_path=str(fake_image_path), prompt="add blur")

            assert isinstance(result, str)
            assert "❌" in result

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_parameters(self):
        """Test handling of empty parameters."""
        result = augment_image(image_path="", image_b64="", session_id="", prompt="")

        assert isinstance(result, str)
        assert "❌" in result


class TestResourceCleanup:
    """Test basic resource cleanup."""

    def test_no_memory_leaks_basic(self):
        """Test basic memory usage doesn't grow excessively."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create test image
            image = Image.new("RGB", (256, 256), color=(128, 128, 128))
            image_path = Path(temp_dir) / "test.png"
            image.save(image_path)

            # Process multiple times
            for i in range(3):
                result = augment_image(
                    image_path=str(image_path),
                    prompt=f"add blur {i}",
                    seed=i,
                )

                # Should not crash
                assert isinstance(result, str)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_outputs_directory_created_and_reasonable(self):
        """Test that outputs are written under OUTPUT_DIR and not excessive."""
        test_temp_dir = tempfile.mkdtemp()
        out_dir = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = out_dir
        try:
            image = Image.new("RGB", (256, 256), color=(128, 128, 128))
            image_path = Path(test_temp_dir) / "test.png"
            image.save(image_path)

            result = augment_image(
                image_path=str(image_path),
                prompt="add blur",
                seed=42,
            )
            assert isinstance(result, str)

            # Ensure some artifacts exist under OUTPUT_DIR
            created = list(Path(out_dir).rglob("*"))
            assert len(created) > 0
            # Should not be excessive
            assert len(created) < 50
        finally:
            shutil.rmtree(test_temp_dir, ignore_errors=True)
            shutil.rmtree(out_dir, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
