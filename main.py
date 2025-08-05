#!/usr/bin/env python3
"""
Albumentations MCP Server

An MCP-compliant image augmentation server that bridges natural language 
processing with computer vision using the Albumentations library.
"""

from mcp.server.fastmcp import FastMCP
import base64
from PIL import Image
import io
import albumentations as A
import numpy as np
from src.parser import parse_prompt, validate_prompt, get_available_transforms
from src.image_utils import base64_to_pil, pil_to_base64

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
                }
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
            "message": f"Error retrieving transforms: {str(e)}",
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
        return validate_prompt(prompt)
    except Exception as e:
        return {
            "valid": False,
            "confidence": 0.0,
            "transforms_found": 0,
            "transforms": [],
            "warnings": [f"Validation error: {str(e)}"],
            "suggestions": ["Please check your prompt and try again"],
            "message": f"Validation failed: {str(e)}",
        }


if __name__ == "__main__":
    # Run the MCP server using stdio for Kiro integration
    mcp.run("stdio")
