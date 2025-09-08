#!/usr/bin/env python3
"""E2E test: suggest a recipe, then run a real VLM edit once.

Skips if VLM is not ready or google-genai is not installed. Writes a real
edited image + verification artifacts to outputs.

Runnable standalone for quick verification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from albumentations_mcp.server import (
    check_vlm_config,
    vlm_edit_image,
    vlm_suggest_recipe,
)


def _skip_reason() -> str | None:
    cfg = check_vlm_config()
    if cfg.get("status") != "ready":
        return f"VLM not ready: {cfg}"
    try:
        from google import genai  # type: ignore  # noqa: F401
    except Exception as e:  # pragma: no cover
        return f"google-genai SDK not available: {e}"
    return None


def test_recipe_to_vlm_edit(tmp_path: Path) -> None:
    reason = _skip_reason()
    if reason:
        import pytest  # type: ignore

        pytest.skip(reason)

    # 1) Suggest and save a recipe for domain shift
    out_dir = tmp_path / "outputs_recipe_e2e"
    out_dir.mkdir(parents=True, exist_ok=True)
    suggested = vlm_suggest_recipe(
        task="domain_shift",
        constraints_json=json.dumps({"output_count": 1, "identity_preserve": True}),
        save=True,
        output_dir=str(out_dir),
    )

    spaths = suggested.get("paths") or {}
    assert spaths, f"Expected saved plan paths: {suggested}"
    assert Path(spaths["dir"]).exists()
    assert Path(spaths["recipe"]).exists()
    assert Path(spaths["rationale"]).exists()
    assert Path(spaths["execution_plan"]).exists()
    assert Path(spaths["manifest"]).exists()

    # 2) Use a hardened, explicit edit prompt for reliability (no text output)
    filled_prompt = (
        "Generate and return only an edited image (no text). "
        "Using the provided photograph of a cat, add a small, knitted wizard hat that sits naturally on its head. "
        "Match the original lighting and perspective; preserve the subject's identity, pose, and composition. "
        "Photorealistic look, natural colors."
    )

    # 3) Run a real VLM edit once
    img_path = Path("examples/basic_images/cat.jpg").resolve()
    resp = vlm_edit_image(
        image_path=str(img_path),
        prompt=filled_prompt,
        edit_type="edit",
        output_dir=str(out_dir),
    )

    assert resp.get("success"), f"vlm_edit_image failed: {resp}"
    paths = resp.get("paths") or {}
    assert Path(paths.get("session", "")).exists()
    assert Path(paths.get("image", "")).exists()
    assert Path(paths.get("report", "")).exists()
    assert Path(paths.get("metadata", "")).exists()


if __name__ == "__main__":
    reason = _skip_reason()
    if reason:
        print(reason)
        sys.exit(0)

    # Save the suggested recipe to outputs/recipes for inspection
    result = vlm_suggest_recipe(
        task="domain_shift",
        constraints_json=json.dumps({"output_count": 1, "identity_preserve": True}),
        save=True,
        output_dir=str(Path("outputs").resolve()),
    )
    print("Suggested recipe (saved):\n", json.dumps(result, indent=2))
    spaths = result.get("paths") or {}
    if spaths:
        print("Saved plan dir:", spaths.get("dir"))
        print("Recipe file:", spaths.get("recipe"))

    # Execute once
    img = Path("examples/basic_images/cat.jpg").resolve()
    # Use a hardened prompt to reduce text-only replies
    hardened_prompt = (
        "Generate and return only an edited image (no text). "
        "Using the provided photograph of a cat, add a small, knitted wizard hat that sits naturally on its head. "
        "Match the original lighting and perspective; preserve the subject's identity, pose, and composition. "
        "Photorealistic look, natural colors."
    )
    resp = vlm_edit_image(
        image_path=str(img),
        prompt=hardened_prompt,
        edit_type="edit",
        output_dir=str(Path("outputs").resolve()),
    )
    print("Execution result:\n", json.dumps(resp, indent=2))
    sys.exit(0 if resp.get("success") else 1)
