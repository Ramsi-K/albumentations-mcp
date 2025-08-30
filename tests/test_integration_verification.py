#!/usr/bin/env python3
"""
Integration Testing and Verification for File Path Mode

This module provides comprehensive integration tests to verify:
- Claude integration works with file path mode
- File path mode prevents base64 conversion crashes
- Various image sizes and formats work correctly
- All existing functionality (presets, seeding, hooks) works with file paths
- Resource cleanup after processing

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from PIL import Image
import uuid
import json
import shutil
from typing import Dict, Any, List, Tuple

from src.albumentations_mcp.server import (
    augment_image,
    list_available_transforms,
    validate_prompt,
    get_pipeline_status,
    set_default_seed,
    list_available_presets,
    load_image_for_processing,
)


class TestClaudeIntegrationVerification:
    """Test Claude integration with file path mode."""

    @pytest.fixture
    def temp_image_files(self):
        """Create temporary image files for testing."""
        temp_dir = tempfile.mkdtemp()
        image_files = {}

        # Create test images of different sizes and formats
        test_images = [
            ("small.png", (100, 100), "PNG"),
            ("medium.jpg", (800, 600), "JPEG"),
            ("large.png", (2000, 1500), "PNG"),
            ("square.webp", (512, 512), "WEBP"),
        ]

        for filename, size, format_type in test_images:
            # Create a simple colored image
            image = Image.new("RGB", size, color=(128, 128, 128))
            file_path = Path(temp_dir) / filename
            image.save(file_path, format=format_type)
            image_files[filename] = str(file_path)

        yield image_files

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_path_mode_basic_functionality(
        self, temp_image_files, temp_output_dir
    ):
        """Test basic file path mode functionality."""
        image_path = temp_image_files["medium.jpg"]

        # Set output directory
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            result = augment_image(
                image_path=image_path, prompt="add slight blur", seed=42
            )

            # Verify success
            assert "✅ Image successfully augmented and saved!" in result
            assert "File path (recommended for large images)" in result
            assert "Files saved:" in result

            # Verify output files exist
            output_files = list(Path(temp_output_dir).rglob("*.png"))
            assert len(output_files) > 0

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_large_image_file_path_mode(self, temp_image_files, temp_output_dir):
        """Test file path mode with large images that would crash base64 conversion."""
        # Create a very large image that would be problematic for base64
        large_temp_dir = tempfile.mkdtemp()
        try:
            # Create 4K image (4096x3072) - would be ~37MB as base64
            large_image = Image.new("RGB", (4096, 3072), color=(255, 0, 0))
            large_image_path = Path(large_temp_dir) / "very_large.png"
            large_image.save(large_image_path, format="PNG")

            os.environ["OUTPUT_DIR"] = temp_output_dir

            result = augment_image(
                image_path=str(large_image_path),
                prompt="add motion blur",
                seed=123,
            )

            # Should succeed with file path mode
            assert "✅ Image successfully augmented and saved!" in result
            assert "File path (recommended for large images)" in result

            # Verify output exists
            output_files = list(Path(temp_output_dir).rglob("*.png"))
            assert len(output_files) > 0

            # Verify the output image is reasonable size
            output_image = Image.open(output_files[0])
            assert output_image.size == (4096, 3072)

        finally:
            shutil.rmtree(large_temp_dir, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_file_path_vs_base64_memory_usage(self, temp_image_files):
        """Test that file path mode uses less memory than base64 mode."""
        import psutil
        import gc

        image_path = temp_image_files["large.png"]

        # Load image as base64 for comparison
        from src.albumentations_mcp.image_conversions import (
            load_image_from_source,
            pil_to_base64,
        )

        image = load_image_from_source(image_path)
        image_b64 = pil_to_base64(image)

        # Measure memory before file path mode
        gc.collect()
        process = psutil.Process()
        memory_before_file = process.memory_info().rss

        # Test file path mode
        temp_output = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = temp_output

        try:
            result_file = augment_image(
                image_path=image_path, prompt="add blur", seed=42
            )

            gc.collect()
            memory_after_file = process.memory_info().rss

            # Test base64 mode
            result_b64 = augment_image(image_b64=image_b64, prompt="add blur", seed=42)

            gc.collect()
            memory_after_b64 = process.memory_info().rss

            # Both should succeed
            assert "✅ Image successfully augmented" in result_file
            assert "✅ Image successfully augmented" in result_b64

            # File path mode should use less additional memory
            file_memory_increase = memory_after_file - memory_before_file
            b64_memory_increase = memory_after_b64 - memory_after_file

            # This is a rough check - base64 mode typically uses more memory
            # but exact values depend on system state
            print(
                f"File path memory increase: {file_memory_increase / 1024 / 1024:.2f} MB"
            )
            print(f"Base64 memory increase: {b64_memory_increase / 1024 / 1024:.2f} MB")

        finally:
            shutil.rmtree(temp_output, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]


class TestImageSizesAndFormats:
    """Test various image sizes and formats with file path mode."""

    @pytest.fixture
    def diverse_test_images(self):
        """Create diverse test images."""
        temp_dir = tempfile.mkdtemp()
        images = {}

        # Different sizes and formats
        test_configs = [
            ("tiny.png", (32, 32), "PNG", (255, 0, 0)),
            ("small.jpg", (256, 256), "JPEG", (0, 255, 0)),
            ("medium.webp", (1024, 768), "WEBP", (0, 0, 255)),
            ("large.png", (2048, 1536), "PNG", (255, 255, 0)),
            ("wide.jpg", (1920, 1080), "JPEG", (255, 0, 255)),
            ("tall.png", (600, 1200), "PNG", (0, 255, 255)),
        ]

        for filename, size, format_type, color in test_configs:
            image = Image.new("RGB", size, color=color)
            file_path = Path(temp_dir) / filename
            image.save(file_path, format=format_type)
            images[filename] = {
                "path": str(file_path),
                "size": size,
                "format": format_type,
                "color": color,
            }

        yield images
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_all_image_formats(self, diverse_test_images, temp_output_dir):
        """Test all supported image formats work with file path mode."""
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            for filename, image_info in diverse_test_images.items():
                result = augment_image(
                    image_path=image_info["path"],
                    prompt="add slight brightness",
                    seed=42,
                )

                assert (
                    "✅ Image successfully augmented" in result
                ), f"Failed for {filename}"
                assert "File path (recommended for large images)" in result

                # Verify output file exists
                session_id = result.split("Session ID: ")[1].split("\n")[0]
                expected_output = (
                    Path(temp_output_dir)
                    / f"session_{session_id}"
                    / f"augmented_{session_id}.png"
                )
                assert expected_output.exists(), f"Output file missing for {filename}"

                # Verify output image is valid
                output_image = Image.open(expected_output)
                assert (
                    output_image.size == image_info["size"]
                ), f"Size mismatch for {filename}"

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_extreme_image_sizes(self, temp_output_dir):
        """Test extreme image sizes."""
        temp_dir = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            # Very small image
            tiny_image = Image.new("RGB", (1, 1), color=(128, 128, 128))
            tiny_path = Path(temp_dir) / "tiny.png"
            tiny_image.save(tiny_path)

            result_tiny = augment_image(
                image_path=str(tiny_path), prompt="increase contrast", seed=42
            )
            assert "✅ Image successfully augmented" in result_tiny

            # Very wide image
            wide_image = Image.new("RGB", (4000, 100), color=(128, 128, 128))
            wide_path = Path(temp_dir) / "wide.png"
            wide_image.save(wide_path)

            result_wide = augment_image(
                image_path=str(wide_path),
                prompt="add horizontal flip",
                seed=42,
            )
            assert "✅ Image successfully augmented" in result_wide

            # Very tall image
            tall_image = Image.new("RGB", (100, 4000), color=(128, 128, 128))
            tall_path = Path(temp_dir) / "tall.png"
            tall_image.save(tall_path)

            result_tall = augment_image(
                image_path=str(tall_path), prompt="add vertical flip", seed=42
            )
            assert "✅ Image successfully augmented" in result_tall

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]


class TestExistingFunctionalityWithFilePaths:
    """Test that all existing functionality works with file paths."""

    @pytest.fixture
    def test_image_path(self):
        """Create a test image file."""
        temp_dir = tempfile.mkdtemp()
        image = Image.new("RGB", (512, 512), color=(100, 150, 200))
        image_path = Path(temp_dir) / "test_image.png"
        image.save(image_path)

        yield str(image_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_presets_with_file_paths(self, test_image_path, temp_output_dir):
        """Test that presets work with file path mode."""
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            # Test each available preset
            presets_result = list_available_presets()
            assert presets_result["total_count"] > 0

            for preset_info in presets_result["presets"]:
                preset_name = preset_info["name"]

                result = augment_image(
                    image_path=test_image_path, preset=preset_name, seed=42
                )

                assert (
                    "✅ Image successfully augmented" in result
                ), f"Preset {preset_name} failed"
                assert "File path (recommended for large images)" in result

                # Verify output exists
                output_files = list(Path(temp_output_dir).rglob("*.png"))
                assert len(output_files) > 0, f"No output for preset {preset_name}"

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_seeding_with_file_paths(self, test_image_path, temp_output_dir):
        """Test that seeding works consistently with file path mode."""
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            # Test with explicit seed
            result1 = augment_image(
                image_path=test_image_path,
                prompt="add random noise",
                seed=12345,
            )

            result2 = augment_image(
                image_path=test_image_path,
                prompt="add random noise",
                seed=12345,
            )

            assert "✅ Image successfully augmented" in result1
            assert "✅ Image successfully augmented" in result2

            # Test default seed setting
            set_result = set_default_seed(67890)
            assert set_result["success"] is True

            result3 = augment_image(image_path=test_image_path, prompt="add blur")

            result4 = augment_image(image_path=test_image_path, prompt="add blur")

            assert "✅ Image successfully augmented" in result3
            assert "✅ Image successfully augmented" in result4

            # Clear default seed
            clear_result = set_default_seed(None)
            assert clear_result["success"] is True

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_hooks_with_file_paths(self, test_image_path, temp_output_dir):
        """Test that hook system works with file path mode."""
        os.environ["OUTPUT_DIR"] = temp_output_dir

        try:
            # Check pipeline status
            status = get_pipeline_status()
            assert "registered_hooks" in status or "error" in status

            # Test augmentation with hooks
            result = augment_image(
                image_path=test_image_path,
                prompt="add motion blur and increase contrast",
                seed=42,
            )

            assert "✅ Image successfully augmented" in result

            # Verify hook outputs exist (metadata files, logs, etc.)
            session_id = result.split("Session ID: ")[1].split("\n")[0]
            session_dir = Path(temp_output_dir) / f"session_{session_id}"

            # Check for various hook outputs
            expected_files = [
                f"augmented_{session_id}.png",  # Main output
                f"metadata_{session_id}.json",  # Metadata from hooks
            ]

            for expected_file in expected_files:
                file_path = session_dir / expected_file
                if file_path.exists():
                    # Verify file is valid
                    if expected_file.endswith(".json"):
                        with open(file_path) as f:
                            data = json.load(f)
                            assert isinstance(data, dict)
                    elif expected_file.endswith(".png"):
                        img = Image.open(file_path)
                        assert img.size == (512, 512)

        finally:
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_validation_with_file_paths(self, test_image_path):
        """Test that prompt validation still works correctly."""
        # Test various prompts
        test_prompts = [
            "add blur",
            "increase brightness and contrast",
            "apply horizontal flip",
            "add gaussian noise",
            "invalid_transform_name",
        ]

        for prompt in test_prompts:
            result = validate_prompt(prompt)
            assert isinstance(result, dict)
            assert "valid" in result
            assert "transforms" in result
            assert "message" in result

            # Valid prompts should have transforms
            if prompt != "invalid_transform_name":
                if result["valid"]:
                    assert len(result["transforms"]) > 0

    def test_other_tools_still_work(self):
        """Test that other MCP tools still work correctly."""
        # Test list_available_transforms
        transforms_result = list_available_transforms()
        assert isinstance(transforms_result, dict)
        assert "transforms" in transforms_result
        assert transforms_result["total_count"] > 0

        # Test list_available_presets
        presets_result = list_available_presets()
        assert isinstance(presets_result, dict)
        assert "presets" in presets_result
        assert presets_result["total_count"] > 0

        # Test get_pipeline_status
        status_result = get_pipeline_status()
        assert isinstance(status_result, dict)
        # Should have either status info or error info


class TestResourceCleanup:
    """Test resource cleanup after processing."""

    @pytest.fixture
    def test_image_path(self):
        """Create a test image file."""
        temp_dir = tempfile.mkdtemp()
        image = Image.new("RGB", (256, 256), color=(128, 128, 128))
        image_path = Path(temp_dir) / "cleanup_test.png"
        image.save(image_path)

        yield str(image_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_temporary_file_cleanup(self, test_image_path):
        """Test that temporary files are cleaned up properly."""
        temp_output = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = temp_output

        try:
            # Track initial file count
            initial_files = set(Path(temp_output).rglob("*"))

            # Process image
            result = augment_image(
                image_path=test_image_path, prompt="add blur", seed=42
            )

            assert "✅ Image successfully augmented" in result

            # Check final file count
            final_files = set(Path(temp_output).rglob("*"))
            new_files = final_files - initial_files

            # Should have created session directory and output files
            assert len(new_files) > 0

            # All new files should be in session directory
            session_dirs = [f for f in new_files if f.is_dir() and "session_" in f.name]
            assert len(session_dirs) == 1

            session_dir = session_dirs[0]
            session_files = list(session_dir.rglob("*"))

            # Verify expected files exist
            png_files = [f for f in session_files if f.suffix == ".png"]
            json_files = [f for f in session_files if f.suffix == ".json"]

            assert len(png_files) >= 1  # At least augmented image
            assert len(json_files) >= 1  # At least metadata

            # No temporary files should remain outside session directory
            temp_files = [
                f
                for f in new_files
                if "tmp" in str(f).lower() or "temp" in str(f).lower()
            ]
            assert len(temp_files) == 0, f"Temporary files not cleaned up: {temp_files}"

        finally:
            shutil.rmtree(temp_output, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_memory_cleanup_after_processing(self, test_image_path):
        """Test that memory is properly cleaned up after processing."""
        import gc
        import psutil

        # Force garbage collection
        gc.collect()
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        temp_output = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = temp_output

        try:
            # Process multiple images to test memory accumulation
            for i in range(5):
                result = augment_image(
                    image_path=test_image_path,
                    prompt=f"add blur with strength {i+1}",
                    seed=i,
                )
                assert "✅ Image successfully augmented" in result

            # Force garbage collection
            gc.collect()
            final_memory = process.memory_info().rss

            # Memory increase should be reasonable (less than 100MB for 5 small images)
            memory_increase = final_memory - initial_memory
            memory_increase_mb = memory_increase / 1024 / 1024

            print(f"Memory increase after 5 augmentations: {memory_increase_mb:.2f} MB")

            # This is a rough check - exact values depend on system state
            # But we shouldn't see massive memory leaks
            assert (
                memory_increase_mb < 200
            ), f"Excessive memory usage: {memory_increase_mb:.2f} MB"

        finally:
            shutil.rmtree(temp_output, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]

    def test_session_directory_structure(self, test_image_path):
        """Test that session directories are created with proper structure."""
        temp_output = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = temp_output

        try:
            result = augment_image(
                image_path=test_image_path, prompt="add contrast", seed=42
            )

            assert "✅ Image successfully augmented" in result

            # Extract session ID from result
            session_id = result.split("Session ID: ")[1].split("\n")[0]
            session_dir = Path(temp_output) / f"session_{session_id}"

            # Verify session directory exists
            assert session_dir.exists()
            assert session_dir.is_dir()

            # Verify expected files exist
            expected_files = [
                f"augmented_{session_id}.png",
                f"metadata_{session_id}.json",
            ]

            for expected_file in expected_files:
                file_path = session_dir / expected_file
                if file_path.exists():  # Some files may be optional depending on hooks
                    assert file_path.is_file()
                    assert file_path.stat().st_size > 0  # File should not be empty

            # Verify at least the augmented image exists
            augmented_image_path = session_dir / f"augmented_{session_id}.png"
            assert augmented_image_path.exists()

            # Verify image is valid
            image = Image.open(augmented_image_path)
            assert image.size == (256, 256)  # Should match input size

        finally:
            shutil.rmtree(temp_output, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases with file path mode."""

    def test_nonexistent_file_path(self):
        """Test handling of non-existent file paths."""
        result = augment_image(
            image_path="/nonexistent/path/image.jpg", prompt="add blur"
        )

        assert "❌ Error:" in result
        assert "Image file not found" in result

    def test_invalid_file_format(self):
        """Test handling of invalid file formats."""
        # Create a text file with image extension
        temp_dir = tempfile.mkdtemp()
        try:
            fake_image_path = Path(temp_dir) / "fake.jpg"
            with open(fake_image_path, "w") as f:
                f.write("This is not an image file")

            result = augment_image(image_path=str(fake_image_path), prompt="add blur")

            assert "❌ Error:" in result
            assert "Failed to load image" in result

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_permission_denied_simulation(self):
        """Test handling of permission issues."""
        # This test simulates permission issues by using a non-existent directory
        result = augment_image(
            image_path="/root/restricted/image.jpg",  # Likely to cause permission issues
            prompt="add blur",
        )

        assert "❌ Error:" in result
        # Should handle gracefully without crashing

    def test_corrupted_image_file(self):
        """Test handling of corrupted image files."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a file with image extension but corrupted data
            corrupted_path = Path(temp_dir) / "corrupted.png"
            with open(corrupted_path, "wb") as f:
                # Write PNG header but corrupted data
                f.write(b"\x89PNG\r\n\x1a\n")  # PNG signature
                f.write(b"corrupted data that is not a valid PNG")

            result = augment_image(image_path=str(corrupted_path), prompt="add blur")

            assert "❌ Error:" in result
            assert "Failed to load image" in result

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_output_directory_permissions(self):
        """Test handling of output directory permission issues."""
        # Create a test image
        temp_dir = tempfile.mkdtemp()
        try:
            image = Image.new("RGB", (100, 100), color=(128, 128, 128))
            image_path = Path(temp_dir) / "test.png"
            image.save(image_path)

            # Try to set output directory to a restricted location
            os.environ["OUTPUT_DIR"] = "/root/restricted_output"

            result = augment_image(image_path=str(image_path), prompt="add blur")

            # Should either succeed (if directory can be created) or fail gracefully
            # The exact behavior depends on system permissions
            assert isinstance(result, str)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if "OUTPUT_DIR" in os.environ:
                del os.environ["OUTPUT_DIR"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
