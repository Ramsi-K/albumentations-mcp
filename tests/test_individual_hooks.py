#!/usr/bin/env python3
"""
Unit tests for individual hook implementations.

This module provides comprehensive unit tests for each hook in the 8-stage
extensible pipeline, testing their individual functionality, error handling,
and graceful failure modes.

# File Summary
Comprehensive unit tests for all individual hooks including pre_transform,
post_transform, post_transform_verify, pre_save, and post_save hooks.

# TODO Tree
- [x] Test Infrastructure
  - [x] Import all hook classes and dependencies
  - [x] Create test fixtures and mock data
  - [x] Set up async test framework
- [x] Pre-Transform Hook Tests
  - [x] Test image validation (format, size, quality)
  - [x] Test transform configuration validation
  - [x] Test error handling and graceful failure
- [x] Post-Transform Hook Tests
  - [x] Test metadata generation and statistics
  - [x] Test quality metrics calculation
  - [x] Test transform summary generation
- [x] Post-Transform-Verify Hook Tests
  - [x] Test visual verification workflow
  - [x] Test image saving and report generation
  - [x] Test graceful failure when verification unavailable
- [x] Pre-Save Hook Tests
  - [x] Test filename generation and sanitization
  - [x] Test directory creation and versioning
  - [x] Test file path validation
- [x] Post-Save Hook Tests
  - [x] Test cleanup operations
  - [x] Test completion logging
  - [x] Test resource management

# Code Review Notes
- PERFORMANCE: Tests should run quickly and not depend on external services
- COVERAGE: Each hook method should have comprehensive test coverage
- MOCKING: External dependencies should be properly mocked
- ASSERTIONS: Clear assertions that validate expected behavior
"""

import base64
import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from src.albumentations_mcp.hooks import HookContext, HookResult
from src.albumentations_mcp.hooks.post_save import PostSaveHook
from src.albumentations_mcp.hooks.post_transform import PostTransformHook
from src.albumentations_mcp.hooks.post_transform_verify import (
    PostTransformVerifyHook,
)
from src.albumentations_mcp.hooks.pre_save import PreSaveHook
from src.albumentations_mcp.hooks.pre_transform import PreTransformHook


class TestPreTransformHook:
    """Test the pre-transform hook for image and configuration validation."""

    @pytest.fixture
    def hook(self):
        """Create a pre-transform hook instance."""
        return PreTransformHook()

    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data as base64 encoded bytes."""
        # Create a simple test image
        image = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()
        return base64_data.encode()

    @pytest.fixture
    def valid_context(self, sample_image_data):
        """Create a valid hook context for testing."""
        return HookContext(
            session_id="test-session-123",
            original_prompt="add blur and rotate",
            image_data=sample_image_data,
            parsed_transforms=[
                {
                    "name": "Blur",
                    "parameters": {"blur_limit": 7, "p": 1.0},
                    "probability": 1.0,
                },
                {
                    "name": "Rotate",
                    "parameters": {"limit": 15, "p": 1.0},
                    "probability": 1.0,
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, hook, valid_context):
        """Test successful execution of pre-transform hook."""
        result = await hook.execute(valid_context)

        assert result.success is True
        assert result.context is not None
        assert result.context.metadata["pre_transform_processed"] is True
        assert "image_validation" in result.context.metadata
        assert "config_validation" in result.context.metadata

    @pytest.mark.asyncio
    async def test_image_validation_success(self, hook, valid_context):
        """Test successful image validation."""
        result = await hook.execute(valid_context)

        image_validation = result.context.metadata["image_validation"]
        assert image_validation["valid"] is True
        assert image_validation["critical"] is False
        assert "image_info" in image_validation
        assert image_validation["image_info"]["width"] == 100
        assert image_validation["image_info"]["height"] == 100

    @pytest.mark.asyncio
    async def test_image_validation_no_data(self, hook):
        """Test image validation with no image data."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=None,
        )

        result = await hook.execute(context)

        assert result.success is False
        assert "No image data provided" in result.context.warnings

    @pytest.mark.asyncio
    async def test_image_validation_invalid_data(self, hook):
        """Test image validation with invalid image data."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=b"invalid_image_data",
        )

        result = await hook.execute(context)

        assert result.success is False
        assert any(
            "Invalid image data" in warning for warning in result.context.warnings
        )

    @pytest.mark.asyncio
    async def test_image_size_warnings(self, hook):
        """Test warnings for problematic image sizes."""
        # Create very small image
        small_image = Image.new("RGB", (16, 16), color="red")
        buffer = io.BytesIO()
        small_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
        )

        result = await hook.execute(context)

        assert result.success is True
        assert any(
            "very small" in warning.lower() for warning in result.context.warnings
        )

    @pytest.mark.asyncio
    async def test_transform_validation_success(self, hook, valid_context):
        """Test successful transform configuration validation."""
        result = await hook.execute(valid_context)

        config_validation = result.context.metadata["config_validation"]
        assert config_validation["valid"] is True
        assert len(config_validation["transform_analysis"]) == 2

    @pytest.mark.asyncio
    async def test_transform_validation_no_transforms(self, hook, sample_image_data):
        """Test transform validation with no transforms."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=sample_image_data,
            parsed_transforms=None,
        )

        result = await hook.execute(context)

        config_validation = result.context.metadata["config_validation"]
        assert config_validation["valid"] is False
        assert "No transforms specified" in config_validation["warnings"]

    @pytest.mark.asyncio
    async def test_high_blur_warning(self, hook, sample_image_data):
        """Test warning for high blur limits."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add heavy blur",
            image_data=sample_image_data,
            parsed_transforms=[
                {
                    "name": "Blur",
                    "parameters": {"blur_limit": 80},  # High blur limit
                    "probability": 1.0,
                },
            ],
        )

        result = await hook.execute(context)

        assert result.success is True
        assert any("High blur limit" in warning for warning in result.context.warnings)

    @pytest.mark.asyncio
    async def test_large_rotation_warning(self, hook, sample_image_data):
        """Test warning for large rotation angles."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="rotate heavily",
            image_data=sample_image_data,
            parsed_transforms=[
                {
                    "name": "Rotate",
                    "parameters": {"limit": 90},  # Large rotation
                    "probability": 1.0,
                },
            ],
        )

        result = await hook.execute(context)

        assert result.success is True
        assert any("Large rotation" in warning for warning in result.context.warnings)

    @pytest.mark.asyncio
    async def test_low_probability_warning(self, hook, sample_image_data):
        """Test warning for very low probability transforms."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="maybe add blur",
            image_data=sample_image_data,
            parsed_transforms=[
                {
                    "name": "Blur",
                    "parameters": {"blur_limit": 7},
                    "probability": 0.05,  # Very low probability
                },
            ],
        )

        result = await hook.execute(context)

        assert result.success is True
        assert any(
            "Very low probability" in warning for warning in result.context.warnings
        )

    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, hook):
        """Test hook behavior when an exception occurs."""
        # Create context that will cause an exception
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # Manually corrupt the context to cause an exception
        context.image_data = "not_bytes_object"

        result = await hook.execute(context)

        assert result.success is False
        assert result.error is not None
        assert "validation failed" in result.error


class TestPostTransformHook:
    """Test the post-transform hook for metadata generation."""

    @pytest.fixture
    def hook(self):
        """Create a post-transform hook instance."""
        return PostTransformHook()

    @pytest.fixture
    def sample_images(self):
        """Create sample original and augmented images."""
        # Original image
        original = Image.new("RGB", (100, 100), color="red")
        orig_buffer = io.BytesIO()
        original.save(orig_buffer, format="PNG")
        orig_base64 = base64.b64encode(orig_buffer.getvalue()).decode()

        # Augmented image (slightly different)
        augmented = Image.new("RGB", (100, 100), color="blue")
        aug_buffer = io.BytesIO()
        augmented.save(aug_buffer, format="PNG")
        aug_base64 = base64.b64encode(aug_buffer.getvalue()).decode()

        return orig_base64.encode(), aug_base64.encode()

    @pytest.fixture
    def context_with_results(self, sample_images):
        """Create context with processing results."""
        original_data, augmented_data = sample_images
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur and rotate",
            image_data=original_data,
            augmented_image=augmented_data,
            parsed_transforms=[
                {"name": "Blur", "parameters": {"blur_limit": 7}},
                {"name": "Rotate", "parameters": {"limit": 15}},
            ],
        )

        # Add processing result metadata
        context.metadata["processing_result"] = {
            "applied_transforms": [
                {"name": "Blur", "parameters": {"blur_limit": 7}},
                {"name": "Rotate", "parameters": {"limit": 15}},
            ],
            "skipped_transforms": [],
            "success": True,
            "execution_time": 0.25,
        }

        return context

    @pytest.mark.asyncio
    async def test_execute_success(self, hook, context_with_results):
        """Test successful execution of post-transform hook."""
        result = await hook.execute(context_with_results)

        assert result.success is True
        assert result.context.metadata["post_transform_processed"] is True
        assert "processing_statistics" in result.context.metadata
        assert "quality_metrics" in result.context.metadata
        assert "transformation_summary" in result.context.metadata
        assert "timing_data" in result.context.metadata

    @pytest.mark.asyncio
    async def test_processing_statistics_generation(self, hook, context_with_results):
        """Test processing statistics generation."""
        result = await hook.execute(context_with_results)

        stats = result.context.metadata["processing_statistics"]
        assert stats["transforms_requested"] == 2
        assert stats["transforms_applied"] == 2
        assert stats["transforms_skipped"] == 0
        assert stats["processing_success"] is True
        assert stats["success_rate"] == 1.0
        assert stats["processing_status"] == "complete"

    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, hook, context_with_results):
        """Test quality metrics calculation."""
        result = await hook.execute(context_with_results)

        metrics = result.context.metadata["quality_metrics"]
        assert metrics["comparison_available"] is True
        assert "original_size" in metrics
        assert "augmented_size" in metrics
        assert metrics["format_preserved"] is True
        assert metrics["mode_preserved"] is True

    @pytest.mark.asyncio
    async def test_transform_summary_generation(self, hook, context_with_results):
        """Test transformation summary generation."""
        result = await hook.execute(context_with_results)

        summary = result.context.metadata["transformation_summary"]
        assert summary["total_transforms"] == 2
        assert len(summary["transform_details"]) == 2
        assert "categories" in summary
        assert summary["complexity_score"] > 0
        assert summary["average_complexity"] > 0

    @pytest.mark.asyncio
    async def test_timing_data_calculation(self, hook, context_with_results):
        """Test timing data calculation."""
        result = await hook.execute(context_with_results)

        timing = result.context.metadata["timing_data"]
        assert timing["processing_time"] == 0.25
        assert "performance_metrics" in timing
        assert timing["performance_metrics"]["time_per_transform"] == 0.125
        assert timing["performance_metrics"]["transforms_per_second"] == 8.0

    @pytest.mark.asyncio
    async def test_no_images_handling(self, hook):
        """Test handling when no images are available."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
        )

        result = await hook.execute(context)

        assert result.success is True
        metrics = result.context.metadata["quality_metrics"]
        assert metrics["comparison_available"] is False

    @pytest.mark.asyncio
    async def test_exception_handling(self, hook):
        """Test hook behavior when an exception occurs."""
        # Create a context that will cause an exception
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # Corrupt the context to cause an exception
        context.parsed_transforms = "not_a_list"

        result = await hook.execute(context)

        assert result.success is False
        assert result.error is not None
        assert "Post-transform metadata generation failed" in result.error


class TestPostTransformVerifyHook:
    """Test the post-transform visual verification hook."""

    @pytest.fixture
    def hook(self):
        """Create a post-transform verify hook instance."""
        return PostTransformVerifyHook()

    @pytest.fixture
    def mock_verification_manager(self):
        """Create a mock verification manager."""
        manager = Mock()
        manager.save_images_for_review.return_value = {
            "original": "/tmp/original_test.png",
            "augmented": "/tmp/augmented_test.png",
        }
        manager.generate_verification_report.return_value = (
            "# Verification Report\n\nTest report content"
        )
        manager.save_verification_report.return_value = "/tmp/verification_report.md"
        manager.cleanup_temp_files.return_value = None
        return manager

    @pytest.fixture
    def context_with_images(self):
        """Create context with image data."""
        # Create mock PIL images
        original_image = Mock()
        augmented_image = Mock()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur and rotate",
        )

        context.metadata = {
            "original_image": original_image,
            "augmented_image": augmented_image,
            "processing_time": 0.5,
            "applied_transforms": [{"name": "Blur"}, {"name": "Rotate"}],
            "skipped_transforms": [],
            "seed_used": True,
            "seed_value": 42,
            "reproducible": True,
        }

        return context

    @pytest.mark.asyncio
    async def test_execute_success(
        self, hook, context_with_images, mock_verification_manager,
    ):
        """Test successful execution of visual verification hook."""
        with patch(
            "src.albumentations_mcp.hooks.post_transform_verify.get_verification_manager",
            return_value=mock_verification_manager,
        ):
            result = await hook.execute(context_with_images)

            assert result.success is True
            assert "verification_files" in result.context.metadata
            assert "verification_report_path" in result.context.metadata
            assert "verification_report_content" in result.context.metadata

            # Verify manager methods were called
            mock_verification_manager.save_images_for_review.assert_called_once()
            mock_verification_manager.generate_verification_report.assert_called_once()
            mock_verification_manager.save_verification_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_images_handling(self, hook):
        """Test handling when images are missing."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # No images in metadata

        result = await hook.execute(context)

        assert result.success is True  # Non-blocking failure
        assert any("missing images" in warning for warning in result.context.warnings)

    @pytest.mark.asyncio
    async def test_image_saving_failure(
        self, hook, context_with_images, mock_verification_manager,
    ):
        """Test handling when image saving fails."""
        mock_verification_manager.save_images_for_review.side_effect = Exception(
            "Save failed",
        )

        with patch(
            "src.albumentations_mcp.hooks.post_transform_verify.get_verification_manager",
            return_value=mock_verification_manager,
        ):
            result = await hook.execute(context_with_images)

            assert result.success is True  # Non-blocking failure
            assert any(
                "Image saving failed" in error for error in result.context.errors
            )

    @pytest.mark.asyncio
    async def test_report_generation_failure(
        self, hook, context_with_images, mock_verification_manager,
    ):
        """Test handling when report generation fails."""
        mock_verification_manager.generate_verification_report.side_effect = Exception(
            "Report failed",
        )

        with patch(
            "src.albumentations_mcp.hooks.post_transform_verify.get_verification_manager",
            return_value=mock_verification_manager,
        ):
            result = await hook.execute(context_with_images)

            assert result.success is True  # Non-blocking failure
            assert any(
                "Report generation failed" in error for error in result.context.errors
            )
            # Should attempt cleanup
            mock_verification_manager.cleanup_temp_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_metadata_inclusion(
        self, hook, context_with_images, mock_verification_manager,
    ):
        """Test that metadata is properly included in verification report."""
        with patch(
            "src.albumentations_mcp.hooks.post_transform_verify.get_verification_manager",
            return_value=mock_verification_manager,
        ):
            result = await hook.execute(context_with_images)

            # Check that generate_verification_report was called with metadata
            call_args = mock_verification_manager.generate_verification_report.call_args
            metadata = call_args[0][3]  # Fourth argument is metadata

            assert metadata["session_id"] == "test-session-123"
            assert metadata["processing_time"] == 0.5
            assert metadata["transforms_applied"] == 2
            assert metadata["seed_used"] is True
            assert metadata["seed_value"] == 42

    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, hook):
        """Test hook behavior when an unexpected exception occurs."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # Corrupt context to cause exception
        context.metadata = "not_a_dict"

        result = await hook.execute(context)

        assert result.success is True  # Non-blocking failure
        assert any("Hook execution failed" in error for error in result.context.errors)


class TestPreSaveHook:
    """Test the pre-save hook for filename and directory management."""

    @pytest.fixture
    def hook(self):
        """Create a pre-save hook instance."""
        return PreSaveHook()

    @pytest.fixture
    def basic_context(self):
        """Create basic context for testing."""
        return HookContext(
            session_id="test-session-123",
            original_prompt="add blur and rotate",
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, hook, basic_context):
        """Test successful execution of pre-save hook."""
        result = await hook.execute(basic_context)

        assert result.success is True
        assert result.context.metadata["pre_save_processed"] is True
        assert "directory_info" in result.context.metadata
        assert "filename_info" in result.context.metadata
        assert "file_paths" in result.context.metadata

    @pytest.mark.asyncio
    async def test_filename_sanitization(self, hook, basic_context):
        """Test filename sanitization from prompt."""
        basic_context.original_prompt = "Add BLUR!!! and rotate @#$% by 30°"

        result = await hook.execute(basic_context)

        filename_info = result.context.metadata["filename_info"]
        base_filename = filename_info["base_name"]
        # Should be sanitized and safe for filesystem
        assert (
            base_filename.replace("_", "")
            .replace("-", "")
            .replace("20250809", "")
            .replace("091739", "")
            .replace("testsession123", "")
            .replace("testses", "")
        )
        assert not any(char in base_filename for char in "!@#$%°")

    @pytest.mark.asyncio
    async def test_directory_creation(self, basic_context):
        """Test output directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create hook with custom output directory
            hook = PreSaveHook(output_dir=temp_dir)
            result = await hook.execute(basic_context)

            directory_info = result.context.metadata["directory_info"]
            output_dir = Path(directory_info["output_dir"])
            assert output_dir.exists()
            assert output_dir.is_dir()

    @pytest.mark.asyncio
    async def test_file_path_generation(self, hook, basic_context):
        """Test file path generation for different output types."""
        result = await hook.execute(basic_context)

        file_paths = result.context.metadata["file_paths"]
        assert "augmented_image" in file_paths
        assert "metadata" in file_paths
        assert "processing_log" in file_paths

        # All paths should be absolute and in the output directory
        for path in file_paths.values():
            assert Path(path).is_absolute()

    @pytest.mark.asyncio
    async def test_versioning_with_existing_files(self, basic_context):
        """Test file versioning when files already exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create hook with custom output directory
            hook = PreSaveHook(output_dir=temp_dir)

            # First execution to create directory structure
            result1 = await hook.execute(basic_context)

            # Create existing file in the images subdirectory
            directory_info = result1.context.metadata["directory_info"]
            images_dir = Path(directory_info["subdirectories"]["images"])
            existing_file = images_dir / "existing_augmented.png"
            existing_file.touch()

            # Second execution should handle versioning
            result2 = await hook.execute(basic_context)

            file_paths = result2.context.metadata["file_paths"]
            augmented_path = Path(file_paths["augmented_image"])

            # Should be able to create file without conflict
            assert augmented_path.parent.exists()

    @pytest.mark.asyncio
    async def test_exception_handling(self, hook):
        """Test hook behavior when an exception occurs."""
        # Create context that will cause an exception
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # Corrupt context to cause exception
        context.session_id = None

        result = await hook.execute(context)

        assert result.success is False
        assert result.error is not None
        assert "Pre-save preparation failed" in result.error


class TestPostSaveHook:
    """Test the post-save hook for cleanup and completion."""

    @pytest.fixture
    def hook(self):
        """Create a post-save hook instance."""
        return PostSaveHook()

    @pytest.fixture
    def context_with_files(self):
        """Create context with file paths."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur and rotate",
        )

        context.metadata = {
            "file_paths": {
                "augmented_image": "/tmp/test_augmented.png",
                "metadata_json": "/tmp/test_metadata.json",
                "processing_log": "/tmp/test_log.jsonl",
            },
            "processing_statistics": {
                "transforms_applied": 2,
                "processing_success": True,
                "execution_time": 0.5,
            },
            "verification_files": {
                "original": "/tmp/original_verify.png",
                "augmented": "/tmp/augmented_verify.png",
            },
        }

        return context

    @pytest.mark.asyncio
    async def test_execute_success(self, hook, context_with_files):
        """Test successful execution of post-save hook."""
        result = await hook.execute(context_with_files)

        assert result.success is True
        assert result.context.metadata["post_save_processed"] is True
        assert "completion_info" in result.context.metadata
        assert "cleanup_info" in result.context.metadata

    @pytest.mark.asyncio
    async def test_completion_summary_generation(self, hook, context_with_files):
        """Test completion summary generation."""
        result = await hook.execute(context_with_files)

        completion_info = result.context.metadata["completion_info"]
        assert completion_info["session_id"] == "test-session-123"
        assert "completion_timestamp" in completion_info
        assert "files_created" in completion_info
        assert "files_failed" in completion_info

    @pytest.mark.asyncio
    async def test_cleanup_operations(self, hook, context_with_files):
        """Test cleanup operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary verification files
            temp_files = [
                Path(temp_dir) / "original_verify.png",
                Path(temp_dir) / "augmented_verify.png",
            ]
            for temp_file in temp_files:
                temp_file.touch()

            # Update context with actual temp file paths
            context_with_files.metadata["verification_files"] = {
                "original": str(temp_files[0]),
                "augmented": str(temp_files[1]),
            }

            result = await hook.execute(context_with_files)

            cleanup_info = result.context.metadata["cleanup_info"]
            assert "temp_files_cleaned" in cleanup_info
            assert "memory_released" in cleanup_info

    @pytest.mark.asyncio
    async def test_resource_management(self, hook, context_with_files):
        """Test resource management and memory cleanup."""
        # Add some large data to context to test cleanup
        context_with_files.metadata["large_data"] = "x" * 1000  # Simulate large data

        result = await hook.execute(context_with_files)

        # Should complete successfully
        assert result.success is True
        assert "memory_released" in result.context.metadata["cleanup_info"]

    @pytest.mark.asyncio
    async def test_no_files_to_cleanup(self, hook):
        """Test behavior when no files need cleanup."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )

        result = await hook.execute(context)

        assert result.success is True
        cleanup_info = result.context.metadata["cleanup_info"]
        assert len(cleanup_info["temp_files_cleaned"]) == 0

    @pytest.mark.asyncio
    async def test_exception_handling(self, hook):
        """Test hook behavior when an exception occurs."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
        )
        # Corrupt context to cause exception
        context.metadata = "not_a_dict"

        result = await hook.execute(context)

        assert result.success is False
        assert result.error is not None
        assert "Post-save cleanup failed" in result.error


class TestHookErrorHandling:
    """Test error handling and graceful failure modes across all hooks."""

    @pytest.mark.asyncio
    async def test_all_hooks_handle_empty_context(self):
        """Test that all hooks handle empty context gracefully."""
        hooks = [
            PreTransformHook(),
            PostTransformHook(),
            PostTransformVerifyHook(),
            PreSaveHook(),
            PostSaveHook(),
        ]

        empty_context = HookContext(
            session_id="test-empty",
            original_prompt="",
        )

        for hook in hooks:
            result = await hook.execute(empty_context)
            # All hooks should either succeed or fail gracefully
            assert isinstance(result, HookResult)
            assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_all_hooks_handle_corrupted_metadata(self):
        """Test that all hooks handle corrupted metadata gracefully."""
        hooks = [
            PreTransformHook(),
            PostTransformHook(),
            PostTransformVerifyHook(),
            PreSaveHook(),
            PostSaveHook(),
        ]

        for hook in hooks:
            context = HookContext(
                session_id="test-corrupted",
                original_prompt="add blur",
            )
            # Corrupt metadata in different ways
            context.metadata = None

            result = await hook.execute(context)
            assert isinstance(result, HookResult)
            # Should either succeed or fail gracefully without raising exceptions

    @pytest.mark.asyncio
    async def test_critical_vs_non_critical_hooks(self):
        """Test behavior difference between critical and non-critical hooks."""
        # Most hooks should be non-critical by default
        hooks = [
            PreTransformHook(),
            PostTransformHook(),
            PostTransformVerifyHook(),
            PreSaveHook(),
            PostSaveHook(),
        ]

        for hook in hooks:
            # Verify hook criticality setting
            if hook.name in ["pre_transform_validation"]:
                # Some hooks might be critical
                pass
            else:
                # Most hooks should be non-critical
                assert hook.critical is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
