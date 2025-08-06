"""Pre-MCP hook for input sanitization and preprocessing."""

import logging
import re

from . import BaseHook, HookContext, HookResult

logger = logging.getLogger(__name__)


class PreMCPHook(BaseHook):
    """Hook for input sanitization and preprocessing before MCP parsing."""

    def __init__(self):
        super().__init__("pre_mcp_sanitization", critical=True)

    async def execute(self, context: HookContext) -> HookResult:
        """Sanitize and preprocess input before parsing."""
        try:
            logger.debug(f"Pre-MCP processing for session {context.session_id}")

            # Sanitize prompt
            sanitized_prompt = self._sanitize_prompt(context.original_prompt)
            if sanitized_prompt != context.original_prompt:
                logger.info(
                    f"Sanitized prompt: '{context.original_prompt}' -> '{sanitized_prompt}'",
                )
                context.original_prompt = sanitized_prompt
                context.metadata["prompt_sanitized"] = True

            # Validate prompt length
            if len(context.original_prompt) > 1000:
                context.warnings.append(
                    "Prompt is very long, consider shortening for better results",
                )

            # Add preprocessing metadata
            context.metadata.update(
                {
                    "pre_mcp_processed": True,
                    "prompt_length": len(context.original_prompt),
                    "prompt_word_count": len(context.original_prompt.split()),
                },
            )

            logger.debug("Pre-MCP processing completed successfully")
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Pre-MCP processing failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize the input prompt."""
        if not prompt or not isinstance(prompt, str):
            return ""

        # Remove excessive whitespace
        sanitized = re.sub(r"\s+", " ", prompt.strip())

        # Remove potentially harmful characters (basic sanitization)
        sanitized = re.sub(r'[<>"\']', "", sanitized)

        # Normalize common variations
        sanitized = sanitized.lower()

        return sanitized
