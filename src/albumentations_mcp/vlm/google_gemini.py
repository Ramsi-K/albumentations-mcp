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
        """Generate an edited image conditioned on the provided image.

        Behavior:
        - Sends the provided PIL image alongside the text prompt in the
          `contents` array to the Gemini preview model, matching the official
          SDK examples for image-conditioned edits.
        - Returns the first inline image from the response as a PIL Image.
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

        # Helper to extract first inline image from a response
        def _extract_image(resp) -> Image.Image | None:
            try:
                for cand in getattr(resp, "candidates", []) or []:
                    content = getattr(cand, "content", None)
                    parts = getattr(content, "parts", None) if content else None
                    if not parts:
                        continue
                    for part in parts:
                        inline = getattr(part, "inline_data", None)
                        if inline is not None and getattr(inline, "data", None):
                            data = inline.data
                            with BytesIO(data) as buf:
                                img = Image.open(buf)
                                img.load()
                                return img
            except Exception:
                return None
            return None

        # Attempt 1: follow working sample ordering [prompt, image]
        response = client.models.generate_content(
            model=self.model,
            contents=[prompt, image],
        )
        img = _extract_image(response)
        if img is not None:
            return img

        # Attempt 2 (fallback): try [image, prompt]
        response2 = client.models.generate_content(
            model=self.model,
            contents=[image, prompt],
        )
        img2 = _extract_image(response2)
        if img2 is not None:
            return img2

        # Collect debug info to aid prompts/model tuning
        def _summarize(resp) -> str:
            try:
                texts = []
                for cand in getattr(resp, "candidates", []) or []:
                    content = getattr(cand, "content", None)
                    for part in getattr(content, "parts", []) or []:
                        if getattr(part, "text", None):
                            texts.append(part.text[:120])
                return "; ".join(texts) if texts else ""
            except Exception:
                return ""

        text_hint = _summarize(response) or _summarize(response2)
        hint_msg = f" Hint: received text parts: {text_hint}" if text_hint else ""
        raise RuntimeError(
            "No image returned by Gemini model; check model name and prompt." + hint_msg
        )
