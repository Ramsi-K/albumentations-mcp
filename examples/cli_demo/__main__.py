#!/usr/bin/env python3
"""
Module entry point for the CLI demo.

Run as a module from the repo root:

    python -m examples.cli_demo --help
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
