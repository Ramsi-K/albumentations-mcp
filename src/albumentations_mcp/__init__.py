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

# Package metadata
from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path as _Path


def _detect_version() -> str:
    """Return the installed package version, or fall back to pyproject.

    - When installed (pip/uv/poetry), resolves via importlib.metadata.
    - In a source checkout without installation, attempts to read pyproject.toml.
    - Falls back to "0.0.0" if neither is available.
    """
    pkg_name = "albumentations-mcp"
    try:
        return _pkg_version(pkg_name)
    except PackageNotFoundError:
        # Try reading pyproject.toml in dev/source checkouts
        try:
            import tomllib  # Python 3.11+

            root = _Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                return data.get("project", {}).get("version", "0.0.0")
        except Exception:
            pass
        return "0.0.0"


__version__ = _detect_version()
__author__ = "Ramsi Kalia"
__email__ = "ramsi.kalia@gmail.com"
__description__ = "MCP-compliant image augmentation server using Albumentations"

# Package exports
from .image_conversions import base64_to_pil, pil_to_base64
from .parser import get_available_transforms, parse_prompt, validate_prompt
from .pipeline import get_pipeline, parse_prompt_with_hooks


# Lazy forwarder: avoid importing server on package import
def main() -> int | None:
    from .server import main as _server_main

    return _server_main()


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
