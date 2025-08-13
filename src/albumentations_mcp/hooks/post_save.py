"""Post-save hook for follow-up actions and cleanup.

This hook logs completion status and file locations, cleans up temporary
files and resources, and performs final housekeeping tasks.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from . import BaseHook, HookContext, HookResult

logger = logging.getLogger(__name__)


class PostSaveHook(BaseHook):
    """Hook for follow-up actions and cleanup after saving."""

    def __init__(self):
        super().__init__("post_save_cleanup", critical=False)

    async def execute(self, context: HookContext) -> HookResult:
        """Perform follow-up actions and cleanup after saving."""
        try:
            logger.debug(f"Post-save cleanup for session {context.session_id}")

            # Log completion status and file locations
            completion_info = self._log_completion_status(context)

            # Generate final summary report
            summary_report = self._generate_summary_report(context)

            # Clean up temporary files and resources
            cleanup_info = self._cleanup_temporary_resources(context)

            # Perform final validation of saved files
            validation_info = self._validate_saved_files(context)

            # Generate completion manifest
            manifest_info = self._generate_completion_manifest(context)

            # Add all information to context metadata
            context.metadata.update(
                {
                    "post_save_processed": True,
                    "completion_info": completion_info,
                    "summary_report": summary_report,
                    "cleanup_info": cleanup_info,
                    "validation_info": validation_info,
                    "manifest_info": manifest_info,
                    "pipeline_completed": True,
                },
            )

            logger.info(
                f"Post-save cleanup completed for session {context.session_id}",
            )
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Post-save cleanup failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _log_completion_status(self, context: HookContext) -> dict[str, Any]:
        """Log detailed completion status and file locations."""
        completion_info = {
            "session_id": context.session_id,
            "completion_timestamp": None,
            "files_created": [],
            "files_failed": [],
            "total_files": 0,
            "success_rate": 0.0,
        }

        try:
            import time

            completion_info["completion_timestamp"] = time.time()

            # Get file paths from metadata
            file_paths = context.metadata.get("output_files", {})
            completion_info["total_files"] = len(file_paths)

            # Check which files were actually created
            for file_type, file_path in file_paths.items():
                if Path(file_path).exists():
                    file_info = {
                        "type": file_type,
                        "path": file_path,
                        "size": Path(file_path).stat().st_size,
                        "created": True,
                    }
                    completion_info["files_created"].append(file_info)
                    logger.info(
                        f"Successfully created {file_type}: {file_path}",
                    )
                else:
                    file_info = {
                        "type": file_type,
                        "path": file_path,
                        "created": False,
                        "reason": "File not found after save operation",
                    }
                    completion_info["files_failed"].append(file_info)
                    logger.warning(
                        f"Failed to create {file_type}: {file_path}",
                    )

            # Calculate success rate
            if completion_info["total_files"] > 0:
                completion_info["success_rate"] = (
                    len(completion_info["files_created"])
                    / completion_info["total_files"]
                )

            # Log overall status
            if completion_info["success_rate"] == 1.0:
                logger.info(
                    f"All files created successfully for session {context.session_id}",
                )
            elif completion_info["success_rate"] > 0.5:
                logger.warning(
                    f"Partial success for session {context.session_id}: "
                    f"{completion_info['success_rate']:.1%} files created",
                )
            else:
                logger.error(
                    f"Most files failed for session {context.session_id}: "
                    f"only {completion_info['success_rate']:.1%} files created",
                )

        except Exception as e:
            logger.error(f"Error logging completion status: {e}")
            completion_info["error"] = str(e)

        return completion_info

    def _generate_summary_report(self, context: HookContext) -> dict[str, Any]:
        """Generate comprehensive summary report of the entire pipeline."""
        summary = {
            "session_summary": {
                "session_id": context.session_id,
                "original_prompt": context.original_prompt,
                "processing_success": len(context.errors) == 0,
                "warnings_count": len(context.warnings),
                "errors_count": len(context.errors),
            },
            "processing_summary": {},
            "output_summary": {},
            "performance_summary": {},
        }

        try:
            # Extract processing information
            if "processing_statistics" in context.metadata:
                stats = context.metadata["processing_statistics"]
                summary["processing_summary"] = {
                    "transforms_requested": stats.get(
                        "transforms_requested",
                        0,
                    ),
                    "transforms_applied": stats.get("transforms_applied", 0),
                    "success_rate": stats.get("success_rate", 0.0),
                    "processing_status": stats.get(
                        "processing_status",
                        "unknown",
                    ),
                }

            # Extract output information
            if "output_files" in context.metadata:
                file_paths = context.metadata["output_files"]
                summary["output_summary"] = {
                    "total_files_planned": len(file_paths),
                    "output_directory": (
                        str(Path(list(file_paths.values())[0]).parent.parent)
                        if file_paths
                        else None
                    ),
                    "file_types": list(file_paths.keys()),
                }

            # Extract performance information
            if "timing_data" in context.metadata:
                timing = context.metadata["timing_data"]
                summary["performance_summary"] = {
                    "processing_time": timing.get("processing_time"),
                    "performance_rating": timing.get(
                        "performance_metrics",
                        {},
                    ).get("performance_rating"),
                    "time_per_transform": timing.get(
                        "performance_metrics",
                        {},
                    ).get("time_per_transform"),
                }

            # Add quality assessment
            if "quality_metrics" in context.metadata:
                quality = context.metadata["quality_metrics"]
                summary["quality_summary"] = {
                    "comparison_available": quality.get(
                        "comparison_available",
                        False,
                    ),
                    "size_preserved": quality.get("size_change", {}).get(
                        "area_change",
                        0,
                    )
                    == 0,
                    "format_preserved": quality.get("format_preserved", True),
                }

            logger.info(
                f"Generated summary report for session {context.session_id}",
            )

        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            summary["error"] = str(e)

        return summary

    def _cleanup_temporary_resources(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Clean up temporary files and resources."""
        cleanup_info = {
            "temp_files_cleaned": [],
            "temp_dirs_cleaned": [],
            "memory_released": False,
            "cleanup_errors": [],
        }

        try:
            # Clean up any temporary files that might have been created
            temp_dir = Path(tempfile.gettempdir())
            session_pattern = f"*{context.session_id[:8]}*"

            # Look for temporary files related to this session
            temp_files = list(temp_dir.glob(session_pattern))
            for temp_file in temp_files:
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                        cleanup_info["temp_files_cleaned"].append(
                            str(temp_file),
                        )
                        logger.debug(f"Cleaned up temporary file: {temp_file}")
                    elif temp_file.is_dir():
                        import shutil

                        shutil.rmtree(temp_file)
                        cleanup_info["temp_dirs_cleaned"].append(
                            str(temp_file),
                        )
                        logger.debug(
                            f"Cleaned up temporary directory: {temp_file}",
                        )
                except Exception as e:
                    cleanup_info["cleanup_errors"].append(
                        {"file": str(temp_file), "error": str(e)},
                    )
                    logger.warning(f"Failed to clean up {temp_file}: {e}")

            # Force garbage collection to release memory
            import gc

            gc.collect()
            cleanup_info["memory_released"] = True

            # Clean up any large objects from context metadata
            if "processing_result" in context.metadata:
                # Remove large image arrays from metadata to free memory
                result = context.metadata["processing_result"]
                if isinstance(result, dict) and "augmented_image" in result:
                    # Keep metadata but remove large image data
                    result["augmented_image"] = "<removed_for_memory_cleanup>"

            logger.debug(
                f"Cleanup completed: {len(cleanup_info['temp_files_cleaned'])} files, "
                f"{len(cleanup_info['temp_dirs_cleaned'])} directories",
            )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            cleanup_info["cleanup_errors"].append({"general_error": str(e)})

        return cleanup_info

    def _validate_saved_files(self, context: HookContext) -> dict[str, Any]:
        """Perform final validation of saved files."""
        validation_info = {
            "files_validated": [],
            "validation_errors": [],
            "total_size": 0,
            "all_files_valid": True,
        }

        try:
            file_paths = context.metadata.get("output_files", {})

            for file_type, file_path in file_paths.items():
                file_validation = {
                    "type": file_type,
                    "path": file_path,
                    "exists": False,
                    "readable": False,
                    "size": 0,
                    "valid": False,
                }

                try:
                    path_obj = Path(file_path)

                    if path_obj.exists():
                        file_validation["exists"] = True
                        file_validation["size"] = path_obj.stat().st_size
                        validation_info["total_size"] += file_validation[
                            "size"
                        ]

                        # Check if file is readable
                        if os.access(path_obj, os.R_OK):
                            file_validation["readable"] = True

                            # Perform basic content validation
                            if self._validate_file_content(
                                path_obj,
                                file_type,
                            ):
                                file_validation["valid"] = True
                            else:
                                validation_info["validation_errors"].append(
                                    {
                                        "file": file_path,
                                        "error": "Content validation failed",
                                    },
                                )
                                validation_info["all_files_valid"] = False
                        else:
                            validation_info["validation_errors"].append(
                                {
                                    "file": file_path,
                                    "error": "File not readable",
                                },
                            )
                            validation_info["all_files_valid"] = False
                    else:
                        validation_info["validation_errors"].append(
                            {
                                "file": file_path,
                                "error": "File does not exist",
                            },
                        )
                        validation_info["all_files_valid"] = False

                except Exception as e:
                    validation_info["validation_errors"].append(
                        {
                            "file": file_path,
                            "error": f"Validation exception: {e}",
                        },
                    )
                    validation_info["all_files_valid"] = False

                validation_info["files_validated"].append(file_validation)

            logger.info(
                f"File validation completed: {len(validation_info['files_validated'])} files, "
                f"total size: {validation_info['total_size']} bytes",
            )

        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            validation_info["validation_errors"].append(
                {"general_error": str(e)},
            )
            validation_info["all_files_valid"] = False

        return validation_info

    def _validate_file_content(self, file_path: Path, file_type: str) -> bool:
        """Perform basic content validation based on file type."""
        try:
            if file_type.endswith("_image"):
                # For image files, try to open with PIL
                from PIL import Image

                with Image.open(file_path) as img:
                    # Basic validation - ensure image can be loaded
                    return img.size[0] > 0 and img.size[1] > 0

            elif file_type.endswith(("_metadata", "_report", "_spec")):
                # For JSON files, validate JSON structure
                with open(file_path) as f:
                    json.load(f)
                return True

            elif file_type.endswith("_log"):
                # For log files, just check if readable
                with open(file_path) as f:
                    f.read(100)  # Read first 100 chars
                return True

            elif file_type.endswith("_eval"):
                # For markdown files, check basic readability
                with open(file_path) as f:
                    content = f.read(100)
                    return len(content) > 0

            else:
                # For unknown types, just check if file has content
                return file_path.stat().st_size > 0

        except Exception as e:
            logger.warning(f"Content validation failed for {file_path}: {e}")
            return False

    def _generate_completion_manifest(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Generate a completion manifest with all session information."""
        manifest = {
            "session_id": context.session_id,
            "completion_timestamp": None,
            "pipeline_version": "1.0.0",
            "original_request": {
                "prompt": context.original_prompt,
                "timestamp": context.metadata.get("timestamp"),
            },
            "processing_results": {
                "success": len(context.errors) == 0,
                "warnings": context.warnings,
                "errors": context.errors,
            },
            "output_files": {},
            "metadata_summary": {},
        }

        try:
            import time

            manifest["completion_timestamp"] = time.time()

            # Add file information
            if "output_files" in context.metadata:
                file_paths = context.metadata["output_files"]
                for file_type, file_path in file_paths.items():
                    path_obj = Path(file_path)
                    manifest["output_files"][file_type] = {
                        "path": file_path,
                        "exists": path_obj.exists(),
                        "size": (
                            path_obj.stat().st_size if path_obj.exists() else 0
                        ),
                    }

            # Add key metadata summaries
            metadata_keys = [
                "processing_statistics",
                "quality_metrics",
                "transformation_summary",
                "timing_data",
                "completion_info",
            ]
            for key in metadata_keys:
                if key in context.metadata:
                    manifest["metadata_summary"][key] = context.metadata[key]

            # Save manifest to file if possible
            if (
                "output_files" in context.metadata
                and "metadata" in context.metadata["output_files"]
            ):
                try:
                    metadata_dir = Path(
                        context.metadata["output_files"]["metadata"],
                    ).parent
                    manifest_path = (
                        metadata_dir
                        / f"completion_manifest_{context.session_id[:8]}.json"
                    )

                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=2, default=str)

                    manifest["manifest_saved"] = str(manifest_path)
                    logger.info(f"Completion manifest saved: {manifest_path}")

                except Exception as e:
                    logger.warning(f"Failed to save completion manifest: {e}")
                    manifest["manifest_save_error"] = str(e)

        except Exception as e:
            logger.error(f"Error generating completion manifest: {e}")
            manifest["error"] = str(e)

        return manifest
