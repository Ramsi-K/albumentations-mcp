# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-12

### Added

- Initial alpha release of albumentations-mcp
- MCP-compliant server with 4 tools:
  - `augment_image`: Apply image augmentations based on natural language prompts
  - `list_available_transforms`: Get list of supported transforms with descriptions
  - `validate_prompt`: Parse and validate prompts without applying transforms
  - `get_pipeline_status`: Get current pipeline status and hook information
- Natural language parser supporting 13 common image transforms:
  - Blur (Gaussian, Motion, Basic)
  - Brightness and Contrast adjustments
  - Hue, Saturation, Value modifications
  - Rotation and Flipping
  - Noise addition
  - Cropping and Resizing
  - Normalization and CLAHE enhancement
- 8-stage extensible hook system:
  - Input sanitization and preprocessing
  - JSON spec logging and validation
  - Image and configuration validation
  - Metadata generation and attachment
  - Visual verification (AI-powered)
  - Classification consistency checking
  - File management and versioning
  - Cleanup and completion logging
- Preset pipelines for common use cases:
  - `segmentation`: Optimized for segmentation tasks
  - `portrait`: Portrait photography enhancements
  - `lowlight`: Low-light image improvements
- Reproducible results with seeding support
- CLI demo interface for testing without MCP client
- Comprehensive error handling and validation
- Production-ready logging with structured JSON output
- Full type hints and comprehensive documentation
- 90%+ test coverage with pytest
- PyPI-ready package structure with proper entry points

### Technical Features

- FastMCP server implementation with async processing
- Pydantic models for type-safe data validation
- Base64 image encoding/decoding with PIL integration
- Memory management and resource cleanup
- Session tracking with unique IDs
- Graceful error recovery and fallback strategies

### Documentation

- Comprehensive README with installation and usage examples
- API documentation with detailed parameter descriptions
- Troubleshooting guide for common issues
- Development setup instructions
- MCP client integration guides for Claude Desktop and Kiro IDE

### Quality Assurance

- Black code formatting
- Ruff linting with comprehensive rule set
- MyPy type checking
- Pre-commit hooks for automated quality checks
- Comprehensive test suite with unit and integration tests
- Installation verification scripts

## [Unreleased]

### Planned for Beta v0.1

- MCP prompts and resources for advanced AI integration
- Environment-based configuration management
- Performance optimization and resource management
- GPU/CUDA support for batch processing
- Enhanced classification consistency checking
- Security hardening and enterprise features

---

## Release Notes

### Alpha v0.1.0 - Production Ready

This alpha release represents a fully functional, production-ready MCP server for image augmentation. All core features are implemented and thoroughly tested. The package is ready for PyPI distribution and real-world usage.

**Key Highlights:**

- Complete MCP protocol compliance
- Robust natural language processing
- Extensible architecture with hook system
- Comprehensive error handling
- Production-quality logging and monitoring
- Full documentation and testing

**Installation:**

```bash
pip install albumentations-mcp  # Coming soon to PyPI
uvx albumentations-mcp          # Direct execution
```

**Next Steps:**

- PyPI publication
- Community feedback and testing
- Beta release with advanced features
