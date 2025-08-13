"""Pre-save hook for filename modification and versioning.

This hook generates unique filenames with timestamps, creates output
directory structure, and prepares file paths for saving operations.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import BaseHook, HookContext, HookResult
from .utils import MAX_VERSION_ATTEMPTS, sanitize_filename

logger = logging.getLogger(__name__)


class PreSaveHook(BaseHook):
    """Hook for filename modification and versioning before saving."""

    def __init__(self, output_dir: str = "./outputs"):
        super().__init__("pre_save_preparation", critical=False)
        self.output_dir = Path(output_dir).resolve()  # Convert to absolute path

    async def execute(self, context: HookContext) -> HookResult:
        """Prepare filenames and directory structure for saving."""
        try:
            logger.debug(
                f"Pre-save preparation for session {context.session_id}",
            )

            # Create output directory structure
            directory_info = self._create_directory_structure(context)

            # Generate unique filenames
            filename_info = self._generate_filenames(
                context,
                directory_info["session_dir"],
            )

            # Prepare file paths
            file_paths = self._prepare_file_paths(
                filename_info,
                directory_info,
            )

            # Validate file paths and permissions
            validation_info = self._validate_file_paths(file_paths)

            # Add all information to context metadata
            context.metadata.update(
                {
                    "pre_save_processed": True,
                    "directory_info": directory_info,
                    "filename_info": filename_info,
                    "file_paths": file_paths,
                    "path_validation": validation_info,
                    "save_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Store file paths in context for easy access by other hooks
            context.metadata["output_files"] = file_paths

            logger.debug("Pre-save preparation completed successfully")
            return HookResult(success=True, context=context)

        except Exception as e:
            error_msg = f"Pre-save preparation failed: {e!s}"
            logger.error(error_msg, exc_info=True)
            return HookResult(success=False, error=error_msg, context=context)

    def _create_directory_structure(
        self,
        context: HookContext,
    ) -> dict[str, Any]:
        """Create organized directory structure for outputs."""
        try:
            # Create main output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Create session-specific subdirectory
            timestamp = datetime.now(UTC)
            session_dir_name = (
                f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{context.session_id[:8]}"
            )
            session_dir = self.output_dir / session_dir_name
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories for different file types
            subdirs = {
                "images": session_dir / "images",
                "metadata": session_dir / "metadata",
                "logs": session_dir / "logs",
                "analysis": session_dir / "analysis",
            }

            for subdir_name, subdir_path in subdirs.items():
                subdir_path.mkdir(parents=True, exist_ok=True)

            directory_info = {
                "output_dir": str(self.output_dir),
                "session_dir": str(session_dir),
                "session_dir_name": session_dir_name,
                "subdirectories": {name: str(path) for name, path in subdirs.items()},
                "created_timestamp": timestamp.isoformat(),
            }

            logger.info(f"Created directory structure: {session_dir}")
            return directory_info

        except Exception as e:
            logger.error(f"Failed to create directory structure: {e}")
            raise

    def _generate_filenames(
        self,
        context: HookContext,
        session_dir: str,
    ) -> dict[str, Any]:
        """Generate unique, descriptive filenames for all output files."""
        timestamp = datetime.now(UTC)
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        session_short = context.session_id[:8]

        # Generate base filename from prompt (sanitized)
        prompt_part = sanitize_filename(context.original_prompt)
        base_name = f"{timestamp_str}_{session_short}_{prompt_part}"

        # Generate specific filenames for different file types
        filenames = {
            "augmented_image": f"{base_name}_augmented.png",
            "original_image": f"{base_name}_original.png",
            "metadata": f"{base_name}_metadata.json",
            "processing_log": f"{base_name}_processing.log",
            "transform_spec": f"{base_name}_transforms.json",
            "quality_report": f"{base_name}_quality.json",
            "visual_eval": f"{base_name}_visual_eval.md",
            "classification_report": f"{base_name}_classification.json",
        }

        # Add versioning if files already exist
        versioned_filenames = {}
        for file_type, filename in filenames.items():
            versioned_filenames[file_type] = self._add_version_if_exists(
                session_dir,
                filename,
            )

        filename_info = {
            "base_name": base_name,
            "timestamp": timestamp_str,
            "session_short": session_short,
            "prompt_part": prompt_part,
            "original_filenames": filenames,
            "versioned_filenames": versioned_filenames,
        }

        return filename_info

    def _add_version_if_exists(self, directory: str, filename: str) -> str:
        """Add version number if file already exists."""
        file_path = Path(directory) / filename

        if not file_path.exists():
            return filename

        # Extract name and extension
        name_part = file_path.stem
        ext_part = file_path.suffix

        # Find next available version number
        version = 1
        while True:
            versioned_name = f"{name_part}_v{version}{ext_part}"
            versioned_path = file_path.parent / versioned_name
            if not versioned_path.exists():
                return versioned_name
            version += 1

            # Prevent infinite loop
            if version > MAX_VERSION_ATTEMPTS:
                import uuid

                unique_id = str(uuid.uuid4())[:8]
                return f"{name_part}_{unique_id}{ext_part}"

    def _prepare_file_paths(
        self,
        filename_info: dict[str, Any],
        directory_info: dict[str, Any],
    ) -> dict[str, str]:
        """Prepare complete file paths for all output files."""
        subdirs = directory_info["subdirectories"]
        filenames = filename_info["versioned_filenames"]

        file_paths = {
            # Images go in images subdirectory
            "augmented_image": str(
                Path(subdirs["images"]) / filenames["augmented_image"],
            ),
            "original_image": str(
                Path(subdirs["images"]) / filenames["original_image"],
            ),
            # Metadata files go in metadata subdirectory
            "metadata": str(Path(subdirs["metadata"]) / filenames["metadata"]),
            "transform_spec": str(
                Path(subdirs["metadata"]) / filenames["transform_spec"],
            ),
            "quality_report": str(
                Path(subdirs["metadata"]) / filenames["quality_report"],
            ),
            # Logs go in logs subdirectory
            "processing_log": str(
                Path(subdirs["logs"]) / filenames["processing_log"],
            ),
            # Analysis files go in analysis subdirectory
            "visual_eval": str(
                Path(subdirs["analysis"]) / filenames["visual_eval"],
            ),
            "classification_report": str(
                Path(subdirs["analysis"]) / filenames["classification_report"],
            ),
        }

        return file_paths

    def _validate_file_paths(
        self,
        file_paths: dict[str, str],
    ) -> dict[str, Any]:
        """Validate file paths and check permissions."""
        validation_info = {
            "all_paths_valid": True,
            "writable_paths": [],
            "invalid_paths": [],
            "permission_issues": [],
        }

        for file_type, file_path in file_paths.items():
            try:
                path_obj = Path(file_path)

                # Check if parent directory exists and is writable
                parent_dir = path_obj.parent
                if parent_dir.exists() and os.access(parent_dir, os.W_OK):
                    validation_info["writable_paths"].append(file_type)
                else:
                    validation_info["permission_issues"].append(
                        {
                            "file_type": file_type,
                            "path": file_path,
                            "issue": "Parent directory not writable or doesn't exist",
                        },
                    )
                    validation_info["all_paths_valid"] = False

                # Check if file already exists (warning, not error)
                if path_obj.exists():
                    logger.warning(
                        f"File already exists and will be overwritten: {file_path}",
                    )

            except Exception as e:
                validation_info["invalid_paths"].append(
                    {
                        "file_type": file_type,
                        "path": file_path,
                        "error": str(e),
                    },
                )
                validation_info["all_paths_valid"] = False

        return validation_info
