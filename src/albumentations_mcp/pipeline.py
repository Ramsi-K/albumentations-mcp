"""Complete augmentation workflow orchestration with hook system integration."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from .hooks import (
    HookContext,
    HookStage,
    execute_stage,
    get_hook_registry,
    register_hook,
)
from .hooks.post_mcp import PostMCPHook
from .hooks.pre_mcp import PreMCPHook
from .parser import PromptParsingError, parse_prompt

logger = logging.getLogger(__name__)


class AugmentationPipeline:
    """Complete augmentation pipeline with hook system integration."""

    def __init__(self):
        """Initialize pipeline and register default hooks."""
        self._setup_default_hooks()

    def _setup_default_hooks(self):
        """Register default hooks for the pipeline."""
        registry = get_hook_registry()

        # Register pre-MCP hook
        register_hook(HookStage.PRE_MCP, PreMCPHook())

        # Register post-MCP hook
        register_hook(HookStage.POST_MCP, PostMCPHook())

        logger.info("Default hooks registered")

    async def parse_prompt_with_hooks(
        self,
        prompt: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Parse prompt using the complete hook system."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Initialize context
        context = HookContext(
            session_id=session_id,
            original_prompt=prompt,
            metadata={
                "timestamp": datetime.now(UTC).isoformat(),
                "pipeline_version": "1.0.0",
            },
        )

        logger.info(f"Starting prompt parsing pipeline for session {session_id}")

        try:
            # Stage 1: Pre-MCP processing
            result = await execute_stage(HookStage.PRE_MCP, context)
            if not result.success or not result.should_continue:
                return self._format_error_response(context, "Pre-MCP stage failed")
            context = result.context

            # Stage 2: Parse the prompt (core functionality)
            try:
                parse_result = parse_prompt(context.original_prompt)

                # Convert parser result to hook context format
                context.parsed_transforms = [
                    {
                        "name": transform.name.value,
                        "parameters": transform.parameters,
                        "probability": transform.probability,
                    }
                    for transform in parse_result.transforms
                ]

                # Add parser metadata
                context.metadata.update(
                    {
                        "parser_confidence": parse_result.confidence,
                        "parser_warnings": parse_result.warnings,
                        "parser_suggestions": parse_result.suggestions,
                    },
                )
                context.warnings.extend(parse_result.warnings)

            except PromptParsingError as e:
                error_msg = f"Prompt parsing failed: {e!s}"
                logger.error(error_msg)
                context.errors.append(error_msg)
                return self._format_error_response(context, error_msg)

            # Stage 3: Post-MCP processing
            result = await execute_stage(HookStage.POST_MCP, context)
            if not result.success:
                logger.warning("Post-MCP stage failed, but continuing")
            context = result.context

            # Format successful response
            response = self._format_success_response(context)
            logger.info(f"Pipeline completed successfully for session {session_id}")
            return response

        except Exception as e:
            error_msg = f"Pipeline execution failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            context.errors.append(error_msg)
            return self._format_error_response(context, error_msg)

    def _format_success_response(self, context: HookContext) -> dict[str, Any]:
        """Format successful pipeline response."""
        return {
            "success": True,
            "session_id": context.session_id,
            "transforms": context.parsed_transforms,
            "metadata": context.metadata,
            "warnings": context.warnings,
            "errors": context.errors,
            "message": f"Successfully parsed {len(context.parsed_transforms or [])} transforms",
        }

    def _format_error_response(
        self,
        context: HookContext,
        error: str,
    ) -> dict[str, Any]:
        """Format error pipeline response."""
        return {
            "success": False,
            "session_id": context.session_id,
            "transforms": context.parsed_transforms or [],
            "metadata": context.metadata,
            "warnings": context.warnings,
            "errors": context.errors,
            "message": error,
        }

    def get_pipeline_status(self) -> dict[str, Any]:
        """Get current pipeline status and registered hooks."""
        registry = get_hook_registry()
        return {
            "registered_hooks": registry.list_hooks(),
            "pipeline_version": "1.0.0",
            "supported_stages": [stage.value for stage in HookStage],
        }


# Global pipeline instance
_pipeline_instance = None


def get_pipeline() -> AugmentationPipeline:
    """Get global pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AugmentationPipeline()
    return _pipeline_instance


async def parse_prompt_with_hooks(
    prompt: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Convenience function to parse prompt with hooks."""
    return await get_pipeline().parse_prompt_with_hooks(prompt, session_id)
