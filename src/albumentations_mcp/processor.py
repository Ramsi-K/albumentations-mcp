"""Image processing engine with Albumentations integration.

This module provides the core image processing functionality that applies
Albumentations transforms to images based on parsed natural language prompts.
Uses Albumentations' native seeding for reproducibility.
"""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

import albumentations as A
from PIL import Image

from .image_utils import (
    numpy_to_pil,
    pil_to_numpy,
    validate_image,
)

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Raised when image processing fails."""


class ProcessingResult(BaseModel):
    """Result of image processing operation."""

    model_config = {"arbitrary_types_allowed": True}

    success: bool = Field(
        ..., description="Whether processing completed successfully"
    )
    augmented_image: Image.Image | None = Field(
        None, description="Processed image"
    )
    applied_transforms: list[dict[str, Any]] = Field(
        default_factory=list, description="Successfully applied transforms"
    )
    skipped_transforms: list[dict[str, Any]] = Field(
        default_factory=list, description="Transforms that were skipped"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Processing metadata"
    )
    execution_time: float = Field(
        ..., ge=0, description="Processing time in seconds"
    )
    error_message: str | None = Field(
        None, description="Error message if failed"
    )


class ImageProcessor:
    """Core image processing engine using Albumentations."""

    def __init__(self):
        """Initialize the image processor."""
        self._transform_cache = {}  # Cache for compiled transforms

    def process_image(
        self,
        image: Image.Image,
        transforms: list[dict[str, Any]],
        seed: int | None = None,
    ) -> ProcessingResult:
        """Process image with given transform specifications.

        Args:
            image: PIL Image to process
            transforms: List of transform specifications from parser
            seed: Optional seed for reproducible results

        Returns:
            ProcessingResult with augmented image and metadata
        """
        start_time = time.time()
        applied_transforms = []
        skipped_transforms = []

        try:
            # Validate input image
            validate_image(image)
            original_size = image.size

            # Convert PIL to numpy for Albumentations
            image_array = pil_to_numpy(image)

            # Get effective seed using simple seed manager
            from .seed_manager import get_effective_seed, get_seed_metadata

            effective_seed = get_effective_seed(seed)
            seed_metadata = get_seed_metadata(effective_seed, seed)

            # Create pipeline with Albumentations native seeding
            pipeline, pipeline_metadata = self._create_pipeline(
                transforms, effective_seed
            )
            applied_transforms.extend(pipeline_metadata["applied"])
            skipped_transforms.extend(pipeline_metadata["skipped"])

            if not pipeline:
                # No valid transforms, return original
                execution_time = time.time() - start_time
                return ProcessingResult(
                    success=True,
                    augmented_image=image,
                    applied_transforms=applied_transforms,
                    skipped_transforms=skipped_transforms,
                    metadata={
                        "original_size": original_size,
                        "output_size": original_size,
                        "processing_time": execution_time,
                        "transforms_applied": 0,
                        "transforms_skipped": len(skipped_transforms),
                        **seed_metadata,
                    },
                    execution_time=execution_time,
                )

            # Apply transforms - Albumentations handles seeding internally
            try:
                augmented = pipeline(image=image_array)["image"]
                augmented_image = numpy_to_pil(augmented)
                execution_time = time.time() - start_time

                return ProcessingResult(
                    success=True,
                    augmented_image=augmented_image,
                    applied_transforms=applied_transforms,
                    skipped_transforms=skipped_transforms,
                    metadata={
                        "original_size": original_size,
                        "output_size": augmented_image.size,
                        "processing_time": execution_time,
                        "transforms_applied": len(applied_transforms),
                        "transforms_skipped": len(skipped_transforms),
                        "pipeline_hash": hash(str(transforms)),
                        **seed_metadata,
                    },
                    execution_time=execution_time,
                )

            except Exception as e:
                logger.error(f"Transform pipeline execution failed: {e}")
                execution_time = time.time() - start_time
                return ProcessingResult(
                    success=False,
                    augmented_image=image,
                    applied_transforms=[],
                    skipped_transforms=transforms,
                    metadata={
                        "original_size": original_size,
                        "output_size": original_size,
                        "processing_time": execution_time,
                        "error": str(e),
                        **seed_metadata,
                    },
                    execution_time=execution_time,
                    error_message=f"Pipeline execution failed: {e}",
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Image processing failed: {e}")

            # Simple fallback metadata
            return ProcessingResult(
                success=False,
                augmented_image=None,
                applied_transforms=[],
                skipped_transforms=transforms,
                metadata={
                    "processing_time": execution_time,
                    "error": str(e),
                    "seed_used": seed is not None,
                    "effective_seed": seed,
                },
                execution_time=execution_time,
                error_message=f"Processing failed: {e}",
            )

    def _create_pipeline(
        self,
        transforms: list[dict[str, Any]],
        seed: int | None = None,
    ) -> tuple[A.Compose | None, dict[str, Any]]:
        """Create Albumentations pipeline from transform specifications.

        Args:
            transforms: List of transform specifications
            seed: Optional seed for reproducible results

        Returns:
            Tuple of (pipeline, metadata) where pipeline may be None if no valid transforms
        """
        valid_transforms = []
        applied_transforms = []
        skipped_transforms = []

        for transform_spec in transforms:
            try:
                transform_obj = self._create_transform(transform_spec)
                if transform_obj:
                    valid_transforms.append(transform_obj)
                    applied_transforms.append(transform_spec)
                else:
                    skipped_transforms.append(transform_spec)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid transform {transform_spec.get('name', 'unknown')}: {e}",
                )
                skipped_transforms.append(transform_spec)

        if not valid_transforms:
            return None, {
                "applied": applied_transforms,
                "skipped": skipped_transforms,
            }

        try:
            # Use Albumentations' built-in seed support
            if seed is not None:
                pipeline = A.Compose(valid_transforms, seed=seed)
            else:
                pipeline = A.Compose(valid_transforms)
            return pipeline, {
                "applied": applied_transforms,
                "skipped": skipped_transforms,
            }
        except Exception as e:
            logger.error(f"Failed to create transform pipeline: {e}")
            return None, {"applied": [], "skipped": transforms}

    def _create_transform(
        self,
        transform_spec: dict[str, Any],
    ) -> A.BasicTransform | None:
        """Create single Albumentations transform from specification.

        Args:
            transform_spec: Transform specification with name and parameters

        Returns:
            Albumentations transform object or None if creation fails
        """
        transform_name = transform_spec.get("name")
        parameters = transform_spec.get("parameters", {})

        if not transform_name:
            logger.warning("Transform specification missing name")
            return None

        try:
            # Get transform class from Albumentations
            if not hasattr(A, transform_name):
                logger.warning(f"Unknown transform: {transform_name}")
                return None

            transform_class = getattr(A, transform_name)

            # Validate and clean parameters
            clean_params = self._validate_parameters(
                transform_name, parameters
            )

            # Create transform instance
            transform = transform_class(**clean_params)

            logger.debug(
                f"Created transform {transform_name} with parameters {clean_params}",
            )
            return transform

        except Exception as e:
            logger.warning(f"Failed to create transform {transform_name}: {e}")
            return None

    def _validate_parameters(
        self,
        transform_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and clean transform parameters.

        Args:
            transform_name: Name of the transform
            parameters: Raw parameters from parser

        Returns:
            Cleaned and validated parameters
        """
        # Remove None values and empty parameters
        clean_params = {k: v for k, v in parameters.items() if v is not None}

        # Transform-specific parameter validation
        if transform_name in ["Blur", "GaussianBlur", "MotionBlur"]:
            if "blur_limit" in clean_params:
                # Ensure blur_limit is odd and within valid range
                blur_limit = clean_params["blur_limit"]
                if isinstance(blur_limit, (int, float)):
                    blur_limit = int(blur_limit)
                    if blur_limit % 2 == 0:
                        blur_limit += 1
                    clean_params["blur_limit"] = max(3, min(blur_limit, 99))

        elif transform_name == "Rotate":
            if "limit" in clean_params:
                # Ensure rotation limit is within valid range
                limit = clean_params["limit"]
                if isinstance(limit, (int, float)):
                    clean_params["limit"] = max(-180, min(float(limit), 180))

        elif transform_name == "RandomBrightnessContrast":
            # Handle brightness limit
            if "brightness_limit" in clean_params:
                brightness_limit = clean_params["brightness_limit"]
                if isinstance(brightness_limit, (int, float)):
                    clean_params["brightness_limit"] = max(
                        0.0,
                        min(float(brightness_limit), 1.0),
                    )

            # Handle contrast limit
            if "contrast_limit" in clean_params:
                contrast_limit = clean_params["contrast_limit"]
                if isinstance(contrast_limit, (int, float)):
                    clean_params["contrast_limit"] = max(
                        0.0,
                        min(float(contrast_limit), 1.0),
                    )

        elif transform_name == "GaussNoise":
            if "var_limit" in clean_params:
                var_limit = clean_params["var_limit"]
                if (
                    isinstance(var_limit, (tuple, list))
                    and len(var_limit) == 2
                ):
                    # Ensure noise variance is within valid range
                    min_var, max_var = var_limit
                    clean_params["var_limit"] = (
                        max(0.0, float(min_var)),
                        min(255.0, float(max_var)),
                    )

        elif transform_name in ["RandomCrop", "RandomResizedCrop"]:
            # Ensure crop dimensions are positive integers
            for dim in ["height", "width"]:
                if dim in clean_params:
                    value = clean_params[dim]
                    if isinstance(value, (int, float)):
                        clean_params[dim] = max(1, int(value))

        # Ensure probability is valid
        if "p" in clean_params:
            p = clean_params["p"]
            if isinstance(p, (int, float)):
                clean_params["p"] = max(0.0, min(1.0, float(p)))

        return clean_params


# Global processor instance
_processor_instance = None


def get_processor() -> ImageProcessor:
    """Get global processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = ImageProcessor()
    return _processor_instance


def process_image(
    image: Image.Image,
    transforms: list[dict[str, Any]],
    seed: int | None = None,
) -> ProcessingResult:
    """Convenience function to process image with transforms."""
    return get_processor().process_image(image, transforms, seed=seed)
