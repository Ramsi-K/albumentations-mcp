#!/usr/bin/env python3
"""
Dev convenience runner.

Allows: python main.py
This simply forwards to albumentations_mcp.server.main().
Not included in package distributions.
"""

from src.albumentations_mcp.server import main

if __name__ == "__main__":
    raise SystemExit(main())
