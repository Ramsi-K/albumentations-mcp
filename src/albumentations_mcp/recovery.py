"""Transform failure recovery and graceful degradation strategies.

This module provides comprehensive error recovery mechanisms for transform
failures, parameter validation errors, and resource exhaustion scenarios.
Implements graceful degradation to ensure the system continues functioning
even when individual transforms fail.

Error recovery system that handles transform failures, parameter
validation errors, and resource exhaustion. Provides fallback
strategies and graceful degradation to maintain system stability.

"""

import gc
import logging
import time

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

import albumentations as A

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategy options for different failure types."""

    SKIP_TRANSFORM = "skip_transform"  # Skip the failing transform
    USE_SAFE_DEFAULTS = "use_safe_defaults"  # Use safe parameter defaults
    PROGRESSIVE_FALLBACK = "progressive_fallback"  # Try progressively safer options
    RETURN_ORIGINAL = "return_original"  # Return original image
    ABORT_PIPELINE = "abort_pipeline"  # Stop entire pipeline


class RecoveryError(Exception):
    """Base class for recovery-related errors."""

    def __init__(
        self,
        message: str,
        recovery_strategy: RecoveryStrategy,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.recovery_strategy = recovery_strategy
        self.details = details or {}


class TransformRecoveryError(RecoveryError):
    """Raised when transform recovery fails."""


class MemoryRecoveryError(RecoveryError):
    """Raised when memory recovery fails."""


@dataclass
class RecoveryContext:
    """Context for tracking recovery attempts and results."""

    transform_name: str
    original_parameters: dict[str, Any]
    attempt_count: int = 0
    max_attempts: int = 3
    recovery_history: list[dict[str, Any]] = None
    start_time: float = None
    memory_usage_mb: float = 0.0

    def __post_init__(self):
        if self.recovery_history is None:
            self.recovery_history = []
        if self.start_time is None:
            self.start_time = time.time()


class TransformRecoveryManager:
    """Manages transform failure recovery and graceful degradation."""

    def __init__(self):
        """Initialize recovery manager with configuration."""
        self.max_memory_mb = 2048  # 2GB memory limit
        self.recovery_stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recovery_strategies_used": {},
        }

        # Safe parameter ranges for common transforms
        # Format: parameter_name: (min_value, max_value) or single_value for non-range params
        self.safe_parameter_ranges = {
            "Blur": {
                "blur_limit": (3, 9),  # Range for safe blur
                "p": 0.5,
            },
            "GaussianBlur": {
                "blur_limit": (3, 9),
                "p": 0.5,
            },
            "MotionBlur": {
                "blur_limit": (3, 9),
                "p": 0.5,
            },
            "RandomBrightnessContrast": {
                "brightness_limit": (0.05, 0.1),
                "contrast_limit": (0.05, 0.1),
                "p": 0.5,
            },
            "HueSaturationValue": {
                "hue_shift_limit": (5, 15),
                "sat_shift_limit": (10, 20),
                "val_shift_limit": (5, 15),
                "p": 0.5,
            },
            "Rotate": {
                "limit": (10, 20),  # Conservative rotation range
                "p": 0.5,
            },
            "GaussNoise": {
                "var_limit": (10.0, 30.0),  # Conservative noise
                "p": 0.5,
            },
            "RandomCrop": {
                "height": 224,
                "width": 224,
                "p": 0.5,
            },
        }

    def recover_transform_failure(
        self,
        transform_name: str,
        parameters: dict[str, Any],
        error: Exception,
        image_shape: tuple[int, ...] | None = None,
    ) -> tuple[A.BasicTransform | None, RecoveryStrategy]:
        """Recover from transform creation or execution failure.

        Args:
            transform_name: Name of the failing transform
            parameters: Original parameters that caused failure
            error: The original error that occurred
            image_shape: Shape of the image being processed (for context)

        Returns:
            Tuple of (recovered_transform, strategy_used) or (None, strategy)
        """
        context = RecoveryContext(transform_name, parameters)

        logger.warning(
            f"Transform failure recovery initiated for {transform_name}: {error}",
            extra={
                "transform": transform_name,
                "error": str(error),
                "parameters": parameters,
            },
        )

        self.recovery_stats["total_recoveries"] += 1

        try:
            # Strategy 1: Try safe parameter defaults
            if context.attempt_count < context.max_attempts:
                recovered_transform = self._try_safe_defaults(context, image_shape)
                if recovered_transform:
                    self._record_successful_recovery(
                        context,
                        RecoveryStrategy.USE_SAFE_DEFAULTS,
                    )
                    return (
                        recovered_transform,
                        RecoveryStrategy.USE_SAFE_DEFAULTS,
                    )

            # Strategy 2: Progressive parameter reduction
            if context.attempt_count < context.max_attempts:
                recovered_transform = self._try_progressive_fallback(
                    context,
                    image_shape,
                )
                if recovered_transform:
                    self._record_successful_recovery(
                        context,
                        RecoveryStrategy.PROGRESSIVE_FALLBACK,
                    )
                    return (
                        recovered_transform,
                        RecoveryStrategy.PROGRESSIVE_FALLBACK,
                    )

            # Strategy 3: Skip transform entirely
            logger.info(
                f"Skipping transform {transform_name} after recovery attempts failed",
            )
            self._record_recovery_attempt(
                context,
                RecoveryStrategy.SKIP_TRANSFORM,
                success=True,
            )
            return None, RecoveryStrategy.SKIP_TRANSFORM

        except Exception as recovery_error:
            logger.error(
                f"Recovery failed for transform {transform_name}: {recovery_error}",
                exc_info=True,
            )
            self.recovery_stats["failed_recoveries"] += 1
            return None, RecoveryStrategy.SKIP_TRANSFORM

    def _try_safe_defaults(
        self,
        context: RecoveryContext,
        image_shape: tuple[int, ...] | None = None,
    ) -> A.BasicTransform | None:
        """Try creating transform with safe default parameters."""
        context.attempt_count += 1

        if context.transform_name not in self.safe_parameter_ranges:
            logger.debug(f"No safe defaults available for {context.transform_name}")
            return None

        try:
            safe_ranges = self.safe_parameter_ranges[context.transform_name]
            safe_params = {}

            # Use safe default values
            for param, safe_value in safe_ranges.items():
                if isinstance(safe_value, tuple) and len(safe_value) == 2:
                    # For range parameters, use the maximum safe value
                    safe_params[param] = safe_value[1]
                else:
                    # For single values, use as-is
                    safe_params[param] = safe_value

            # Adjust parameters based on image shape if available
            if image_shape and context.transform_name in [
                "RandomCrop",
                "RandomResizedCrop",
            ]:
                height, width = image_shape[:2]
                safe_params["height"] = min(safe_params.get("height", 224), height // 2)
                safe_params["width"] = min(safe_params.get("width", 224), width // 2)

            # Create transform with safe parameters
            transform_class = getattr(A, context.transform_name)
            transform = transform_class(**safe_params)

            self._record_recovery_attempt(
                context,
                RecoveryStrategy.USE_SAFE_DEFAULTS,
                success=True,
            )
            logger.info(
                f"Successfully created {context.transform_name} with safe defaults: {safe_params}",
            )

            return transform

        except Exception as e:
            self._record_recovery_attempt(
                context,
                RecoveryStrategy.USE_SAFE_DEFAULTS,
                success=False,
                error=str(e),
            )
            logger.debug(f"Safe defaults failed for {context.transform_name}: {e}")
            return None

    def _try_progressive_fallback(
        self,
        context: RecoveryContext,
        image_shape: tuple[int, ...] | None = None,
    ) -> A.BasicTransform | None:
        """Try progressively safer parameter values."""
        context.attempt_count += 1

        if context.transform_name not in self.safe_parameter_ranges:
            return None

        try:
            safe_ranges = self.safe_parameter_ranges[context.transform_name]

            # Try multiple progressive reductions
            reduction_factors = [0.8, 0.6, 0.4, 0.2]

            for factor in reduction_factors:
                try:
                    progressive_params = {}

                    for param, safe_value in safe_ranges.items():
                        if isinstance(safe_value, tuple) and len(safe_value) == 2:
                            min_val, max_val = safe_value
                            if isinstance(min_val, (int, float)) and isinstance(
                                max_val,
                                (int, float),
                            ):
                                # Reduce the range by the factor
                                reduced_range = (max_val - min_val) * factor
                                progressive_params[param] = min_val + reduced_range / 2

                                # Handle special cases
                                if param.endswith("_limit") and param != "p":
                                    if "blur" in param:
                                        progressive_params[param] = max(
                                            3,
                                            int(progressive_params[param]),
                                        )
                                        if progressive_params[param] % 2 == 0:
                                            progressive_params[param] += 1
                            else:
                                progressive_params[param] = min_val
                        else:
                            # Single value parameter (like 'p')
                            progressive_params[param] = safe_value

                    # Adjust for image shape
                    if image_shape and context.transform_name in [
                        "RandomCrop",
                        "RandomResizedCrop",
                    ]:
                        height, width = image_shape[:2]
                        progressive_params["height"] = min(
                            progressive_params.get("height", 224),
                            height // 2,
                        )
                        progressive_params["width"] = min(
                            progressive_params.get("width", 224),
                            width // 2,
                        )

                    # Try creating transform
                    transform_class = getattr(A, context.transform_name)
                    transform = transform_class(**progressive_params)

                    self._record_recovery_attempt(
                        context,
                        RecoveryStrategy.PROGRESSIVE_FALLBACK,
                        success=True,
                    )
                    logger.info(
                        f"Progressive fallback successful for {context.transform_name} "
                        f"with factor {factor}: {progressive_params}",
                    )

                    return transform

                except Exception as e:
                    logger.debug(f"Progressive fallback factor {factor} failed: {e}")
                    continue

            self._record_recovery_attempt(
                context,
                RecoveryStrategy.PROGRESSIVE_FALLBACK,
                success=False,
            )
            return None

        except Exception as e:
            self._record_recovery_attempt(
                context,
                RecoveryStrategy.PROGRESSIVE_FALLBACK,
                success=False,
                error=str(e),
            )
            logger.debug(
                f"Progressive fallback failed for {context.transform_name}: {e}",
            )
            return None

    def _record_recovery_attempt(
        self,
        context: RecoveryContext,
        strategy: RecoveryStrategy,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record recovery attempt for statistics and debugging."""
        attempt_record = {
            "strategy": strategy.value,
            "success": success,
            "attempt_number": context.attempt_count,
            "timestamp": time.time(),
            "duration_ms": (time.time() - context.start_time) * 1000,
        }

        if error:
            attempt_record["error"] = error

        context.recovery_history.append(attempt_record)

        # Update global statistics
        strategy_key = strategy.value
        if strategy_key not in self.recovery_stats["recovery_strategies_used"]:
            self.recovery_stats["recovery_strategies_used"][strategy_key] = {
                "attempts": 0,
                "successes": 0,
            }

        self.recovery_stats["recovery_strategies_used"][strategy_key]["attempts"] += 1
        if success:
            self.recovery_stats["recovery_strategies_used"][strategy_key][
                "successes"
            ] += 1

    def _record_successful_recovery(
        self,
        context: RecoveryContext,
        strategy: RecoveryStrategy,
    ) -> None:
        """Record successful recovery for statistics."""
        self.recovery_stats["successful_recoveries"] += 1
        self._record_recovery_attempt(context, strategy, success=True)

        logger.info(
            f"Transform recovery successful for {context.transform_name} using {strategy.value}",
            extra={
                "transform": context.transform_name,
                "strategy": strategy.value,
                "attempts": context.attempt_count,
                "duration_ms": (time.time() - context.start_time) * 1000,
            },
        )


class MemoryRecoveryManager:
    """Manages memory exhaustion recovery and cleanup."""

    def __init__(self, max_memory_mb: int = 2048):
        """Initialize memory recovery manager.

        Args:
            max_memory_mb: Maximum memory usage in MB before triggering recovery
        """
        self.max_memory_mb = max_memory_mb
        self.memory_stats = {
            "peak_usage_mb": 0.0,
            "recovery_triggers": 0,
            "successful_cleanups": 0,
            "failed_cleanups": 0,
        }

    @contextmanager
    def memory_recovery_context(self, operation_name: str = "unknown"):
        """Context manager for memory recovery during operations."""
        initial_memory = self._get_memory_usage_mb()

        try:
            yield

        except MemoryError as e:
            logger.error(f"Memory exhaustion during {operation_name}: {e}")
            self.memory_stats["recovery_triggers"] += 1

            # Attempt memory recovery
            if self._attempt_memory_recovery():
                self.memory_stats["successful_cleanups"] += 1
                logger.info(f"Memory recovery successful for {operation_name}")
                # Re-raise to let caller handle the retry
                raise MemoryRecoveryError(
                    f"Memory exhausted during {operation_name}, recovery attempted",
                    RecoveryStrategy.RETURN_ORIGINAL,
                )
            else:
                self.memory_stats["failed_cleanups"] += 1
                logger.error(f"Memory recovery failed for {operation_name}")
                raise MemoryRecoveryError(
                    f"Memory exhausted during {operation_name}, recovery failed",
                    RecoveryStrategy.ABORT_PIPELINE,
                )

        finally:
            final_memory = self._get_memory_usage_mb()
            peak_memory = max(initial_memory, final_memory)

            self.memory_stats["peak_usage_mb"] = max(
                self.memory_stats["peak_usage_mb"],
                peak_memory,
            )

            # Log memory usage if significant
            memory_delta = final_memory - initial_memory
            if abs(memory_delta) > 100:  # 100MB threshold
                logger.debug(
                    f"Memory usage change for {operation_name}: {memory_delta:+.1f}MB "
                    f"(initial: {initial_memory:.1f}MB, final: {final_memory:.1f}MB)",
                )

    def check_memory_limits(self, operation_name: str = "unknown") -> bool:
        """Check if current memory usage exceeds limits.

        Args:
            operation_name: Name of the operation for logging

        Returns:
            True if memory usage is within limits, False otherwise
        """
        current_memory = self._get_memory_usage_mb()

        if current_memory > self.max_memory_mb:
            logger.warning(
                f"Memory limit exceeded during {operation_name}: "
                f"{current_memory:.1f}MB > {self.max_memory_mb}MB",
            )
            return False

        return True

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except Exception:
            # Fallback if psutil is not available or fails
            return 0.0

    def _attempt_memory_recovery(self) -> bool:
        """Attempt to recover memory by cleanup operations.

        Returns:
            True if recovery was successful, False otherwise
        """
        initial_memory = self._get_memory_usage_mb()

        try:
            # Force garbage collection
            gc.collect()

            # Additional cleanup strategies could be added here
            # - Clear caches
            # - Release temporary objects
            # - Reduce image resolution

            final_memory = self._get_memory_usage_mb()
            memory_freed = initial_memory - final_memory

            logger.info(f"Memory recovery freed {memory_freed:.1f}MB")

            # Consider recovery successful if we freed at least 100MB
            return memory_freed > 100

        except Exception as e:
            logger.error(f"Memory recovery attempt failed: {e}")
            return False


class PipelineRecoveryManager:
    """Manages recovery for entire processing pipelines."""

    def __init__(self):
        """Initialize pipeline recovery manager."""
        self.transform_recovery = TransformRecoveryManager()
        self.memory_recovery = MemoryRecoveryManager()

        self.pipeline_stats = {
            "total_pipelines": 0,
            "successful_pipelines": 0,
            "recovered_pipelines": 0,
            "failed_pipelines": 0,
        }

    def execute_pipeline_with_recovery(
        self,
        pipeline_func: Callable,
        *args,
        **kwargs,
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Execute pipeline function with comprehensive recovery.

        Args:
            pipeline_func: Function to execute with recovery
            *args: Arguments for the pipeline function
            **kwargs: Keyword arguments for the pipeline function

        Returns:
            Tuple of (result, recovery_events)
        """
        self.pipeline_stats["total_pipelines"] += 1
        recovery_events = []

        try:
            with self.memory_recovery.memory_recovery_context("pipeline_execution"):
                result = pipeline_func(*args, **kwargs)
                self.pipeline_stats["successful_pipelines"] += 1
                return result, recovery_events

        except MemoryRecoveryError as e:
            recovery_events.append(
                {
                    "type": "memory_recovery",
                    "strategy": e.recovery_strategy.value,
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )

            if e.recovery_strategy == RecoveryStrategy.RETURN_ORIGINAL:
                # Try to return original data if available
                original_data = (
                    kwargs.get("original_image") or args[0] if args else None
                )
                if original_data:
                    self.pipeline_stats["recovered_pipelines"] += 1
                    return original_data, recovery_events

            self.pipeline_stats["failed_pipelines"] += 1
            raise

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            self.pipeline_stats["failed_pipelines"] += 1
            raise

    def get_recovery_statistics(self) -> dict[str, Any]:
        """Get comprehensive recovery statistics."""
        return {
            "pipeline_stats": self.pipeline_stats.copy(),
            "transform_recovery_stats": self.transform_recovery.recovery_stats.copy(),
            "memory_recovery_stats": self.memory_recovery.memory_stats.copy(),
            "timestamp": time.time(),
        }


# Global recovery manager instances
_transform_recovery_manager = None
_memory_recovery_manager = None
_pipeline_recovery_manager = None


def get_transform_recovery_manager() -> TransformRecoveryManager:
    """Get global transform recovery manager instance."""
    global _transform_recovery_manager
    if _transform_recovery_manager is None:
        _transform_recovery_manager = TransformRecoveryManager()
    return _transform_recovery_manager


def get_memory_recovery_manager() -> MemoryRecoveryManager:
    """Get global memory recovery manager instance."""
    global _memory_recovery_manager
    if _memory_recovery_manager is None:
        _memory_recovery_manager = MemoryRecoveryManager()
    return _memory_recovery_manager


def get_pipeline_recovery_manager() -> PipelineRecoveryManager:
    """Get global pipeline recovery manager instance."""
    global _pipeline_recovery_manager
    if _pipeline_recovery_manager is None:
        _pipeline_recovery_manager = PipelineRecoveryManager()
    return _pipeline_recovery_manager


def recover_from_transform_failure(
    transform_name: str,
    parameters: dict[str, Any],
    error: Exception,
    image_shape: tuple[int, ...] | None = None,
) -> tuple[A.BasicTransform | None, RecoveryStrategy]:
    """Convenience function for transform failure recovery."""
    return get_transform_recovery_manager().recover_transform_failure(
        transform_name,
        parameters,
        error,
        image_shape,
    )


def check_memory_limits(operation_name: str = "unknown") -> bool:
    """Convenience function for memory limit checking."""
    return get_memory_recovery_manager().check_memory_limits(operation_name)


def get_recovery_statistics() -> dict[str, Any]:
    """Get comprehensive recovery statistics from all managers."""
    return get_pipeline_recovery_manager().get_recovery_statistics()
