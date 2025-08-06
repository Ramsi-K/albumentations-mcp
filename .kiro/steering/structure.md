# Project Structure and Organization

## Repository Layout

```
albumentations-mcp/
├── .git/                    # Git version control
├── .kiro/                   # Kiro IDE configuration
│   ├── specs/               # Project specifications
│   │   └── albumentations-mcp/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       ├── tasks.md
│   │       ├── testing.md
│   │       └── prompts.md
│   └── steering/            # AI assistant guidance (this folder)
│       ├── product.md
│       ├── tech.md
│       └── structure.md
├── src/                     # Source code directory
│   └── albumentations_mcp/  # Main package (underscores for Python)
├── tests/                   # Test suite
├── prompts/                 # Prompt templates (optional)
├── README.md                # Project overview and documentation
├── LICENSE                  # MIT license
└── .gitignore              # Git ignore patterns
```

## PyPI Package Structure

The `src/albumentations_mcp/` directory follows Python packaging standards:

### Core MCP Layer

- `__init__.py` - Package initialization and version info
- `__main__.py` - CLI entry point for `uvx albumentations-mcp`
- `server.py` - Main MCP server with FastMCP tools
- `models.py` - Pydantic data models with JSON serialization (optional)

### Processing Pipeline

- `parser.py` - Natural language to Albumentations transform parsing
- `image_utils.py` - Base64 ↔ PIL Image conversion utilities
- `processor.py` - Image processing engine with Albumentations integration
- `pipeline.py` - Complete augmentation workflow orchestration

### Hook System (8-Stage Extensible Pipeline)

```
hooks/
├── __init__.py          # Hook registry and execution framework
├── pre_mcp.py           # Input sanitization and preprocessing
├── post_mcp.py          # JSON spec logging and validation
├── pre_transform.py     # Image and configuration validation
├── post_transform.py    # Metadata attachment
├── post_transform_verify.py    # Vision model verification
├── post_transform_classify.py  # Classification consistency
├── pre_save.py          # Filename modification and versioning
└── post_save.py         # Follow-up actions and cleanup
```

### Analysis Components

```
analysis/
├── __init__.py          # Analysis interfaces
├── vision.py            # Vision model integration (Kiro, Claude, GPT-4V)
├── classification.py    # Classification models (MobileNet, CNN explainer)
└── reports.py           # Report generation and formatting
```

### Utilities

```
utils/
├── __init__.py          # Utility functions
├── serialization.py     # Image serialization helpers
├── timing.py            # Performance measurement decorators
└── validation.py        # Input validation and sanitization
```

## File Organization Principles

### Separation of Concerns

- **MCP Protocol**: Isolated in `server.py` with clear interfaces
- **Business Logic**: Processing pipeline separate from protocol handling
- **Analysis**: Vision and classification models in dedicated modules
- **Configuration**: Environment-based config with sensible defaults

### Modularity

- **Hook System**: Each hook is a separate, testable module
- **Model Interfaces**: Abstract base classes for pluggable models
- **Storage Backends**: Configurable storage with local/cloud options
- **Error Handling**: Centralized error handling with recovery strategies

### Testing Structure

```
tests/
├── unit/                # Component-level tests
│   ├── test_parser.py
│   ├── test_hooks.py
│   ├── test_models.py
│   └── test_transforms.py
├── integration/         # End-to-end workflow tests
│   ├── test_mcp_protocol.py
│   ├── test_pipeline.py
│   └── test_fallbacks.py
├── fixtures/            # Test data and samples
│   ├── images/          # Sample images for testing
│   ├── prompts/         # Test prompt variations
│   └── responses/       # Expected response data
└── mocks/               # Mock implementations
    ├── vision_models.py
    ├── classifiers.py
    └── storage.py
```

## Configuration Management

### Environment-Based Configuration

- Development, testing, and production configurations
- Environment variables for sensitive data (API keys, model endpoints)
- YAML/TOML files for complex configuration structures

### Session Management

- Unique session IDs for request tracking
- Temporary file cleanup with configurable retention
- Session-aware logging and error reporting

## Documentation Structure

### Specification Documents (`.kiro/specs/`)

- **requirements.md**: User stories and acceptance criteria
- **design.md**: System architecture and component interfaces
- **tasks.md**: Implementation plan and task breakdown
- **testing.md**: Comprehensive test strategy
- **prompts.md**: Structured prompt templates

### Steering Documents (`.kiro/steering/`)

- **product.md**: Product overview and value proposition
- **tech.md**: Technology stack and build commands
- **structure.md**: Project organization and conventions

### Runtime Documentation

- **README.md**: Quick start and usage examples
- **API Documentation**: Auto-generated from Pydantic models
- **Hook Development Guide**: Custom hook creation instructions

## Development Workflow

### Code Organization Standards

- **PEP 8**: Python style guide compliance
- **Type Hints**: Full type annotation with mypy validation
- **Docstrings**: Google-style docstrings for all public APIs
- **Import Organization**: isort for consistent import ordering

### Quality Assurance

- **Pre-commit Hooks**: Automatic formatting and linting
- **Test Coverage**: Minimum 90% coverage requirement
- **CI/CD Pipeline**: Automated testing and deployment
- **Security Scanning**: Dependency vulnerability checks

### Version Control

- **Git Flow**: Feature branches with pull request reviews
- **Semantic Versioning**: Clear version numbering for releases
- **Changelog**: Automated changelog generation
- **Release Tags**: Tagged releases with deployment artifacts

This structure ensures maintainability, testability, and clear separation of concerns while supporting the extensible hook system and MCP protocol compliance.
