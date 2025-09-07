#!/usr/bin/env python3
"""Simple Gemini VLM smoke test.

Usage:
  uv run python scripts/vlm_smoke.py "your prompt here"

Requires:
  - google-genai installed (e.g., `uv add google-genai`)
  - VLM config set via VLM_CONFIG_PATH pointing to config/vlm.json

This script loads the VLM config, constructs the GoogleGeminiClient, generates
an image for the given prompt, and writes it to OUTPUT_DIR/vlm_tests.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

from albumentations_mcp.vlm.config import load_vlm_config, get_vlm_api_key
from albumentations_mcp.vlm.google_gemini import GoogleGeminiClient


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/vlm_smoke.py "<prompt>"')
        return 2

    prompt = sys.argv[1]

    cfg = load_vlm_config()
    if not cfg.get("enabled"):
        print("VLM disabled in config. Set enabled=true in your VLM config file.")
        return 1

    if (cfg.get("provider") or "").lower() != "google":
        print("Only provider 'google' is supported for this smoke test.")
        return 1

    model = cfg.get("model") or "gemini-2.5-flash-image-preview"
    api_key = get_vlm_api_key()

    client = GoogleGeminiClient(model=model, api_key=api_key)

    # Placeholder input image (not used for generation in this MVP)
    temp_img = Image.new("RGB", (16, 16), color=(0, 0, 0))
    out = client.apply(temp_img, prompt)

    out_dir = Path(os.getenv("OUTPUT_DIR", "outputs")) / "vlm_tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"gemini_preview_{ts}.png"
    out.save(out_path)
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
