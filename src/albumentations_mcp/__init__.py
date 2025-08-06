"""
Albumentations MCP Server

An MCP-compliant image augmentation server that bridges natural language
processing with computer vision using the Albumentations library.

This package provides:
- Natural language to image augmentation translation
- MCP protocol compliance for seamless integration
- Comprehensive hook system for extensibility
- Vision model verification and classification consistency checking
"""

__version__ = "0.1.0"
__author__ = "Albumentations MCP Team"
__email__ = "support@albumentations-mcp.com"
__description__ = "MCP-compliant image augmentation server using Albumentations"

# Package exports
from .image_utils import base64_to_pil, pil_to_base64
from .parser import get_available_transforms, parse_prompt, validate_prompt
from .pipeline import get_pipeline, parse_prompt_with_hooks
from .server import main

__all__ = [
    "__author__",
    "__description__",
    "__email__",
    "__version__",
    "base64_to_pil",
    "get_available_transforms",
    "get_pipeline",
    "main",
    "parse_prompt",
    "parse_prompt_with_hooks",
    "pil_to_base64",
    "validate_prompt",
]
