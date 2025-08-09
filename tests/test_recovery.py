"""Tests for transform failure recovery and graceful degradation."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import albumentations as A
import numpy as np
from PIL import Image

from src.albumentations_mcp.recovery import (
    RecoveryStrategy,
    RecoveryError,
    TransformRecoveryError,
    MemoryRecoveryError,
    RecoveryContext,
    TransformRecoveryManager,
    MemoryRecoveryManager,
    PipelineRecoveryManager,
    recover_from_transform_failure,
    check_memory_limits,
    get_recovery_statistics,
)


class TestRecoveryContext:
    """Test recovery context management."""

    def test_recovery_context_initialization(self):
        """Test recovery context initialization."""
        context = RecoveryContext("Blur", {"blur_limit": 7})

        assert context.transform_name == "Blur"
        assert context.original_parameters == {"blur_limit": 7}
        assert context.attempt_count == 0
        assert context.max_attempts == 3
        assert context.recovery_history == []
        assert context.start_time is not None

    def test_recovery_context_with_custom_values(self):
        """Test recovery context with custom values."""
        context = RecoveryContext(
            "MotionBlur",
            {"blur_limit": 15},
            max_attempts=5,
            recovery_history=[{"test": "data"}],
        )

        assert context.transform_name == "MotionBlur"
        assert context.max_attempts == 5
        assert len(context.recovery_history) == 1


class TestTransformRecoveryManager:
    """Test transform failure recovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.recovery_manager = TransformRecoveryManager()

    def test_successful_safe_defaults_recovery(self):
        """Test successful recovery using safe defaults."""
        # Simulate a parameter error
        error = ValueError("blur_limit must be odd")

        transform, strategy = self.recovery_manager.recover_transform_failure(
            "Blur", {"blur_limit": 100}, error
        )

        assert transform is not None
        assert isinstance(transform, A.Blur)
        assert strategy == RecoveryStrategy.USE_SAFE_DEFAULTS
        assert (
            self.recovery_manager.recovery_stats["successful_recoveries"] == 1
        )

    def test_progressive_fallback_recovery(self):
        """Test progressive fallback recovery."""
        # Mock safe defaults to fail, forcing progressive fallback
        with patch.object(
            self.recovery_manager, "_try_safe_defaults", return_value=None
        ):
            error = ValueError("Parameter out of range")

            transform, strategy = (
                self.recovery_manager.recover_transform_failure(
                    "RandomBrightnessContrast",
                    {"brightness_limit": 10.0},
                    error,
                )
            )

            assert transform is not None
            assert isinstance(transform, A.RandomBrightnessContrast)
            assert strategy == RecoveryStrategy.PROGRESSIVE_FALLBACK

    def test_skip_transform_recovery(self):
        """Test skipping transform when recovery fails."""
        # Mock both recovery methods to fail
        with (
            patch.object(
                self.recovery_manager, "_try_safe_defaults", return_value=None
            ),
            patch.object(
                self.recovery_manager,
                "_try_progressive_fallback",
                return_value=None,
            ),
        ):

            error = ValueError("Unrecoverable error")

            transform, strategy = (
                self.recovery_manager.recover_transform_failure(
                    "UnknownTransform", {}, error
                )
            )

            assert transform is None
            assert strategy == RecoveryStrategy.SKIP_TRANSFORM

    def test_recovery_with_image_shape_context(self):
        """Test recovery with image shape context for crop transforms."""
        error = ValueError("Crop size too large")
        image_shape = (100, 100, 3)

        transform, strategy = self.recovery_manager.recover_transform_failure(
            "RandomCrop", {"height": 200, "width": 200}, error, image_shape
        )

        assert transform is not None
        assert isinstance(transform, A.RandomCrop)
        # Should adjust crop size based on image shape
        assert transform.height <= 50  # Half of image height
        assert transform.width <= 50  # Half of image width

    def test_safe_parameter_ranges(self):
        """Test that safe parameter ranges are applied correctly."""
        error = ValueError("Parameter out of range")

        transform, strategy = self.recovery_manager.recover_transform_failure(
            "Blur", {"blur_limit": 1000}, error
        )

        assert transform is not None
        # Should use safe range values - blur_limit is a tuple (min, max)
        if isinstance(transform.blur_limit, tuple):
            min_blur, max_blur = transform.blur_limit
            assert 3 <= min_blur <= 15
            assert 3 <= max_blur <= 15
            assert min_blur % 2 == 1  # Should be odd
            assert max_blur % 2 == 1  # Should be odd
        else:
            assert 3 <= transform.blur_limit <= 15
            assert transform.blur_limit % 2 == 1  # Should be odd

    def test_recovery_statistics_tracking(self):
        """Test that recovery statistics are tracked correctly."""
        initial_stats = self.recovery_manager.recovery_stats.copy()

        # Perform several recovery attempts
        for i in range(3):
            self.recovery_manager.recover_transform_failure(
                "Blur", {"blur_limit": 1000}, ValueError("Test error")
            )

        stats = self.recovery_manager.recovery_stats
        assert (
            stats["total_recoveries"] == initial_stats["total_recoveries"] + 3
        )
        assert (
            stats["successful_recoveries"]
            > initial_stats["successful_recoveries"]
        )
        assert "use_safe_defaults" in stats["recovery_strategies_used"]

    def test_unknown_transform_handling(self):
        """Test handling of unknown transforms."""
        error = AttributeError("Unknown transform")

        transform, strategy = self.recovery_manager.recover_transform_failure(
            "NonExistentTransform", {}, error
        )

        assert transform is None
        assert strategy == RecoveryStrategy.SKIP_TRANSFORM

    def test_recovery_attempt_limits(self):
        """Test that recovery attempts are limited."""
        # Mock methods to always fail
        with (
            patch.object(
                self.recovery_manager, "_try_safe_defaults", return_value=None
            ),
            patch.object(
                self.recovery_manager,
                "_try_progressive_fallback",
                return_value=None,
            ),
        ):

            error = ValueError("Persistent error")

            transform, strategy = (
                self.recovery_manager.recover_transform_failure(
                    "Blur", {}, error
                )
            )

            assert transform is None
            assert strategy == RecoveryStrategy.SKIP_TRANSFORM


class TestMemoryRecoveryManager:
    """Test memory exhaustion recovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.memory_manager = MemoryRecoveryManager(
            max_memory_mb=100
        )  # Low limit for testing

    def test_memory_recovery_context_success(self):
        """Test successful operation within memory context."""
        with self.memory_manager.memory_recovery_context("test_operation"):
            # Simulate successful operation
            result = "success"

        assert result == "success"

    def test_memory_recovery_context_memory_error(self):
        """Test memory error handling in context."""
        with pytest.raises(MemoryRecoveryError):
            with self.memory_manager.memory_recovery_context("test_operation"):
                raise MemoryError("Out of memory")

    def test_memory_limits_checking(self):
        """Test memory limits checking."""
        # Mock memory usage to exceed limits
        with patch.object(
            self.memory_manager, "_get_memory_usage_mb", return_value=200
        ):
            assert not self.memory_manager.check_memory_limits(
                "test_operation"
            )

        # Mock memory usage within limits
        with patch.object(
            self.memory_manager, "_get_memory_usage_mb", return_value=50
        ):
            assert self.memory_manager.check_memory_limits("test_operation")

    def test_memory_recovery_attempt(self):
        """Test memory recovery attempt."""
        # Mock memory usage before and after recovery
        with patch.object(
            self.memory_manager, "_get_memory_usage_mb", side_effect=[500, 300]
        ):
            result = self.memory_manager._attempt_memory_recovery()
            assert result is True  # Should succeed since we "freed" 200MB

    def test_memory_recovery_failure(self):
        """Test memory recovery failure."""
        # Mock memory usage to not change significantly
        with patch.object(
            self.memory_manager, "_get_memory_usage_mb", side_effect=[500, 490]
        ):
            result = self.memory_manager._attempt_memory_recovery()
            assert result is False  # Should fail since we only "freed" 10MB

    def test_memory_statistics_tracking(self):
        """Test memory statistics tracking."""
        initial_stats = self.memory_manager.memory_stats.copy()

        # Trigger memory recovery
        try:
            with self.memory_manager.memory_recovery_context("test"):
                raise MemoryError("Test memory error")
        except MemoryRecoveryError:
            pass

        stats = self.memory_manager.memory_stats
        assert (
            stats["recovery_triggers"]
            == initial_stats["recovery_triggers"] + 1
        )


class TestPipelineRecoveryManager:
    """Test pipeline-level recovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline_manager = PipelineRecoveryManager()

    def test_successful_pipeline_execution(self):
        """Test successful pipeline execution."""

        def mock_pipeline(data):
            return f"processed_{data}"

        result, recovery_events = (
            self.pipeline_manager.execute_pipeline_with_recovery(
                mock_pipeline, "test_data"
            )
        )

        assert result == "processed_test_data"
        assert len(recovery_events) == 0
        assert (
            self.pipeline_manager.pipeline_stats["successful_pipelines"] == 1
        )

    def test_pipeline_memory_recovery(self):
        """Test pipeline memory recovery."""

        def mock_pipeline_with_memory_error(data):
            raise MemoryError("Out of memory")

        with pytest.raises(MemoryRecoveryError):
            self.pipeline_manager.execute_pipeline_with_recovery(
                mock_pipeline_with_memory_error, "test_data"
            )

        assert self.pipeline_manager.pipeline_stats["failed_pipelines"] == 1

    def test_pipeline_with_original_data_recovery(self):
        """Test pipeline recovery with original data fallback."""

        def mock_pipeline_with_recoverable_error(data, original_image=None):
            from src.albumentations_mcp.recovery import (
                MemoryRecoveryError,
                RecoveryStrategy,
            )

            raise MemoryRecoveryError(
                "Memory exhausted", RecoveryStrategy.RETURN_ORIGINAL
            )

        original_image = Image.new("RGB", (100, 100))

        result, recovery_events = (
            self.pipeline_manager.execute_pipeline_with_recovery(
                mock_pipeline_with_recoverable_error,
                "test_data",
                original_image=original_image,
            )
        )

        assert result == original_image
        assert len(recovery_events) == 1
        assert recovery_events[0]["type"] == "memory_recovery"
        assert self.pipeline_manager.pipeline_stats["recovered_pipelines"] == 1

    def test_pipeline_statistics(self):
        """Test pipeline statistics collection."""

        # Execute successful pipeline
        def success_pipeline(data):
            return data

        self.pipeline_manager.execute_pipeline_with_recovery(
            success_pipeline, "test"
        )

        # Execute failed pipeline
        def fail_pipeline(data):
            raise ValueError("Test error")

        try:
            self.pipeline_manager.execute_pipeline_with_recovery(
                fail_pipeline, "test"
            )
        except ValueError:
            pass

        stats = self.pipeline_manager.get_recovery_statistics()

        assert "pipeline_stats" in stats
        assert "transform_recovery_stats" in stats
        assert "memory_recovery_stats" in stats
        assert stats["pipeline_stats"]["total_pipelines"] == 2
        assert stats["pipeline_stats"]["successful_pipelines"] == 1
        assert stats["pipeline_stats"]["failed_pipelines"] == 1


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_recover_from_transform_failure_function(self):
        """Test convenience function for transform recovery."""
        error = ValueError("Test error")

        transform, strategy = recover_from_transform_failure(
            "Blur", {"blur_limit": 1000}, error
        )

        assert (
            transform is not None
            or strategy == RecoveryStrategy.SKIP_TRANSFORM
        )

    def test_check_memory_limits_function(self):
        """Test convenience function for memory checking."""
        # Should not raise exception
        result = check_memory_limits("test_operation")
        assert isinstance(result, bool)

    def test_get_recovery_statistics_function(self):
        """Test convenience function for getting statistics."""
        stats = get_recovery_statistics()

        assert isinstance(stats, dict)
        assert "pipeline_stats" in stats
        assert "transform_recovery_stats" in stats
        assert "memory_recovery_stats" in stats


class TestIntegrationScenarios:
    """Test integration scenarios with real-world edge cases."""

    def test_extreme_parameter_recovery(self):
        """Test recovery from extreme parameter values."""
        recovery_manager = TransformRecoveryManager()

        # Test with extremely large blur value
        error = ValueError("blur_limit too large")
        transform, strategy = recovery_manager.recover_transform_failure(
            "Blur", {"blur_limit": 999999}, error
        )

        assert transform is not None
        assert transform.blur_limit <= 15  # Should be within safe range
        assert transform.blur_limit % 2 == 1  # Should be odd

    def test_multiple_transform_failures(self):
        """Test handling multiple transform failures in sequence."""
        recovery_manager = TransformRecoveryManager()

        failing_transforms = [
            ("Blur", {"blur_limit": -1}),
            ("Rotate", {"limit": 999}),
            ("RandomBrightnessContrast", {"brightness_limit": 100}),
        ]

        recovered_count = 0
        skipped_count = 0

        for transform_name, params in failing_transforms:
            error = ValueError(f"Invalid parameters for {transform_name}")
            transform, strategy = recovery_manager.recover_transform_failure(
                transform_name, params, error
            )

            if transform is not None:
                recovered_count += 1
            else:
                skipped_count += 1

        # Should recover most transforms or skip them gracefully
        assert recovered_count + skipped_count == len(failing_transforms)
        assert recovery_manager.recovery_stats["total_recoveries"] == len(
            failing_transforms
        )

    def test_memory_exhaustion_simulation(self):
        """Test memory exhaustion simulation and recovery."""
        memory_manager = MemoryRecoveryManager(
            max_memory_mb=1
        )  # Very low limit

        # Mock high memory usage
        with patch.object(
            memory_manager, "_get_memory_usage_mb", return_value=100
        ):
            assert not memory_manager.check_memory_limits("test")

        # Test recovery context with memory error
        with pytest.raises(MemoryRecoveryError):
            with memory_manager.memory_recovery_context("test"):
                raise MemoryError("Simulated memory exhaustion")

    def test_concurrent_recovery_operations(self):
        """Test recovery operations under concurrent access."""
        import threading
        import time

        recovery_manager = TransformRecoveryManager()
        results = []
        errors = []

        def recovery_worker(worker_id):
            try:
                for i in range(5):
                    error = ValueError(f"Worker {worker_id} error {i}")
                    transform, strategy = (
                        recovery_manager.recover_transform_failure(
                            "Blur", {"blur_limit": 1000 + i}, error
                        )
                    )
                    results.append((worker_id, i, transform is not None))
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append((worker_id, e))

        # Run multiple threads
        threads = [
            threading.Thread(target=recovery_worker, args=(i,))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should handle concurrent access without errors
        assert len(errors) == 0
        assert len(results) == 15  # 3 workers * 5 iterations
        assert recovery_manager.recovery_stats["total_recoveries"] == 15


if __name__ == "__main__":
    pytest.main([__file__])
