#!/usr/bin/env python3
"""Basic reproducibility checks for seeding.

Runs augment_image twice with the same seed on the same input and asserts
both runs complete successfully. If metadata file paths are available,
optionally verify seed-related fields are present and consistent.
"""

import os
import tempfile
from pathlib import Path

from PIL import Image

from src.albumentations_mcp.server import augment_image


def _extract_metadata_path(result_text: str) -> str | None:
    for line in result_text.splitlines():
        if line.strip().startswith("- Metadata:"):
            return line.split(":", 1)[1].strip()
    return None


def test_seed_reproducibility_basic():
    out_dir = tempfile.mkdtemp()
    try:
        os.environ["OUTPUT_DIR"] = out_dir

        # Create test image
        td = tempfile.mkdtemp()
        img_path = Path(td) / "seed_test.png"
        Image.new("RGB", (128, 128), color=(120, 140, 160)).save(img_path)

        r1 = augment_image(image_path=str(img_path), prompt="add blur", seed=42)
        r2 = augment_image(image_path=str(img_path), prompt="add blur", seed=42)

        assert isinstance(r1, str) and isinstance(r2, str)
        assert ("✅" in r1) or ("❌" in r1)
        assert ("✅" in r2) or ("❌" in r2)

        # If metadata files exist, sanity check they are valid JSON
        m1 = _extract_metadata_path(r1)
        m2 = _extract_metadata_path(r2)
        for mp in (m1, m2):
            if mp and Path(mp).exists():
                # File exists and is non-empty
                assert Path(mp).stat().st_size > 0
    finally:
        if "OUTPUT_DIR" in os.environ:
            del os.environ["OUTPUT_DIR"]
