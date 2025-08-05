# Technology Stack

## Core Technologies

- **Python 3.9+**: Primary language with async/await support
- **Pydantic v2**: Data validation and serialization with JSON Schema
- **Albumentations**: Computer vision augmentation library
- **MCP Protocol**: Model Context Protocol for tool integration
- **Structlog**: Structured JSON logging for production monitoring

## Key Dependencies

```python
# Core MCP and processing
mcp>=1.0.0
pydantic>=2.0.0
albumentations>=1.3.0
pillow>=9.0.0
numpy>=1.21.0

# Async and web framework
uvicorn>=0.20.0
fastapi>=0.100.0  # Optional web interface
asyncio

# Logging and monitoring
structlog>=22.0.0
python-json-logger>=2.0.0

# Development tools
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
pre-commit>=3.0.0
```

## Architecture Patterns

- **Layered Architecture**: MCP Interface → Processing Pipeline → Analysis → Storage
- **Hook System**: 8-stage extensible pipeline with priority-based execution
- **Dependency Injection**: Modular components with interface-based design
- **Async/Await**: Full async support for concurrent processing
- **Pydantic Models**: Type-safe data validation and serialization

## Build Commands

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run development server
python -m albumentations_mcp.main
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests only
pytest -m slow           # Performance tests
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Run all quality checks
pre-commit run --all-files
```

### MCP Server Deployment

```bash
# Run as MCP server (for Kiro integration)
python -m albumentations_mcp.main

# Run with specific configuration
MCP_LOG_LEVEL=DEBUG python -m albumentations_mcp.main

# Docker deployment
docker build -t albumentations-mcp .
docker run -p 8000:8000 albumentations-mcp
```

## Project Structure

```
src/albumentations_mcp/
├── main.py              # MCP server entrypoint
├── server.py            # MCP protocol implementation
├── models.py            # Pydantic data models
├── parser.py            # Natural language parsing
├── processor.py         # Image processing engine
├── hooks/               # 8-stage hook system
│   ├── pre_mcp.py
│   ├── post_mcp.py
│   ├── pre_transform.py
│   ├── post_transform.py
│   ├── post_transform_verify.py
│   ├── post_transform_classify.py
│   ├── pre_save.py
│   └── post_save.py
├── analysis/            # Vision and classification
│   ├── vision.py
│   └── classification.py
└── utils/               # Utilities and helpers

tests/
├── unit/                # Component tests
├── integration/         # End-to-end tests
├── fixtures/            # Test data
└── mocks/               # Mock implementations

prompts/                 # Structured prompt templates
├── augmentation_parser.txt
├── vision_verification.txt
└── classification_reasoning.txt
```

## Configuration

### Environment Variables

```bash
# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Model Configuration
VISION_MODEL_PROVIDER=kiro  # kiro, claude, gpt4v, mock
CLASSIFICATION_MODEL=mobilenet  # mobilenet, cnn_explainer, mock

# Storage Configuration
OUTPUT_DIR=./outputs
ENABLE_JSONL_LOGGING=true
SESSION_CLEANUP_HOURS=24
```

## Performance Considerations

- **Async Processing**: All I/O operations use async/await
- **Memory Management**: Automatic cleanup of large image arrays
- **Batch Processing**: Efficient handling of multiple images
- **Caching**: Optional result caching for repeated operations
- **Resource Limits**: Configurable image size and processing limits
