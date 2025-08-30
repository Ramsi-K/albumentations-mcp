# Requirements Document

## Introduction

The albumentations-mcp tool is an MCP-compliant image augmentation system that accepts natural language commands and applies corresponding image transformations using the Albumentations Python library. The tool features a comprehensive hook system for extensibility, developer tooling integration, and structured output generation. This system enables users to describe desired image augmentations in plain English and receive professionally augmented images with full transformation metadata.

## Requirements

### Requirement 1

**User Story:** As a user, I want to provide natural language commands for image augmentation, so that I can easily apply complex transformations without knowing specific API parameters.

#### Acceptance Criteria

1. WHEN a user provides a natural language prompt like "Add motion blur and increase contrast" THEN the system SHALL parse the prompt into structured transformation parameters
2. WHEN a user uploads an image file THEN the system SHALL accept common image formats (PNG, JPEG, WEBP, TIFF)
3. WHEN the parsing is complete THEN the system SHALL generate a valid JSON specification for Albumentations transforms
4. IF the natural language prompt is ambiguous THEN the system SHALL use reasonable default parameters for the requested transformations

### Requirement 2

**User Story:** As a user, I want MCP-compliant functionality, so that the tool integrates seamlessly with Claude Desktop, Kiro, and other MCP-compatible systems.

#### Acceptance Criteria

1. WHEN the tool receives an MCP request THEN it SHALL respond with valid MCP protocol messages
2. WHEN processing requests THEN the system SHALL maintain MCP message structure and formatting
3. WHEN errors occur THEN the system SHALL return MCP-compliant error responses
4. WHEN successful THEN the system SHALL return results in the expected MCP response format

### Requirement 3

**User Story:** As a user, I want a comprehensive hook system, so that I can customize and extend the augmentation pipeline at key stages.

#### Acceptance Criteria

1. WHEN the system starts processing THEN it SHALL trigger the pre_mcp hook before parsing natural language
2. WHEN MCP parsing completes THEN it SHALL trigger the post_mcp hook with the generated JSON spec
3. WHEN image transformation begins THEN it SHALL trigger the pre_transform hook for validation
4. WHEN transformation completes THEN it SHALL trigger the post_transform hook for metadata attachment
5. WHEN transformation completes THEN it SHALL trigger the post_transform_verify hook for visual verification
6. WHEN transformation completes THEN it SHALL trigger the post_transform_classify hook for classification consistency
7. WHEN saving begins THEN it SHALL trigger the pre_save hook for filename modification
8. WHEN saving completes THEN it SHALL trigger the post_save hook for follow-up actions
9. WHEN any hook fails THEN the system SHALL log the error and continue processing unless the hook is marked as critical

### Requirement 4

**User Story:** As a maintainer, I want integrated quality tools, so that code quality is maintained automatically throughout the project.

#### Acceptance Criteria

1. WHEN code is committed THEN the pre-commit Git hook SHALL run black, ruff, and mypy checks
2. WHEN formatting issues are found THEN the system SHALL prevent the commit and display clear error messages
3. WHEN type checking fails THEN the system SHALL show specific type errors with file locations
4. WHEN all checks pass THEN the commit SHALL proceed normally

### Requirement 5

**User Story:** As a user, I want comprehensive logging and output, so that I can track what transformations were applied and troubleshoot issues.

#### Acceptance Criteria

1. WHEN any operation occurs THEN the system SHALL log to console with clear, readable messages
2. WHEN logging is enabled THEN the system SHALL optionally write structured logs to a .jsonl file
3. WHEN processing completes THEN the system SHALL generate a final augmented image file
4. WHEN processing completes THEN the system SHALL create a JSON metadata file showing applied transforms
5. WHEN processing completes THEN the system SHALL create a timestamped log entry with operation details

### Requirement 6

**User Story:** As a maintainer, I want a clean project structure, so that the codebase is maintainable and components are properly separated.

#### Acceptance Criteria

1. WHEN the project is structured THEN MCP logic SHALL be separated into dedicated modules
2. WHEN the project is structured THEN hook system SHALL be in isolated, pluggable modules
3. WHEN the project is structured THEN augmentation logic SHALL be separated from MCP and hook concerns
4. WHEN adding new functionality THEN maintainers SHALL be able to extend each component independently

### Requirement 7

**User Story:** As a user, I want reliable image transformation, so that my images are processed correctly with the intended augmentations.

#### Acceptance Criteria

1. WHEN an image is processed THEN the system SHALL apply transformations using the Albumentations library
2. WHEN transformations are applied THEN the system SHALL preserve image quality where possible
3. WHEN invalid parameters are detected THEN the system SHALL use safe fallback values
4. WHEN transformation fails THEN the system SHALL return the original image with error metadata
5. WHEN multiple transforms are requested THEN the system SHALL apply them in a logical sequence

### Requirement 8

**User Story:** As a user, I want visual verification of augmentations, so that I can confirm the intended transformations were successfully applied.

#### Acceptance Criteria

1. WHEN image transformation completes THEN the system SHALL trigger the post_transform_verify hook
2. WHEN the verify hook runs THEN it SHALL analyze both original and augmented images using a vision-capable model
3. WHEN visual analysis completes THEN it SHALL generate a confidence score from 1-5 for transformation success
4. WHEN visual analysis completes THEN it SHALL provide a brief explanation of observed changes
5. WHEN verification completes THEN it SHALL save results as visual_eval.md in the output directory
6. IF the vision model is unavailable THEN the system SHALL log the error and continue processing

### Requirement 9

**User Story:** As a user, I want classification consistency checking, so that I can understand if augmentations affect downstream ML model performance.

#### Acceptance Criteria

1. WHEN image transformation completes THEN the system SHALL trigger the post_transform_classify hook
2. WHEN the classify hook runs THEN it SHALL run a lightweight classifier on both original and augmented images
3. WHEN classification completes THEN it SHALL log predicted classes and confidence scores for both images
4. WHEN classification completes THEN it SHALL detect and log any label changes between original and augmented images
5. WHEN classification completes THEN it SHALL save results as classification_report.json in the output directory
6. WHEN the --toy-classifier flag is provided THEN it SHALL use the CNN explainer model instead of MobileNet
7. IF the classifier model is unavailable THEN the system SHALL log the error and continue processing

### Requirement 10

**User Story:** As a user, I want comprehensive output files, so that I have complete documentation of the augmentation process and its effects.

#### Acceptance Criteria

1. WHEN processing completes THEN the system SHALL generate a final augmented image file
2. WHEN processing completes THEN the system SHALL create a JSON metadata file showing applied transforms
3. WHEN processing completes THEN the system SHALL create a timestamped log entry with operation details
4. WHEN visual verification runs THEN the system SHALL create visual_eval.md with verification results
5. WHEN classification checking runs THEN the system SHALL create classification_report.json with consistency analysis
6. WHEN all outputs are generated THEN they SHALL be organized in a structured output directory

### Requirement 11

**User Story:** As a user, I want optional advanced features, so that I can use the tool in different contexts and workflows.

#### Acceptance Criteria

1. IF a web interface is implemented THEN it SHALL use Gradio for user-friendly interaction
2. IF a CLI tool is implemented THEN it SHALL accept command-line arguments for batch processing
3. IF batch processing is implemented THEN it SHALL handle multiple images efficiently
4. WHEN advanced features are available THEN they SHALL maintain the same hook system and logging capabilities

### Requirement 12

**User Story:** As a user, I want automatic handling of oversized images, so that I can process large images without manual resizing or pipeline failures.

#### Acceptance Criteria

1. WHEN an image exceeds the maximum size limit THEN the PreTransformHook SHALL automatically downscale the image while preserving aspect ratio
2. WHEN auto-resizing occurs THEN the system SHALL use LANCZOS filter for high-quality downscaling
3. WHEN auto-resizing occurs THEN the system SHALL save the resized copy to `session_dir/tmp/` directory
4. WHEN auto-resizing occurs THEN the system SHALL log metadata including original dimensions, resized dimensions, resize_applied=True, and reason
5. WHEN STRICT_MODE is enabled THEN the system SHALL reject oversized images with an error instead of auto-resizing
6. WHEN STRICT_MODE is disabled (default) THEN the system SHALL auto-resize oversized images and continue processing
7. WHEN the maximum image size limit is configurable THEN it SHALL default to 4096 pixels on the largest dimension

### Requirement 13

**User Story:** As a user, I want comprehensive temporary file cleanup, so that no orphaned files accumulate on my system after processing.

#### Acceptance Criteria

1. WHEN temporary files are created from any source THEN they SHALL be saved within the proper session directory structure (`session_dir/tmp/`)
2. WHEN files are loaded from URLs or pasted images THEN they SHALL be saved in the correct session ID folder format (`outputs/YYYYMMDD_HHMMSS_sessionID/tmp/`)
3. WHEN PostSaveHook executes THEN it SHALL track and clean up all temporary files and directories created during processing
4. WHEN PostSaveHook executes THEN it SHALL clean up temporary files regardless of their naming pattern
5. WHEN PostSaveHook executes THEN it SHALL confine cleanup to session-specific temporary directories and never touch user original files
6. WHEN PostSaveHook executes THEN it SHALL log cleanup results including files removed, directories removed, and any cleanup warnings
7. WHEN processing completes THEN the `session_dir/tmp/` directory SHALL be empty or removed entirely
8. WHEN cleanup fails for any temporary file THEN the system SHALL log warnings but continue processing
