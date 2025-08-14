#!/usr/bin/env python3
"""
Albumentations MCP Server

An MCP-compliant image augmentation server that bridges natural language
processing with computer vision using the Albumentations library.
"""

import asyncio

from mcp.server.fastmcp import FastMCP

from .parser import get_available_transforms
from .pipeline import get_pipeline, parse_prompt_with_hooks
from .presets import get_available_presets, get_preset

# Initialize FastMCP server
mcp = FastMCP("albumentations-mcp")


@mcp.tool()
def augment_image(
    image_b64: str,
    prompt: str = "",
    seed: int | None = None,
    preset: str | None = None,
) -> str:
    """Apply image augmentations based on natural language prompt or preset.

    Args:
        image_b64: Base64-encoded image data
        prompt: Natural language description of desired augmentations (optional if preset is used)
        seed: Optional random seed for reproducible results.
              When provided, ensures identical results across runs with same inputs.
              When omitted, Albumentations uses system randomness for varied results.
        preset: Optional preset name (segmentation, portrait, lowlight) to use instead of prompt

    Returns:
        Success message with file path where augmented image was saved

    Note:
        Either prompt or preset must be provided, but not both.
        Reproducibility requires identical inputs (image, prompt/preset, seed).
        The seed affects all random transforms like blur amounts, rotation angles,
        crop positions, noise levels, etc.
    """
    import asyncio

    from .image_utils import ImageConversionError, base64_to_pil

    try:
        # Validate input parameters
        prompt_provided = prompt and prompt.strip()
        preset_provided = preset and preset.strip()

        if not prompt_provided and not preset_provided:
            return "❌ Error: Either prompt or preset must be provided. Use validate_prompt tool to test prompts or list_available_presets tool to see available presets."

        if prompt_provided and preset_provided:
            # Log warning but prefer preset
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Both prompt and preset provided, using preset")

        # Convert base64 to PIL Image
        image = base64_to_pil(image_b64)

        # Handle preset or parse prompt
        if preset_provided:
            # Use preset configuration
            preset_config = get_preset(preset)
            if not preset_config:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Unknown preset: {preset}")
                return f"❌ Error: Preset '{preset}' not found. Use list_available_presets tool to see available presets."

            from .presets import preset_to_transforms

            transforms = preset_to_transforms(preset)
            if not transforms:
                return f"❌ Error: Preset '{preset}' contains no valid transforms. Use list_available_presets tool to see available presets."

            # Create a mock parse result for consistency
            parse_result = {
                "success": True,
                "transforms": transforms,
                "message": f"Using preset: {preset}",
                "warnings": [],
                "session_id": f"preset_{preset}_{int(__import__('time').time())}",
                "metadata": {
                    "preset_used": preset,
                    "preset_config": preset_config,
                },
            }
        else:
            # Parse prompt using hook-integrated pipeline
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in a running loop, we need to use a different approach
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            parse_prompt_with_hooks(prompt),
                        )
                        parse_result = future.result()
                else:
                    parse_result = asyncio.run(parse_prompt_with_hooks(prompt))
            except RuntimeError:
                parse_result = asyncio.run(parse_prompt_with_hooks(prompt))

        # Check if this was a preset request
        warnings = parse_result.get("warnings", [])
        preset_detected = any("Preset request detected:" in w for w in warnings)

        if preset_detected:
            # Extract preset name from warning
            preset_warning = next(
                w for w in warnings if "Preset request detected:" in w
            )
            detected_preset = preset_warning.split(": ")[1]

            # Load preset transforms
            from .presets import preset_to_transforms

            preset_transforms = preset_to_transforms(detected_preset)

            if preset_transforms:
                # Use preset transforms directly - bypass normal parsing
                effective_prompt = f"preset:{detected_preset}"

                # TODO: Apply preset transforms directly instead of going through pipeline
                # For now, let the pipeline handle it but it will show warnings

        elif not parse_result["success"] or not parse_result["transforms"]:
            # If parsing failed, return helpful error message
            error_msg = parse_result.get("message", "Could not parse prompt")
            return f"❌ Error: {error_msg}. Use validate_prompt tool to test your prompt or list_available_transforms tool to see available transforms."

        # Use full pipeline with all 7 hooks
        from .pipeline import process_image_with_hooks

        # Use the appropriate prompt for the pipeline
        effective_prompt = prompt if prompt_provided else f"apply {preset} preset"

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in a running loop, use thread executor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        process_image_with_hooks(image_b64, effective_prompt, seed),
                    )
                    pipeline_result = future.result()
            else:
                pipeline_result = asyncio.run(
                    process_image_with_hooks(image_b64, effective_prompt, seed),
                )
        except RuntimeError:
            pipeline_result = asyncio.run(
                process_image_with_hooks(image_b64, effective_prompt, seed),
            )

        if pipeline_result["success"]:
            # Always return success message - files should be saved by hooks
            file_paths = pipeline_result["metadata"].get("file_paths", {})
            session_id = pipeline_result.get("session_id", "unknown")

            if file_paths and "augmented_image" in file_paths:
                return f"✅ Image successfully augmented and saved!\n\n📁 Files saved:\n• Augmented image: {file_paths['augmented_image']}\n• Session ID: {session_id}\n\nUse the file path to access your augmented image."
            # Even if file saving failed, return success message with the actual transforms applied
            applied_transforms = (
                pipeline_result["metadata"]
                .get("processing_result", {})
                .get("applied_transforms", [])
            )
            transform_names = [t.get("name", "Unknown") for t in applied_transforms]
            return f"✅ Image successfully augmented!\n\n🔧 Transforms applied: {', '.join(transform_names) if transform_names else 'None'}\n• Session ID: {session_id}\n\nNote: File saving may have failed, but transformation was successful."
        # Pipeline failed
        import logging

        logger = logging.getLogger(__name__)
        error_msg = pipeline_result.get("message", "Unknown error")
        logger.error(f"Pipeline processing failed: {error_msg}")
        return f"❌ Error: {error_msg}. Use validate_prompt tool to test your prompt or list_available_transforms tool to see available transforms."

    except ImageConversionError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Image conversion error in augment_image: {e}")
        return f"❌ Error: Invalid image format or corrupted image data. Please provide a valid base64-encoded image. Details: {e!s}"
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
    try:
        # Use hook-integrated pipeline for validation
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        parse_prompt_with_hooks(prompt),
                    )
                    result = future.result()
            else:
                result = asyncio.run(parse_prompt_with_hooks(prompt))
        except RuntimeError:
            result = asyncio.run(parse_prompt_with_hooks(prompt))

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
    try:
        from .seed_manager import get_global_seed, set_global_seed

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
    # Run the MCP server using stdio for Kiro integration
    mcp.run("stdio")


if __name__ == "__main__":
    main()
