"""Natural language parser for image augmentation prompts.

This module provides simple string-matching based parsing to convert
natural language descriptions into structured Albumentations transform
specifications.

Natural language parser that converts English descriptions like
"add blur and rotate" into structured Albumentations transform
specifications. Core component that bridges human language with
computer vision transformations.

"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class TransformType(str, Enum):
    """Supported Albumentations transform types."""

    BLUR = "Blur"
    MOTION_BLUR = "MotionBlur"
    GAUSSIAN_BLUR = "GaussianBlur"
    RANDOM_BRIGHTNESS_CONTRAST = "RandomBrightnessContrast"
    HUE_SATURATION_VALUE = "HueSaturationValue"
    ROTATE = "Rotate"
    HORIZONTAL_FLIP = "HorizontalFlip"
    VERTICAL_FLIP = "VerticalFlip"
    GAUSSIAN_NOISE = "GaussNoise"
    RANDOM_CROP = "RandomCrop"
    RANDOM_RESIZE_CROP = "RandomResizedCrop"
    NORMALIZE = "Normalize"
    CLAHE = "CLAHE"


class TransformConfig(BaseModel):
    """Configuration for a single transform."""

    name: TransformType = Field(
        ..., description="Name of the Albumentations transform"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Transform parameters",
    )
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probability of applying transform",
    )

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v, info):
        """Validate parameters based on transform type."""
        transform_name = info.data.get("name") if info.data else None
        if transform_name and transform_name in [
            "Blur",
            "MotionBlur",
            "GaussianBlur",
        ]:
            if "blur_limit" in v and (
                v["blur_limit"] < 3 or v["blur_limit"] > 100
            ):
                raise ValueError("blur_limit must be between 3 and 100")
        return v


class ParseResult(BaseModel):
    """Result of parsing a natural language prompt."""

    transforms: list[TransformConfig] = Field(
        ...,
        description="List of parsed transform configurations",
    )
    original_prompt: str = Field(..., description="Original input prompt")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for parsing accuracy",
    )
    warnings: list[str] = Field(
        default_factory=list, description="Parsing warnings"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )


class TransformConfig(BaseModel):
    """Configuration for a single transform."""

    name: TransformType = Field(
        ..., description="Name of the Albumentations transform"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Transform parameters",
    )
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probability of applying transform",
    )

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v, info):
        """Validate parameters based on transform type."""
        transform_name = info.data.get("name") if info.data else None
        if transform_name and transform_name in [
            "Blur",
            "MotionBlur",
            "GaussianBlur",
        ]:
            if "blur_limit" in v and (
                v["blur_limit"] < 3 or v["blur_limit"] > 100
            ):
                raise ValueError("blur_limit must be between 3 and 100")
        return v


class ParseResult(BaseModel):
    """Result of parsing a natural language prompt."""

    transforms: list[TransformConfig] = Field(
        ...,
        description="List of parsed transform configurations",
    )
    original_prompt: str = Field(..., description="Original input prompt")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for parsing accuracy",
    )
    warnings: list[str] = Field(
        default_factory=list, description="Parsing warnings"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for improvement",
    )


class PromptParsingError(Exception):
    """Raised when prompt parsing fails."""


class PromptParser:
    """Simple string-matching based natural language parser."""

    def __init__(self):
        """Initialize parser with transform mappings and defaults."""
        self._transform_mappings = self._build_transform_mappings()
        self._default_parameters = self._build_default_parameters()
        self._parameter_patterns = self._build_parameter_patterns()

        # Performance optimizations
        self._phrase_cache = {}  # Cache for phrase matching results
        self._split_cache = {}  # Cache for prompt splitting results
        self._max_cache_size = 1000  # Limit cache size

        # Pre-compile regex patterns for better performance
        self._compiled_patterns = {}
        for name, pattern in self._parameter_patterns.items():
            if isinstance(pattern, str):
                self._compiled_patterns[name] = re.compile(
                    pattern, re.IGNORECASE
                )
            else:
                # Pattern is already compiled
                self._compiled_patterns[name] = pattern

    def _build_transform_mappings(self) -> dict[str, TransformType]:
        """Build mapping from natural language phrases to transforms."""
        return {
            # Blur transforms
            "blur": TransformType.BLUR,
            "blurry": TransformType.BLUR,
            "gaussian blur": TransformType.GAUSSIAN_BLUR,
            "motion blur": TransformType.MOTION_BLUR,
            "motion blurry": TransformType.MOTION_BLUR,
            "add blur": TransformType.BLUR,
            "make blurry": TransformType.BLUR,
            # Contrast and brightness
            "contrast": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "increase contrast": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "enhance contrast": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "brightness": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "brighten": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "darken": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "increase brightness": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            "decrease brightness": TransformType.RANDOM_BRIGHTNESS_CONTRAST,
            # Color adjustments
            "hue": TransformType.HUE_SATURATION_VALUE,
            "saturation": TransformType.HUE_SATURATION_VALUE,
            "color": TransformType.HUE_SATURATION_VALUE,
            "adjust color": TransformType.HUE_SATURATION_VALUE,
            "change hue": TransformType.HUE_SATURATION_VALUE,
            "adjust saturation": TransformType.HUE_SATURATION_VALUE,
            # Geometric transforms
            "rotate": TransformType.ROTATE,
            "rotation": TransformType.ROTATE,
            "turn": TransformType.ROTATE,
            "flip horizontal": TransformType.HORIZONTAL_FLIP,
            "flip vertically": TransformType.VERTICAL_FLIP,
            "horizontal flip": TransformType.HORIZONTAL_FLIP,
            "vertical flip": TransformType.VERTICAL_FLIP,
            "mirror": TransformType.HORIZONTAL_FLIP,
            # Noise and distortion
            "noise": TransformType.GAUSSIAN_NOISE,
            "add noise": TransformType.GAUSSIAN_NOISE,
            "gaussian noise": TransformType.GAUSSIAN_NOISE,
            "noisy": TransformType.GAUSSIAN_NOISE,
            # Cropping
            "crop": TransformType.RANDOM_CROP,
            "random crop": TransformType.RANDOM_CROP,
            "resize crop": TransformType.RANDOM_RESIZE_CROP,
            "random resize crop": TransformType.RANDOM_RESIZE_CROP,
            # Enhancement
            "normalize": TransformType.NORMALIZE,
            "clahe": TransformType.CLAHE,
            "histogram equalization": TransformType.CLAHE,
            "enhance": TransformType.CLAHE,
            "sharpen": TransformType.CLAHE,  # Use CLAHE for sharpening effect
            "sharpening": TransformType.CLAHE,
            # Grayscale
            "grayscale": TransformType.TO_GRAY,
            "gray scale": TransformType.TO_GRAY,
            "grey scale": TransformType.TO_GRAY,
            "greyscale": TransformType.TO_GRAY,
            "to gray": TransformType.TO_GRAY,
            "to grey": TransformType.TO_GRAY,
            "make gray": TransformType.TO_GRAY,
            "make grey": TransformType.TO_GRAY,
            "turn gray": TransformType.TO_GRAY,
            "turn grey": TransformType.TO_GRAY,
        }

    def _build_default_parameters(self) -> dict[TransformType, dict[str, Any]]:
        """Build default parameters for each transform type."""
        return {
            TransformType.BLUR: {"blur_limit": 7, "p": 1.0},
            TransformType.GAUSSIAN_BLUR: {"blur_limit": 7, "p": 1.0},
            TransformType.MOTION_BLUR: {"blur_limit": 7, "p": 1.0},
            TransformType.RANDOM_BRIGHTNESS_CONTRAST: {
                "brightness_limit": 0.2,
                "contrast_limit": 0.2,
                "p": 1.0,
            },
            TransformType.HUE_SATURATION_VALUE: {
                "hue_shift_limit": 20,
                "sat_shift_limit": 30,
                "val_shift_limit": 20,
                "p": 1.0,
            },
            TransformType.ROTATE: {"limit": 45, "p": 1.0},
            TransformType.HORIZONTAL_FLIP: {"p": 1.0},
            TransformType.VERTICAL_FLIP: {"p": 1.0},
            TransformType.GAUSSIAN_NOISE: {
                "var_limit": (10.0, 50.0),
                "p": 1.0,
            },
            TransformType.RANDOM_CROP: {"height": 224, "width": 224, "p": 1.0},
            TransformType.RANDOM_RESIZE_CROP: {
                "height": 224,
                "width": 224,
                "p": 1.0,
            },
            TransformType.NORMALIZE: {"p": 1.0},
            TransformType.CLAHE: {
                "clip_limit": 4.0,
                "tile_grid_size": (8, 8),
                "p": 1.0,
            },
        }

    def _build_parameter_patterns(self) -> dict[str, re.Pattern]:
        """Build regex patterns for extracting parameters from text."""
        return {
            "blur_amount": re.compile(
                r"blur\s+(?:by\s+)?(\d+(?:\.\d+)?)",
                re.IGNORECASE,
            ),
            "rotation_angle": re.compile(
                r"rotate\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*(?:degrees?)?",
                re.IGNORECASE,
            ),
            "brightness_amount": re.compile(
                r"brightness\s+(?:by\s+)?(\d+(?:\.\d+)?)",
                re.IGNORECASE,
            ),
            "contrast_amount": re.compile(
                r"contrast\s+(?:by\s+)?(\d+(?:\.\d+)?)",
                re.IGNORECASE,
            ),
            "noise_level": re.compile(
                r"noise\s+(?:level\s+)?(\d+(?:\.\d+)?)",
                re.IGNORECASE,
            ),
            "crop_size": re.compile(
                r"crop\s+(?:to\s+)?(\d+)(?:x(\d+))?",
                re.IGNORECASE,
            ),
        }

    def parse_prompt(self, prompt: str) -> ParseResult:
        """Parse natural language prompt into transform specifications.

        Args:
            prompt: Natural language description of desired augmentations

        Returns:
            ParseResult with transforms, confidence, and metadata

        Raises:
            PromptParsingError: If prompt cannot be parsed

        # Code Review Findings:
        # BAD PRACTICE: Method too complex (80+ lines) - should be split
        # MISSING: Input validation for prompt length limits
        # SECURITY: No protection against ReDoS attacks
        # EDGE CASE: No handling of Unicode characters
        # PERFORMANCE: Inefficient O(n*m) string matching
        """
        # Use comprehensive validation system
        from .validation import ValidationError, validate_prompt

        try:
            validation_result = validate_prompt(prompt, strict=True)
            sanitized_prompt = validation_result["sanitized_prompt"]
        except ValidationError as e:
            raise PromptParsingError(f"Prompt validation failed: {e}")

        prompt = sanitized_prompt.lower()

        logger.debug(f"Parsing prompt: '{prompt}'")

        transforms = []
        warnings = []
        suggestions = []
        confidence = 0.0

        try:
            # Split prompt into phrases and process each
            phrases = self._split_prompt(prompt)
            matched_phrases = 0

            for phrase in phrases:
                phrase = phrase.strip()
                if not phrase:
                    continue

                # Try to match phrase to transform
                transform_config = self._match_phrase_to_transform(phrase)
                if transform_config:
                    transforms.append(transform_config)
                    matched_phrases += 1
                    logger.debug(
                        "Matched phrase '%s' to %s",
                        phrase,
                        transform_config.name,
                    )
                else:
                    warnings.append(f"Could not understand phrase: '{phrase}'")
                    suggestions.extend(self._suggest_alternatives(phrase))

            # Calculate confidence based on matched phrases
            if phrases:
                confidence = matched_phrases / len(phrases)

            # Handle empty results
            if not transforms:
                if not warnings:
                    warnings.append(
                        "No recognizable transformations found in prompt",
                    )
                suggestions.extend(
                    [
                        "Try phrases like: 'add blur', 'increase contrast', "
                        "'rotate image'",
                        "Use simple descriptions: 'blur', 'brighten', 'add noise'",
                    ],
                )

            result = ParseResult(
                transforms=transforms,
                original_prompt=prompt,
                confidence=confidence,
                warnings=warnings,
                suggestions=suggestions,
            )

            logger.info(
                "Parsed prompt successfully: %d transforms, confidence: %.2f",
                len(transforms),
                confidence,
            )
            return result

        except Exception as e:
            logger.error(f"Error parsing prompt '{prompt}': {e!s}")
            raise PromptParsingError(f"Failed to parse prompt: {e!s}")

    def _split_prompt(self, prompt: str) -> list[str]:
        """Split prompt into individual phrases."""
        # Split on common separators
        separators = [" and ", " then ", " also ", ",", ";"]
        phrases = [prompt]

        for separator in separators:
            new_phrases = []
            for phrase in phrases:
                new_phrases.extend(phrase.split(separator))
            phrases = new_phrases

        return [p.strip() for p in phrases if p.strip()]

    def _match_phrase_to_transform(
        self,
        phrase: str,
    ) -> TransformConfig | None:
        """Match a phrase to a transform configuration."""
        # Direct mapping lookup
        for pattern, transform_type in self._transform_mappings.items():
            if pattern in phrase:
                # Extract parameters from phrase
                parameters = self._extract_parameters(phrase, transform_type)
                return TransformConfig(
                    name=transform_type,
                    parameters=parameters,
                    probability=1.0,
                )

        return None

    def _extract_parameters(
        self,
        phrase: str,
        transform_type: TransformType,
    ) -> dict[str, Any]:
        """Extract parameters from phrase for specific transform type."""
        # Start with defaults
        parameters = self._default_parameters[transform_type].copy()

        # Extract specific parameters based on transform type
        if transform_type in [
            TransformType.BLUR,
            TransformType.GAUSSIAN_BLUR,
            TransformType.MOTION_BLUR,
        ]:
            match = self._parameter_patterns["blur_amount"].search(phrase)
            if match:
                blur_value = float(match.group(1))
                # Ensure odd number for blur_limit
                blur_limit = (
                    int(blur_value)
                    if int(blur_value) % 2 == 1
                    else int(blur_value) + 1
                )
                parameters["blur_limit"] = max(3, min(blur_limit, 99))

        elif transform_type == TransformType.ROTATE:
            match = self._parameter_patterns["rotation_angle"].search(phrase)
            if match:
                angle = float(match.group(1))
                parameters["limit"] = max(1, min(angle, 180))

        elif transform_type == TransformType.RANDOM_BRIGHTNESS_CONTRAST:
            # Handle brightness parameters
            brightness_match = self._parameter_patterns[
                "brightness_amount"
            ].search(
                phrase,
            )
            if brightness_match:
                brightness = float(brightness_match.group(1))
                if brightness > 1:
                    brightness = brightness / 100  # Convert percentage
                parameters["brightness_limit"] = max(0.1, min(brightness, 1.0))

            # Handle contrast parameters
            contrast_match = self._parameter_patterns[
                "contrast_amount"
            ].search(phrase)
            if contrast_match:
                contrast = float(contrast_match.group(1))
                if contrast > 1:
                    contrast = contrast / 100  # Convert percentage
                parameters["contrast_limit"] = max(0.1, min(contrast, 1.0))

            # Handle increase/decrease keywords for brightness
            if (
                "brighten" in phrase
                or "increase brightness" in phrase
                or "darken" in phrase
                or "decrease brightness" in phrase
            ):
                if "brightness_limit" not in parameters:
                    parameters["brightness_limit"] = 0.2

            # Handle contrast keywords
            if (
                "contrast" in phrase
                and "brightness_limit" not in parameters
                and "contrast_limit" not in parameters
            ):
                parameters["contrast_limit"] = 0.2

        elif transform_type == TransformType.GAUSSIAN_NOISE:
            match = self._parameter_patterns["noise_level"].search(phrase)
            if match:
                noise_level = float(match.group(1))
                if noise_level <= 1:
                    noise_level *= 100  # Convert to 0-100 range
                parameters["var_limit"] = (
                    max(1.0, noise_level * 0.5),
                    min(100.0, noise_level),
                )

        elif transform_type in [
            TransformType.RANDOM_CROP,
            TransformType.RANDOM_RESIZE_CROP,
        ]:
            match = self._parameter_patterns["crop_size"].search(phrase)
            if match:
                width = int(match.group(1))
                height = int(match.group(2)) if match.group(2) else width
                parameters["width"] = max(32, min(width, 2048))
                parameters["height"] = max(32, min(height, 2048))

        return parameters

    def _suggest_alternatives(self, phrase: str) -> list[str]:
        """Suggest alternative phrasings for unrecognized phrases."""
        suggestions = []

        # Look for partial matches
        phrase_words = set(phrase.split())
        for pattern in self._transform_mappings.keys():
            pattern_words = set(pattern.split())
            if phrase_words & pattern_words:  # If there's any word overlap
                suggestions.append(f"Did you mean '{pattern}'?")

        # Limit suggestions to avoid overwhelming output
        return suggestions[:3]

    def get_available_transforms(self) -> dict[str, dict[str, Any]]:
        """Get information about available transforms and their parameters."""
        result = {}

        for transform_type in TransformType:
            # Get example phrases for this transform
            example_phrases = [
                phrase
                for phrase, t_type in self._transform_mappings.items()
                if t_type == transform_type
            ]

            result[transform_type.value] = {
                "description": self._get_transform_description(transform_type),
                "example_phrases": example_phrases[:3],  # Limit examples
                "default_parameters": self._default_parameters[transform_type],
                "parameter_ranges": self._get_parameter_ranges(transform_type),
            }

        return result

    def _get_transform_description(self, transform_type: TransformType) -> str:
        """Get human-readable description for transform type."""
        descriptions = {
            TransformType.BLUR: "Apply gaussian blur to the image",
            TransformType.GAUSSIAN_BLUR: (
                "Apply gaussian blur with configurable kernel"
            ),
            TransformType.MOTION_BLUR: "Apply motion blur effect",
            TransformType.RANDOM_BRIGHTNESS_CONTRAST: "Randomly adjust image brightness and contrast",
            TransformType.HUE_SATURATION_VALUE: (
                "Adjust hue, saturation, and value"
            ),
            TransformType.ROTATE: "Rotate image by specified angle",
            TransformType.HORIZONTAL_FLIP: "Flip image horizontally",
            TransformType.VERTICAL_FLIP: "Flip image vertically",
            TransformType.GAUSSIAN_NOISE: "Add gaussian noise to image",
            TransformType.RANDOM_CROP: (
                "Randomly crop image to specified size"
            ),
            TransformType.RANDOM_RESIZE_CROP: "Randomly crop and resize image",
            TransformType.NORMALIZE: "Normalize image pixel values",
            TransformType.CLAHE: (
                "Apply Contrast Limited Adaptive Histogram Equalization"
            ),
        }
        return descriptions.get(
            transform_type,
            f"Apply {transform_type.value} transformation",
        )

    def _get_parameter_ranges(
        self,
        transform_type: TransformType,
    ) -> dict[str, str]:
        """Get parameter ranges for transform type."""
        ranges = {
            TransformType.BLUR: {"blur_limit": "3-99 (odd numbers)"},
            TransformType.GAUSSIAN_BLUR: {"blur_limit": "3-99 (odd numbers)"},
            TransformType.MOTION_BLUR: {"blur_limit": "3-99 (odd numbers)"},
            TransformType.RANDOM_BRIGHTNESS_CONTRAST: {
                "brightness_limit": "0.1-1.0",
                "contrast_limit": "0.1-1.0",
            },
            TransformType.HUE_SATURATION_VALUE: {
                "hue_shift_limit": "0-180",
                "sat_shift_limit": "0-100",
                "val_shift_limit": "0-100",
            },
            TransformType.ROTATE: {"limit": "1-180 degrees"},
            TransformType.HORIZONTAL_FLIP: {"p": "0.0-1.0"},
            TransformType.VERTICAL_FLIP: {"p": "0.0-1.0"},
            TransformType.GAUSSIAN_NOISE: {"var_limit": "1.0-100.0"},
            TransformType.RANDOM_CROP: {
                "height": "32-2048",
                "width": "32-2048",
            },
            TransformType.RANDOM_RESIZE_CROP: {
                "height": "32-2048",
                "width": "32-2048",
            },
            TransformType.NORMALIZE: {"p": "0.0-1.0"},
            TransformType.CLAHE: {
                "clip_limit": "1.0-40.0",
                "tile_grid_size": "(2,2)-(16,16)",
            },
        }
        return ranges.get(transform_type, {})

    def validate_prompt(self, prompt: str) -> dict[str, Any]:
        """Validate prompt and return detailed analysis."""
        try:
            result = self.parse_prompt(prompt)

            return {
                "valid": len(result.transforms) > 0,
                "confidence": result.confidence,
                "transforms_found": len(result.transforms),
                "transforms": [
                    {
                        "name": t.name.value,
                        "parameters": t.parameters,
                        "probability": t.probability,
                    }
                    for t in result.transforms
                ],
                "warnings": result.warnings,
                "suggestions": result.suggestions,
                "message": (
                    f"Found {len(result.transforms)} transforms with "
                    f"{result.confidence:.1%} confidence"
                ),
            }

        except PromptParsingError as e:
            return {
                "valid": False,
                "confidence": 0.0,
                "transforms_found": 0,
                "transforms": [],
                "warnings": [str(e)],
                "suggestions": [
                    "Try simple phrases like 'blur image' or 'increase brightness'",
                    "Use 'and' to combine multiple transformations",
                    "Be specific with parameters like 'rotate by 45 degrees'",
                ],
                "message": f"Parsing failed: {e!s}",
            }

    def clear_caches(self) -> None:
        """Clear parser caches to free memory."""
        self._phrase_cache.clear()
        self._split_cache.clear()
        logger.debug("Cleared parser caches")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "phrase_cache_size": len(self._phrase_cache),
            "split_cache_size": len(self._split_cache),
            "max_cache_size": self._max_cache_size,
        }

    def _manage_cache_size(self) -> None:
        """Manage cache size to prevent memory leaks."""
        if len(self._phrase_cache) > self._max_cache_size:
            # Remove oldest 20% of entries
            items_to_remove = len(self._phrase_cache) // 5
            for _ in range(items_to_remove):
                self._phrase_cache.pop(next(iter(self._phrase_cache)))

        if len(self._split_cache) > self._max_cache_size:
            items_to_remove = len(self._split_cache) // 5
            for _ in range(items_to_remove):
                self._split_cache.pop(next(iter(self._split_cache)))


# Global parser instance
_parser_instance = None


def get_parser() -> PromptParser:
    """Get global parser instance (singleton pattern)."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = PromptParser()
    return _parser_instance


def parse_prompt(prompt: str) -> ParseResult:
    """Convenience function to parse a prompt using global parser."""
    return get_parser().parse_prompt(prompt)


def validate_prompt(prompt: str) -> dict[str, Any]:
    """Convenience function to validate a prompt using global parser."""
    return get_parser().validate_prompt(prompt)


def get_available_transforms() -> dict[str, dict[str, Any]]:
    """Convenience function to get available transforms."""
    return get_parser().get_available_transforms()
