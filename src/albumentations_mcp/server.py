#!/usr/bin/env python3
"""
Albumentations MCP Server

An MCP-compliant image augmentation server that bridges natural language
processing with computer vision using the Albumentations library.
"""


from mcp.server.fastmcp import FastMCP

from .parser import get_available_transforms
from .pipeline import get_pipeline, parse_prompt_with_hooks
from .presets import get_available_presets, get_preset

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
        validate_string_input,
        validate_numeric_range,
    )

    try:
        # Tool-specific validation using existing utilities
        if tool_name == "augment_image":
            if "image_path" in kwargs and kwargs["image_path"]:
                validate_string_input(
                    kwargs["image_path"], "image_path", max_length=1000
                )
            if "image_b64" in kwargs and kwargs["image_b64"]:
                validate_string_input(
                    kwargs["image_b64"], "image_b64", max_length=50000000
                )  # ~50MB base64
            if "session_id" in kwargs and kwargs["session_id"]:
                validate_string_input(kwargs["session_id"], "session_id", max_length=50)
            if "prompt" in kwargs and kwargs["prompt"]:
                validate_string_input(kwargs["prompt"], "prompt", max_length=1000)
            if "preset" in kwargs and kwargs["preset"]:
                validate_string_input(kwargs["preset"], "preset", max_length=50)
                if kwargs["preset"] not in [
                    "segmentation",
                    "portrait",
                    "lowlight",
                ]:
                    return (
                        False,
                        f"preset must be one of: segmentation, portrait, lowlight",
                    )
            if "seed" in kwargs and kwargs["seed"] is not None:
                validate_numeric_range(
                    kwargs["seed"], "seed", min_value=0, max_value=4294967295
                )
            if "output_dir" in kwargs and kwargs["output_dir"]:
                validate_string_input(
                    kwargs["output_dir"], "output_dir", max_length=500
                )

        elif tool_name == "validate_prompt":
            if "prompt" in kwargs:
                validate_string_input(kwargs["prompt"], "prompt", max_length=1000)

        elif tool_name == "set_default_seed":
            if "seed" in kwargs and kwargs["seed"] is not None:
                validate_numeric_range(
                    kwargs["seed"], "seed", min_value=0, max_value=4294967295
                )

        elif tool_name == "load_image_for_processing":
            if "image_source" in kwargs:
                validate_string_input(
                    kwargs["image_source"], "image_source", max_length=10000
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
    import os
    from pathlib import Path

    from PIL import Image

    from .image_conversions import pil_to_base64

    output_dir = os.getenv("OUTPUT_DIR", "outputs")
    session_dir = Path(output_dir) / f"session_{session_id}"

    if not session_dir.exists():
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
    pipeline_result: dict, session_id: str, input_mode: str = "session"
) -> str:
    """Format successful pipeline response."""
    file_paths = pipeline_result["metadata"].get("file_paths", {})
    returned_session_id = pipeline_result.get("session_id", session_id)

    if file_paths and "augmented_image" in file_paths:
        input_info = ""
        if input_mode == "file_path":
            input_info = "\n🔄 Input mode: File path (recommended for large images)"
        elif input_mode == "base64":
            input_info = "\n🔄 Input mode: Base64 data"
        elif input_mode == "session":
            input_info = "\n🔄 Input mode: Session (legacy)"

        return f"✅ Image successfully augmented and saved!{input_info}\n\n📁 Files saved:\n• Augmented image: {file_paths['augmented_image']}\n• Session ID: {returned_session_id}\n\nUse the file path to access your augmented image."

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

    Returns:
        Success message with file path where augmented image was saved

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
            input_mode, image_path, image_b64, session_id
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
    image_path: str, image_b64: str, session_id: str
) -> tuple[str, str | None]:
    """Detect input mode and return (mode, error_message).

    Args:
        image_path: File path parameter
        image_b64: Base64 data parameter
        session_id: Session ID parameter

    Returns:
        Tuple of (mode, error_message) where mode is 'file_path', 'base64', or 'session'
    """
    # Count non-empty inputs
    inputs_provided = sum(
        [
            bool(image_path and image_path.strip()),
            bool(image_b64 and image_b64.strip()),
            bool(session_id and session_id.strip()),
        ]
    )

    if inputs_provided == 0:
        return "", "Must provide either image_path, image_b64, or session_id"

    if inputs_provided > 1:
        return "", "Provide only one of: image_path, image_b64, or session_id"

    if image_path and image_path.strip():
        return "file_path", None
    elif image_b64 and image_b64.strip():
        return "base64", None
    elif session_id and session_id.strip():
        return "session", None

    return "", "Invalid input parameters"


def _load_image_from_input(
    mode: str, image_path: str, image_b64: str, session_id: str
) -> tuple[str | None, str | None]:
    """Load image based on input mode. Returns (image_b64, error_message)."""
    if mode == "file_path":
        try:
            from pathlib import Path
            from .image_conversions import (
                load_image_from_source,
                pil_to_base64,
            )

            # Validate file exists
            if not Path(image_path).exists():
                return None, f"Image file not found: {image_path}"

            # Load image from file path
            image = load_image_from_source(image_path)
            image_b64_data = pil_to_base64(image)
            return image_b64_data, None

        except Exception as e:
            return None, f"Failed to load image from file path: {e}"

    elif mode == "base64":
        # Validate base64 data
        try:
            from .image_conversions import base64_to_pil, pil_to_base64

            # Test conversion to ensure valid base64
            image = base64_to_pil(image_b64)
            return image_b64, None
        except Exception as e:
            return None, f"Invalid base64 image data: {e}"

    elif mode == "session":
        # Use existing session loading logic
        return _load_session_image(session_id)

    return None, f"Unknown input mode: {mode}"


def _create_session_directory(session_id: str) -> str:
    """Create session directory with proper structure and return path."""
    import os
    from datetime import datetime
    from pathlib import Path

    output_dir = os.getenv("OUTPUT_DIR", "outputs")

    # Create session directory with timestamp format: YYYYMMDD_HHMMSS_sessionID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir_name = f"{timestamp}_{session_id}"
    session_dir = Path(output_dir) / session_dir_name

    # Create main session directory and tmp subdirectory
    session_dir.mkdir(parents=True, exist_ok=True)
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
        "load_image_for_processing", image_source=image_source
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


def main():
    """Main entry point for the MCP server."""
    # Validate configuration on startup
    from .config import validate_config_on_startup, get_config_summary

    try:
        validate_config_on_startup()
        logger = logging.getLogger(__name__)
        logger.info("Starting albumentations-mcp server")
        logger.info(get_config_summary())
    except Exception as e:
        import sys

        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the MCP server using stdio for Kiro integration
    mcp.run("stdio")


if __name__ == "__main__":
    main()
