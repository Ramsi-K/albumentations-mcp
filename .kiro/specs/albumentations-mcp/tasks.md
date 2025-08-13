# Implementation Plan

Production-ready PyPI package for natural language image augmentation via MCP protocol. Focus on easy installation (`uv add albumentations-mcp`) and seamless MCP client integration (`uvx albumentations-mcp`).

## 🎉 PROJECT STATUS: BETA v0.1 - PUBLISHED ON PYPI

**✅ CORE FUNCTIONALITY COMPLETE**

- 4 MCP Tools implemented and working
- Complete 7-stage hook system (all hooks active and integrated)
- Natural language parser with 20+ transform mappings
- Reproducible seeding system
- Preset pipelines (segmentation, portrait, lowlight)
- CLI demo with full functionality
- Comprehensive testing (100% pass rate - 311/311 tests passing)
- PyPI package published and available
- Production logging and error handling

**🚀 BETA v0.2 ROADMAP - ADVANCED FEATURES**

- Individual hook toggles via environment variables
- Complete 8-stage hook system (5 additional hooks)
- Custom hook development framework
- Advanced preset system with user-defined presets
- Batch processing capabilities
- Performance optimizations for large images

**📊 CURRENT METRICS**

- **Test Coverage**: 100% (311/311 tests passing)
- **Code Quality**: Black formatted, Ruff linted, MyPy validated
- **Package Status**: Ready for PyPI publication
- **Documentation**: Comprehensive README and API docs

## Task List

- [x] 1. Set up FastMCP server

  - Initialize project with `uv init` and create virtual environment
  - Install dependencies: `uv add mcp albumentations pillow`
  - Create `main.py` with FastMCP import and basic structure
  - Set up project structure: `src/`, `tests/`
  - Create `pyproject.toml` with minimal dependencies (handled by uv)
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Create image handling utilities

  - Write Base64 ↔ PIL Image conversion functions
  - Add basic image format validation
  - Create simple error handling for invalid images
  - Write unit tests for image conversion
  - _Requirements: 1.2, 7.1, 7.2_

- [x] 3. Build natural language parser

  - Create simple prompt parser using string matching
  - Map phrases to Albumentations transforms ("blur" → Blur)
  - Add parameter extraction with defaults
  - Handle basic errors and provide suggestions
  - _Requirements: 1.1, 1.4, 7.3_

- [x] 4. Restructure for PyPI distribution

  - Restructure to `src/albumentations_mcp/` package layout
  - Create `__init__.py` with package exports and version info
  - Create `__main__.py` entry point for `uvx albumentations-mcp`
  - Move existing files to proper package structure with relative imports
  - Update `pyproject.toml` with proper package metadata and entry points
  - Test package installation and CLI command functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

- [x] 5. Implement MCP tools with @mcp.tool() decorators

  - [x] 5.1 Create augment_image tool

    - Use `@mcp.tool()` decorator in `server.py`
    - Accept `image_b64: str` and `prompt: str`
    - Parse prompt → create Albumentations pipeline → apply
    - Return augmented image as Base64 string
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 7.5_

  - [x] 5.2 Add list_available_transforms tool

    - Use `@mcp.tool()` decorator
    - Return list of transforms with descriptions
    - Include parameter ranges and examples
    - _Requirements: 2.1, 2.2_

  - [x] 5.3 Create validate_prompt tool

    - Use `@mcp.tool()` decorator
    - Parse prompt and return what would be applied
    - Show parameters and warnings
    - _Requirements: 1.4, 2.1, 2.2_

  - [x] 5.4 Add get_pipeline_status tool

    - Use `@mcp.tool()` decorator
    - Return current pipeline status and registered hooks
    - Show hook system information for debugging
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [x] 6. Create hook system framework

  - [x] 6.1 Implement hook registry and base classes

    - Create HookRegistry class for managing hooks
    - Define BaseHook abstract class and HookContext/HookResult data structures
    - Implement hook stage enumeration (8 stages)
    - Add hook execution framework with error handling
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x] 6.2 Implement basic hooks

    - Create pre_mcp hook for input sanitization and preprocessing
    - Create post_mcp hook for JSON spec logging and validation
    - Register hooks in pipeline initialization
    - _Requirements: 3.1, 3.2_

- [x] 7. Create image processor and pipeline orchestration

  - [x] 7.1 Implement image processor

    - Create ImageProcessor class with Albumentations integration
    - Add transform pipeline creation and execution
    - Implement parameter validation and error recovery
    - Add processing result metadata and timing
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 7.2 Create pipeline orchestration

    - Implement AugmentationPipeline class with hook integration
    - Add parse_prompt_with_hooks function for complete workflow
    - Integrate hook execution at appropriate stages
    - Add pipeline status reporting
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [x] 8. Complete remaining hook implementations

  - [x] 8.1 Implement pre_transform hook

    - Create hook for image and configuration validation before processing
    - Validate image format, size, and quality
    - Validate transform parameters and provide warnings
    - _Requirements: 3.3, 7.1, 7.2_

  - [x] 8.2 Implement post_transform hook

    - Create hook for metadata attachment after processing
    - Add processing statistics and quality metrics
    - Generate transformation summary and timing data
    - _Requirements: 3.4, 5.1, 5.2, 5.3_

  - [x] 8.3 Implement pre_save hook

    - Create hook for filename modification and versioning
    - Generate unique filenames with timestamps
    - Create output directory structure
    - _Requirements: 3.7, 5.4, 10.1, 10.2_

  - [x] 8.4 Implement post_save hook

    - Create hook for follow-up actions and cleanup
    - Log completion status and file locations
    - Clean up temporary files and resources
    - _Requirements: 3.8, 5.5, 10.3, 10.4, 10.5, 10.6_

  - [x] 8.5 **CODE QUALITY CHECKPOINT: Hook System Review**

    - Review all hook implementations for code duplication and complexity
    - Ensure each hook function is under 20 lines and single-purpose
    - Refactor common patterns into shared utilities
    - Verify consistent error handling across all hooks
    - Check for circular dependencies and unnecessary coupling
    - _Requirements: 4.1, 4.2_

- [x] 9. Add LLM-based visual verification system

  - [x] 9.1 Create image file output system

    - Create utility functions to save images to temporary files
    - Generate unique filenames with timestamps for original and augmented images
    - Add file cleanup utilities for temporary image files
    - Create verification report templates that reference saved image files
    - _Requirements: 8.1, 8.2, 8.6_

  - [x] 9.2 Implement post_transform_verify hook

    - Create hook that saves both original and augmented images to files
    - Generate visual_eval.md report with image file paths and verification prompts
    - Include structured questions for the LLM to evaluate transformation success
    - Add confidence scoring framework (1-5) and change description templates
    - Make verification optional and non-blocking (graceful failure on file I/O errors)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

## 🚀 ALPHA v0.1 - COMPLETE

- [x] 10. Add reproducibility and seeding support

  - [x] 10.1 Implement seeding infrastructure

    - Add seed parameter to augment_image MCP tool (optional)
    - Create seed management utilities for consistent random state
    - Set numpy.random.seed and random.seed before transform application
    - Add seed to processing metadata and logs for debugging
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 10.2 Enhance transform reproducibility

    - Ensure Albumentations transforms use consistent random state
    - Add seed validation and range checking (0 to 2^32-1)
    - Document seeding behavior in tool descriptions
    - Add seed to verification reports for debugging
    - _Requirements: 1.1, 1.2, 7.1, 7.2_

- [x] 11. Complete hook system testing

  - [x] 11.1 Test individual hook implementations

    - Write unit tests for pre_transform hook (image/config validation)
    - Write unit tests for post_transform hook (metadata generation)
    - Write unit tests for post_transform_verify hook (visual verification)
    - Write unit tests for pre_save hook (filename/directory management)
    - Write unit tests for post_save hook (cleanup and completion)
    - Test hook error handling and graceful failure modes
    - _Requirements: 3.3, 3.4, 3.5, 3.7, 3.8, 8.1, 8.2_

  - [x] 11.2 Test hook system integration

    - Test complete hook pipeline execution (all 8 stages)
    - Test hook failure recovery and pipeline continuation
    - Test hook context passing and metadata accumulation
    - Test hook registry management and dynamic registration
    - Verify hook execution order and dependencies
    - _Requirements: 3.1, 3.2, 3.9_

- [x] 12. Robust Error Handling & Edge Cases

  - [x] 12.1 Input validation edge cases

    - Invalid/corrupted Base64 images
    - Extremely large images (memory limits)
    - Unsupported image formats
    - Malformed natural language prompts
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 12.2 Transform failure recovery

    - Parameter out of range handling
    - Albumentations library errors
    - Memory exhaustion during processing
    - Graceful degradation strategies
    - _Requirements: 7.4, 7.5_

- [x] 13. Add CLI demo and development tools

  - [x] 13.1 Create CLI demo interface

    - Add `python -m albumentations_mcp.demo` command
    - Support `--image examples/cat.jpg --prompt "add blur"`
    - Add `--seed` parameter for reproducible demos
    - Create example images and demo scripts
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

  - [x] 13.2 Add preset pipeline support

    - Create preset configurations: "segmentation", "portrait", "lowlight"
    - Add `--preset` parameter to CLI and MCP tools
    - Define YAML/JSON preset format
    - Include preset documentation and examples
    - _Requirements: 1.1, 1.4, 2.1, 2.2_

- [x] 14. Code Review and Quality Improvements

  **Note**: This is a methodical, step-by-step refactoring process. Only refactor code that truly needs improvement - if something works well and is readable, leave it as is. The goal is targeted improvements, not wholesale changes.

  - [x] 14.1 Fix Kiro IDE hooks (if possible)

    - Investigate why `.kiro/hooks/*.kiro.hook` files are not executing
    - Test hook trigger conditions and syntax
    - Try alternative hook configurations or formats
    - Document findings - this may be an IDE setup issue that cannot be resolved
    - Create manual quality checklist as fallback if hooks cannot be fixed
    - _Note: This is exploratory - hooks may not work due to IDE configuration issues_

  - [x] 14.2 Code duplication analysis

    - Search for repeated code patterns across all modules
    - Identify common utility functions that could be extracted
    - Look for similar validation logic, error handling patterns, logging calls
    - Create `src/albumentations_mcp/utils.py` if significant duplication found
    - Focus on: image validation, parameter sanitization, error formatting, file operations
    - _Requirements: 4.1, 4.2_

  - [x] 14.3 Function complexity review

    - Identify functions with high cyclomatic complexity (>10)
    - Break down large functions into smaller, focused utilities
    - Look for functions doing multiple responsibilities
    - Extract complex conditional logic into helper functions
    - Focus on: parser.py, processor.py, validation.py, hooks modules
    - _Requirements: 4.1, 4.2_

  - [x] 14.4 Error handling consistency

    - Review exception handling patterns across modules
    - Standardize error message formats and logging levels
    - Ensure proper exception chaining with `raise ... from e`
    - Add missing error context and recovery information
    - Focus on: graceful degradation, user-friendly error messages
    - _Requirements: 7.4, 7.5_

  - [x] 14.5 Type hints and documentation review

    - Update to modern Python type hints (dict vs Dict, list vs List)
    - Ensure all public functions have proper docstrings
    - Add missing type hints for complex return types
    - Review and improve existing docstring quality
    - Focus on: API clarity, parameter descriptions, return value documentation
    - _Requirements: 4.1, 4.2_

  - [x] 14.6 Performance and memory optimization

    - Identify potential memory leaks or inefficient operations
    - Review large data structure handling (images, transform lists)
    - Look for unnecessary object creation or copying
    - Optimize hot paths in image processing pipeline
    - Focus on: image processing, hook execution, file I/O operations
    - _Requirements: 7.1, 7.2_

  - [x] 14.7 Security and input validation review

    - Review all user input validation and sanitization
    - Check for potential injection vulnerabilities
    - Ensure safe file path handling and temporary file cleanup
    - Review regex patterns for ReDoS vulnerabilities
    - Focus on: Base64 handling, file operations, parameter validation
    - _Requirements: 7.1, 7.2_

  - [x] 14.8 Testing gaps analysis

    - Identify untested or under-tested code paths
    - Add tests for edge cases and error conditions
    - Improve test coverage for new preset and CLI functionality
    - Add integration tests for complete workflows
    - Focus on: preset system, CLI demo, error recovery, hook integration
    - _Requirements: 4.1, 4.2_

## � MAIENTENANCE & IMPROVEMENTS

### Current Issues to Address

- [x] 16. Fix remaining test failures (12 out of 308 tests failing)

  - [x] 16.1 Fix image utils test expectations

    - Update test expectations for enhanced error message formats
    - Fix large image validation test to expect security validation errors
    - _Requirements: 7.1, 7.2_

  - [x] 16.2 Fix hook system validation warnings

    - Debug hook validation logic for image size, blur, rotation, and probability warnings
    - Verify hook validation thresholds are correct
    - Update hook exception handling tests for improved error recovery
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 16.3 Fix recovery system data types

    - Fix recovery system to return correct data types instead of tuples
    - Debug progressive fallback recovery logic
    - Update mock setups for new memory recovery manager integration
    - _Requirements: 7.4, 7.5_

  - [x] 16.4 Fix validation edge cases

    - Debug punctuation ratio calculation in validation
    - Verify file path generation behavior (relative vs absolute paths)
    - Fix memory limit exceeded test mock setup
    - _Requirements: 7.3, 7.4_

- [x] 15. Prepare for PyPI publishing

  - [x] 15.1 Create comprehensive documentation

    - Write detailed README.md with installation and usage examples
    - Add API documentation with examples for all MCP tools
    - Create preset and CLI usage guides
    - Document seeding and reproducibility features
    - Add MCP client setup guides with screenshots
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 15.2 Finalize package distribution

    - Add MIT LICENSE file
    - Test package build with `uv build`
    - Test local installation and verify all entry points work
    - Validate `uvx albumentations-mcp` command functionality
    - Create GitHub repository with proper CI/CD setup
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

## 🔧 BETA v0.1 - ENHANCED FEATURES

- [ ] 17. Implement MCP prompts and resources

  - [ ] 17.1 Add MCP prompt templates

    - Create @mcp.prompt() decorators for structured prompt templates
    - Implement augmentation_parser prompt for natural language parsing
    - Add vision_verification prompt for image comparison analysis
    - Add error_handler prompt for user-friendly error messages
    - _Requirements: 1.1, 1.4, 8.1, 8.2, 9.1, 9.2_

  - [ ] 17.2 Add MCP resources

    - Add @mcp.resource() for transform documentation
    - Add resource for available transforms with examples
    - Create resource for preset pipelines and best practices
    - Add resource for troubleshooting common issues
    - _Requirements: 2.1, 2.2, 11.1, 11.2_

- [ ] 18. Configuration & Environment Management

  - [ ] 18.1 Environment-based configuration

    - ENABLE_VISION_VERIFICATION=true/false
    - OUTPUT_DIR customization
    - LOG_LEVEL configuration
    - DEFAULT_SEED for reproducible testing
    - PRESET_DIR for custom preset locations
    - _Requirements: 5.1, 5.2, 8.6_

  - [ ] 18.2 Runtime configuration

    - Per-tool parameter overrides
    - Hook enable/disable flags
    - Processing timeout settings
    - Seed management and validation
    - _Requirements: 3.9, 5.1, 5.2_

- [x] 19. Implement comprehensive testing and quality tools

  - [x] 19.1 Expand test coverage for remaining components

    - Write unit tests for verification system
    - Add integration tests for complete MCP tool workflows
    - Create tests for CLI demo and preset functionality
    - Add performance and memory usage tests
    - _Requirements: 4.1, 4.2_

  - [x] 19.2 Set up quality assurance automation

    - Configure pre-commit hooks with black, ruff, and mypy
    - Set up pytest with coverage reporting
    - Add type checking and linting to CI pipeline
    - Create quality gates for code commits
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

## 🚀 LONG-TERM - ADVANCED FEATURES

- [ ] 20. Add GPU/CUDA support for batch processing

  - [ ] 20.1 GPU acceleration infrastructure

    - Add CUDA detection and device management
    - Implement GPU-accelerated Albumentations transforms
    - Add `--gpu` flag to CLI and MCP tools
    - Create GPU memory management and fallback to CPU
    - _Requirements: 7.1, 7.2_

  - [ ] 20.2 Batch processing optimization

    - Implement efficient batch transform pipelines
    - Add batch size optimization based on GPU memory
    - Create batch processing CLI commands
    - Add progress tracking for large batch operations
    - _Requirements: 7.1, 7.2_

- [ ] 21. Add classification consistency checking

  - [ ] 21.1 Create classification interface

    - Define ClassificationAnalyzer abstract base class
    - Create mock classifier for testing
    - Add support for MobileNet and CNN explainer models
    - _Requirements: 9.1, 9.2, 9.7_

  - [ ] 21.2 Implement post_transform_classify hook

    - Create hook that runs classification on both images
    - Compare predicted classes and confidence scores
    - Detect label changes and confidence deltas
    - Save classification report as classification_report.json
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [ ] 22. Performance & Resource Management

  - [ ] 22.1 Memory management

    - Large image processing limits
    - Automatic garbage collection
    - Memory usage monitoring
    - Resource cleanup after processing
    - _Requirements: 7.1, 7.2_

  - [ ] 20.2 Processing timeouts

    - Hook execution timeouts
    - Vision model API timeouts
    - Classification model timeouts
    - Overall pipeline timeout limits
    - _Requirements: 3.9, 8.6, 9.7_

- [ ] 21. Security & Safety

  - [ ] 21.1 Input sanitization

    - Path traversal prevention
    - Command injection prevention
    - Resource limits enforcement
    - Safe parameter validation
    - _Requirements: 7.1, 7.2_

  - [ ] 21.2 Safe defaults

    - Reasonable parameter ranges
    - Memory/disk usage limits
    - Hook execution sandboxing
    - Secure temporary file handling
    - _Requirements: 7.3, 7.4, 7.5_

- [ ] 22. User Validation & Feedback

  - [ ] 22.1 Alpha testing with computer vision engineers

    - Test with real datasets and workflows
    - Gather feedback on natural language interface
    - Validate preset usefulness and CLI workflow
    - Test batch processing scenarios
    - _Requirements: 1.1, 1.4, 3.1, 3.2_

  - [ ] 22.2 Beta testing with MCP client users

    - Test across different MCP clients
    - Validate installation process
    - Gather performance feedback
    - Test real-world usage patterns
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 16. Configuration & Environment Management

  - [ ] 16.1 Environment-based configuration

    - ENABLE_VISION_VERIFICATION=true/false
    - VISION_MODEL=claude/gpt4v/kiro/mock
    - OUTPUT_DIR customization
    - LOG_LEVEL configuration
    - DEFAULT_SEED for reproducible testing
    - _Requirements: 5.1, 5.2, 8.6, 9.7_

  - [ ] 16.2 Runtime configuration

    - Per-tool parameter overrides
    - Hook enable/disable flags
    - Model fallback chains
    - Processing timeout settings
    - Seed management and validation
    - _Requirements: 3.9, 5.1, 5.2_

- [ ] 17. Performance & Resource Management

  - [ ] 17.1 Memory management

    - Large image processing limits
    - Automatic garbage collection
    - Memory usage monitoring
    - Resource cleanup after processing
    - _Requirements: 7.1, 7.2_

  - [ ] 17.2 Processing timeouts

    - Hook execution timeouts
    - Vision model API timeouts
    - Classification model timeouts
    - Overall pipeline timeout limits
    - _Requirements: 3.9, 8.6, 9.7_

- [ ] 18. Security & Safety

  - [ ] 18.1 Input sanitization

    - Path traversal prevention
    - Command injection prevention
    - Resource limits enforcement
    - Safe parameter validation
    - _Requirements: 7.1, 7.2_

  - [ ] 18.2 Safe defaults

    - Reasonable parameter ranges
    - Memory/disk usage limits
    - Hook execution sandboxing
    - Secure temporary file handling
    - _Requirements: 7.3, 7.4, 7.5_

- [ ] 21. User Validation & Feedback

  - [ ] 21.1 Alpha testing with computer vision engineers

    - Test with real datasets and workflows
    - Gather feedback on natural language interface
    - Validate hook system usefulness
    - Test batch processing scenarios
    - _Requirements: 1.1, 1.4, 3.1, 3.2_

  - [ ] 21.2 Beta testing with MCP client users

    - Test across different MCP clients
    - Validate installation process
    - Gather performance feedback
    - Test real-world usage patterns
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

## PyPI Package Structure

```
albumentations-mcp/                    # Project root
├── pyproject.toml                     # Package metadata & dependencies
├── README.md                          # Documentation
├── LICENSE                            # MIT license
├── src/                              # Source code directory
│   └── albumentations_mcp/           # Your package
│       ├── __init__.py               # Package initialization
│       ├── __main__.py               # Entry point for uvx
│       ├── server.py                 # Main MCP server & tools
│       ├── parser.py                 # Natural language parsing
│       ├── image_utils.py            # Image processing utilities
│       ├── processor.py              # Image processing logic
│       ├── hooks/                    # Hook system (Python files)
│       │   ├── __init__.py           # Hook registry
│       │   ├── vision_verify.py     # Vision verification hook
│       │   ├── classification.py    # Classification hook
│       │   └── metadata_logger.py   # Metadata logging hook
│       ├── prompts/                  # MCP prompt templates
│       │   ├── __init__.py           # Prompt registry
│       │   ├── augmentation_parser.py    # Natural language parsing prompts
│       │   ├── vision_verification.py   # Image comparison prompts
│       │   ├── classification_reasoning.py  # Consistency analysis prompts
│       │   └── error_handler.py     # User-friendly error prompts
│       └── resources/                # MCP resources (optional)
│           ├── __init__.py           # Resource registry
│           ├── transforms_guide.py  # Available transforms documentation
│           ├── best_practices.py    # Augmentation best practices
│           └── troubleshooting.py   # Common issues and solutions
└── tests/                            # Test files
    ├── test_server.py
    ├── test_hooks.py
    └── fixtures/
        └── sample_images/
```

## Entry Point Structure

**`src/albumentations_mcp/__main__.py`** (for `uvx albumentations-mcp`):

```python
#!/usr/bin/env python3
"""CLI entry point for albumentations-mcp server."""

import sys
from .server import main

if __name__ == "__main__":
    sys.exit(main())
```

**`src/albumentations_mcp/server.py`** (main MCP server):

```python
from mcp.server.fastmcp import FastMCP
from .parser import parse_prompt
from .image_utils import base64_to_pil, pil_to_base64
from .hooks import HookRegistry

mcp = FastMCP("albumentations-mcp")
hook_registry = HookRegistry()

@mcp.tool()
def augment_image(image_b64: str, prompt: str) -> str:
    """Apply image augmentations based on natural language prompt."""
    # Implementation with hook integration
    pass

@mcp.prompt()
def augmentation_parser(user_prompt: str, available_transforms: list) -> str:
    """Parse natural language into Albumentations transforms."""
    # Return structured prompt template for parsing
    pass

@mcp.resource()
def transforms_guide() -> str:
    """Available transforms documentation with examples."""
    # Return comprehensive transform documentation
    pass

def main():
    """Main entry point for the MCP server."""
    mcp.run("stdio")

if __name__ == "__main__":
    main()
```

**`pyproject.toml`** configuration:

```toml
[project.scripts]
albumentations-mcp = "albumentations_mcp.__main__:main"

[project.entry-points."console_scripts"]
albumentations-mcp = "albumentations_mcp.__main__:main"
```

This structure enables:

- `uv add albumentations-mcp` (PyPI installation)
- `uvx albumentations-mcp` (direct execution)
- Proper Python package imports and distribution
- Full MCP protocol support with tools, prompts, and resources

## 🔮 BETA v0.2 TASKS - ADVANCED FEATURES

### Hook System Enhancement

- [ ] **Hook Toggle System**

  - Add environment variables for individual hook control (ENABLE_PRE_TRANSFORM, ENABLE_POST_SAVE, etc.)
  - Implement hook registry filtering based on environment settings
  - Add runtime hook enable/disable via MCP tool
  - Update documentation with hook configuration examples

- [ ] **Complete 8-Stage Hook System**

  - [ ] Implement pre_transform hook (image validation, size checks)
  - [ ] Implement post_transform hook (metadata generation)
  - [ ] Implement post_transform_classify hook (classification consistency)
  - [ ] Implement pre_save hook (file management, versioning)
  - [ ] Implement post_save hook (cleanup, completion logging)
  - [ ] Register all hooks in pipeline with proper error handling

- [ ] **Custom Hook Framework**
  - Add hook development documentation
  - Create hook template generator
  - Implement hook priority system
  - Add hook dependency management

### Advanced Features

- [ ] **User-Defined Presets**

  - Allow users to create custom preset configurations
  - Add preset validation and error handling
  - Implement preset sharing/export functionality

- [ ] **Batch Processing**

  - Add batch_augment_images MCP tool
  - Implement efficient memory management for multiple images
  - Add progress tracking and cancellation support

- [ ] **Performance Optimizations**
  - Implement image caching for repeated operations
  - Add async processing for independent transforms
  - Optimize memory usage for large images

### Developer Experience

- [ ] **Enhanced CLI**

  - Add interactive mode for testing transforms
  - Implement batch processing via CLI
  - Add preset management commands

- [ ] **Advanced Debugging**
  - Add hook execution tracing
  - Implement performance profiling tools
  - Add visual diff tools for before/after comparison
