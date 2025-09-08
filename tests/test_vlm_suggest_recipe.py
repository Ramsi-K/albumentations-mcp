#!/usr/bin/env python3
"""Structure tests for vlm_suggest_recipe (planning-only).

This test validates the returned JSON shape without performing any
network calls or file writes. It is safe to run offline.

It is also runnable as a standalone script for quick checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from albumentations_mcp.server import vlm_suggest_recipe


def _validate_recipe_payload(payload: dict) -> list[str]:
    errors: list[str] = []

    # Core keys
    for key in ("recipe", "rationale", "execution_plan", "recipe_hash"):
        if key not in payload:
            errors.append(f"missing key: {key}")

    recipe = payload.get("recipe") or {}
    if not isinstance(recipe, dict):
        errors.append("recipe not a dict")
        return errors

    # Alb compose block shape
    alb = recipe.get("alb") or {}
    compose = alb.get("Compose") if isinstance(alb, dict) else None
    if not isinstance(compose, list):
        errors.append("alb.Compose missing or not a list")
    else:
        for i, item in enumerate(compose):
            if not isinstance(item, dict):
                errors.append(f"alb.Compose[{i}] not a dict")
                continue
            for k in ("name", "parameters", "probability"):
                if k not in item:
                    errors.append(f"alb.Compose[{i}] missing '{k}'")

    # Optional VLM block shape
    vlm = recipe.get("vlm")
    if vlm is not None:
        if not isinstance(vlm, dict) or "VLMEdit" not in vlm:
            errors.append("vlm.VLMEdit missing or malformed")
        else:
            edit = vlm["VLMEdit"]
            if not all(
                k in edit for k in ("prompt_template", "edit_type", "vlm_required")
            ):
                errors.append("VLMEdit missing required fields")

    # Hash looks plausible
    rh = payload.get("recipe_hash")
    if not isinstance(rh, str) or len(rh) < 8:
        errors.append("recipe_hash missing or too short")

    # Execution plan core keys
    plan = payload.get("execution_plan") or {}
    if not isinstance(plan, dict):
        errors.append("execution_plan not a dict")
    else:
        for k in ("order", "output_count", "seed_strategy"):
            if k not in plan:
                errors.append(f"execution_plan missing '{k}'")

    return errors


def test_vlm_suggest_recipe_structure_and_save(tmp_path: Path) -> None:
    # Enable save and write under a temp outputs dir to avoid polluting repo
    out_dir = tmp_path / "outputs_recipes"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = vlm_suggest_recipe(
        task="classification",
        constraints_json=json.dumps(
            {
                "photometric_strength": "mild",
                "output_count": 4,
                "identity_preserve": True,
                "avoid_ops": ["Rotate"],
            }
        ),
        save=True,
        output_dir=str(out_dir),
    )

    errors = _validate_recipe_payload(payload)
    assert not errors, f"Invalid recipe payload: {errors}\nPayload: {payload}"

    # Verify planning artifacts were saved
    p = payload.get("paths") or {}
    assert p, f"Expected saved paths in payload: {payload}"
    assert Path(p["dir"]).exists()
    assert Path(p["recipe"]).exists()
    assert Path(p["rationale"]).exists()
    assert Path(p["execution_plan"]).exists()
    assert Path(p["manifest"]).exists()


if __name__ == "__main__":
    result = vlm_suggest_recipe(
        task="domain_shift",
        constraints_json=json.dumps({"output_count": 3, "identity_preserve": True}),
    )
    print(json.dumps(result, indent=2))
    errs = _validate_recipe_payload(result)
    if errs:
        print("Errors:", errs)
        sys.exit(1)
    sys.exit(0)
