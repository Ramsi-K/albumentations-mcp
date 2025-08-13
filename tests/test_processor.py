"""Tests for the image processor module."""

from unittest.mock import Mock, patch

from PIL import Image

from src.albumentations_mcp.processor import (
    ImageProcessor,
    ProcessingError,
    ProcessingResult,
    get_processor,
    process_image,
)


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_successful_result(self):
        """Test creating successful processing result."""
        image = Image.new("RGB", (100, 100), color="red")

        result = ProcessingResult(
            success=True,
            augmented_image=image,
            applied_transforms=[{"name": "Blur", "parameters": {"blur_limit": 3}}],
            skipped_transforms=[],
            metadata={"processing_time": 0.1},
            execution_time=0.1,
        )

        assert result.success is True
        assert result.augmented_image is not None
        assert len(result.applied_transforms) == 1
        assert result.execution_time == 0.1

    def test_failed_result(self):
        """Test creating failed processing result."""
        result = ProcessingResult(
            success=False,
            augmented_image=None,
            applied_transforms=[],
            skipped_transforms=[{"name": "Blur"}],
            metadata={"error": "Processing failed"},
            execution_time=0.05,
            error_message="Test error",
        )

        assert result.success is False
        assert result.augmented_image is None
        assert result.error_message == "Test error"


class TestImageProcessor:
    """Test ImageProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ImageProcessor()
        self.test_image = Image.new("RGB", (100, 100), color="red")

    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = ImageProcessor()

        assert hasattr(processor, "_transform_cache")
        assert hasattr(processor, "_pipeline_cache")
        assert hasattr(processor, "_max_cache_size")
        assert processor._max_cache_size == 100

    def test_process_image_no_transforms(self):
        """Test processing image with no transforms."""
        processor = ImageProcessor()

        result = processor.process_image(self.test_image, [])

        assert result.success is True
        assert result.augmented_image is not None
        assert len(result.applied_transforms) == 0
        assert result.metadata["transforms_applied"] == 0

    def test_process_image_with_valid_transforms(self):
        """Test processing image with valid transforms."""
        processor = ImageProcessor()
        transforms = [
            {"name": "HorizontalFlip", "parameters": {"p": 1.0}},
            {"name": "VerticalFlip", "parameters": {"p": 1.0}},
        ]

        result = processor.process_image(self.test_image, transforms)

        assert result.success is True
        assert result.augmented_image is not None
        assert len(result.applied_transforms) <= len(transforms)

    def test_process_image_with_invalid_transforms(self):
        """Test processing image with invalid transforms."""
        processor = ImageProcessor()
        transforms = [
            {"name": "NonExistentTransform", "parameters": {}},
            {"name": "HorizontalFlip", "parameters": {"p": 1.0}},
        ]

        result = processor.process_image(self.test_image, transforms)

        # Should still succeed with valid transforms
        assert result.success is True
        assert len(result.skipped_transforms) >= 1

    def test_process_image_with_seed(self):
        """Test processing image with seed for reproducibility."""
        processor = ImageProcessor()
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        result1 = processor.process_image(self.test_image, transforms, seed=42)
        result2 = processor.process_image(self.test_image, transforms, seed=42)

        assert result1.success is True
        assert result2.success is True
        # Results should be identical with same seed
        assert result1.metadata.get("effective_seed") == result2.metadata.get(
            "effective_seed",
        )

    @patch("src.albumentations_mcp.processor.validate_image")
    def test_process_image_validation_failure(self, mock_validate):
        """Test processing with image validation failure."""
        mock_validate.side_effect = ValueError("Invalid image")
        processor = ImageProcessor()

        result = processor.process_image(self.test_image, [])

        assert result.success is False
        assert "Invalid image" in result.error_message

    def test_create_transform_valid(self):
        """Test creating valid transform."""
        processor = ImageProcessor()
        transform_spec = {"name": "HorizontalFlip", "parameters": {"p": 1.0}}

        transform = processor._create_transform(transform_spec)

        assert transform is not None
        assert callable(transform)

    def test_create_transform_invalid_name(self):
        """Test creating transform with invalid name."""
        processor = ImageProcessor()
        transform_spec = {"name": "NonExistentTransform", "parameters": {}}

        transform = processor._create_transform(transform_spec)

        assert transform is None

    def test_create_transform_missing_name(self):
        """Test creating transform with missing name."""
        processor = ImageProcessor()
        transform_spec = {"parameters": {"p": 1.0}}

        transform = processor._create_transform(transform_spec)

        assert transform is None

    def test_create_transform_cached(self):
        """Test transform caching functionality."""
        processor = ImageProcessor()
        transform_spec = {"name": "HorizontalFlip", "parameters": {"p": 1.0}}

        # First call should create and cache
        transform1 = processor._create_transform_cached(transform_spec)
        cache_size_after_first = len(processor._transform_cache)

        # Second call should use cache
        transform2 = processor._create_transform_cached(transform_spec)
        cache_size_after_second = len(processor._transform_cache)

        assert transform1 is not None
        assert transform2 is not None
        assert cache_size_after_first == cache_size_after_second

    def test_validate_parameters_blur_transforms(self):
        """Test parameter validation for blur transforms."""
        processor = ImageProcessor()

        # Test blur_limit validation
        params = processor._validate_parameters(
            "Blur",
            {"blur_limit": 4},
        )  # Even number
        assert params["blur_limit"] == 5  # Should be made odd

        params = processor._validate_parameters(
            "Blur",
            {"blur_limit": 101},
        )  # Too large
        assert params["blur_limit"] == 99  # Should be capped

        params = processor._validate_parameters("Blur", {"blur_limit": 1})  # Too small
        assert params["blur_limit"] == 3  # Should be minimum

    def test_validate_parameters_rotate_transform(self):
        """Test parameter validation for rotate transform."""
        processor = ImageProcessor()

        params = processor._validate_parameters("Rotate", {"limit": 200})  # Too large
        assert params["limit"] == 180  # Should be capped

        params = processor._validate_parameters("Rotate", {"limit": -200})  # Too small
        assert params["limit"] == -180  # Should be capped

    def test_validate_parameters_brightness_contrast(self):
        """Test parameter validation for brightness/contrast transform."""
        processor = ImageProcessor()

        params = processor._validate_parameters(
            "RandomBrightnessContrast",
            {"brightness_limit": 2.0, "contrast_limit": 2.0},
        )

        assert params["brightness_limit"] == 1.0  # Should be capped
        assert params["contrast_limit"] == 1.0  # Should be capped

    def test_validate_parameters_gauss_noise(self):
        """Test parameter validation for Gaussian noise transform."""
        processor = ImageProcessor()

        params = processor._validate_parameters(
            "GaussNoise",
            {"var_limit": (300, 400)},  # Too large
        )

        assert params["var_limit"][1] == 255.0  # Should be capped

    def test_validate_parameters_crop_transforms(self):
        """Test parameter validation for crop transforms."""
        processor = ImageProcessor()

        params = processor._validate_parameters(
            "RandomCrop",
            {"height": 0, "width": -5},  # Invalid dimensions
        )

        assert params["height"] == 1  # Should be minimum
        assert params["width"] == 1  # Should be minimum

    def test_validate_parameters_probability(self):
        """Test probability parameter validation."""
        processor = ImageProcessor()

        params = processor._validate_parameters(
            "HorizontalFlip",
            {"p": 2.0},
        )  # Too large
        assert params["p"] == 1.0  # Should be capped

        params = processor._validate_parameters(
            "HorizontalFlip",
            {"p": -0.5},
        )  # Too small
        assert params["p"] == 0.0  # Should be capped

    def test_validate_parameters_none_removal(self):
        """Test removal of None parameters."""
        processor = ImageProcessor()

        params = processor._validate_parameters(
            "HorizontalFlip",
            {"p": 1.0, "none_param": None},
        )

        assert "p" in params
        assert "none_param" not in params

    def test_clear_caches(self):
        """Test cache clearing functionality."""
        processor = ImageProcessor()

        # Add something to caches
        processor._transform_cache["test"] = "value"
        processor._pipeline_cache["test"] = "value"

        processor.clear_caches()

        assert len(processor._transform_cache) == 0
        assert len(processor._pipeline_cache) == 0

    def test_get_cache_stats(self):
        """Test cache statistics."""
        processor = ImageProcessor()

        stats = processor.get_cache_stats()

        assert "transform_cache_size" in stats
        assert "pipeline_cache_size" in stats
        assert "max_cache_size" in stats
        assert stats["max_cache_size"] == 100

    @patch("src.albumentations_mcp.recovery.get_memory_recovery_manager")
    def test_memory_limit_exceeded(self, mock_memory_manager):
        """Test behavior when memory limits are exceeded."""
        # Mock memory manager to simulate limit exceeded
        mock_manager = Mock()
        mock_manager.check_memory_limits.return_value = False
        # Mock the context manager
        mock_manager.memory_recovery_context.return_value.__enter__ = Mock(
            return_value=None,
        )
        mock_manager.memory_recovery_context.return_value.__exit__ = Mock(
            return_value=None,
        )
        mock_memory_manager.return_value = mock_manager

        processor = ImageProcessor()
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        result = processor.process_image(self.test_image, transforms)

        assert result.success is True  # Should still succeed
        assert result.metadata.get("memory_limit_exceeded") is True
        assert "Memory limits exceeded" in result.error_message

    def test_pipeline_caching(self):
        """Test pipeline caching functionality."""
        processor = ImageProcessor()
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        # First call should create and cache pipeline
        pipeline1, metadata1 = processor._create_pipeline(transforms)
        cache_size_after_first = len(processor._pipeline_cache)

        # Second call with same transforms should use cache
        pipeline2, metadata2 = processor._create_pipeline(transforms)
        cache_size_after_second = len(processor._pipeline_cache)

        assert pipeline1 is not None
        assert pipeline2 is not None
        assert cache_size_after_first == cache_size_after_second


class TestGlobalFunctions:
    """Test global processor functions."""

    def test_get_processor_singleton(self):
        """Test that get_processor returns singleton."""
        processor1 = get_processor()
        processor2 = get_processor()

        assert processor1 is processor2
        assert isinstance(processor1, ImageProcessor)

    def test_process_image_convenience_function(self):
        """Test convenience process_image function."""
        test_image = Image.new("RGB", (100, 100), color="red")
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        result = process_image(test_image, transforms)

        assert isinstance(result, ProcessingResult)
        assert result.success is True

    def test_process_image_with_seed(self):
        """Test convenience function with seed."""
        test_image = Image.new("RGB", (100, 100), color="red")
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        result = process_image(test_image, transforms, seed=42)

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.metadata.get("effective_seed") is not None


class TestErrorHandling:
    """Test error handling in processor."""

    def test_processing_error_exception(self):
        """Test ProcessingError exception."""
        error = ProcessingError("Test error")
        assert str(error) == "Test error"

    @patch("src.albumentations_mcp.processor.pil_to_numpy")
    def test_image_conversion_error(self, mock_pil_to_numpy):
        """Test handling of image conversion errors."""
        mock_pil_to_numpy.side_effect = ValueError("Conversion failed")

        processor = ImageProcessor()
        test_image = Image.new("RGB", (100, 100), color="red")

        result = processor.process_image(test_image, [])

        assert result.success is False
        assert "Conversion failed" in result.error_message

    def test_transform_recovery_integration(self):
        """Test integration with transform recovery system."""
        processor = ImageProcessor()

        # Use invalid parameters that should trigger recovery
        transform_spec = {
            "name": "Blur",
            "parameters": {"blur_limit": "invalid_value"},
        }

        # Should not raise exception, should attempt recovery
        transform = processor._create_transform(transform_spec)

        # Recovery might succeed or fail, but shouldn't crash
        assert transform is None or callable(transform)


class TestPerformanceOptimizations:
    """Test performance optimization features."""

    def test_cache_size_limit(self):
        """Test that caches don't exceed size limits."""
        processor = ImageProcessor()
        processor._max_cache_size = 2  # Set small limit for testing

        # Add more items than the limit
        for i in range(5):
            transform_spec = {
                "name": "HorizontalFlip",
                "parameters": {"p": i / 10},
            }
            processor._create_transform_cached(transform_spec)

        # Cache should not exceed limit
        assert len(processor._transform_cache) <= processor._max_cache_size

    def test_pipeline_cache_with_seed(self):
        """Test pipeline caching behavior with seeds."""
        processor = ImageProcessor()
        transforms = [{"name": "HorizontalFlip", "parameters": {"p": 1.0}}]

        # Create pipeline without seed (should be cached)
        pipeline1, _ = processor._create_pipeline(transforms)

        # Create pipeline with seed (should reuse cached base)
        pipeline2, _ = processor._create_pipeline(transforms, seed=42)

        assert pipeline1 is not None
        assert pipeline2 is not None
        # Both should work but may be different instances due to seeding
