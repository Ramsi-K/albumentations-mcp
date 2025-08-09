#!/usr/bin/env python3
"""
Simple test to verify hook system functionality.
"""

import pytest
from src.albumentations_mcp.hooks import (
    HookContext,
    HookStage,
    get_hook_registry,
)


def test_hook_context_creation():
    """Test that HookContext can be created."""
    context = HookContext(session_id="test-123", original_prompt="add blur")

    assert context.session_id == "test-123"
    assert context.original_prompt == "add blur"
    assert isinstance(context.metadata, dict)
    assert isinstance(context.errors, list)
    assert isinstance(context.warnings, list)


def test_hook_registry_exists():
    """Test that hook registry can be accessed."""
    registry = get_hook_registry()
    hooks = registry.list_hooks()

    # Should have all expected stages
    expected_stages = [
        "pre_mcp",
        "post_mcp",
        "pre_transform",
        "post_transform",
        "post_transform_verify",
        "post_transform_classify",
        "pre_save",
        "post_save",
    ]

    for stage in expected_stages:
        assert stage in hooks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
