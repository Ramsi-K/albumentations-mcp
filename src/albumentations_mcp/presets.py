#!/usr/bin/env python3
"""
Preset Pipeline Configurations for Albumentations MCP

Provides predefined augmentation pipelines optimized for specific use cases.
Each preset contains a curated set of transforms with parameters tuned for
optimal results in that domain.

Available presets:
- segmentation: Mild augmentations that preserve object boundaries
- portrait: Transforms suitable for human faces and portraits
- lowlight: Enhancements for low-light and dark images
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Preset definitions with optimized parameters
PRESET_DEFINITIONS = {
    "segmentation": {
        "name": "Segmentation",
        "description": "Mild augmentations that preserve object boundaries for segmentation tasks",
        "use_cases": [
            "semantic segmentation",
            "instance segmentation",
            "object detection",
        ],
        "transforms": [
            {
                "name": "HorizontalFlip",
                "parameters": {"p": 0.5},
                "probability": 0.5,
            },
            {
                "name": "RandomBrightnessContrast",
                "parameters": {
                    "brightness_limit": 0.1,
                    "contrast_limit": 0.1,
                    "p": 0.8,
                },
                "probability": 0.8,
            },
            {
                "name": "HueSaturationValue",
                "parameters": {
                    "hue_shift_limit": 10,
                    "sat_shift_limit": 15,
                    "val_shift_limit": 10,
                    "p": 0.7,
                },
                "probability": 0.7,
            },
            {
                "name": "Rotate",
                "parameters": {
                    "limit": 15,
                    "border_mode": 0,
                    "p": 0.6,
                },
                "probability": 0.6,
            },
            # RandomScale not supported, using RandomResizedCrop instead
            {
                "name": "RandomResizedCrop",
                "parameters": {
                    "height": 224,
                    "width": 224,
                    "scale": (0.9, 1.1),
                    "p": 0.5,
                },
                "probability": 0.5,
            },
        ],
        "metadata": {
            "category": "computer_vision",
            "intensity": "mild",
            "preserves_geometry": True,
            "recommended_for": ["training", "data_augmentation"],
        },
    },
    "portrait": {
        "name": "Portrait",
        "description": "Transforms suitable for human faces and portrait photography",
        "use_cases": [
            "face recognition",
            "portrait enhancement",
            "facial analysis",
        ],
        "transforms": [
            {
                "name": "RandomBrightnessContrast",
                "parameters": {
                    "brightness_limit": 0.2,
                    "contrast_limit": 0.2,
                    "p": 0.8,
                },
                "probability": 0.8,
            },
            {
                "name": "HueSaturationValue",
                "parameters": {
                    "hue_shift_limit": 5,
                    "sat_shift_limit": 20,
                    "val_shift_limit": 15,
                    "p": 0.7,
                },
                "probability": 0.7,
            },
            {
                "name": "CLAHE",
                "parameters": {
                    "clip_limit": 2.0,
                    "tile_grid_size": [8, 8],
                    "p": 0.6,
                },
                "probability": 0.6,
            },
            # Sharpen not supported, using CLAHE for enhancement instead
            {
                "name": "CLAHE",
                "parameters": {
                    "clip_limit": 3.0,
                    "tile_grid_size": (4, 4),
                    "p": 0.5,
                },
                "probability": 0.5,
            },
            {
                "name": "Rotate",
                "parameters": {
                    "limit": 10,
                    "border_mode": 1,
                    "p": 0.4,
                },
                "probability": 0.4,
            },
            {
                "name": "GaussianNoise",
                "parameters": {
                    "var_limit": (5.0, 15.0),
                    "p": 0.3,
                },
                "probability": 0.3,
            },
        ],
        "metadata": {
            "category": "photography",
            "intensity": "moderate",
            "preserves_geometry": False,
            "recommended_for": ["enhancement", "training", "preprocessing"],
        },
    },
    "lowlight": {
        "name": "Low Light",
        "description": "Enhancements for low-light and dark images",
        "use_cases": [
            "night photography",
            "indoor scenes",
            "low-light enhancement",
        ],
        "transforms": [
            {
                "name": "RandomBrightnessContrast",
                "parameters": {
                    "brightness_limit": [0.1, 0.4],
                    "contrast_limit": [0.1, 0.3],
                    "p": 0.9,
                },
                "probability": 0.9,
            },
            {
                "name": "CLAHE",
                "parameters": {
                    "clip_limit": 4.0,
                    "tile_grid_size": [8, 8],
                    "p": 0.8,
                },
                "probability": 0.8,
            },
            {
                "name": "HueSaturationValue",
                "parameters": {
                    "hue_shift_limit": 5,
                    "sat_shift_limit": 25,
                    "val_shift_limit": 20,
                    "p": 0.7,
                },
                "probability": 0.7,
            },
            # Sharpen and UnsharpMask not supported, using additional CLAHE for enhancement
            {
                "name": "CLAHE",
                "parameters": {
                    "clip_limit": 6.0,
                    "tile_grid_size": (6, 6),
                    "p": 0.6,
                },
                "probability": 0.6,
            },
            {
                "name": "GaussianNoise",
                "parameters": {
                    "var_limit": (3.0, 8.0),
                    "p": 0.3,
                },
                "probability": 0.3,
            },
            {
                "name": "ToGray",
                "parameters": {"p": 0.1},
                "probability": 0.1,
            },
        ],
        "metadata": {
            "category": "enhancement",
            "intensity": "strong",
            "preserves_geometry": True,
            "recommended_for": ["preprocessing", "enhancement", "restoration"],
        },
    },
}


def get_available_presets() -> dict[str, dict[str, Any]]:
    """Get all available preset configurations.

    Returns:
        Dictionary mapping preset names to their configurations
    """
    return PRESET_DEFINITIONS.copy()


def get_preset(preset_name: str) -> dict[str, Any] | None:
    """Get a specific preset configuration by name.

    Args:
        preset_name: Name of the preset to retrieve

    Returns:
        Preset configuration dictionary, or None if not found
    """
    return PRESET_DEFINITIONS.get(preset_name.lower())


def list_preset_names() -> list[str]:
    """Get list of available preset names.

    Returns:
        List of preset names
    """
    return list(PRESET_DEFINITIONS.keys())


def validate_preset(preset_config: dict[str, Any]) -> bool:
    """Validate a preset configuration structure.

    Args:
        preset_config: Preset configuration to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        required_fields = ["name", "description", "transforms"]
        for field in required_fields:
            if field not in preset_config:
                logger.error(f"Missing required field: {field}")
                return False

        if not isinstance(preset_config["transforms"], list):
            logger.error("Transforms must be a list")
            return False

        for i, transform in enumerate(preset_config["transforms"]):
            if not isinstance(transform, dict):
                logger.error(f"Transform {i} must be a dictionary")
                return False

            if "name" not in transform:
                logger.error(f"Transform {i} missing 'name' field")
                return False

            if "parameters" not in transform:
                logger.error(f"Transform {i} missing 'parameters' field")
                return False

        return True

    except Exception as e:
        logger.error(f"Error validating preset: {e}")
        return False


def preset_to_transforms(preset_name: str) -> list[dict[str, Any]] | None:
    """Convert a preset to a list of transform configurations.

    Args:
        preset_name: Name of the preset to convert

    Returns:
        List of transform configurations, or None if preset not found
    """
    preset = get_preset(preset_name)
    if not preset:
        return None

    return preset["transforms"]


def create_custom_preset(
    name: str,
    description: str,
    transforms: list[dict[str, Any]],
    use_cases: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a custom preset configuration.

    Args:
        name: Preset name
        description: Preset description
        transforms: List of transform configurations
        use_cases: Optional list of use cases
        metadata: Optional metadata dictionary

    Returns:
        Custom preset configuration
    """
    preset = {
        "name": name,
        "description": description,
        "transforms": transforms,
    }

    if use_cases:
        preset["use_cases"] = use_cases

    if metadata:
        preset["metadata"] = metadata

    return preset


def save_preset_to_file(preset_config: dict[str, Any], filepath: str) -> bool:
    """Save a preset configuration to a JSON file.

    Args:
        preset_config: Preset configuration to save
        filepath: Path to save the preset file

    Returns:
        True if successful, False otherwise
    """
    try:
        if not validate_preset(preset_config):
            logger.error("Invalid preset configuration")
            return False

        with open(filepath, "w") as f:
            json.dump(preset_config, f, indent=2)

        logger.info(f"Preset saved to {filepath}")
        return True

    except Exception as e:
        logger.error(f"Error saving preset to {filepath}: {e}")
        return False


def load_preset_from_file(filepath: str) -> dict[str, Any] | None:
    """Load a preset configuration from a JSON file.

    Args:
        filepath: Path to the preset file

    Returns:
        Preset configuration, or None if loading failed
    """
    try:
        with open(filepath) as f:
            preset_config = json.load(f)

        if not validate_preset(preset_config):
            logger.error(f"Invalid preset configuration in {filepath}")
            return None

        logger.info(f"Preset loaded from {filepath}")
        return preset_config

    except Exception as e:
        logger.error(f"Error loading preset from {filepath}: {e}")
        return None


def get_preset_summary() -> dict[str, str]:
    """Get a summary of all available presets.

    Returns:
        Dictionary mapping preset names to their descriptions
    """
    return {name: config["description"] for name, config in PRESET_DEFINITIONS.items()}


def apply_preset_to_prompt(preset_name: str, additional_prompt: str = "") -> str:
    """Generate a natural language prompt that represents a preset.

    This is useful for combining presets with additional user prompts.

    Args:
        preset_name: Name of the preset
        additional_prompt: Additional prompt to append

    Returns:
        Combined natural language prompt
    """
    preset = get_preset(preset_name)
    if not preset:
        return additional_prompt

    # Generate a natural language description of the preset
    preset_descriptions = {
        "segmentation": "apply mild augmentations suitable for segmentation",
        "portrait": "enhance portrait with face-friendly adjustments",
        "lowlight": "brighten and enhance low-light image",
    }

    preset_prompt = preset_descriptions.get(
        preset_name.lower(),
        f"apply {preset_name} preset",
    )

    if additional_prompt:
        return f"{preset_prompt} and {additional_prompt}"
    return preset_prompt
