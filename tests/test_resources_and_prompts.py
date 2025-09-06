#!/usr/bin/env python3
"""Tests for resource JSON endpoints and prompt generators.

Covers:
- transforms_guide, policy_presets, available_transforms_examples,
  troubleshooting_common_issues (JSON structure)
- compose_preset, explain_effects, augmentation_parser,
  vision_verification, error_handler (non-empty strings with key phrases)
"""

import json

from src.albumentations_mcp.server import (
    augmentation_parser,
    available_transforms_examples,
    compose_preset,
    error_handler,
    explain_effects,
    policy_presets,
    transforms_guide,
    troubleshooting_common_issues,
    vision_verification,
)


def test_resource_transforms_guide_json():
    data = json.loads(transforms_guide())
    assert "metadata" in data
    assert "transforms" in data


def test_resource_policy_presets_json():
    data = json.loads(policy_presets())
    assert "metadata" in data
    assert "presets" in data


def test_resource_available_transforms_examples_json():
    data = json.loads(available_transforms_examples())
    assert "metadata" in data
    assert "categories" in data


def test_resource_troubleshooting_json():
    data = json.loads(troubleshooting_common_issues())
    assert "metadata" in data
    assert "common_issues" in data


def test_prompt_compose_preset_text():
    text = compose_preset("portrait", "minor tweaks", "json")
    assert isinstance(text, str) and text
    assert "BASE PRESET:" in text or "BASE PRESET" in text


def test_prompt_explain_effects_text():
    pipeline_json = json.dumps({"transforms": [{"name": "Blur", "parameters": {}}]})
    text = explain_effects(pipeline_json, "portrait image")
    assert isinstance(text, str) and text
    assert "ANALYSIS REQUIREMENTS" in text or "Summary of" in text


def test_prompt_augmentation_parser_text():
    text = augmentation_parser("add blur and rotate")
    assert isinstance(text, str) and text
    assert "USER REQUEST" in text


def test_prompt_vision_verification_text():
    text = vision_verification("orig.png", "aug.png", "blur + rotate")
    assert isinstance(text, str) and text
    assert "ORIGINAL IMAGE" in text and "AUGMENTED IMAGE" in text


def test_prompt_error_handler_text():
    text = error_handler("processing", "B64_INVALID", "Uploading image via base64")
    assert isinstance(text, str) and text
    assert "RESPONSE FORMAT" in text or "PROBLEM:" in text
