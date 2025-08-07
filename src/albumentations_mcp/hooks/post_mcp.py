"""Post-MCP hook for JSON spec logging and validation."""

import json
import logging
from typing import Any

from . import BaseHook, HookContext, HookResult

logger = logging.getLogger(__name__)


class PostMCPHook(BaseHook):
    """Hook for JSON spec logging and validation after MCP parsing."""

    def __init__(self):
        super().__init__("post_mcp_validation", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """Log and validate the generated JSON spec."""
        try:
            logger.debug(
                f"Post-MCP processing for session {context.session_id}",
            )

            if not context.parsed_transforms:
                context.warnings.append(
                    "No transforms were parsed from the prompt",
                )
                return HookResult(success=True, context=context)

            # Validate transform specifications
            validation_result = self._validate_transforms(
                context.parsed_transforms,
            )
            if not validation_result["valid"]:
                context.warnings.extend(validation_result["warnings"])

            # Generate JSON spec for logging
            json_spec = self._generate_json_spec(context)

            # Log the JSON spec
            logger.info(
                f"Generated JSON spec: {json.dumps(json_spec, indent=2)}",
            )

            # Add to metadata
            context.metadata.update(
                {
                    "post_mcp_processed": True,
                    "json_spec": json_spec,
                    "transforms_count": len(context.parsed_transforms),
                    "validation_warnings": validation_result["warnings"],
                },
            )

            logger.debug("Post-MCP processing completed successfully")
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Post-MCP processing failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _validate_transforms(
        self,
        transforms: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validate the parsed transforms."""
        warnings = []

        for i, transform in enumerate(transforms):
            if not isinstance(transform, dict):
                warnings.append(f"Transform {i} is not a dictionary")
                continue

            if "name" not in transform:
                warnings.append(f"Transform {i} missing 'name' field")

            if "parameters" not in transform:
                warnings.append(f"Transform {i} missing 'parameters' field")
            elif not isinstance(transform["parameters"], dict):
                warnings.append(
                    f"Transform {i} parameters is not a dictionary",
                )

        return {"valid": len(warnings) == 0, "warnings": warnings}

    def _generate_json_spec(self, context: HookContext) -> dict[str, Any]:
        """Generate a complete JSON specification for the augmentation."""
        return {
            "session_id": context.session_id,
            "original_prompt": context.original_prompt,
            "transforms": context.parsed_transforms,
            "metadata": {
                "timestamp": context.metadata.get("timestamp"),
                "prompt_length": context.metadata.get("prompt_length"),
                "prompt_word_count": context.metadata.get("prompt_word_count"),
                "transforms_count": len(context.parsed_transforms or []),
            },
            "warnings": context.warnings,
            "errors": context.errors,
        }
