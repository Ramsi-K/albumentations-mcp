"""Pre-transform hook for image and configuration validation before processing.

This hook validates image format, size, and quality, and validates transform
parameters to provide warnings before processing begins.
"""

import logging
from typing import Any

from ..image_conversions import base64_to_pil
from . import BaseHook, HookContext, HookResult
from .utils import (
    HIGH_BLUR_LIMIT,
    HIGH_BRIGHTNESS_CONTRAST,
    HIGH_NOISE_VARIANCE,
    LOW_PROBABILITY_THRESHOLD,
    MAX_ROTATION_DEGREES,
    MIN_CROP_SIZE,
    MIN_IMAGE_QUALITY,
    check_image_size_warnings,
    check_transform_conflicts,
    validate_image_format,
    validate_image_mode,
)

logger = logging.getLogger(__name__)


class PreTransformHook(BaseHook):
    """Hook for image and configuration validation before processing."""

    def __init__(self):
        super().__init__("pre_transform_validation", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """Validate image and configuration before processing."""
        try:
            logger.debug(
                f"Pre-transform validation for session {context.session_id}",
            )

            # Validate image data
            image_validation = self._validate_image(context)
            # Always add warnings, regardless of validation status
            context.warnings.extend(image_validation["warnings"])
            if image_validation["critical"]:
                return HookResult(
                    success=False,
                    error="Critical image validation failed",
                    context=context,
                )

            # Validate transform configuration
            config_validation = self._validate_transform_config(context)
            # Always add warnings, regardless of validation status
            context.warnings.extend(config_validation["warnings"])

            # Add validation metadata
            context.metadata.update(
                {
                    "pre_transform_processed": True,
                    "image_validation": image_validation,
                    "config_validation": config_validation,
                    "validation_warnings_count": len(context.warnings),
                },
            )

            logger.debug("Pre-transform validation completed successfully")
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Pre-transform validation failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _validate_image(self, context: HookContext) -> dict[str, Any]:
        """Validate image format, size, and quality."""
        validation_result = {
            "valid": True,
            "critical": False,
            "warnings": [],
            "image_info": {},
        }

        try:
            if not context.image_data:
                validation_result.update(
                    {
                        "valid": False,
                        "critical": True,
                        "warnings": ["No image data provided"],
                    },
                )
                return validation_result

            # Convert image data to PIL for validation
            try:
                image = base64_to_pil(context.image_data.decode())
            except Exception as e:
                validation_result.update(
                    {
                        "valid": False,
                        "critical": True,
                        "warnings": [f"Invalid image data: {e!s}"],
                    },
                )
                return validation_result

            # Store image info
            validation_result["image_info"] = {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height,
            }

            # Validate image format
            if not validate_image_format(image.format):
                validation_result["warnings"].append(
                    f"Unsupported image format: {image.format}. "
                    "Supported formats: JPEG, PNG, WEBP, TIFF",
                )

            # Validate image mode
            if not validate_image_mode(image.mode):
                validation_result["warnings"].append(
                    f"Image mode {image.mode} may cause processing issues. "
                    "Recommended modes: RGB, RGBA, L",
                )

            # Validate image size
            width, height = image.size
            size_warnings = check_image_size_warnings(width, height)
            validation_result["warnings"].extend(size_warnings)

            # Validate image quality (basic checks)
            if hasattr(image, "info") and "quality" in image.info:
                quality = image.info["quality"]
                if quality < MIN_IMAGE_QUALITY:
                    validation_result["warnings"].append(
                        f"Low image quality detected ({quality}). "
                        "Results may be degraded.",
                    )

        except Exception as e:
            validation_result.update(
                {
                    "valid": False,
                    "critical": False,
                    "warnings": [f"Image validation error: {e!s}"],
                },
            )

        return validation_result

    def _validate_transform_config(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Validate transform parameters and provide warnings."""
        validation_result = {
            "valid": True,
            "warnings": [],
            "transform_analysis": [],
        }

        try:
            if not context.parsed_transforms:
                validation_result.update(
                    {
                        "valid": False,
                        "warnings": ["No transforms specified"],
                    },
                )
                return validation_result

            for i, transform in enumerate(context.parsed_transforms):
                transform_analysis = self._analyze_transform(transform, i)
                validation_result["transform_analysis"].append(
                    transform_analysis,
                )
                validation_result["warnings"].extend(
                    transform_analysis["warnings"],
                )

            # Check for potentially conflicting transforms
            conflict_warnings = check_transform_conflicts(
                context.parsed_transforms,
            )
            validation_result["warnings"].extend(conflict_warnings)

        except Exception as e:
            validation_result.update(
                {
                    "valid": False,
                    "warnings": [f"Transform validation error: {e!s}"],
                },
            )

        return validation_result

    def _analyze_transform(
        self,
        transform: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        """Analyze individual transform for potential issues."""
        analysis = {
            "transform_index": index,
            "transform_name": transform.get("name", "unknown"),
            "warnings": [],
            "parameter_issues": [],
        }

        transform_name = transform.get("name")
        parameters = transform.get("parameters", {})

        if not transform_name:
            analysis["warnings"].append(
                f"Transform {index}: Missing transform name",
            )
            return analysis

        # Transform-specific validation
        if transform_name in ["Blur", "GaussianBlur", "MotionBlur"]:
            blur_limit = parameters.get("blur_limit")
            if blur_limit and blur_limit > HIGH_BLUR_LIMIT:
                analysis["warnings"].append(
                    f"Transform {index} ({transform_name}): "
                    f"High blur limit ({blur_limit}) may severely degrade image quality",
                )

        elif transform_name == "Rotate":
            limit = parameters.get("limit")
            if limit and abs(limit) > MAX_ROTATION_DEGREES:
                analysis["warnings"].append(
                    f"Transform {index} ({transform_name}): "
                    f"Large rotation ({limit}°) may crop significant image content",
                )

        elif transform_name == "RandomBrightnessContrast":
            brightness_limit = parameters.get("brightness_limit", 0)
            contrast_limit = parameters.get("contrast_limit", 0)
            if (
                brightness_limit > HIGH_BRIGHTNESS_CONTRAST
                or contrast_limit > HIGH_BRIGHTNESS_CONTRAST
            ):
                analysis["warnings"].append(
                    f"Transform {index} ({transform_name}): "
                    "High brightness/contrast limits may cause over/under-exposure",
                )

        elif transform_name == "GaussNoise":
            var_limit = parameters.get("var_limit")
            if var_limit:
                if isinstance(var_limit, (list, tuple)) and len(var_limit) >= 2:
                    max_noise = var_limit[1]
                    if max_noise > HIGH_NOISE_VARIANCE:
                        analysis["warnings"].append(
                            f"Transform {index} ({transform_name}): "
                            f"High noise variance ({max_noise}) may severely degrade image",
                        )

        elif transform_name in ["RandomCrop", "RandomResizedCrop"]:
            height = parameters.get("height")
            width = parameters.get("width")
            if height and width:
                if height < MIN_CROP_SIZE or width < MIN_CROP_SIZE:
                    analysis["warnings"].append(
                        f"Transform {index} ({transform_name}): "
                        f"Small crop size ({width}x{height}) may lose important details",
                    )

        # Check probability (can be in parameters as 'p' or top-level as 'probability')
        probability = parameters.get("p", transform.get("probability", 1.0))
        if probability < LOW_PROBABILITY_THRESHOLD:
            analysis["warnings"].append(
                f"Transform {index} ({transform_name}): "
                f"Very low probability ({probability}) - transform rarely applied",
            )

        return analysis
