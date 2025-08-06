#!/usr/bin/env python3
"""
Entry point for running albumentations-mcp as a module.

This allows the package to be run with:
- python -m albumentations_mcp
- uvx albumentations-mcp
"""

from .server import main

if __name__ == "__main__":
    main()
