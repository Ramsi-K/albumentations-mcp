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

# Initialize FastMCP server
mcp = FastMCP("albumentations-mcp")


@mcp.tool()
def augment_image(image_b64: str, prompt: str) -> str:
    """Apply image augmentations based on natural language prompt.

    Args:
        image_b64: Base64-encoded image data
        prompt: Natural language description of desired augmentations

    Returns:
        Base64-encoded augmented image
    """
    # TODO: Implement in task 2-4
    # Convert base64 to PIL Image
    # Parse prompt and create transforms
    # Apply transforms
    # Convert back to base64
    return image_b64  # Placeholder - return original for now


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
            transforms_list.append(
                {
                    "name": name,
                    "description": info["description"],
                    "example_phrases": info["example_phrases"],
                    "parameters": info["default_parameters"],
                    "parameter_ranges": info["parameter_ranges"],
                },
            )

        return {
            "transforms": transforms_list,
            "total_count": len(transforms_list),
            "message": f"Found {len(transforms_list)} available transforms",
        }
    except Exception as e:
        return {
            "transforms": [],
            "total_count": 0,
            "error": str(e),
            "message": f"Error retrieving transforms: {e!s}",
        }


@mcp.tool()
def validate_prompt_tool(prompt: str) -> dict:
    """Validate and preview what transforms would be applied for a given prompt.

    Args:
        prompt: Natural language description of desired augmentations

    Returns:
        Dictionary with validation results and transform preview
    """
    try:
        # Use hook-integrated pipeline for validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(parse_prompt_with_hooks(prompt))
        finally:
            loop.close()

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
