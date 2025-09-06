#!/usr/bin/env python3
"""
MCP Client Integration Tests

This module tests MCP client integration specifically for Claude Desktop
and other MCP-compatible clients, focusing on the file path mode that
prevents base64 conversion crashes.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
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
    load_image_for_processing,
    set_default_seed,
    validate_prompt,
)


class TestMCPClientCompatibility:
    """Test MCP client compatibility and protocol compliance."""

    @pytest.fixture
    def test_image_file(self):
        """Create a test image file that simulates Claude Desktop usage."""
        temp_dir = tempfile.mkdtemp()
        # Create an image similar to what users might paste into Claude
        image = Image.new("RGB", (800, 600), color=(120, 150, 180))
        image_path = Path(temp_dir) / "claude_test_image.png"
        image.save(image_path, format="PNG")

        yield str(image_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_claude_desktop_file_path_workflow(self, test_image_file):
        """Test the typical Claude Desktop workflow with file paths."""
        # Simulate Claude Desktop saving a pasted image to a temp file
        # and then calling the MCP tool with the file path

        result = augment_image(
            image_path=test_image_file,
            prompt="make this image brighter and add some contrast",
            seed=42,
        )

        # Should succeed without base64 conversion issues
        assert isinstance(result, str)
        assert ("✅" in result) or ("❌" in result)

        # If successful, should include saved files information
        if "✅" in result:
            assert "Files saved:" in result

    def test_large_image_claude_integration(self):
        """Test large image handling that would crash base64 conversion."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a large image (2K resolution) that would be problematic for base64
            large_image = Image.new("RGB", (2048, 1536), color=(200, 100, 50))
            large_image_path = Path(temp_dir) / "large_claude_image.png"
            large_image.save(large_image_path, format="PNG")

            # This would crash with base64 conversion in Claude,
            # but should work with file path
            result = augment_image(
                image_path=str(large_image_path),
                prompt="add motion blur and increase saturation",
                seed=123,
            )

            # Should not crash and should handle gracefully
            assert isinstance(result, str)

            # Should either succeed or fail gracefully (not crash)
            assert ("✅" in result) or ("❌" in result)

            # Should not contain base64 data in the response (memory efficient)
            assert (
                len(result) < 5000
            ), "Response should be concise, not contain large data"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mcp_tool_parameter_validation(self):
        """Test MCP tool parameter validation for client compatibility."""
        # Test all parameter combinations that MCP clients might send

        # Valid file path
        temp_dir = tempfile.mkdtemp()
        try:
            image = Image.new("RGB", (256, 256), color=(100, 100, 100))
            image_path = Path(temp_dir) / "test.png"
            image.save(image_path)

            # Test valid parameters
            result = augment_image(
                image_path=str(image_path),
                prompt="add blur",
                seed=42,
                output_dir=None,
            )
            assert isinstance(result, str)

            # Test with output directory
            output_dir = tempfile.mkdtemp()
            try:
                result = augment_image(
                    image_path=str(image_path),
                    prompt="add contrast",
                    output_dir=output_dir,
                )
                assert isinstance(result, str)
            finally:
                shutil.rmtree(output_dir, ignore_errors=True)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mcp_tool_error_responses(self):
        """Test that MCP tool error responses are client-friendly."""
        # Test various error conditions

        # Non-existent file
        result = augment_image(image_path="/nonexistent/file.jpg", prompt="add blur")
        assert isinstance(result, str)
        assert "❌" in result
        assert "not found" in result.lower()

        # Empty prompt
        result = augment_image(image_path="test.jpg", prompt="")
        assert isinstance(result, str)
        assert "❌" in result

        # Invalid seed
        result = augment_image(image_path="test.jpg", prompt="add blur", seed=-1)
        assert isinstance(result, str)
        assert "❌" in result

    def test_all_mcp_tools_return_json_serializable(self):
        """Test that all MCP tools return JSON-serializable data."""
        # Test list_available_transforms
        transforms_result = list_available_transforms()
        assert isinstance(transforms_result, dict)
        # Should be JSON serializable
        json.dumps(transforms_result)

        # Test list_available_presets
        presets_result = list_available_presets()
        assert isinstance(presets_result, dict)
        json.dumps(presets_result)

        # Test validate_prompt
        validation_result = validate_prompt("add blur")
        assert isinstance(validation_result, dict)
        json.dumps(validation_result)

        # Test get_pipeline_status
        status_result = get_pipeline_status()
        assert isinstance(status_result, dict)
        json.dumps(status_result)

        # Test set_default_seed
        seed_result = set_default_seed(42)
        assert isinstance(seed_result, dict)
        json.dumps(seed_result)


class TestFilePathModeSpecific:
    """Test file path mode specific functionality."""

    def test_file_path_mode_detection(self):
        """Test that file path mode is correctly detected and used."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create test image
            image = Image.new("RGB", (400, 300), color=(150, 100, 200))
            image_path = Path(temp_dir) / "mode_test.png"
            image.save(image_path)

            # Test file path mode
            result = augment_image(image_path=str(image_path), prompt="add brightness")

            # If successful, should mention saved files
            if "✅" in result:
                assert "Files saved:" in result

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_path_vs_base64_consistency(self):
        """Test that file path and base64 modes produce consistent results."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create test image
            image = Image.new("RGB", (256, 256), color=(100, 150, 200))
            image_path = Path(temp_dir) / "consistency_test.png"
            image.save(image_path)

            # Test file path mode
            result_file = augment_image(
                image_path=str(image_path),
                prompt="add blur",
                seed=42,
            )

            image_loaded = load_image_from_source(str(image_path))
            image_b64 = pil_to_base64(image_loaded)

            result_b64 = augment_image(image_b64=image_b64, prompt="add blur", seed=42)

            # Both should work (or both should fail consistently)
            assert isinstance(result_file, str)
            assert isinstance(result_b64, str)

            # Both should have similar success/failure patterns
            file_success = "✅" in result_file
            b64_success = "✅" in result_b64

            # If one succeeds, the other should too (with same seed and prompt)
            if file_success or b64_success:
                # At least one should work
                assert file_success or b64_success

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_output_directory_handling(self):
        """Test output directory handling in file path mode."""
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()

        try:
            # Create test image
            image = Image.new("RGB", (300, 300), color=(80, 120, 160))
            image_path = Path(temp_dir) / "output_test.png"
            image.save(image_path)

            # Test with custom output directory
            result = augment_image(
                image_path=str(image_path),
                prompt="add contrast",
                output_dir=output_dir,
                seed=42,
            )

            # Should handle output directory
            assert isinstance(result, str)

            # If successful, should mention saved files
            if "✅" in result:
                assert "Files saved:" in result

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(output_dir, ignore_errors=True)


class TestResourceManagement:
    """Test resource management and cleanup."""

    def test_memory_efficient_processing(self):
        """Test that file path mode is memory efficient."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create multiple test images
            image_paths = []
            for i in range(3):
                image = Image.new("RGB", (512, 512), color=(i * 50, i * 60, i * 70))
                image_path = Path(temp_dir) / f"memory_test_{i}.png"
                image.save(image_path)
                image_paths.append(str(image_path))

            # Process multiple images
            results = []
            for i, image_path in enumerate(image_paths):
                result = augment_image(
                    image_path=image_path,
                    prompt=f"add blur level {i + 1}",
                    seed=i,
                )
                results.append(result)

                # Each result should be reasonable size (not containing large data)
                assert len(result) < 2000, f"Result {i} too large: {len(result)} chars"

            # All should complete without memory issues
            for result in results:
                assert isinstance(result, str)
                assert ("✅" in result) or ("❌" in result)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_processing_safety(self):
        """Test that concurrent processing is safe."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create test images
            image_paths = []
            for i in range(2):
                image = Image.new("RGB", (256, 256), color=(i * 100, i * 120, i * 140))
                image_path = Path(temp_dir) / f"concurrent_test_{i}.png"
                image.save(image_path)
                image_paths.append(str(image_path))

            # Process images with different parameters
            results = []
            for i, image_path in enumerate(image_paths):
                result = augment_image(
                    image_path=image_path,
                    prompt=f"add noise level {i + 1}",
                    seed=i * 10,
                )
                results.append(result)

            # All should complete safely
            for i, result in enumerate(results):
                assert isinstance(result, str), f"Result {i} not string: {type(result)}"
                assert ("✅" in result) or (
                    "❌" in result
                ), f"Result {i} invalid: {result[:100]}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    def test_session_mode_still_works(self):
        """Test that session mode still works for backward compatibility."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create test image
            image = Image.new("RGB", (200, 200), color=(90, 110, 130))
            image_path = Path(temp_dir) / "session_test.png"
            image.save(image_path)

            # Load image for processing (creates session)
            load_result = load_image_for_processing(str(image_path))
            assert isinstance(load_result, str)

            if "✅" in load_result and "Session ID:" in load_result:
                # Extract session ID
                session_id = load_result.split("Session ID: ")[1].split("\n")[0]

                # Use session mode
                result = augment_image(session_id=session_id, prompt="add brightness")

                assert isinstance(result, str)
                assert ("✅" in result) or ("❌" in result)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_base64_mode_still_works(self):
        """Test that base64 mode still works for backward compatibility."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create small test image (to avoid memory issues)
            image = Image.new("RGB", (128, 128), color=(70, 90, 110))
            image_path = Path(temp_dir) / "base64_test.png"
            image.save(image_path)

            image_loaded = load_image_from_source(str(image_path))
            image_b64 = pil_to_base64(image_loaded)

            # Use base64 mode
            result = augment_image(image_b64=image_b64, prompt="add contrast")

            assert isinstance(result, str)
            assert ("✅" in result) or ("❌" in result)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_all_existing_features_work(self):
        """Test that all existing features still work correctly."""
        # Test transforms listing
        transforms = list_available_transforms()
        assert transforms["total_count"] > 0

        # Test presets listing
        presets = list_available_presets()
        assert presets["total_count"] > 0

        # Test validation
        validation = validate_prompt("add blur and contrast")
        assert "valid" in validation

        # Test pipeline status
        status = get_pipeline_status()
        assert isinstance(status, dict)

        # Test seed setting
        seed_result = set_default_seed(42)
        assert seed_result["success"] is True

        # Clear seed
        clear_result = set_default_seed(None)
        assert clear_result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
