"""Tests for hook system integration."""

import pytest
import asyncio
from src.albumentations_mcp.hooks import (
    HookContext,
    HookStage,
    get_hook_registry,
    register_hook,
)
from src.albumentations_mcp.hooks.pre_mcp import PreMCPHook
from src.albumentations_mcp.hooks.post_mcp import PostMCPHook
from src.albumentations_mcp.pipeline import (
    AugmentationPipeline,
    parse_prompt_with_hooks,
)


class TestHookSystem:
    """Test the hook system functionality."""

    def test_hook_registry_initialization(self):
        """Test that hook registry initializes correctly."""
        registry = get_hook_registry()
        hooks = registry.list_hooks()

        # Should have all stages
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

    @pytest.mark.asyncio
    async def test_pre_mcp_hook(self):
        """Test pre-MCP hook functionality."""
        hook = PreMCPHook()
        context = HookContext(
            session_id="test-123", original_prompt="  ADD BLUR  and  ROTATE  "
        )

        result = await hook.execute(context)

        assert result.success
        assert result.context.original_prompt == "add blur and rotate"
        assert result.context.metadata["pre_mcp_processed"] is True
        assert result.context.metadata["prompt_length"] > 0

    @pytest.mark.asyncio
    async def test_post_mcp_hook(self):
        """Test post-MCP hook functionality."""
        hook = PostMCPHook()
        context = HookContext(
            session_id="test-123",
            original_prompt="add blur",
            parsed_transforms=[
                {
                    "name": "Blur",
                    "parameters": {"blur_limit": 7, "p": 1.0},
                    "probability": 1.0,
                }
            ],
        )

        result = await hook.execute(context)

        assert result.success
        assert result.context.metadata["post_mcp_processed"] is True
        assert "json_spec" in result.context.metadata
        assert result.context.metadata["transforms_count"] == 1


class TestPipelineIntegration:
    """Test pipeline integration with hooks."""

    @pytest.mark.asyncio
    async def test_pipeline_with_hooks(self):
        """Test complete pipeline with hook integration."""
        result = await parse_prompt_with_hooks(
            "add blur and rotate by 30 degrees"
        )

        assert result["success"] is True
        assert len(result["transforms"]) == 2
        assert "session_id" in result
        assert "metadata" in result

        # Check that hooks were executed
        metadata = result["metadata"]
        assert metadata.get("pre_mcp_processed") is True
        assert metadata.get("post_mcp_processed") is True
        assert "parser_confidence" in metadata

    @pytest.mark.asyncio
    async def test_pipeline_with_invalid_prompt(self):
        """Test pipeline with invalid prompt."""
        result = await parse_prompt_with_hooks("")

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_pipeline_with_unrecognized_prompt(self):
        """Test pipeline with unrecognized prompt."""
        result = await parse_prompt_with_hooks("make it sparkly and magical")

        assert (
            result["success"] is True
        )  # Pipeline succeeds even with no transforms
        assert len(result["transforms"]) == 0
        assert len(result["warnings"]) > 0
        assert result["metadata"]["parser_confidence"] == 0.0

    def test_pipeline_status(self):
        """Test pipeline status reporting."""
        pipeline = AugmentationPipeline()
        status = pipeline.get_pipeline_status()

        assert "registered_hooks" in status
        assert "pipeline_version" in status
        assert "supported_stages" in status

        # Should have pre_mcp and post_mcp hooks registered
        hooks = status["registered_hooks"]
        assert len(hooks["pre_mcp"]) > 0
        assert len(hooks["post_mcp"]) > 0


class TestMCPToolsWithHooks:
    """Test MCP tools with hook integration."""

    def test_validate_prompt_tool_with_hooks(self):
        """Test validate_prompt_tool using hooks."""
        # Import here to avoid circular imports
        from src.albumentations_mcp.server import validate_prompt

        result = validate_prompt("add blur and increase contrast")

        assert result["valid"] is True
        assert result["transforms_found"] == 2
        assert "session_id" in result
        assert "pipeline_metadata" in result

        # Check hook execution metadata
        metadata = result["pipeline_metadata"]
        assert metadata.get("pre_mcp_processed") is True
        assert metadata.get("post_mcp_processed") is True

    def test_get_pipeline_status_tool(self):
        """Test get_pipeline_status tool."""
        from src.albumentations_mcp.server import get_pipeline_status

        result = get_pipeline_status()

        assert "registered_hooks" in result
        assert "pipeline_version" in result
        assert "supported_stages" in result


if __name__ == "__main__":
    pytest.main([__file__])
