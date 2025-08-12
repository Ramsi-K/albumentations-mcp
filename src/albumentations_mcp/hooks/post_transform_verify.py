#!/usr/bin/env python3
"""
Post-Transform Visual Verification Hook

This hook saves original and augmented images to temporary files and generates
a verification report that can be reviewed by the same LLM (Kiro, Claude Desktop)
that's using the MCP tools.

# File Summary
Hook that implements LLM-based visual verification by saving images to files
and generating structured reports for the VLM to review transformation success.

# TODO Tree
- [x] Hook Implementation
  - [x] Import dependencies and verification manager
  - [x] Implement execute function with proper signature
  - [x] Handle image saving and report generation
  - [x] Add error handling and graceful failure
- [x] Integration with Pipeline
  - [x] Extract images and metadata from context
  - [x] Generate unique session identifiers
  - [x] Save verification results to context
  - [x] Return proper hook result format
- [x] Quality Assurance
  - [x] Input validation and error handling
  - [x] Logging for debugging and monitoring
  - [x] Non-blocking operation (graceful failure)

# Code Review Notes
- PERFORMANCE: Hook should be fast and non-blocking
- ERROR HANDLING: Must not break pipeline if verification fails
- MEMORY: Efficient handling of image data
- LOGGING: Clear logging for debugging verification issues
"""

import logging

from ..verification import get_verification_manager
from . import BaseHook, HookContext, HookResult

logger = logging.getLogger(__name__)


class PostTransformVerifyHook(BaseHook):
    """
    Post-transform visual verification hook.

    Saves original and augmented images to temporary files and generates
    a verification report for LLM review.
    """

    def __init__(self):
        super().__init__("post_transform_verify", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute visual verification hook.

        Args:
            context: Hook context containing images and metadata

        Returns:
            Hook result with verification information
        """
        try:
            # Extract required data from context metadata
            original_image = context.metadata.get("original_image")
            augmented_image = context.metadata.get("augmented_image")
            prompt = context.original_prompt
            session_id = context.session_id

            # Validate required inputs
            if not original_image or not augmented_image:
                logger.warning("Visual verification skipped: missing images")
                context.warnings.append("Visual verification skipped: missing images")
                return HookResult(success=True, context=context)

            # Get verification manager
            verification_manager = get_verification_manager()

            # Save images for LLM review
            try:
                file_paths = verification_manager.save_images_for_review(
                    original_image,
                    augmented_image,
                    session_id,
                )
                logger.info(f"Saved verification images for session {session_id}")

            except Exception as e:
                logger.error(f"Failed to save verification images: {e}")
                context.errors.append(f"Image saving failed: {e!s}")
                return HookResult(success=True, context=context)  # Non-blocking failure

            # Generate verification report
            try:
                # Collect metadata for the report
                metadata = {
                    "session_id": session_id,
                    "processing_time": context.metadata.get("processing_time", 0),
                    "transforms_applied": len(
                        context.metadata.get("applied_transforms", []),
                    ),
                    "transforms_skipped": len(
                        context.metadata.get("skipped_transforms", []),
                    ),
                    "pipeline_version": context.metadata.get(
                        "pipeline_version",
                        "unknown",
                    ),
                    # Include seed information for debugging
                    "seed_used": context.metadata.get("seed_used", False),
                    "seed_value": context.metadata.get("seed_value", None),
                    "reproducible": context.metadata.get("reproducible", False),
                }

                # Add transform details if available
                applied_transforms = context.metadata.get("applied_transforms", [])
                if applied_transforms:
                    transform_names = [
                        t.get("name", "unknown") for t in applied_transforms
                    ]
                    metadata["applied_transform_names"] = ", ".join(transform_names)

                # Generate the verification report
                report_content = verification_manager.generate_verification_report(
                    file_paths,
                    prompt,
                    session_id,
                    metadata,
                )

                # Save the report to file
                report_path = verification_manager.save_verification_report(
                    report_content,
                    session_id,
                )

                # Add verification info to context metadata
                context.metadata["verification_files"] = file_paths
                context.metadata["verification_report_path"] = report_path
                context.metadata["verification_report_content"] = report_content

                logger.info(f"Generated verification report for session {session_id}")

            except Exception as e:
                logger.error(f"Failed to generate verification report: {e}")
                context.errors.append(f"Report generation failed: {e!s}")

                # Clean up images if report generation failed
                try:
                    verification_manager.cleanup_temp_files(list(file_paths.values()))
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to cleanup files after report error: {cleanup_error}",
                    )

                return HookResult(success=True, context=context)  # Non-blocking failure

            logger.debug(
                f"Visual verification completed successfully for session {session_id}",
            )
            return HookResult(success=True, context=context)

        except Exception as e:
            logger.error(f"Visual verification hook failed: {e}")
            context.errors.append(f"Hook execution failed: {e!s}")
            return HookResult(success=True, context=context)  # Non-blocking failure


# Create hook instance for registration
post_transform_verify_hook = PostTransformVerifyHook()
