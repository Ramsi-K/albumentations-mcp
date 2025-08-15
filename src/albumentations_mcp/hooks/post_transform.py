"""Post-transform hook for metadata attachment after processing.

This hook adds processing statistics, quality metrics, and generates
transformation summary and timing data after image processing completes.
"""

import logging
import time
from typing import Any

import numpy as np
from PIL import Image

from ..image_conversions import base64_to_pil
from . import BaseHook, HookContext, HookResult
from .utils import (
    HIGH_COMPLEXITY_THRESHOLD,
    calculate_transform_complexity,
    categorize_transform,
    rate_performance,
)

logger = logging.getLogger(__name__)


class PostTransformHook(BaseHook):
    """Hook for metadata attachment after processing."""

    def __init__(self):
        super().__init__("post_transform_metadata", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """Attach metadata and statistics after processing."""
        try:
            logger.debug(
                f"Post-transform metadata for session {context.session_id}",
            )

            # Validate context structure first
            if context.parsed_transforms is not None and not isinstance(
                context.parsed_transforms,
                list,
            ):
                raise ValueError(
                    f"parsed_transforms must be a list, got {type(context.parsed_transforms)}",
                )

            # Generate processing statistics
            processing_stats = self._generate_processing_stats(context)

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(context)

            # Generate transformation summary
            transform_summary = self._generate_transform_summary(context)

            # Calculate timing data
            timing_data = self._calculate_timing_data(context)

            # Add all metadata to context
            context.metadata.update(
                {
                    "post_transform_processed": True,
                    "processing_statistics": processing_stats,
                    "quality_metrics": quality_metrics,
                    "transformation_summary": transform_summary,
                    "timing_data": timing_data,
                    "metadata_generation_time": time.time(),
                },
            )

            logger.debug(
                "Post-transform metadata generation completed successfully",
            )
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Post-transform metadata generation failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _generate_processing_stats(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Generate comprehensive processing statistics."""
        stats = {
            "transforms_requested": len(context.parsed_transforms or []),
            "transforms_applied": 0,
            "transforms_skipped": 0,
            "processing_success": False,
            "has_original_image": context.image_data is not None,
            "has_augmented_image": context.augmented_image is not None,
        }

        try:
            # Extract processing results from metadata if available
            if "processing_result" in context.metadata:
                result = context.metadata["processing_result"]
                stats.update(
                    {
                        "transforms_applied": len(
                            result.get("applied_transforms", []),
                        ),
                        "transforms_skipped": len(
                            result.get("skipped_transforms", []),
                        ),
                        "processing_success": result.get("success", False),
                        "execution_time": result.get("execution_time", 0),
                    },
                )

            # Calculate success rate
            if stats["transforms_requested"] > 0:
                stats["success_rate"] = (
                    stats["transforms_applied"] / stats["transforms_requested"]
                )
            else:
                stats["success_rate"] = 0.0

            # Determine processing status
            if stats["transforms_applied"] == stats["transforms_requested"]:
                stats["processing_status"] = "complete"
            elif stats["transforms_applied"] > 0:
                stats["processing_status"] = "partial"
            else:
                stats["processing_status"] = "failed"

        except Exception as e:
            logger.warning(f"Error generating processing stats: {e}")
            stats["error"] = str(e)

        return stats

    def _calculate_quality_metrics(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Calculate image quality metrics comparing original and augmented images."""
        metrics = {
            "comparison_available": False,
            "size_change": None,
            "format_preserved": None,
            "mode_preserved": None,
        }

        try:
            if not context.image_data or not context.augmented_image:
                return metrics

            # Load original image
            original_image = base64_to_pil(context.image_data.decode())

            # Load augmented image (assuming it's also base64 encoded bytes)
            if isinstance(context.augmented_image, bytes):
                augmented_image = base64_to_pil(
                    context.augmented_image.decode(),
                )
            else:
                # If it's already a PIL Image
                augmented_image = context.augmented_image

            metrics["comparison_available"] = True

            # Size comparison
            orig_size = original_image.size
            aug_size = augmented_image.size
            metrics.update(
                {
                    "original_size": orig_size,
                    "augmented_size": aug_size,
                    "size_change": {
                        "width_change": aug_size[0] - orig_size[0],
                        "height_change": aug_size[1] - orig_size[1],
                        "area_change": (aug_size[0] * aug_size[1])
                        - (orig_size[0] * orig_size[1]),
                        "aspect_ratio_change": (aug_size[0] / aug_size[1])
                        - (orig_size[0] / orig_size[1]),
                    },
                },
            )

            # Format and mode preservation
            metrics.update(
                {
                    "format_preserved": original_image.format == augmented_image.format,
                    "mode_preserved": original_image.mode == augmented_image.mode,
                    "original_format": original_image.format,
                    "augmented_format": augmented_image.format,
                    "original_mode": original_image.mode,
                    "augmented_mode": augmented_image.mode,
                },
            )

            # Basic quality metrics
            if original_image.mode == augmented_image.mode and orig_size == aug_size:
                quality_metrics = self._calculate_image_similarity(
                    original_image,
                    augmented_image,
                )
                metrics["similarity_metrics"] = quality_metrics

        except Exception as e:
            logger.warning(f"Error calculating quality metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    def _calculate_image_similarity(
        self,
        original: Image.Image,
        augmented: Image.Image,
    ) -> dict[str, Any]:
        """Calculate basic similarity metrics between original and augmented images."""
        try:
            # Convert to numpy arrays
            orig_array = np.array(original)
            aug_array = np.array(augmented)

            # Ensure same shape
            if orig_array.shape != aug_array.shape:
                return {
                    "error": "Image shapes don't match for similarity calculation",
                }

            # Calculate basic metrics
            mse = np.mean(
                (orig_array.astype(float) - aug_array.astype(float)) ** 2,
            )

            # Calculate PSNR (Peak Signal-to-Noise Ratio)
            if mse == 0:
                psnr = float("inf")
            else:
                max_pixel = 255.0
                psnr = 20 * np.log10(max_pixel / np.sqrt(mse))

            # Calculate structural similarity (basic version)
            mean_orig = np.mean(orig_array)
            mean_aug = np.mean(aug_array)
            std_orig = np.std(orig_array)
            std_aug = np.std(aug_array)

            # Normalized cross-correlation
            if std_orig > 0 and std_aug > 0:
                correlation = np.corrcoef(
                    orig_array.flatten(),
                    aug_array.flatten(),
                )[0, 1]
            else:
                correlation = 0.0

            return {
                "mse": float(mse),
                "psnr": float(psnr),
                "correlation": (
                    float(correlation) if not np.isnan(correlation) else 0.0
                ),
                "mean_difference": float(abs(mean_orig - mean_aug)),
                "std_difference": float(abs(std_orig - std_aug)),
                "pixel_change_percentage": float(
                    np.mean(orig_array != aug_array) * 100,
                ),
            }

        except Exception as e:
            return {"error": f"Similarity calculation failed: {e}"}

    def _generate_transform_summary(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Generate detailed transformation summary."""
        summary = {
            "total_transforms": len(context.parsed_transforms or []),
            "transform_details": [],
            "categories": {},
            "complexity_score": 0,
        }

        try:
            if not context.parsed_transforms:
                return summary

            # Categorize transforms
            categories = {}
            complexity_score = 0

            for i, transform in enumerate(context.parsed_transforms):
                transform_name = transform.get("name", "unknown")
                parameters = transform.get("parameters", {})
                probability = transform.get("probability", 1.0)

                # Categorize transform
                category = categorize_transform(transform_name)
                if category not in categories:
                    categories[category] = []
                categories[category].append(transform_name)

                # Calculate complexity contribution
                complexity_score += calculate_transform_complexity(
                    transform_name,
                    parameters,
                )

                # Add detailed info
                transform_detail = {
                    "index": i,
                    "name": transform_name,
                    "category": category,
                    "probability": probability,
                    "parameter_count": len(parameters),
                    "parameters": parameters,
                    "complexity": calculate_transform_complexity(
                        transform_name,
                        parameters,
                    ),
                }
                summary["transform_details"].append(transform_detail)

            summary.update(
                {
                    "categories": {
                        cat: len(transforms) for cat, transforms in categories.items()
                    },
                    "complexity_score": complexity_score,
                    "average_complexity": complexity_score
                    / len(context.parsed_transforms),
                    "high_complexity_transforms": [
                        t["name"]
                        for t in summary["transform_details"]
                        if t["complexity"] > HIGH_COMPLEXITY_THRESHOLD
                    ],
                },
            )

        except Exception as e:
            logger.warning(f"Error generating transform summary: {e}")
            summary["error"] = str(e)

        return summary

    def _calculate_timing_data(self, context: HookContext) -> dict[str, Any]:
        """Calculate timing and performance data."""
        timing_data = {
            "total_pipeline_time": None,
            "processing_time": None,
            "hook_execution_times": {},
            "performance_metrics": {},
        }

        try:
            # Calculate total pipeline time if timestamps are available
            if "timestamp" in context.metadata:
                current_time = time.time()
                timing_data["metadata_generation_timestamp"] = current_time

            # Extract processing time from results
            if "processing_result" in context.metadata:
                result = context.metadata["processing_result"]
                timing_data["processing_time"] = result.get("execution_time")

            # Performance assessment
            processing_time = timing_data.get("processing_time", 0)
            transform_count = len(context.parsed_transforms or [])

            if processing_time and transform_count:
                timing_data["performance_metrics"] = {
                    "time_per_transform": processing_time / transform_count,
                    "transforms_per_second": transform_count / processing_time,
                    "performance_rating": rate_performance(
                        processing_time,
                        transform_count,
                    ),
                }

        except Exception as e:
            logger.warning(f"Error calculating timing data: {e}")
            timing_data["error"] = str(e)

        return timing_data
