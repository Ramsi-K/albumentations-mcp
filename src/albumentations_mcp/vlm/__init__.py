"""VLM (Vision Language Model) integration package.

This package houses adapters and configuration helpers for optional VLM-backed
semantic/contextual augmentations (e.g., Nano Banana / Gemini 2.5 Flash Image).

Networking and API usage are kept separate from core pipeline code and are
fully optional, enabled only when environment configuration is present.
"""

from . import config as _config  # noqa: F401

__all__ = [
    "_config",
]
