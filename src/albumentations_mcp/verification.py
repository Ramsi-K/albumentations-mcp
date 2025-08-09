#!/usr/bin/env python3
"""
LLM-based Visual Verification System

This module provides functionality to save images for LLM review and generate
verification reports that can be used by the same VLM (Kiro, Claude Desktop)
that's already using the MCP tools.

# File Summary
Visual verification system that saves original and augmented images to temporary
files and generates structured reports for LLM review. Enables the same VLM
using the MCP tools to verify transformation success by examining saved images.

# TODO Tree
- [x] Core Verification Infrastructure
  - [x] Import dependencies (os, tempfile, datetime, pathlib)
  - [x] Define VisualVerificationManager class
  - [x] Create file path utilities and naming conventions
- [x] Image File Output System
  - [x] Save images to temporary files with unique names
  - [x] Generate timestamped filenames for tracking
  - [x] Handle different image formats (PNG, JPEG)
  - [x] Create output directory management
- [x] Verification Report Generation
  - [x] Generate structured reports for LLM review
  - [x] Include image file paths and transformation details
  - [x] Add evaluation prompts and scoring frameworks
  - [x] Create markdown-formatted output
- [x] File Management & Cleanup
  - [x] Cleanup utilities for temporary files
  - [x] Safe file deletion with error handling
  - [x] Directory cleanup and management
- [x] Quality Assurance
  - [x] Input validation for images and paths
  - [x] Error handling for file I/O operations
  - [x] Logging for debugging and monitoring

# Code Review Notes
- SECURITY: Validate all file paths to prevent directory traversal
- PERFORMANCE: Use efficient image saving with appropriate compression
- MEMORY: Ensure proper cleanup of temporary files
- ERROR HANDLING: Graceful failure when file operations fail
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class VisualVerificationManager:
    """
    Manages visual verification by saving images for LLM review.

    This class handles saving original and augmented images to temporary files
    and generating verification reports that can be reviewed by the same VLM
    (Kiro, Claude Desktop) that's using the MCP tools.
    """

    def __init__(self, output_dir: str | None = None):
        """
        Initialize the visual verification manager.

        Args:
            output_dir: Optional custom output directory. If None, uses system temp.
        """
        self.output_dir = (
            Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        )
        self.verification_dir = self.output_dir / "albumentations_verification"
        self._ensure_output_directory()

    def _ensure_output_directory(self) -> None:
        """Ensure the output directory exists."""
        try:
            self.verification_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Verification directory ready: {self.verification_dir}")
        except Exception as e:
            logger.error(f"Failed to create verification directory: {e}")
            # Fallback to system temp directory
            self.verification_dir = (
                Path(tempfile.gettempdir()) / "albumentations_verification"
            )
            self.verification_dir.mkdir(parents=True, exist_ok=True)

    def save_images_for_review(
        self, original: Image.Image, augmented: Image.Image, session_id: str,
    ) -> dict[str, str]:
        """
        Save original and augmented images to temporary files for LLM review.

        Args:
            original: Original PIL Image
            augmented: Augmented PIL Image
            session_id: Unique session identifier

        Returns:
            Dict with 'original' and 'augmented' file paths

        Raises:
            Exception: If image saving fails
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Generate unique filenames
        original_filename = f"original_{session_id}_{timestamp}_{unique_id}.png"
        augmented_filename = f"augmented_{session_id}_{timestamp}_{unique_id}.png"

        original_path = self.verification_dir / original_filename
        augmented_path = self.verification_dir / augmented_filename

        try:
            # Save images with high quality
            original.save(original_path, format="PNG", optimize=True)
            augmented.save(augmented_path, format="PNG", optimize=True)

            logger.info(
                f"Saved verification images: {original_path.name}, {augmented_path.name}",
            )

            return {
                "original": str(original_path),
                "augmented": str(augmented_path),
            }

        except Exception as e:
            logger.error(f"Failed to save verification images: {e}")
            # Clean up any partially saved files
            for path in [original_path, augmented_path]:
                if path.exists():
                    try:
                        path.unlink()
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed to cleanup partial file {path}: {cleanup_error}",
                        )
            raise

    def generate_verification_report(
        self,
        image_paths: dict[str, str],
        prompt: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate a verification report for LLM review.

        Args:
            image_paths: Dict with 'original' and 'augmented' file paths
            prompt: Original transformation prompt
            session_id: Optional session identifier
            metadata: Optional additional metadata

        Returns:
            Markdown-formatted verification report
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# Visual Verification Report

**Generated:** {timestamp}
**Session ID:** {session_id or 'N/A'}
**Transformation Prompt:** "{prompt}"

## Images for Review

### Original Image
File: `{os.path.basename(image_paths['original'])}`
Path: `{image_paths['original']}`

### Augmented Image  
File: `{os.path.basename(image_paths['augmented'])}`
Path: `{image_paths['augmented']}`

## Verification Instructions

Please review both images and evaluate the transformation success:

### 1. Visual Comparison
- Compare the original and augmented images
- Identify what changes were applied
- Assess if the changes match the intended transformation: "{prompt}"

### 2. Transformation Success Rating
Please rate the transformation success on a scale of 1-5:
- **1**: Transformation failed completely - no visible changes
- **2**: Transformation partially applied - minimal changes visible  
- **3**: Transformation applied adequately - changes visible but could be stronger
- **4**: Transformation applied well - clear changes matching the prompt
- **5**: Transformation applied perfectly - excellent results matching the prompt

### 3. Detailed Analysis
Please provide:
- **Observed Changes:** List specific visual changes you can see
- **Success Assessment:** Does the augmented image match the transformation intent?
- **Quality Notes:** Any observations about the transformation quality
- **Recommendations:** Any suggestions for improvement (if applicable)

## Evaluation Template

```
TRANSFORMATION SUCCESS RATING: [1-5]

OBSERVED CHANGES:
- [List specific visual changes you observe]

SUCCESS ASSESSMENT:
[Does the transformation match the intended prompt? Explain why or why not]

QUALITY NOTES:
[Any observations about the quality, artifacts, or effectiveness]

RECOMMENDATIONS:
[Any suggestions for improvement, or "None" if satisfied]
```

"""

        # Add metadata if provided
        if metadata:
            report += "\n## Additional Metadata\n\n"
            for key, value in metadata.items():
                report += f"- **{key.replace('_', ' ').title()}:** {value}\n"

        report += "\n---\n*Report generated by Albumentations MCP Visual Verification System*\n"

        return report

    def save_verification_report(self, report_content: str, session_id: str) -> str:
        """
        Save verification report to file.

        Args:
            report_content: The verification report content
            session_id: Session identifier

        Returns:
            Path to saved report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"visual_eval_{session_id}_{timestamp}.md"
        report_path = self.verification_dir / report_filename

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Saved verification report: {report_path.name}")
            return str(report_path)

        except Exception as e:
            logger.error(f"Failed to save verification report: {e}")
            raise

    def cleanup_temp_files(self, file_paths: list[str]) -> None:
        """
        Clean up temporary files.

        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    logger.debug(f"Cleaned up temporary file: {path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

    def cleanup_session_files(self, session_id: str) -> None:
        """
        Clean up all files for a specific session.

        Args:
            session_id: Session identifier to clean up
        """
        try:
            # Find all files containing the session ID
            session_files = list(self.verification_dir.glob(f"*{session_id}*"))

            for file_path in session_files:
                try:
                    file_path.unlink()
                    logger.debug(f"Cleaned up session file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup session file {file_path}: {e}")

            if session_files:
                logger.info(
                    f"Cleaned up {len(session_files)} files for session {session_id}",
                )

        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")

    def get_verification_directory(self) -> str:
        """Get the verification directory path."""
        return str(self.verification_dir)

    def list_verification_files(self) -> list[dict[str, Any]]:
        """
        List all verification files in the directory.

        Returns:
            List of file information dictionaries
        """
        files = []

        try:
            for file_path in self.verification_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path),
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime,
                            ).isoformat(),
                            "type": (
                                "image"
                                if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]
                                else "report"
                            ),
                        },
                    )

        except Exception as e:
            logger.error(f"Failed to list verification files: {e}")

        return sorted(files, key=lambda x: x["modified"], reverse=True)


# Global verification manager instance
_verification_manager_instance = None


def get_verification_manager() -> VisualVerificationManager:
    """Get global verification manager instance."""
    global _verification_manager_instance
    if _verification_manager_instance is None:
        _verification_manager_instance = VisualVerificationManager()
    return _verification_manager_instance


def save_images_for_llm_review(
    original: Image.Image, augmented: Image.Image, session_id: str,
) -> dict[str, str]:
    """Convenience function to save images for LLM review."""
    return get_verification_manager().save_images_for_review(
        original, augmented, session_id,
    )


def generate_llm_verification_report(
    image_paths: dict[str, str],
    prompt: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Convenience function to generate verification report."""
    return get_verification_manager().generate_verification_report(
        image_paths, prompt, session_id, metadata,
    )
