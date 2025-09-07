"""Base interfaces for VLM adapters.

Adapters should implement minimal methods for suggestion and application.
This keeps the MCP server decoupled from specific providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image


class VLMClient(ABC):
    """Abstract client for Vision-Language Model providers."""

    def __init__(self, provider: str, model: str, api_key: str | None = None):
        self.provider = provider
        self.model = model
        self._api_key = api_key

    @abstractmethod
    def apply(
        self,
        image: Image.Image,
        prompt_or_recipe: dict[str, Any] | str,
        *,
        seed: int | None = None,
        timeout: int | None = None,
    ) -> Image.Image:
        """Apply a semantic/contextual edit and return a PIL image.

        Implementations may choose to accept either a simple prompt (str)
        or a structured recipe (dict). This base method should handle both.
        """

    def suggest_recipe(
        self, image: Image.Image, task: str, constraints: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Optional: suggest a hybrid recipe. Default: not implemented."""
        raise NotImplementedError("suggest_recipe not implemented for this provider")
