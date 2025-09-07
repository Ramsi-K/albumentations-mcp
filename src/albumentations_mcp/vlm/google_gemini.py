"""Google Gemini (2.5 Flash Image Preview) adapter.

Uses the `google-genai` SDK (https://pypi.org/project/google-genai/) to
generate an image from a text prompt and return it as a PIL Image.

Note: This is for the new Preview API surface (e.g.,
model="gemini-2.5-flash-image-preview").
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from .base import VLMClient


class GoogleGeminiClient(VLMClient):
    """Adapter for Google Gemini image generation."""

    def __init__(self, model: str, api_key: str | None = None):
        super().__init__(provider="google", model=model, api_key=api_key)

    def apply(
        self,
        image: Image.Image,
        prompt_or_recipe: dict[str, Any] | str,
        *,
        seed: int | None = None,
        timeout: int | None = None,
    ) -> Image.Image:
        """Generate an image for the given prompt.

        For MVP, this ignores the input image and treats `prompt_or_recipe` as a
        string prompt. Returning a generated PIL Image.
        """
        try:
            # Lazy import so server can start without dependency installed
            from google import genai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "google-genai SDK not installed. Install with `pip install google-genai`"
            ) from e

        prompt: str
        if isinstance(prompt_or_recipe, str):
            prompt = prompt_or_recipe
        elif isinstance(prompt_or_recipe, dict) and "prompt" in prompt_or_recipe:
            prompt = str(prompt_or_recipe.get("prompt", "")).strip()
        else:
            raise ValueError("prompt_or_recipe must be a string or dict with 'prompt'")

        # Construct client (api_key may be None; SDK will look to env if so)
        client = (
            genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
        )

        # Generate content
        response = client.models.generate_content(
            model=self.model,
            contents=[prompt],
        )

        # Find first inline image in parts
        candidate = response.candidates[0]
        for part in candidate.content.parts:
            if getattr(part, "inline_data", None) is not None:
                data = part.inline_data.data
                with BytesIO(data) as buf:
                    img = Image.open(buf)
                    img.load()
                    return img

        # If no image parts, try any text fallback (not expected for image model)
        raise RuntimeError(
            "No image returned by Gemini model; check model name and prompt"
        )
