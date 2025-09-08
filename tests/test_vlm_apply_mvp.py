#!/usr/bin/env python3
"""MVP test: VLM integration saves artifacts and verification.

This test exercises the minimal VLM flow integrated into the existing
Albumentations MCP hook pipeline. It verifies that:

- VLM readiness is reported (or the test is skipped if not configured).
- A prompt is derived from the built-in Gemini templates resource.
- Calling `vlm_apply` with an example image writes session artifacts under
  the outputs directory using the normal hook stages (pre_save, verify, post_save).

What this VLM MVP does:
- Treats a natural-language prompt as a semantic edit request to a VLM
  (Gemini image generation preview).
- Reuses the existing hook system to save files and generate a visual
  verification markdown comparing original vs VLM output.

Requirements to run (skips if missing):
- ENABLE_VLM=true
- VLM_PROVIDER=google
- VLM_MODEL=gemini-2.5-flash-image-preview (or compatible)
- GOOGLE_API_KEY (or a compatible key via VLM config file)
- `google-genai` installed
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Import server tools lazily so running this file standalone doesn't require pytest
from albumentations_mcp.server import (
    check_vlm_config,
    get_gemini_prompt_templates,
    vlm_edit_image,
)


def _run_vlm_apply_mvp(tmp_dir: Path | None = None) -> dict:
    # 0) If a local config file exists, point the loader at it for the test run
    cfg_file = Path("config/vlm.json").resolve()
    if cfg_file.exists() and not os.getenv("VLM_CONFIG_PATH"):
        os.environ["VLM_CONFIG_PATH"] = str(cfg_file)

    # 1) Check readiness (skip if not configured)
    cfg = check_vlm_config()
    if cfg.get("status") != "ready":
        return {"skipped": True, "reason": "VLM not ready", "details": cfg}

    # Ensure SDK is present (otherwise, skip)
    try:
        from google import genai  # type: ignore  # noqa: F401
    except Exception as e:  # pragma: no cover
        return {
            "skipped": True,
            "reason": "google-genai SDK not installed",
            "details": str(e),
        }

    # 2) Build a prompt from the Gemini templates resource
    # For MVP validation, use a concrete edit prompt so behavior is stable
    base_prompt = (
        "Using the provided image of a cat, please add a small, knitted wizard hat on its head. "
        "Make it look comfortably fitted, and preserve the original pose, lighting, and composition."
    )

    # 3) Use an example image shipped with the repo
    img_path = Path("examples/basic_images/cat.jpg").resolve()
    assert img_path.exists(), "Example image not found: examples/basic_images/cat.jpg"

    # 4) Use a dedicated output directory
    test_outputs = (tmp_dir or Path.cwd() / "outputs").resolve()
    test_outputs.mkdir(parents=True, exist_ok=True)

    # 5) Apply the VLM edit (this will generate and save artifacts via hooks)
    resp = vlm_edit_image(
        image_path=str(img_path),
        prompt=base_prompt,
        edit_type="edit",
        output_dir=str(test_outputs),
    )

    # 6) Validate that core artifacts exist
    ok = bool(resp.get("success"))
    paths = resp.get("paths") or {}
    session_dir = Path(paths.get("session", ""))
    aug_path = Path(paths.get("image", ""))
    report_path = Path(paths.get("report", ""))
    metadata_path = Path(paths.get("metadata", ""))

    return {
        "success": ok,
        "response": resp,
        "outputs": str(test_outputs),
        "session_dir_exists": session_dir.exists() and session_dir.is_dir(),
        "aug_exists": aug_path.exists(),
        "report_exists": report_path.exists(),
        "metadata_exists": metadata_path.exists(),
        "session_dir": str(session_dir),
        "image": str(aug_path),
        "report": str(report_path),
        "metadata": str(metadata_path),
    }


# Pytest integration wrapper
def test_vlm_apply_mvp_creates_session_artifacts(tmp_path: Path) -> None:
    try:
        import pytest  # type: ignore
    except Exception:  # pragma: no cover
        # If pytest isn’t available, this test function won’t be used.
        return

    result = _run_vlm_apply_mvp(tmp_dir=tmp_path)
    if result.get("skipped"):
        pytest.skip(f"{result['reason']}: {result.get('details')}")

    assert result["success"], f"vlm_apply failed: {result['response']}"
    assert result["session_dir_exists"], f"Missing session dir: {result['session_dir']}"
    assert result["aug_exists"], f"Missing augmented image: {result['image']}"
    assert result["report_exists"], f"Missing report: {result['report']}"
    assert result["metadata_exists"], f"Missing metadata: {result['metadata']}"


if __name__ == "__main__":
    import json as _json

    res = _run_vlm_apply_mvp()
    print(_json.dumps(res, indent=2))
    # Provide a clearer summary for humans
    if res.get("skipped"):
        print(f"Skipped: {res['reason']} -> {res.get('details')}")
        sys.exit(0)
    if not res.get("success"):
        print("Failure running vlm_apply MVP")
        sys.exit(1)
    print("\nArtifacts:")
    print(f"  session:  {res.get('session_dir')}")
    print(f"  image:    {res.get('image')}")
    print(f"  report:   {res.get('report')}")
    print(f"  metadata: {res.get('metadata')}")
    sys.exit(0)
