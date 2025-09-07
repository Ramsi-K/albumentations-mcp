#!/usr/bin/env python3
"""
Albumentations MCP Server

An MCP-compliant image augmentation server that bridges natural language
processing with computer vision using the Albumentations library.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from PIL import Image

from .parser import get_available_transforms
from .pipeline import get_pipeline, parse_prompt_with_hooks
from .presets import get_available_presets, get_preset

# VLM config loader (file-first)
from .vlm.config import get_vlm_api_key, load_vlm_config

# Initialize FastMCP server
mcp = FastMCP("albumentations-mcp")


# Use existing validation system instead of recreating validation logic
def validate_mcp_request(tool_name: str, **kwargs) -> tuple[bool, str | None]:
    """Validate MCP tool request using existing validation utilities.

    Args:
        tool_name: Name of the MCP tool being called
        **kwargs: Tool parameters to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    from .utils.validation_utils import (
        validate_numeric_range,
        validate_string_input,
    )

    try:
        # Tool-specific validation using existing utilities
        if tool_name == "augment_image":
            if kwargs.get("image_path"):
                validate_string_input(
                    kwargs["image_path"],
                    "image_path",
                    max_length=1000,
                )
            if kwargs.get("image_b64"):
                validate_string_input(
                    kwargs["image_b64"],
                    "image_b64",
                    max_length=50000000,
                )  # ~50MB base64
            if kwargs.get("session_id"):
                validate_string_input(kwargs["session_id"], "session_id", max_length=50)
            if kwargs.get("prompt"):
                validate_string_input(kwargs["prompt"], "prompt", max_length=1000)
            if kwargs.get("preset"):
                validate_string_input(kwargs["preset"], "preset", max_length=50)
                if kwargs["preset"] not in [
                    "segmentation",
                    "portrait",
                    "lowlight",
                ]:
                    return (
                        False,
                        "preset must be one of: segmentation, portrait, lowlight",
                    )
            if "seed" in kwargs and kwargs["seed"] is not None:
                validate_numeric_range(
                    kwargs["seed"],
                    "seed",
                    min_value=0,
                    max_value=4294967295,
                )
            if kwargs.get("output_dir"):
                validate_string_input(
                    kwargs["output_dir"],
                    "output_dir",
                    max_length=500,
                )

        elif tool_name == "validate_prompt":
            if "prompt" in kwargs:
                validate_string_input(kwargs["prompt"], "prompt", max_length=1000)

        elif tool_name == "set_default_seed":
            if "seed" in kwargs and kwargs["seed"] is not None:
                validate_numeric_range(
                    kwargs["seed"],
                    "seed",
                    min_value=0,
                    max_value=4294967295,
                )

        elif tool_name == "load_image_for_processing":
            if "image_source" in kwargs:
                validate_string_input(
                    kwargs["image_source"],
                    "image_source",
                    max_length=2000000,
                )

        return True, None

    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {e}"


def _validate_augmentation_inputs(
    prompt: str,
    preset: str | None,
) -> tuple[bool, str | None]:
    """Validate augmentation inputs and return validation result."""
    prompt_provided = prompt and prompt.strip()
    preset_provided = preset and preset.strip()

    if not prompt_provided and not preset_provided:
        return (
            False,
            "Either prompt or preset must be provided. Use validate_prompt tool to test prompts or list_available_presets tool to see available presets.",
        )

    if prompt_provided and preset_provided:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Both prompt and preset provided, using preset")

    return True, None


def _load_session_image(session_id: str) -> tuple[str | None, str | None]:
    """Load image from session directory. Returns (image_b64, error_message)."""

    from PIL import Image

    from .image_conversions import pil_to_base64

    output_dir = os.getenv("OUTPUT_DIR", "outputs")
    out_path = Path(output_dir)
    # Locate existing session directory matching *_{session_id}
    candidates = sorted(
        [
            d
            for d in out_path.iterdir()
            if d.is_dir() and d.name.endswith(f"_{session_id}")
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    session_dir = candidates[0] if candidates else None

    if session_dir is None or not session_dir.exists():
        return (
            None,
            f"Session '{session_id}' not found. Use load_image_for_processing first to load an image.",
        )

    original_image_path = session_dir / f"original_{session_id}.png"
    if not original_image_path.exists():
        return (
            None,
            f"Original image not found for session '{session_id}'. Use load_image_for_processing first.",
        )

    try:
        image = Image.open(original_image_path)
        image_b64 = pil_to_base64(image)
        return image_b64, None
    except Exception as e:
        return None, f"Failed to load session image: {e}"


def _prepare_processing_prompt(
    prompt: str,
    preset: str | None,
) -> tuple[str | None, str | None]:
    """Prepare the effective prompt for processing. Returns (effective_prompt, error_message)."""
    if preset and preset.strip():
        preset_config = get_preset(preset)
        if not preset_config:
            return (
                None,
                f"Preset '{preset}' not found. Use list_available_presets tool to see available presets.",
            )

        from .presets import preset_to_transforms

        transforms = preset_to_transforms(preset)
        if not transforms:
            return (
                None,
                f"Preset '{preset}' contains no valid transforms. Use list_available_presets tool to see available presets.",
            )

        return f"apply {preset} preset", None
    return prompt.strip(), None


def _execute_pipeline(
    image_b64: str,
    effective_prompt: str,
    seed: int | None,
    session_id: str,
) -> dict:
    """Execute the processing pipeline. Returns pipeline result."""
    from .pipeline import process_image_with_hooks

    # Using master async function to eliminate duplicate code
    from .utils import run_async_safely

    return run_async_safely(
        process_image_with_hooks,
        image_b64,
        effective_prompt,
        seed,
        session_id,
    )


def _format_success_response(
    pipeline_result: dict,
    session_id: str,
    input_mode: str = "session",
) -> str:
    """Format successful pipeline response."""
    file_paths = pipeline_result["metadata"].get("file_paths", {})
    returned_session_id = pipeline_result.get("session_id", session_id)

    if file_paths and "augmented_image" in file_paths:
        from pathlib import Path

        augmented_path = file_paths.get("augmented_image")
        original_path = file_paths.get("original_image")
        metadata_path = file_paths.get("metadata") or file_paths.get(
            "transform_spec",
        )

        # Derive full session folder from any known artifact path
        session_dir = None
        for p in (augmented_path, original_path, metadata_path):
            if p:
                try:
                    session_dir = str(Path(p).parent.parent)
                    break
                except Exception:
                    continue

        lines: list[str] = []
        lines.append("✅ Image successfully augmented and saved!")
        lines.append("")
        lines.append("📁 Files saved:")
        if augmented_path:
            lines.append(f"- Augmented image: {augmented_path}")
        if original_path:
            lines.append(f"- Original image: {original_path}")
        if metadata_path:
            lines.append(f"- Metadata: {metadata_path}")
        if session_dir:
            lines.append(f"- Full session folder: {session_dir}")
        lines.append("")
        lines.append(
            "💡 All files are accessible via filesystem tools for further analysis.",
        )

        return "\n".join(lines)

    # Fallback if file saving failed
    applied_transforms = (
        pipeline_result["metadata"]
        .get("processing_result", {})
        .get("applied_transforms", [])
    )
    transform_names = [t.get("name", "Unknown") for t in applied_transforms]
    return f"✅ Image successfully augmented!\n\n🔧 Transforms applied: {', '.join(transform_names) if transform_names else 'None'}\n• Session ID: {returned_session_id}\n\nNote: File saving may have failed, but transformation was successful."


@mcp.tool()
def augment_image(
    image_path: str = "",
    image_b64: str = "",
    session_id: str = "",
    prompt: str = "",
    seed: int | None = None,
    preset: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Apply image augmentations using file path or base64 data.

    Args:
        image_path: Path to image file (preferred for large images to avoid base64 conversion)
        image_b64: Base64 encoded image data (for backward compatibility)
        session_id: Session ID from load_image_for_processing tool (for backward compatibility)
        prompt: Natural language description of desired augmentations (optional if preset is used)
        seed: Optional random seed for reproducible results
        preset: Optional preset name (segmentation, portrait, lowlight) to use instead of prompt
        output_dir: Directory to save output files (optional, defaults to ./outputs)

    IMPORTANT FOR ASSISTANTS:
    Use available resources to properly interpret user prompts before calling this tool:
    1. Use transforms_guide() and get_available_transforms_examples() to understand valid transforms
    2. Use list_available_presets() to see preset options
    3. Convert vague user language into specific transform terms from the available list
    4. If unsure, use validate_prompt() to test your interpretation before augmenting
    5. Prefer combining multiple specific transforms over vague descriptions

    Example: "make it look cool" → check resources → "add blur and increase contrast"

    Returns:
        Success message with file paths. All generated files are accessible via filesystem tools.
        Includes: augmented image path, original backup, metadata location, and full session folder.

    Note:
        Provide either image_path, image_b64, or session_id (in order of preference).
        Either prompt or preset must be provided, but not both.
        File path mode is recommended for large images to avoid memory issues.
    """
    # Validate request before processing
    valid, error = validate_mcp_request(
        "augment_image",
        session_id=session_id,
        prompt=prompt,
        seed=seed,
        preset=preset,
    )
    if not valid:
        return f"❌ Validation Error: {error}"

    try:
        # 1. Detect input mode and validate
        input_mode, error = _detect_input_mode(image_path, image_b64, session_id)
        if error:
            return f"❌ Error: {error}"

        # 2. Validate augmentation inputs
        valid, error = _validate_augmentation_inputs(prompt, preset)
        if not valid:
            return f"❌ Error: {error}"

        # 3. Load image based on input mode
        loaded_image_b64, error = _load_image_from_input(
            input_mode,
            image_path,
            image_b64,
            session_id,
        )
        if error:
            return f"❌ Error: {error}"

        # 4. Prepare processing prompt
        effective_prompt, error = _prepare_processing_prompt(prompt, preset)
        if error:
            return f"❌ Error: {error}"

        # 5. Generate session ID if not provided
        if not session_id or not session_id.strip():
            import uuid

            session_id = str(uuid.uuid4())[:8]

        # 6. Set up output directory
        if output_dir:
            import os

            os.environ["OUTPUT_DIR"] = output_dir

        # 7. Check pipeline status (hooks employed)
        pipeline = get_pipeline()
        status = pipeline.get_pipeline_status()
        if not status.get("registered_hooks"):
            return "❌ Error: Pipeline not ready - no hooks registered."

        # 8. Execute pipeline
        pipeline_result = _execute_pipeline(
            loaded_image_b64,
            effective_prompt,
            seed,
            session_id,
        )

        if pipeline_result["success"]:
            return _format_success_response(pipeline_result, session_id, input_mode)
        error_msg = pipeline_result.get("message", "Unknown error")
        return f"❌ Error: {error_msg}. Use validate_prompt tool to test your prompt or list_available_transforms tool to see available transforms."

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in augment_image: {e}")
        return f"❌ Error: Image augmentation failed due to unexpected error. Please try again or contact support. Details: {e!s}"


@mcp.tool()
def get_quick_transform_reference():
    """Get condensed list of transform keywords for quick assistant reference"""
    return {
        "blur_effects": ["blur", "gaussian blur", "motion blur"],
        "color_adjustments": ["brightness", "contrast", "hue", "saturation"],
        "geometric": ["rotate", "flip horizontal", "flip vertical"],
        "effects": ["noise", "grayscale", "enhance", "clahe"],
        "cropping": ["crop", "resize crop"],
        "presets": ["segmentation", "portrait", "lowlight"],
    }


@mcp.tool()
def list_available_transforms() -> dict:
    """List all available Albumentations transforms with descriptions.

    Returns:
        Dictionary containing available transforms and their descriptions
    """
    try:
        transforms_info = get_available_transforms()

        # Format for MCP response
        transforms_list = []
        for name, info in transforms_info.items():
            try:
                transforms_list.append(
                    {
                        "name": name,
                        "description": info.get(
                            "description",
                            f"Apply {name} transformation",
                        ),
                        "example_phrases": info.get("example_phrases", []),
                        "parameters": info.get("default_parameters", {}),
                        "parameter_ranges": info.get("parameter_ranges", {}),
                    },
                )
            except Exception as transform_error:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Skipping transform {name} due to error: {transform_error}",
                )
                continue

        return {
            "transforms": transforms_list,
            "total_count": len(transforms_list),
            "message": f"Found {len(transforms_list)} available transforms",
        }
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving transforms: {e}", exc_info=True)
        return {
            "transforms": [],
            "total_count": 0,
            "error": f"Failed to retrieve transforms: {e!s}",
            "message": "Error retrieving transforms. Please check logs for details.",
        }


@mcp.tool()
def validate_prompt(prompt: str) -> dict:
    """Validate and preview what transforms would be applied for a given prompt.

    Args:
        prompt: Natural language description of desired augmentations

    Returns:
        Dictionary with validation results and transform preview
    """
    # Validate request before processing
    valid, error = validate_mcp_request("validate_prompt", prompt=prompt)
    if not valid:
        return {
            "valid": False,
            "error": f"Validation Error: {error}",
            "transforms": [],
            "warnings": [],
            "suggestions": [],
            "message": f"Request validation failed: {error}",
        }

    try:
        # Use hook-integrated pipeline for validation
        # Using master async function to eliminate duplicate code
        from .utils import run_async_safely

        result = run_async_safely(parse_prompt_with_hooks, prompt)

        # Convert pipeline result to validation format
        return {
            "valid": result["success"] and len(result["transforms"]) > 0,
            "confidence": result["metadata"].get("parser_confidence", 0.0),
            "transforms_found": len(result["transforms"]),
            "transforms": result["transforms"],
            "warnings": result["warnings"],
            "suggestions": result["metadata"].get("parser_suggestions", []),
            "message": result["message"],
            "session_id": result["session_id"],
            "pipeline_metadata": result["metadata"],
        }
    except Exception as e:
        return {
            "valid": False,
            "confidence": 0.0,
            "transforms_found": 0,
            "transforms": [],
            "warnings": [f"Validation error: {e!s}"],
            "suggestions": ["Please check your prompt and try again"],
            "message": f"Validation failed: {e!s}",
        }


@mcp.tool()
def set_default_seed(seed: int | None = None) -> dict:
    """Set default seed for consistent reproducibility across all augment_image calls.

    This seed will be used for all future augment_image calls when no per-transform
    seed is provided. Persists until changed or cleared (for duration of MCP server process).

    Args:
        seed: Default seed value (0 to 4294967295), or None to clear default seed

    Returns:
        Dictionary with operation status and current default seed
    """
    # Validate request before processing
    valid, error = validate_mcp_request("set_default_seed", seed=seed)
    if not valid:
        return {
            "success": False,
            "error": f"Validation Error: {error}",
            "message": f"Request validation failed: {error}",
        }

    try:
        from .utils.seed_utils import get_global_seed, set_global_seed

        # Set the default seed (using global_seed internally)
        set_global_seed(seed)

        return {
            "success": True,
            "default_seed": get_global_seed(),
            "message": (
                f"Default seed set to {seed}"
                if seed is not None
                else "Default seed cleared"
            ),
            "note": "This seed will be used for all future augment_image calls unless overridden by per-transform seed",
        }
    except Exception as e:
        return {
            "success": False,
            "default_seed": None,
            "error": str(e),
            "message": f"Failed to set default seed: {e}",
        }


@mcp.tool()
def list_available_presets() -> dict:
    """List all available preset configurations.

    Returns:
        Dictionary containing available presets and their descriptions
    """
    try:
        presets_info = get_available_presets()

        # Format for MCP response
        presets_list = []
        for name, config in presets_info.items():
            presets_list.append(
                {
                    "name": name,
                    "display_name": config["name"],
                    "description": config["description"],
                    "use_cases": config.get("use_cases", []),
                    "transforms_count": len(config["transforms"]),
                    "transforms": config["transforms"],  # Include actual transforms
                    "metadata": config.get("metadata", {}),
                },
            )

        return {
            "presets": presets_list,
            "total_count": len(presets_list),
            "message": f"Found {len(presets_list)} available presets",
        }
    except Exception as e:
        return {
            "presets": [],
            "total_count": 0,
            "error": str(e),
            "message": f"Error retrieving presets: {e!s}",
        }


def _detect_image_source_type(image_source: str) -> str:
    """Detect the type of image source (url, file, base64)."""
    if image_source.startswith(("http://", "https://")):
        return "url"
    if image_source.startswith("data:image/") or (
        len(image_source) > 100
        and image_source.replace("=", "").replace("+", "").replace("/", "").isalnum()
    ):
        return "base64"
    return "file"


def _detect_input_mode(
    image_path: str,
    image_b64: str,
    session_id: str,
) -> tuple[str, str | None]:
    """Detect input mode and return (mode, error_message).

    Args:
        image_path: File path parameter
        image_b64: Base64 data parameter
        session_id: Session ID parameter

    Returns:
        Tuple of (mode, error_message) where mode is 'path', 'base64', or 'session'
    """
    # Count non-empty inputs
    inputs_provided = sum(
        [
            bool(image_path and image_path.strip()),
            bool(image_b64 and image_b64.strip()),
            bool(session_id and session_id.strip()),
        ],
    )

    if inputs_provided == 0:
        return "", "Must provide either image_path, image_b64, or session_id"

    if inputs_provided > 1:
        return "", "Provide only one of: image_path, image_b64, or session_id"

    if image_path and image_path.strip():
        return "path", None
    if image_b64 and image_b64.strip():
        return "base64", None
    if session_id and session_id.strip():
        return "session", None

    return "", "Invalid input parameters"


def _load_image_from_input(
    mode: str,
    image_path: str,
    image_b64: str,
    session_id: str,
) -> tuple[str | None, str | None]:
    """Load and preprocess image based on input mode. Returns (image_b64, error_message)."""
    if mode == "path":
        return _load_and_preprocess_from_file(image_path)
    if mode == "base64":
        return _load_and_preprocess_from_base64(image_b64)
    if mode == "session":
        return _load_session_image(session_id)
    return None, f"Unknown input mode: {mode}"


def _load_and_preprocess_from_file(
    image_path: str,
) -> tuple[str | None, str | None]:
    """Load image from file path, optionally resize, then return as base64.

    Behavior:
    - Always prefer decoding with PIL first, then validate dimensions/pixels.
    - In strict mode: reject oversized images with IMAGE_DIMENSIONS_TOO_LARGE.
    - In permissive mode: auto-resize to fit constraints, then encode once.
    - Error taxonomy: FILE_NOT_FOUND when path missing.
    """
    try:
        from pathlib import Path

        from PIL import Image

        from .config import (
            get_max_image_size,
            get_max_pixels_in,
            is_strict_mode,
        )
        from .image_conversions import pil_to_base64

        # Validate file exists early
        if not Path(image_path).exists():
            return None, f"FILE_NOT_FOUND: Image file not found: {image_path}"

        # Decode with PIL
        image = Image.open(image_path)
        image.load()

        # Determine constraints
        max_dim = get_max_image_size()
        max_pixels = get_max_pixels_in()

        width, height = image.size
        pixels = width * height
        oversized = width > max_dim or height > max_dim or pixels > max_pixels

        if oversized:
            if is_strict_mode():
                return (
                    None,
                    (
                        "IMAGE_DIMENSIONS_TOO_LARGE: "
                        f"{width}x{height} exceeds limits (max_dim={max_dim}, max_pixels={max_pixels:,})"
                    ),
                )
            image = _resize_image_smart(image, max_dim, max_pixels)

        # Choose compact encoding: JPEG for opaque, WEBP for alpha
        out_format = "WEBP" if (getattr(image, "mode", "").endswith("A")) else "JPEG"
        # Encode exactly once for downstream
        image_b64 = pil_to_base64(image, format=out_format, quality=85)
        return image_b64, None

    except Exception as e:
        return None, f"Failed to load image from file: {e}"


def _load_and_preprocess_from_base64(
    image_b64: str,
) -> tuple[str | None, str | None]:
    """Sanitize, decode, optionally resize, and re-encode base64 input.

    Behavior:
    - Light transport sanity check on base64 length to prevent DoS.
    - Sanitize and decode; invalid base64 → B64_INVALID.
    - In strict mode: reject oversized images with IMAGE_DIMENSIONS_TOO_LARGE.
    - In permissive mode: auto-resize using thumbnail-like logic, then re-encode once.
    - Error taxonomy includes: B64_INVALID, B64_INPUT_TOO_LARGE, IMAGE_DIMENSIONS_TOO_LARGE.
    """
    try:
        import base64
        import io

        from PIL import Image

        from .config import (
            get_max_bytes_in,
            get_max_image_size,
            get_max_pixels_in,
            is_strict_mode,
        )
        from .image_conversions import pil_to_base64
        from .utils.validation_utils import sanitize_base64_input

        # Transport sanity check before decode (very coarse)
        max_bytes = get_max_bytes_in()
        # Base64 expands ~4/3; reject only if clearly excessive to avoid DoS
        if len(image_b64 or "") > int(max_bytes * 2.0):
            return (
                None,
                (
                    "B64_INPUT_TOO_LARGE: Base64 input length exceeds transport cap "
                    f"(len={len(image_b64):,}, cap≈{int(max_bytes*2.0):,})"
                ),
            )

        # Sanitize and decode base64
        try:
            clean_b64 = sanitize_base64_input(image_b64)
        except Exception as e:
            return None, f"B64_INVALID: {e}"

        try:
            image_data = base64.b64decode(clean_b64, validate=True)
        except Exception as e:
            return None, f"B64_INVALID: Invalid base64 encoding ({e})"

        # Decode to PIL
        try:
            with io.BytesIO(image_data) as buffer:
                image = Image.open(buffer)
                image.load()
                image = image.copy()
        except Exception as e:
            return None, f"B64_INVALID: Unable to open image from base64 ({e})"

        # Validate/resize by dimensions and pixel count
        max_dim = get_max_image_size()
        max_pixels = get_max_pixels_in()

        width, height = image.size
        pixels = width * height
        oversized = width > max_dim or height > max_dim or pixels > max_pixels

        if oversized:
            if is_strict_mode():
                return (
                    None,
                    (
                        "IMAGE_DIMENSIONS_TOO_LARGE: "
                        f"{width}x{height} exceeds limits (max_dim={max_dim}, max_pixels={max_pixels:,})"
                    ),
                )
            image = _resize_image_smart(image, max_dim, max_pixels)

        # Choose compact encoding: JPEG for opaque, WEBP for alpha
        out_format = "WEBP" if (getattr(image, "mode", "").endswith("A")) else "JPEG"
        # Always return sanitized or re-encoded base64
        return pil_to_base64(image, format=out_format, quality=85), None

    except Exception as e:
        return None, f"Failed to load image from base64: {e}"


def _resize_image_smart(
    image: "Image.Image",
    max_dimension: int,
    max_pixels: int,
) -> "Image.Image":
    """Resize image to satisfy both max_dimension and max_pixels.

    Uses high-quality downscaling and preserves aspect ratio.
    """
    from math import sqrt

    from PIL import Image

    width, height = image.size
    if width <= 0 or height <= 0:
        return image

    # Compute scale to meet both constraints
    scale_dim = min(max_dimension / width, max_dimension / height, 1.0)
    pix_limit_scale = (
        sqrt(max_pixels / float(width * height)) if (width * height) > 0 else 1.0
    )
    scale = min(scale_dim, pix_limit_scale, 1.0)

    # If already within limits, return as-is
    if scale >= 1.0:
        return image

    new_w = max(int(width * scale), 32)
    new_h = max(int(height * scale), 32)

    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    resized.format = getattr(image, "format", None)
    return resized


def _create_session_directory(session_id: str) -> str:
    """Create session directory with proper structure and return path."""
    from pathlib import Path

    output_dir = os.getenv("OUTPUT_DIR", "outputs")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Reuse existing session directory if found (created by pipeline or prior tool)
    existing = sorted(
        [
            d
            for d in out_path.iterdir()
            if d.is_dir() and d.name.endswith(f"_{session_id}")
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if existing:
        session_dir = existing[0]
    else:
        # Create session directory with timestamp format: YYYYMMDD_HHMMSS_sessionID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir_name = f"{timestamp}_{session_id}"
        session_dir = out_path / session_dir_name
        session_dir.mkdir(parents=True, exist_ok=True)

    # Ensure tmp subdirectory exists
    tmp_dir = session_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    return str(session_dir)


@mcp.tool()
def load_image_for_processing(image_source: str) -> str:
    """Load image from URL, file path, or base64 and save it for processing.

    Args:
        image_source: Image source - URL, local file path, or base64 data

    Returns:
        Success message with session ID and saved image path
    """
    # Validate request before processing
    valid, error = validate_mcp_request(
        "load_image_for_processing",
        image_source=image_source,
    )
    if not valid:
        return f"❌ Validation Error: {error}"

    try:
        import uuid
        from pathlib import Path

        from .image_conversions import load_image_from_source

        # 1. Check input format
        source_type = _detect_image_source_type(image_source)

        # 2. Generate session ID
        session_id = str(uuid.uuid4())[:8]

        # 3. Create session directory with proper structure
        session_dir = _create_session_directory(session_id)

        # 4. Initialize temp_paths tracking
        temp_paths = []

        # 5. Load image (external function handles URL/file/base64 and saves temps)
        image = load_image_from_source(image_source, session_dir, temp_paths)

        # 6. Save original image
        image_filename = f"original_{session_id}.png"
        image_path = Path(session_dir) / image_filename
        image.save(image_path, format="PNG")

        return f"✅ Image loaded and saved successfully!\n\n📁 Session ID: {session_id}\n📄 Source type: {source_type}\n📄 Image saved: {image_path}\n📄 Temp files tracked: {len(temp_paths)}\n\n🔄 Use augment_image with session_id='{session_id}' to process this image."

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error loading image: {e}")
        return f"❌ Error: Failed to load image. Details: {e}"


@mcp.tool()
def get_pipeline_status() -> dict:
    """Get current pipeline status and registered hooks.

    Returns:
        Dictionary with pipeline status and hook information
    """
    try:
        pipeline = get_pipeline()
        return pipeline.get_pipeline_status()
    except Exception as e:
        return {
            "error": str(e),
            "message": f"Error getting pipeline status: {e!s}",
        }


# VLM Tools
@mcp.tool()
def check_vlm_config() -> dict:
    """Report VLM readiness without exposing secrets.

    Returns:
        { status, provider, model, config_path, api_key_present, source, suggestions }
    """
    try:
        cfg = load_vlm_config()
        enabled = bool(cfg.get("enabled", False))
        provider = cfg.get("provider") or ""
        model = cfg.get("model") or ""
        api_key_present = bool(cfg.get("api_key_present", False))
        source = cfg.get("source") or "none"
        config_path = cfg.get("config_path") or ""

        status = (
            "ready"
            if (enabled and provider and model and api_key_present)
            else ("partial" if enabled else "disabled")
        )

        suggestions: list[str] = []
        if not enabled:
            suggestions.append(
                "Set enabled=true in your VLM config file or ENABLE_VLM=true in env"
            )
        if not provider:
            suggestions.append("Set provider='google' in VLM config")
        if not model:
            suggestions.append("Set model, e.g. 'gemini-2.5-flash-image-preview'")
        if enabled and not api_key_present:
            suggestions.append(
                "Provide API key in config file (api_key) or set GOOGLE_API_KEY in env"
            )

        return {
            "status": status,
            "provider": provider,
            "model": model,
            "config_path": config_path,
            "api_key_present": api_key_present,
            "source": source,
            "suggestions": suggestions,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "suggestions": ["Verify your VLM_CONFIG_PATH and JSON format"],
        }


@mcp.tool()
def vlm_test_prompt(
    prompt: str,
    model: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Generate a single image from a prompt using Google Gemini preview.

    Notes:
    - Requires 'google-genai' package and a valid API key.
    - Saves image to a simple test folder under OUTPUT_DIR (vlm_tests).
    """
    try:
        cfg = load_vlm_config()
        if not cfg.get("enabled"):
            return {"success": False, "message": "VLM disabled. Enable in config."}

        provider = (cfg.get("provider") or "").lower()
        if provider != "google":
            return {
                "success": False,
                "message": f"Unsupported provider '{provider}'. Only 'google' is wired for MVP.",
            }

        # Resolve model and API key
        use_model = model or cfg.get("model") or "gemini-2.5-flash-image-preview"
        api_key = get_vlm_api_key()

        # Lazy import adapter to avoid import-time errors if deps missing
        from PIL import Image

        from .vlm.google_gemini import GoogleGeminiClient

        client = GoogleGeminiClient(model=use_model, api_key=api_key)

        # For MVP test, we don't use an input image; pass a tiny blank image placeholder
        temp_img = Image.new("RGB", (16, 16), color=(0, 0, 0))
        generated = client.apply(temp_img, prompt)

        # Save to OUTPUT_DIR/vlm_tests
        out_base = output_dir or os.getenv("OUTPUT_DIR", "outputs")
        from datetime import datetime
        from pathlib import Path

        tests_dir = Path(out_base) / "vlm_tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = tests_dir / f"gemini_preview_{ts}.png"
        generated.save(out_path)

        return {
            "success": True,
            "message": "Image generated",
            "model": use_model,
            "path": str(out_path.resolve()),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# MCP Prompt Templates
@mcp.prompt()
def compose_preset(base: str, tweak_note: str = "", output_format: str = "json") -> str:
    """Generate a policy skeleton based on presets with optional tweaks.

    Args:
        base: Base preset name (segmentation, portrait, lowlight)
        tweak_note: Optional description of desired modifications
        output_format: Output format (json, yaml, text)

    Returns:
        Structured prompt for creating augmentation policies
    """
    from .presets import get_preset

    preset_config = get_preset(base)
    if not preset_config:
        available_presets = ["segmentation", "portrait", "lowlight"]
        return f"Error: Unknown preset '{base}'. Available presets: {', '.join(available_presets)}"

    base_transforms = preset_config.get("transforms", [])

    prompt = f"""Create an image augmentation policy based on the '{base}' preset.

BASE PRESET: {base}
Description: {preset_config.get('description', 'No description available')}
Use cases: {', '.join(preset_config.get('use_cases', []))}

BASE TRANSFORMS:
"""

    for i, transform in enumerate(base_transforms, 1):
        prompt += f"{i}. {transform['name']}: {transform.get('parameters', {})}\n"

    if tweak_note:
        prompt += f"\nREQUESTED MODIFICATIONS:\n{tweak_note}\n"

    prompt += f"""
TASK: Generate a complete augmentation policy that:
1. Starts with the base preset transforms
2. Incorporates the requested modifications (if any)
3. Maintains compatibility with the original use case
4. Returns the result in {output_format} format

Please provide the augmentation policy with clear parameter values and explanations for any modifications made."""

    return prompt


@mcp.prompt()
def explain_effects(pipeline_json: str, image_context: str = "") -> str:
    """Generate plain-English critique/summary of any augmentation pipeline.

    Args:
        pipeline_json: JSON string containing the augmentation pipeline
        image_context: Optional context about the image type or use case

    Returns:
        Structured prompt for analyzing pipeline effects
    """
    try:
        import json

        pipeline_data = json.loads(pipeline_json)
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in pipeline_json parameter"

    transforms = pipeline_data.get("transforms", [])
    if not transforms:
        return "Error: No transforms found in pipeline"

    prompt = f"""Analyze this image augmentation pipeline and explain its effects in plain English.

PIPELINE TO ANALYZE:
{json.dumps(pipeline_data, indent=2)}
"""

    if image_context:
        prompt += f"\nIMAGE CONTEXT: {image_context}\n"

    prompt += """
ANALYSIS REQUIREMENTS:
1. Explain what each transform does in simple terms
2. Describe the combined visual effects
3. Identify potential benefits and drawbacks
4. Assess suitability for the given image context (if provided)
5. Suggest improvements or alternatives if needed

Please provide:
- Summary of overall effects
- Transform-by-transform breakdown
- Potential issues or concerns
- Recommendations for optimization"""

    return prompt


@mcp.prompt()
def augmentation_parser(
    user_prompt: str,
    available_transforms: list | None = None,
) -> str:
    """Parse natural language into Albumentations transforms.

    Args:
        user_prompt: Natural language description of desired augmentations
        available_transforms: Optional list of available transform names

    Returns:
        Structured prompt for parsing natural language to transforms
    """
    if available_transforms is None:
        from .parser import get_available_transforms

        transforms_info = get_available_transforms()
        available_transforms = list(transforms_info.keys())

    prompt = f"""Parse this natural language request into structured Albumentations transforms.

USER REQUEST: "{user_prompt}"

AVAILABLE TRANSFORMS:
{', '.join(available_transforms)}

PARSING GUIDELINES:
1. Identify specific augmentation requests in the user prompt
2. Map each request to appropriate Albumentations transforms
3. Extract or infer reasonable parameter values
4. Handle ambiguous requests with sensible defaults
5. Suggest alternatives for unsupported requests

OUTPUT FORMAT:
Provide a JSON structure with:
- transforms: List of transform objects with name, parameters, and probability
- confidence: Parsing confidence score (0.0-1.0)
- warnings: Any ambiguities or assumptions made
- suggestions: Alternative interpretations if applicable

Example output:
{{
  "transforms": [
    {{"name": "Blur", "parameters": {{"blur_limit": 7}}, "probability": 1.0}}
  ],
  "confidence": 0.9,
  "warnings": ["Using default blur intensity"],
  "suggestions": ["Consider specifying blur amount for more control"]
}}"""

    return prompt


@mcp.prompt()
def vision_verification(
    original_image_path: str,
    augmented_image_path: str,
    requested_transforms: str,
) -> str:
    """Generate prompt for vision model to verify augmentation results.

    Args:
        original_image_path: Path to the original image
        augmented_image_path: Path to the augmented image
        requested_transforms: Description of transforms that were applied

    Returns:
        Structured prompt for vision model analysis
    """
    prompt = f"""Compare these two images to verify that the requested augmentations were applied correctly.

ORIGINAL IMAGE: {original_image_path}
AUGMENTED IMAGE: {augmented_image_path}
REQUESTED TRANSFORMS: {requested_transforms}

VERIFICATION TASKS:
1. Compare the original and augmented images side by side
2. Identify visible changes between the images
3. Verify that the changes match the requested transforms
4. Rate the quality and appropriateness of the augmentations

EVALUATION CRITERIA:
- Accuracy: Do the changes match what was requested?
- Quality: Are the augmentations well-executed and natural-looking?
- Preservation: Are important image features preserved?
- Artifacts: Are there any unwanted distortions or artifacts?

RESPONSE FORMAT:
Provide your analysis in this structure:
- RATING: [1-5] (1=poor, 5=excellent)
- CHANGES_DETECTED: [List of specific visual changes observed]
- ACCURACY_ASSESSMENT: [How well changes match the request]
- QUALITY_NOTES: [Comments on augmentation quality]
- RECOMMENDATIONS: [Suggestions for improvement if needed]

Please be specific about what you observe and provide constructive feedback."""

    return prompt


@mcp.prompt()
def error_handler(error_type: str, error_message: str, user_context: str = "") -> str:
    """Generate user-friendly error messages and recovery suggestions.

    Args:
        error_type: Category of error (parsing, processing, validation, etc.)
        error_message: Technical error message
        user_context: Optional context about what the user was trying to do

    Returns:
        Structured prompt for generating helpful error responses
    """
    prompt = f"""Generate a user-friendly error message and recovery suggestions.

ERROR TYPE: {error_type}
TECHNICAL MESSAGE: {error_message}
"""

    if user_context:
        prompt += f"USER CONTEXT: {user_context}\n"

    prompt += """
REQUIREMENTS:
1. Explain the error in simple, non-technical terms
2. Provide specific steps the user can take to resolve it
3. Suggest alternatives if the original request isn't possible
4. Include relevant examples or documentation links if helpful

RESPONSE FORMAT:
- PROBLEM: [Clear explanation of what went wrong]
- SOLUTION: [Step-by-step recovery instructions]
- ALTERNATIVES: [Other approaches the user could try]
- EXAMPLES: [Helpful examples if applicable]

Keep the tone helpful and encouraging. Focus on getting the user back on track quickly."""

    return prompt


# MCP Resources
@mcp.tool()
@mcp.resource("file://getting_started_guide")
def get_getting_started_guide() -> str:
    """Getting started guide for first-time assistants.

    Returns structured JSON covering:
    - Workflow steps
    - Tool relationship map
    - Quick examples
    - Common patterns
    - Entry points by intent
    """

    guide = {
        "title": "Albumentations MCP — Getting Started",
        "version": "1.0",
        "workflow_steps": [
            {
                "step": 1,
                "title": "Pick input method",
                "description": "Use image_path directly with augment_image, or preload once with load_image_for_processing to get a session_id (recommended for large images).",
                "tools": ["augment_image", "load_image_for_processing"],
            },
            {
                "step": 2,
                "title": "Preview or choose transforms",
                "description": "Use validate_prompt to check a natural-language prompt, or browse transforms/presets via list_available_transforms, transforms_guide, available_transforms_examples, policy_presets, get_quick_transform_reference.",
                "tools": [
                    "validate_prompt",
                    "list_available_transforms",
                    "transforms_guide",
                    "available_transforms_examples",
                    "policy_presets",
                    "list_available_presets",
                    "get_quick_transform_reference",
                ],
            },
            {
                "step": 3,
                "title": "Run augmentation",
                "description": "Call augment_image with either a prompt or a preset (mutually exclusive). Optionally include seed or set a default via set_default_seed for reproducibility.",
                "tools": ["augment_image", "set_default_seed"],
            },
            {
                "step": 4,
                "title": "Inspect outputs",
                "description": "Check the session folder paths returned by augment_image for images, metadata, logs, and analysis.",
                "tools": ["augment_image", "get_pipeline_status"],
            },
        ],
        "tool_relationships": [
            {
                "tool": "load_image_for_processing",
                "purpose": "Preload an image (URL/file/base64) and save it under a session directory; returns session_id.",
                "use_when": "Working with large images or multiple successive operations on the same image.",
                "next": ["augment_image"],
                "inputs": ["image_source"],
                "outputs": ["session_id", "original image path"],
            },
            {
                "tool": "validate_prompt",
                "purpose": "Parse a natural-language prompt into transforms and show warnings.",
                "use_when": "You want to verify a prompt before running augmentation.",
                "next": ["augment_image"],
                "inputs": ["prompt"],
                "outputs": ["transforms", "confidence", "warnings"],
            },
            {
                "tool": "list_available_transforms",
                "purpose": "List supported transforms with defaults and parameter ranges.",
                "use_when": "Browsing capabilities or building structured prompts.",
                "next": ["validate_prompt", "augment_image"],
                "inputs": [],
                "outputs": ["transforms[]"],
            },
            {
                "tool": "transforms_guide",
                "purpose": "Comprehensive JSON guide of transforms (resource-style).",
                "use_when": "You need detailed reference data for planning transforms.",
                "next": ["validate_prompt", "augment_image"],
                "inputs": [],
                "outputs": ["json"],
            },
            {
                "tool": "available_transforms_examples",
                "purpose": "Practical examples and usage patterns grouped by category.",
                "use_when": "Looking for example phrasing and patterns.",
                "next": ["validate_prompt", "augment_image"],
                "inputs": [],
                "outputs": ["json"],
            },
            {
                "tool": "list_available_presets",
                "purpose": "Enumerate built-in presets.",
                "use_when": "You prefer preset-based pipelines.",
                "next": ["augment_image"],
                "inputs": [],
                "outputs": ["presets[]"],
            },
            {
                "tool": "policy_presets",
                "purpose": "Full preset configurations with transforms and metadata.",
                "use_when": "You need full JSON of preset policies.",
                "next": ["augment_image"],
                "inputs": [],
                "outputs": ["json"],
            },
            {
                "tool": "get_quick_transform_reference",
                "purpose": "Condensed keyword reference for quick prompting.",
                "use_when": "You want a short list of common transform keywords.",
                "next": ["validate_prompt", "augment_image"],
                "inputs": [],
                "outputs": ["keywords by category"],
            },
            {
                "tool": "augment_image",
                "purpose": "Main processing entry point; runs the pipeline.",
                "use_when": "You’re ready to apply transforms or a preset to an image.",
                "next": [],
                "inputs": [
                    "image_path | image_b64 | session_id",
                    "prompt | preset",
                    "seed?",
                    "output_dir?",
                ],
                "outputs": ["filesystem paths", "status string"],
            },
            {
                "tool": "set_default_seed",
                "purpose": "Set a default seed used by future augment_image calls.",
                "use_when": "You want reproducible results across runs.",
                "next": ["augment_image"],
                "inputs": ["seed?"],
                "outputs": ["default_seed"],
            },
            {
                "tool": "get_pipeline_status",
                "purpose": "Check pipeline health and which hooks are registered.",
                "use_when": "Diagnostics or capability checks.",
                "next": [],
                "inputs": [],
                "outputs": ["registered_hooks", "pipeline_version"],
            },
            {
                "tool": "troubleshooting_common_issues",
                "purpose": "Common errors and resolutions.",
                "use_when": "Recovery guidance after a failed run.",
                "next": ["validate_prompt", "augment_image"],
                "inputs": [],
                "outputs": ["json"],
            },
        ],
        "quick_examples": [
            {
                "name": "Quick blur + rotate via path",
                "calls": [
                    {
                        "tool": "augment_image",
                        "args": {
                            "image_path": "path/to/photo.jpg",
                            "prompt": "add gaussian blur and rotate 15 degrees",
                        },
                        "result": "Saves augmented image + metadata under outputs/<session>/",
                    },
                ],
            },
            {
                "name": "Use preset for segmentation",
                "calls": [
                    {
                        "tool": "augment_image",
                        "args": {
                            "image_path": "path/to/mask_image.png",
                            "preset": "segmentation",
                        },
                        "result": "Applies preset transforms and saves outputs.",
                    },
                ],
            },
            {
                "name": "Preload then process (large image)",
                "calls": [
                    {
                        "tool": "load_image_for_processing",
                        "args": {"image_source": "path/to/large.jpg"},
                        "result": "Returns session_id and stores original image.",
                    },
                    {
                        "tool": "augment_image",
                        "args": {
                            "session_id": "<returned>",
                            "prompt": "increase brightness and add noise",
                        },
                        "result": "Processes the preloaded image; outputs in the same session folder.",
                    },
                ],
            },
            {
                "name": "Process directly from URL",
                "calls": [
                    {
                        "tool": "load_image_for_processing",
                        "args": {"image_source": "https://example.com/image.jpg"},
                        "result": "Downloads and stores original image under a session; returns session_id.",
                    },
                    {
                        "tool": "augment_image",
                        "args": {
                            "session_id": "<returned>",
                            "prompt": "sharpen slightly and adjust saturation",
                        },
                        "result": "Applies transforms and writes all artifacts to the same session folder.",
                    },
                ],
            },
            {
                "name": "Preview prompt before running",
                "calls": [
                    {
                        "tool": "validate_prompt",
                        "args": {"prompt": "sharpen slightly and boost contrast"},
                        "result": "Returns transforms, confidence, and warnings.",
                    },
                ],
            },
        ],
        "common_patterns": [
            {
                "pattern": "Portrait enhancement",
                "approach": "Use preset 'portrait' or combine color + mild sharpening transforms.",
                "tools": [
                    "list_available_presets",
                    "policy_presets",
                    "augment_image",
                ],
            },
            {
                "pattern": "Low-light improvement",
                "approach": "Use preset 'lowlight' or increase brightness/contrast + CLAHE.",
                "tools": [
                    "list_available_presets",
                    "policy_presets",
                    "augment_image",
                ],
            },
            {
                "pattern": "Geometric tweaks",
                "approach": "rotate, flips, random scale; validate via validate_prompt then run augment_image.",
                "tools": [
                    "list_available_transforms",
                    "validate_prompt",
                    "augment_image",
                ],
            },
        ],
        "entry_points": [
            {
                "intent": "I want to augment an image now",
                "start_with": "augment_image",
                "notes": "Pass image_path and a simple prompt or a preset.",
            },
            {
                "intent": "I want to test prompts first",
                "start_with": "validate_prompt",
                "notes": "Then call augment_image with the refined prompt.",
            },
            {
                "intent": "I have a large image",
                "start_with": "load_image_for_processing",
                "notes": "Use returned session_id in augment_image.",
            },
            {
                "intent": "I need reproducible results",
                "start_with": "set_default_seed",
                "notes": "Then call augment_image; include per-call seed to override.",
            },
        ],
    }

    return json.dumps(guide, indent=2)


@mcp.tool()
@mcp.resource("file://transforms_guide")
def transforms_guide() -> str:
    """JSON of supported transforms, defaults, and parameter ranges (auto-generated from parser).

    Returns:
        Comprehensive guide to available transforms in JSON format
    """
    try:
        import json

        from .parser import get_available_transforms

        transforms_info = get_available_transforms()

        # Structure the data for easy consumption
        guide = {
            "metadata": {
                "total_transforms": len(transforms_info),
                "generated_at": "runtime",
                "version": "1.0",
            },
            "transforms": {},
        }

        for name, info in transforms_info.items():
            guide["transforms"][name] = {
                "description": info.get("description", f"Apply {name} transformation"),
                "example_phrases": info.get("example_phrases", []),
                "default_parameters": info.get("default_parameters", {}),
                "parameter_ranges": info.get("parameter_ranges", {}),
                "category": _get_transform_category(name),
            }

        return json.dumps(guide, indent=2)

    except Exception as e:
        error_response = {
            "error": f"Failed to generate transforms guide: {e}",
            "transforms": {},
            "metadata": {"total_transforms": 0},
        }
        return json.dumps(error_response, indent=2)


@mcp.tool()
@mcp.resource("file://policy_presets")
def policy_presets() -> str:
    """JSON of built-in presets: segmentation, portrait, lowlight.

    Returns:
        Complete preset configurations in JSON format
    """
    try:
        import json

        from .presets import get_available_presets

        presets_info = get_available_presets()

        # Structure the data with additional metadata
        policy_guide = {
            "metadata": {
                "total_presets": len(presets_info),
                "generated_at": "runtime",
                "version": "1.0",
            },
            "presets": {},
        }

        for name, config in presets_info.items():
            policy_guide["presets"][name] = {
                "display_name": config.get("name", name.title()),
                "description": config.get("description", f"{name.title()} preset"),
                "use_cases": config.get("use_cases", []),
                "transforms": config.get("transforms", []),
                "metadata": config.get("metadata", {}),
                "transform_count": len(config.get("transforms", [])),
                "recommended_for": _get_preset_recommendations(name),
            }

        return json.dumps(policy_guide, indent=2)

    except Exception as e:
        error_response = {
            "error": f"Failed to generate policy presets: {e}",
            "presets": {},
            "metadata": {"total_presets": 0},
        }
        return json.dumps(error_response, indent=2)


@mcp.tool()
@mcp.resource("file://available_transforms_examples")
def available_transforms_examples() -> str:
    """Available transforms with practical examples and usage patterns.

    Returns:
        Transform examples and usage patterns in JSON format
    """
    try:
        import json

        examples = {
            "metadata": {
                "description": "Practical examples and usage patterns for image augmentations",
                "version": "1.0",
            },
            "categories": {
                "blur_effects": {
                    "description": "Various blur transformations",
                    "examples": [
                        {
                            "prompt": "add slight blur",
                            "transforms": [
                                {
                                    "name": "Blur",
                                    "parameters": {"blur_limit": 3},
                                },
                            ],
                            "use_case": "Subtle image softening",
                        },
                        {
                            "prompt": "motion blur effect",
                            "transforms": [
                                {
                                    "name": "MotionBlur",
                                    "parameters": {"blur_limit": 7},
                                },
                            ],
                            "use_case": "Simulate camera movement",
                        },
                    ],
                },
                "color_adjustments": {
                    "description": "Color and lighting modifications",
                    "examples": [
                        {
                            "prompt": "increase brightness and contrast",
                            "transforms": [
                                {
                                    "name": "RandomBrightnessContrast",
                                    "parameters": {
                                        "brightness_limit": 0.2,
                                        "contrast_limit": 0.2,
                                    },
                                },
                            ],
                            "use_case": "Enhance image visibility",
                        },
                        {
                            "prompt": "adjust colors",
                            "transforms": [
                                {
                                    "name": "HueSaturationValue",
                                    "parameters": {
                                        "hue_shift_limit": 20,
                                        "sat_shift_limit": 30,
                                    },
                                },
                            ],
                            "use_case": "Color variation for training",
                        },
                    ],
                },
                "geometric_transforms": {
                    "description": "Spatial transformations",
                    "examples": [
                        {
                            "prompt": "rotate image",
                            "transforms": [
                                {
                                    "name": "Rotate",
                                    "parameters": {"limit": 45},
                                },
                            ],
                            "use_case": "Orientation variation",
                        },
                        {
                            "prompt": "flip horizontally",
                            "transforms": [
                                {
                                    "name": "HorizontalFlip",
                                    "parameters": {"p": 1.0},
                                },
                            ],
                            "use_case": "Mirror augmentation",
                        },
                    ],
                },
                "noise_and_artifacts": {
                    "description": "Noise and distortion effects",
                    "examples": [
                        {
                            "prompt": "add noise",
                            "transforms": [
                                {
                                    "name": "GaussNoise",
                                    "parameters": {"var_limit": (10.0, 50.0)},
                                },
                            ],
                            "use_case": "Simulate sensor noise",
                        },
                    ],
                },
            },
            "common_combinations": [
                {
                    "name": "Basic Data Augmentation",
                    "prompt": "flip and rotate with slight color changes",
                    "transforms": [
                        {"name": "HorizontalFlip", "parameters": {"p": 0.5}},
                        {"name": "Rotate", "parameters": {"limit": 15}},
                        {
                            "name": "RandomBrightnessContrast",
                            "parameters": {
                                "brightness_limit": 0.1,
                                "contrast_limit": 0.1,
                            },
                        },
                    ],
                },
                {
                    "name": "Photo Enhancement",
                    "prompt": "enhance contrast and reduce noise",
                    "transforms": [
                        {"name": "CLAHE", "parameters": {"clip_limit": 4.0}},
                        {
                            "name": "RandomBrightnessContrast",
                            "parameters": {"contrast_limit": 0.2},
                        },
                    ],
                },
            ],
        }

        return json.dumps(examples, indent=2)

    except Exception as e:
        error_response = {
            "error": f"Failed to generate transform examples: {e}",
            "categories": {},
            "metadata": {"description": "Error generating examples"},
        }
        return json.dumps(error_response, indent=2)


@mcp.tool()
@mcp.resource("file://preset_pipelines_best_practices")
def preset_pipelines_best_practices() -> str:
    """Best practices for creating and using augmentation presets.

    Returns:
        Best practices guide in JSON format
    """
    try:
        import json

        best_practices = {
            "metadata": {
                "title": "Augmentation Pipeline Best Practices",
                "version": "1.0",
                "last_updated": "2024",
            },
            "general_principles": {
                "preserve_semantics": {
                    "description": "Ensure augmentations don't change the fundamental meaning of the image",
                    "examples": [
                        "Don't over-rotate images with text",
                        "Preserve object boundaries for segmentation tasks",
                        "Maintain facial features for portrait recognition",
                    ],
                },
                "gradual_intensity": {
                    "description": "Start with mild augmentations and gradually increase intensity",
                    "recommendation": "Begin with probability 0.5 and small parameter ranges",
                },
                "domain_specific": {
                    "description": "Tailor augmentations to your specific use case",
                    "examples": [
                        "Medical images: Focus on contrast and noise",
                        "Natural scenes: Use geometric and color transforms",
                        "Documents: Minimize geometric distortions",
                    ],
                },
            },
            "preset_guidelines": {
                "segmentation": {
                    "focus": "Preserve object boundaries and spatial relationships",
                    "recommended_transforms": [
                        "HorizontalFlip",
                        "RandomBrightnessContrast",
                        "HueSaturationValue",
                    ],
                    "avoid": [
                        "Heavy rotation",
                        "Aggressive cropping",
                        "Strong distortions",
                    ],
                    "parameter_tips": "Use low intensity values (< 0.2) for color transforms",
                },
                "portrait": {
                    "focus": "Maintain facial features and natural appearance",
                    "recommended_transforms": [
                        "RandomBrightnessContrast",
                        "HueSaturationValue",
                        "Blur",
                    ],
                    "avoid": [
                        "Vertical flips",
                        "Heavy geometric distortions",
                        "Extreme color shifts",
                    ],
                    "parameter_tips": "Keep hue shifts minimal (< 10 degrees)",
                },
                "lowlight": {
                    "focus": "Enhance visibility while preserving details",
                    "recommended_transforms": [
                        "CLAHE",
                        "RandomBrightnessContrast",
                        "GaussNoise",
                    ],
                    "avoid": ["Further darkening", "High contrast reduction"],
                    "parameter_tips": "Use positive brightness limits and moderate contrast",
                },
            },
            "performance_tips": {
                "probability_tuning": "Use probabilities < 1.0 to create variation in your dataset",
                "parameter_ranges": "Define ranges rather than fixed values for more diversity",
                "pipeline_order": "Apply geometric transforms before photometric ones",
                "batch_consistency": "Use seeds for reproducible results during testing",
            },
            "common_mistakes": [
                {
                    "mistake": "Over-augmentation",
                    "description": "Applying too many or too intense transforms",
                    "solution": "Start simple and validate results visually",
                },
                {
                    "mistake": "Ignoring data distribution",
                    "description": "Not considering the original data characteristics",
                    "solution": "Analyze your dataset before choosing augmentations",
                },
                {
                    "mistake": "Fixed parameters",
                    "description": "Using the same parameters for all images",
                    "solution": "Use parameter ranges and probabilities for variation",
                },
            ],
        }

        return json.dumps(best_practices, indent=2)

    except Exception as e:
        error_response = {
            "error": f"Failed to generate best practices guide: {e}",
            "general_principles": {},
            "metadata": {"title": "Error generating guide"},
        }
        return json.dumps(error_response, indent=2)


@mcp.tool()
@mcp.resource("file://troubleshooting_common_issues")
def troubleshooting_common_issues() -> str:
    """Common issues and solutions for image augmentation.

    Returns:
        Troubleshooting guide in JSON format
    """
    try:
        import json

        troubleshooting = {
            "metadata": {
                "title": "Image Augmentation Troubleshooting Guide",
                "version": "1.0",
            },
            "common_issues": {
                "parsing_errors": {
                    "symptoms": [
                        "Prompt not recognized",
                        "No transforms applied",
                        "Unexpected results",
                    ],
                    "causes": [
                        "Ambiguous natural language",
                        "Unsupported transform names",
                        "Typos in prompt",
                    ],
                    "solutions": [
                        "Use specific transform names from the available list",
                        "Try the validate_prompt tool to test your request",
                        "Check spelling and use simple, clear language",
                        "Use presets for common augmentation patterns",
                    ],
                    "examples": [
                        "Instead of 'make it blurry', try 'add blur'",
                        "Instead of 'change colors', try 'adjust hue and saturation'",
                    ],
                },
                "image_quality_issues": {
                    "symptoms": [
                        "Artifacts in output",
                        "Loss of detail",
                        "Unnatural appearance",
                    ],
                    "causes": [
                        "Excessive parameter values",
                        "Incompatible transform combinations",
                        "Poor quality input image",
                    ],
                    "solutions": [
                        "Reduce transform intensity parameters",
                        "Use presets designed for your use case",
                        "Check input image quality and format",
                        "Apply transforms gradually and validate results",
                    ],
                },
                "performance_issues": {
                    "symptoms": [
                        "Slow processing",
                        "Memory errors",
                        "Timeouts",
                    ],
                    "causes": [
                        "Large image files",
                        "Complex transform pipelines",
                        "Resource limitations",
                    ],
                    "solutions": [
                        "Use file path input mode for large images",
                        "Resize images before processing if appropriate",
                        "Simplify transform pipelines",
                        "Process images in smaller batches",
                    ],
                },
                "reproducibility_issues": {
                    "symptoms": [
                        "Different results each time",
                        "Cannot recreate specific output",
                    ],
                    "causes": [
                        "Random seed not set",
                        "Non-deterministic transforms",
                        "Different processing environments",
                    ],
                    "solutions": [
                        "Use the seed parameter for consistent results",
                        "Set default seed with set_default_seed tool",
                        "Document transform parameters for reproduction",
                        "Use the same software versions",
                    ],
                },
            },
            "diagnostic_steps": [
                {
                    "step": 1,
                    "action": "Test with validate_prompt",
                    "description": "Verify your prompt is understood correctly",
                },
                {
                    "step": 2,
                    "action": "Check available transforms",
                    "description": "Use list_available_transforms to see supported operations",
                },
                {
                    "step": 3,
                    "action": "Try a preset",
                    "description": "Use a known-good preset to isolate issues",
                },
                {
                    "step": 4,
                    "action": "Simplify the request",
                    "description": "Start with a single transform and build up",
                },
                {
                    "step": 5,
                    "action": "Check logs",
                    "description": "Review error messages and warnings in the output",
                },
            ],
            "getting_help": {
                "documentation": "Check the transforms_guide resource tool for detailed parameter information",
                "examples": "Use available_transforms_examples resource for usage patterns",
                "presets": "Try policy_presets resource for pre-configured pipelines",
                "validation": "Always use validate_prompt before processing important images",
            },
        }

        return json.dumps(troubleshooting, indent=2)

    except Exception as e:
        error_response = {
            "error": f"Failed to generate troubleshooting guide: {e}",
            "common_issues": {},
            "metadata": {"title": "Error generating guide"},
        }
        return json.dumps(error_response, indent=2)


def _get_transform_category(transform_name: str) -> str:
    """Get category for a transform name."""
    blur_transforms = ["Blur", "MotionBlur", "GaussianBlur"]
    color_transforms = [
        "RandomBrightnessContrast",
        "HueSaturationValue",
        "CLAHE",
        "Normalize",
    ]
    geometric_transforms = [
        "Rotate",
        "HorizontalFlip",
        "VerticalFlip",
        "RandomCrop",
        "RandomResizedCrop",
    ]
    noise_transforms = ["GaussNoise"]

    if transform_name in blur_transforms:
        return "blur_effects"
    if transform_name in color_transforms:
        return "color_adjustments"
    if transform_name in geometric_transforms:
        return "geometric_transforms"
    if transform_name in noise_transforms:
        return "noise_and_artifacts"
    return "other"


def _get_preset_recommendations(preset_name: str) -> list[str]:
    """Get recommendations for when to use a preset."""
    recommendations = {
        "segmentation": [
            "Semantic segmentation tasks",
            "Instance segmentation",
            "Object detection training",
            "When preserving object boundaries is critical",
        ],
        "portrait": [
            "Face recognition systems",
            "Portrait photography enhancement",
            "Human pose estimation",
            "When maintaining facial features is important",
        ],
        "lowlight": [
            "Night vision applications",
            "Low-light photography enhancement",
            "Security camera footage",
            "When improving visibility is the goal",
        ],
    }
    return recommendations.get(preset_name, [])


def main():
    """Main entry point for the MCP server."""
    # Validate configuration on startup
    from .config import get_config_summary, validate_config_on_startup

    try:
        validate_config_on_startup()
        logger = logging.getLogger(__name__)
        logger.info("Starting albumentations-mcp server")
        logger.info(get_config_summary())
    except Exception as e:
        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the MCP server using stdio for Kiro integration
    mcp.run("stdio")


if __name__ == "__main__":
    main()
