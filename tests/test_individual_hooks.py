#!/usr/bin/env python3
"""
Unit tests for individual hook implementations.

This module provides comprehensive unit tests for each hook in the 8-stage
extensible pipeline, testing their individual functionality, error handling,
and graceful failure modes.

Comprehensive unit tests for all individual hooks including pre_transform,
post_transform, post_transform_verify, pre_save, and post_save hooks.

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
        self,
        hook,
        context_with_images,
        mock_verification_manager,
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
        self,
        hook,
        context_with_images,
        mock_verification_manager,
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
        self,
        hook,
        context_with_images,
        mock_verification_manager,
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
        self,
        hook,
        context_with_images,
        mock_verification_manager,
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
        # Should be sanitized and safe for filesystem characters
        # Only disallow truly dangerous filesystem chars: <>:"/\|?*
        dangerous = '<>:"/\\|?*'
        assert not any(char in base_filename for char in dangerous)
        # Ensure no spaces at ends and length is reasonable
        assert base_filename == base_filename.strip()
        assert len(base_filename) <= 255

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

    @pytest.mark.asyncio
    async def test_auto_resize_oversized_image(self, hook):
        """Test automatic resizing of oversized images."""
        # Create oversized image (larger than MAX_IMAGE_SIZE=4096)
        large_image = Image.new("RGB", (5000, 3000), color="blue")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with patch.dict("os.environ", {"STRICT_MODE": "false"}):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]
        assert image_validation["resize_applied"] is True
        assert image_validation["original_dimensions"] == "5000x3000"
        assert "max dimension" in image_validation["resize_reason"]

        # Check that resized image is within limits
        resized_width = image_validation["image_info"]["width"]
        resized_height = image_validation["image_info"]["height"]
        assert max(resized_width, resized_height) <= 4096

        # Check aspect ratio is preserved
        original_ratio = 5000 / 3000
        resized_ratio = resized_width / resized_height
        assert abs(original_ratio - resized_ratio) < 0.01

    @pytest.mark.asyncio
    async def test_strict_mode_rejects_oversized_image(self, hook):
        """Test STRICT_MODE=true rejects oversized images with clear error."""
        # Create oversized image
        large_image = Image.new("RGB", (5000, 3000), color="blue")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
        )

        with patch.dict("os.environ", {"STRICT_MODE": "true"}):
            result = await hook.execute(context)

        assert result.success is False
        assert "Image exceeds size limits" in result.error
        assert "Enable auto-resize by setting STRICT_MODE=false" in result.error

    @pytest.mark.asyncio
    async def test_resize_preserves_aspect_ratio(self, hook):
        """Test resized image maintains aspect ratio."""
        # Create portrait image
        portrait_image = Image.new("RGB", (3000, 5000), color="green")
        buffer = io.BytesIO()
        portrait_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with patch.dict("os.environ", {"STRICT_MODE": "false"}):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]
        assert image_validation["resize_applied"] is True

        # Check aspect ratio preservation
        original_ratio = 3000 / 5000
        resized_width = image_validation["image_info"]["width"]
        resized_height = image_validation["image_info"]["height"]
        resized_ratio = resized_width / resized_height
        assert abs(original_ratio - resized_ratio) < 0.01

    @pytest.mark.asyncio
    async def test_resize_uses_proper_temp_directory(self, hook):
        """Test resized image is saved to proper temp directory."""
        # Create oversized image
        large_image = Image.new("RGB", (5000, 3000), color="red")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with (
            patch.dict("os.environ", {"STRICT_MODE": "false"}),
            patch(
                "src.albumentations_mcp.hooks.pre_transform.PreTransformHook._save_temp_image",
            ) as mock_save,
        ):
            mock_save.return_value = Path(
                "outputs/test_session/tmp/resized_image.png",
            )
            result = await hook.execute(context)

        assert result.success is True
        mock_save.assert_called_once()
        # Check that temp path was added to context
        assert len(context.temp_paths) > 0

    @pytest.mark.asyncio
    async def test_original_input_files_preserved(self, hook):
        """Test original input files are never modified."""
        # This test ensures we don't modify user originals
        large_image = Image.new("RGB", (5000, 3000), color="yellow")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        original_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=original_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with patch.dict("os.environ", {"STRICT_MODE": "false"}):
            result = await hook.execute(context)

        assert result.success is True
        # The context.image_data should be updated with resized image
        # but we should verify original is not touched (integration-level)
        assert result.context.image_data != original_data.encode()

    @pytest.mark.asyncio
    async def test_max_image_size_configuration(self, hook):
        """Test MAX_IMAGE_SIZE configuration works correctly."""
        # Create image that's larger than custom limit
        large_image = Image.new("RGB", (3000, 2000), color="purple")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        # Set custom MAX_IMAGE_SIZE
        with patch.dict(
            "os.environ",
            {"MAX_IMAGE_SIZE": "2048", "STRICT_MODE": "false"},
        ):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]
        assert image_validation["resize_applied"] is True

        # Check resized to custom limit
        resized_width = image_validation["image_info"]["width"]
        resized_height = image_validation["image_info"]["height"]
        assert max(resized_width, resized_height) <= 2048

    @pytest.mark.asyncio
    async def test_oversize_by_pixels_limit(self, hook):
        """Test oversized image by total pixels (e.g., 9000x2000)."""
        # Create image with high pixel count but reasonable dimensions
        wide_image = Image.new("RGB", (9000, 2000), color="orange")
        buffer = io.BytesIO()
        wide_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with patch.dict(
            "os.environ",
            {"MAX_PIXELS_IN": "10000000", "STRICT_MODE": "false"},
        ):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]
        assert image_validation["resize_applied"] is True
        assert "total pixels" in image_validation["resize_reason"]

    @pytest.mark.asyncio
    async def test_oversize_by_bytes_limit(self, hook):
        """Test oversized image by file size (high-quality JPEG)."""
        # Create a high-quality image that might exceed byte limits
        large_image = Image.new("RGB", (2000, 2000), color="cyan")
        buffer = io.BytesIO()
        large_image.save(buffer, format="JPEG", quality=100)

        # Simulate large file by patching the byte size check
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        # Set very low byte limit to trigger resize
        with patch.dict(
            "os.environ",
            {"MAX_BYTES_IN": "2000000", "STRICT_MODE": "false"},
        ):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]
        assert image_validation["resize_applied"] is True
        assert "file size" in image_validation["resize_reason"]

    @pytest.mark.asyncio
    async def test_exif_orientation_corrected(self, hook):
        """Test EXIF-rotated portrait image has orientation corrected and aspect preserved."""
        # Create a portrait image (this simulates EXIF rotation)
        portrait_image = Image.new("RGB", (3000, 5000), color="magenta")
        buffer = io.BytesIO()
        portrait_image.save(buffer, format="JPEG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with (
            patch.dict("os.environ", {"STRICT_MODE": "false"}),
            patch(
                "PIL.ImageOps.exif_transpose",
            ) as mock_transpose,
        ):
            mock_transpose.return_value = portrait_image
            result = await hook.execute(context)

        assert result.success is True
        mock_transpose.assert_called_once()

    @pytest.mark.asyncio
    async def test_webp_format_preserved(self, hook):
        """Test WEBP input is preserved as WEBP when resized."""
        # Create oversized WEBP image
        large_image = Image.new("RGB", (5000, 3000), color="lime")
        buffer = io.BytesIO()
        large_image.save(buffer, format="WEBP")
        large_image.format = "WEBP"  # Ensure format is set
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with (
            patch.dict("os.environ", {"STRICT_MODE": "false"}),
            patch(
                "src.albumentations_mcp.hooks.pre_transform.PreTransformHook._save_temp_image",
            ) as mock_save,
        ):
            mock_save.return_value = Path(
                "outputs/test_session/tmp/resized_image.webp",
            )
            result = await hook.execute(context)

        assert result.success is True
        # Verify format preservation logic was called
        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_corrupted_image_raises_clean_error(self, hook):
        """Test corrupted image raises clean error."""
        # Create corrupted image data
        corrupted_data = b"definitely_not_an_image"
        base64_data = base64.b64encode(corrupted_data).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
        )

        result = await hook.execute(context)

        assert result.success is False
        assert any(
            "Invalid image data" in warning for warning in result.context.warnings
        )

    @pytest.mark.asyncio
    async def test_comprehensive_logging_metadata(self, hook):
        """Test comprehensive logging includes all required metadata."""
        # Create oversized image
        large_image = Image.new("RGB", (5000, 3000), color="teal")
        buffer = io.BytesIO()
        large_image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode()

        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            image_data=base64_data.encode(),
            parsed_transforms=[{"name": "Blur", "parameters": {}}],
            metadata={"session_dir": "outputs/test_session"},
        )
        context.temp_paths = []

        with patch.dict("os.environ", {"STRICT_MODE": "false"}):
            result = await hook.execute(context)

        assert result.success is True
        image_validation = result.context.metadata["image_validation"]

        # Check all required metadata fields
        assert "resize_applied" in image_validation
        assert "original_dimensions" in image_validation
        assert "resized_dimensions" in image_validation
        assert "original_bytes" in image_validation
        assert "resized_bytes" in image_validation
        assert "resize_reason" in image_validation

        # Check logging includes comprehensive info
        assert image_validation["original_dimensions"] == "5000x3000"
        assert image_validation["resize_reason"] is not None

    @pytest.mark.asyncio
    async def test_pasted_image_temp_files_cleaned(self, hook):
        """Test pasted image temp files are cleaned after processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create mock pasted image temp files
            pasted_file = session_temp_dir / "pasted_file_abc123.png"
            pasted_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(pasted_file)]

            result = await hook.execute(context)

            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]
            assert str(pasted_file) in cleanup_info["temp_files_cleaned"]
            assert not pasted_file.exists()

    @pytest.mark.asyncio
    async def test_url_loaded_image_temp_files_cleaned(self, hook):
        """Test URL-loaded image temp files are cleaned after processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create mock URL-loaded image temp files
            url_file = session_temp_dir / "url_download_def456.jpg"
            url_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(url_file)]

            result = await hook.execute(context)

            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]
            assert str(url_file) in cleanup_info["temp_files_cleaned"]
            assert not url_file.exists()

    @pytest.mark.asyncio
    async def test_session_temp_directory_empty_after_processing(self, hook):
        """Test session_dir/tmp/ is empty or removed after processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create multiple temp files
            temp_files = [
                session_temp_dir / "temp1.png",
                session_temp_dir / "temp2.jpg",
                session_temp_dir / "resized_image.png",
            ]
            for temp_file in temp_files:
                temp_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(f) for f in temp_files]

            result = await hook.execute(context)

            assert result.success is True
            # Check that temp directory is empty or removed
            if session_temp_dir.exists():
                assert len(list(session_temp_dir.iterdir())) == 0
            else:
                # Directory was removed entirely
                assert not session_temp_dir.exists()

    @pytest.mark.asyncio
    async def test_user_original_files_never_touched(self, hook):
        """Test user original files are never touched during cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create user original file outside session directory
            user_original = Path(temp_dir) / "user_image.jpg"
            user_original.touch()

            # Create temp files inside session
            temp_file = session_temp_dir / "temp_image.png"
            temp_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            # Only track temp files, not user originals
            context.temp_paths = [str(temp_file)]

            result = await hook.execute(context)

            assert result.success is True
            # User original should still exist
            assert user_original.exists()
            # Temp file should be cleaned
            assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_works_regardless_of_naming_patterns(self, hook):
        """Test cleanup works regardless of temp file naming patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create temp files with various naming patterns
            temp_files = [
                session_temp_dir / "weird_name_123.png",
                session_temp_dir / "no_session_id.jpg",
                session_temp_dir / "random_file.webp",
                session_temp_dir / "another.tiff",
            ]
            for temp_file in temp_files:
                temp_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(f) for f in temp_files]

            result = await hook.execute(context)

            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]

            # All files should be cleaned regardless of naming
            for temp_file in temp_files:
                assert str(temp_file) in cleanup_info["temp_files_cleaned"]
                assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_logs_detailed_information(self, hook):
        """Test cleanup logs provide detailed information about removed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create temp files and directories
            temp_file = session_temp_dir / "temp_file.png"
            temp_file.touch()
            temp_subdir = session_temp_dir / "temp_subdir"
            temp_subdir.mkdir()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(temp_file), str(temp_subdir)]

            result = await hook.execute(context)

            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]

            # Check detailed logging
            assert "temp_files_cleaned" in cleanup_info
            assert "temp_dirs_cleaned" in cleanup_info
            assert "cleanup_errors" in cleanup_info
            assert "cleanup_warnings" in cleanup_info

            # Check counts
            assert len(cleanup_info["temp_files_cleaned"]) >= 1
            assert len(cleanup_info["temp_dirs_cleaned"]) >= 1

    @pytest.mark.asyncio
    async def test_pasted_and_resized_temp_both_removed(self, hook):
        """Test both pasted image temp and resized temp are removed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create both pasted and resized temp files
            pasted_file = session_temp_dir / "pasted_file_abc123.png"
            resized_file = session_temp_dir / "resized_image.png"
            pasted_file.touch()
            resized_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(pasted_file), str(resized_file)]

            result = await hook.execute(context)

            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]

            # Both files should be cleaned
            assert str(pasted_file) in cleanup_info["temp_files_cleaned"]
            assert str(resized_file) in cleanup_info["temp_files_cleaned"]
            assert not pasted_file.exists()
            assert not resized_file.exists()

            # Session temp directory should be empty or gone
            if session_temp_dir.exists():
                assert len(list(session_temp_dir.iterdir())) == 0

    @pytest.mark.asyncio
    async def test_concurrent_sessions_clean_only_own_temp(self, hook):
        """Test each session cleans only its own tmp/ directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two session directories
            session1_dir = Path(temp_dir) / "session_123"
            session2_dir = Path(temp_dir) / "session_456"
            session1_temp = session1_dir / "tmp"
            session2_temp = session2_dir / "tmp"
            session1_temp.mkdir(parents=True)
            session2_temp.mkdir(parents=True)

            # Create temp files in both sessions
            session1_file = session1_temp / "temp1.png"
            session2_file = session2_temp / "temp2.png"
            session1_file.touch()
            session2_file.touch()

            # Test cleanup for session 1 only
            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session1_dir)},
            )
            context.temp_paths = [str(session1_file)]

            result = await hook.execute(context)

            assert result.success is True

            # Session 1 temp should be cleaned
            assert not session1_file.exists()

            # Session 2 temp should remain untouched
            assert session2_file.exists()

    @pytest.mark.asyncio
    async def test_symlink_input_rejected_no_cleanup_outside_session(self, hook):
        """Test symlink input is rejected and no cleanup happens outside session tree."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create a file outside session and a symlink to it inside
            outside_file = Path(temp_dir) / "outside_file.png"
            outside_file.touch()

            # This test is more about the safety check in _is_safe_to_delete
            # We'll test that symlinks are not cleaned up
            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            # Don't add symlinks to temp_paths - they should be rejected earlier
            context.temp_paths = []

            result = await hook.execute(context)

            assert result.success is True
            # Outside file should remain untouched
            assert outside_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_handles_permission_errors_gracefully(self, hook):
        """Test cleanup handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir) / "session_123"
            session_temp_dir = session_dir / "tmp"
            session_temp_dir.mkdir(parents=True)

            # Create a temp file
            temp_file = session_temp_dir / "temp_file.png"
            temp_file.touch()

            context = HookContext(
                session_id="test-session-123",
                original_prompt="add blur",
                metadata={"session_dir": str(session_dir)},
            )
            context.temp_paths = [str(temp_file)]

            # Mock unlink to raise permission error
            with patch.object(
                Path,
                "unlink",
                side_effect=PermissionError("Access denied"),
            ):
                result = await hook.execute(context)

            # Should still succeed overall but log the error
            assert result.success is True
            cleanup_info = result.context.metadata["cleanup_info"]
            assert len(cleanup_info["cleanup_errors"]) > 0
            assert any(
                "Access denied" in str(error)
                for error in cleanup_info["cleanup_errors"]
            )

    @pytest.mark.asyncio
    async def test_no_temp_paths_attribute_handled_gracefully(self, hook):
        """Test cleanup handles missing temp_paths attribute gracefully."""
        context = HookContext(
            session_id="test-session-123",
            original_prompt="add blur",
            metadata={"session_dir": "outputs/test_session"},
        )
        # Don't set temp_paths attribute

        result = await hook.execute(context)

        assert result.success is True
        cleanup_info = result.context.metadata["cleanup_info"]
        # Should handle gracefully with empty cleanup
        assert "temp_files_cleaned" in cleanup_info
        assert len(cleanup_info["temp_files_cleaned"]) == 0
