"""Pre-transform hook for image and configuration validation before processing.

This hook validates image format, size, and quality, validates transform
parameters, and automatically resizes oversized images when needed.
"""

import logging
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from ..image_conversions import base64_to_pil, pil_to_base64
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

# Configuration constants - validated from environment variables
from ..config import (
    get_max_bytes_in,
    get_max_image_size,
    get_max_pixels_in,
    is_strict_mode,
)


def _get_config_values():
    """Get validated configuration values."""
    return {
        "MAX_IMAGE_SIZE": get_max_image_size(),
        "MAX_PIXELS_IN": get_max_pixels_in(),
        "MAX_BYTES_IN": get_max_bytes_in(),
        "STRICT_MODE": is_strict_mode(),
    }


# Supported formats for preservation
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "TIFF"}


class PreTransformHook(BaseHook):
    """Hook for image and configuration validation before processing."""

    def __init__(self):
        super().__init__("pre_transform_validation", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """Validate image and configuration before processing, with auto-resize capability."""
        try:
            logger.debug(
                f"Pre-transform validation for session {context.session_id}",
            )

            # Initialize temp_paths list if not exists
            if not hasattr(context, "temp_paths"):
                context.temp_paths = []

            # Validate and potentially resize image
            image_validation = self._validate_and_resize_image(context)
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

    def _validate_and_resize_image(self, context: HookContext) -> dict[str, Any]:
        """Validate image format, size, and quality, with automatic resizing."""
        validation_result = {
            "valid": True,
            "critical": False,
            "warnings": [],
            "image_info": {},
            "resize_applied": False,
            "original_dimensions": None,
            "resized_dimensions": None,
            "original_bytes": None,
            "resized_bytes": None,
            "resize_reason": None,
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

            # Normalize EXIF orientation and convert to RGB before measuring
            image = self._normalize_image(image)

            # Store original image info
            original_width, original_height = image.size
            original_pixels = original_width * original_height
            original_bytes = len(context.image_data)

            validation_result["image_info"] = {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": original_width,
                "height": original_height,
                "pixels": original_pixels,
                "bytes": original_bytes,
            }
            validation_result["original_dimensions"] = (
                f"{original_width}x{original_height}"
            )
            validation_result["original_bytes"] = original_bytes

            # Validate image format
            if not validate_image_format(image.format):
                config = _get_config_values()
                if config["STRICT_MODE"]:
                    validation_result.update(
                        {
                            "valid": False,
                            "critical": True,
                            "warnings": [
                                f"Unsupported image format: {image.format}. Supported formats: {', '.join(SUPPORTED_FORMATS)}",
                            ],
                        },
                    )
                    return validation_result
                validation_result["warnings"].append(
                    f"Unsupported image format: {image.format}. "
                    f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
                )

            # Validate image mode
            if not validate_image_mode(image.mode):
                validation_result["warnings"].append(
                    f"Image mode {image.mode} may cause processing issues. "
                    "Recommended modes: RGB, RGBA, L",
                )

            # Check if image needs resizing
            needs_resize, resize_reason = self._check_resize_needed(
                original_width,
                original_height,
                original_pixels,
                original_bytes,
            )

            if needs_resize:
                config = _get_config_values()
                if config["STRICT_MODE"]:
                    validation_result.update(
                        {
                            "valid": False,
                            "critical": True,
                            "warnings": [
                                f"Image exceeds size limits: {resize_reason}. Enable auto-resize by setting STRICT_MODE=false",
                            ],
                        },
                    )
                    return validation_result
                # Auto-resize the image
                resized_image, resize_info = self._resize_image(image, context)
                if resized_image:
                    # Update context with resized image
                    context.image_data = pil_to_base64(
                        resized_image,
                        format=image.format or "PNG",
                    ).encode()

                    validation_result.update(
                        {
                            "resize_applied": True,
                            "resized_dimensions": f"{resized_image.width}x{resized_image.height}",
                            "resized_bytes": len(context.image_data),
                            "resize_reason": resize_reason,
                        },
                    )

                    # Update image info with resized dimensions
                    validation_result["image_info"].update(
                        {
                            "width": resized_image.width,
                            "height": resized_image.height,
                            "size": resized_image.size,
                            "pixels": resized_image.width * resized_image.height,
                            "bytes": len(context.image_data),
                        },
                    )

                    logger.info(
                        f"Auto-resized image: {original_width}x{original_height} -> "
                        f"{resized_image.width}x{resized_image.height}, "
                        f"reason: {resize_reason}",
                    )
                else:
                    validation_result["warnings"].append(
                        f"Failed to auto-resize oversized image: {resize_reason}",
                    )

            # Add size warnings for remaining issues
            current_width = validation_result["image_info"]["width"]
            current_height = validation_result["image_info"]["height"]
            size_warnings = check_image_size_warnings(current_width, current_height)
            validation_result["warnings"].extend(size_warnings)

            # Validate image quality (basic checks)
            if hasattr(image, "info") and "quality" in image.info:
                quality = image.info["quality"]
                if quality < MIN_IMAGE_QUALITY:
                    validation_result["warnings"].append(
                        f"Low image quality detected ({quality}). "
                        "Results may be degraded.",
                    )

            # Log comprehensive metadata
            logger.debug(
                f"Image validation complete - resize_applied: {validation_result['resize_applied']}, "
                f"original: {validation_result['original_dimensions']}, "
                f"final: {current_width}x{current_height}, "
                f"reason: {validation_result['resize_reason']}",
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

    def _normalize_image(self, image: Image.Image) -> Image.Image:
        """Normalize EXIF orientation and convert to RGB before measuring/resizing."""
        try:
            # Fix EXIF orientation
            image = ImageOps.exif_transpose(image)

            # Convert to RGB if needed (but preserve RGBA for transparency)
            if image.mode not in ("RGB", "RGBA"):
                if image.mode in ("P", "L", "LA"):
                    image = image.convert("RGB")
                else:
                    try:
                        image = image.convert("RGB")
                    except Exception:
                        # If conversion fails, keep original
                        pass

            return image
        except Exception as e:
            logger.warning(f"Failed to normalize image: {e}")
            return image

    def _check_resize_needed(
        self,
        width: int,
        height: int,
        pixels: int,
        bytes_size: int,
    ) -> tuple[bool, str]:
        """Check if image needs resizing based on various limits."""
        config = _get_config_values()
        reasons = []

        # Check maximum dimension
        max_dimension = max(width, height)
        if max_dimension > config["MAX_IMAGE_SIZE"]:
            reasons.append(
                f"max dimension {max_dimension}px > {config['MAX_IMAGE_SIZE']}px",
            )

        # Check total pixels
        if pixels > config["MAX_PIXELS_IN"]:
            reasons.append(f"total pixels {pixels:,} > {config['MAX_PIXELS_IN']:,}")

        # Check file size
        if bytes_size > config["MAX_BYTES_IN"]:
            reasons.append(
                f"file size {bytes_size:,} bytes > {config['MAX_BYTES_IN']:,} bytes",
            )

        if reasons:
            return True, "; ".join(reasons)

        return False, ""

    def _resize_image(
        self,
        image: Image.Image,
        context: HookContext,
    ) -> tuple[Image.Image | None, dict[str, Any]]:
        """Resize image while preserving aspect ratio and format."""
        try:
            original_width, original_height = image.size
            original_format = image.format or "PNG"

            # Calculate new dimensions preserving aspect ratio
            config = _get_config_values()
            aspect_ratio = original_width / original_height

            if original_width > original_height:
                new_width = config["MAX_IMAGE_SIZE"]
                new_height = int(config["MAX_IMAGE_SIZE"] / aspect_ratio)
            else:
                new_height = config["MAX_IMAGE_SIZE"]
                new_width = int(config["MAX_IMAGE_SIZE"] * aspect_ratio)

            # Ensure minimum size
            new_width = max(new_width, 32)
            new_height = max(new_height, 32)

            # Resize using high-quality LANCZOS filter
            resized_image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS,
            )

            # Preserve format information
            resized_image.format = original_format

            # Save resized copy to session temp directory
            temp_path = self._save_temp_image(resized_image, context, "resized")
            if temp_path:
                context.temp_paths.append(str(temp_path))

            resize_info = {
                "original_size": (original_width, original_height),
                "new_size": (new_width, new_height),
                "aspect_ratio_preserved": True,
                "filter_used": "LANCZOS",
                "temp_path": str(temp_path) if temp_path else None,
            }

            logger.debug(
                f"Image resized: {original_width}x{original_height} -> {new_width}x{new_height}",
            )

            return resized_image, resize_info

        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return None, {"error": str(e)}

    def _save_temp_image(
        self,
        image: Image.Image,
        context: HookContext,
        suffix: str = "",
    ) -> Path | None:
        """Save image to session temp directory with proper format preservation."""
        try:
            # Use existing session directory from pre_save hook
            session_dir_str = context.metadata.get("session_dir")
            if not session_dir_str:
                logger.warning("No session directory found, creating fallback")
                session_dir = Path("outputs") / f"{context.session_id}"
            else:
                session_dir = Path(session_dir_str)

            temp_dir = session_dir / "tmp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Determine format and extension
            original_format = image.format or "PNG"
            ext_map = {
                "JPEG": "jpg",
                "PNG": "png",
                "WEBP": "webp",
                "TIFF": "tiff",
            }
            extension = ext_map.get(original_format.upper(), "png")

            # Generate filename
            filename = f"image_{suffix}.{extension}" if suffix else f"image.{extension}"
            temp_path = temp_dir / filename

            # Save with format-specific options
            save_kwargs = {"format": original_format}
            if original_format.upper() == "JPEG":
                save_kwargs["quality"] = 85
                save_kwargs["optimize"] = True
                # Convert RGBA to RGB for JPEG
                if image.mode == "RGBA":
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background
            elif original_format.upper() == "PNG":
                save_kwargs["optimize"] = True
            elif original_format.upper() == "WEBP":
                save_kwargs["lossless"] = True
                save_kwargs["quality"] = 100

            image.save(temp_path, **save_kwargs)

            logger.debug(f"Saved temp image: {temp_path}")
            return temp_path

        except Exception as e:
            logger.warning(f"Failed to save temp image: {e}")
            return None

    def _validate_path_security(self, path: str) -> bool:
        """Validate path for security (prevent path traversal, symlinks)."""
        try:
            # Reject absolute paths outside session directory
            if os.path.isabs(path):
                return False

            # Reject paths with '..' segments
            if ".." in Path(path).parts:
                return False

            # Reject symlinks
            if Path(path).is_symlink():
                return False

            return True
        except Exception:
            return False
