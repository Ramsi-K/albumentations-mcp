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
albumentations>=1.3.0
pillow>=9.0.0
numpy>=1.21.0

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

- **Simple MCP Tools**: Use `@mcp.tool()` decorators for function registration
- **FastMCP Library**: Built-in MCP protocol handling via `mcp.run("stdio")`
- **Minimal Dependencies**: Just MCP + Albumentations + Pillow
- **Direct Processing**: Simple function calls without complex pipelines

## Build Commands

**IMPORTANT: This project uses UV for dependency management. Always use `uv run` instead of direct python commands.**

### Development Setup

```bash
# Install dependencies (handled automatically by uv)
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run development server
uv run python main.py
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/unit/        # Unit tests only
uv run pytest tests/integration/ # Integration tests only
uv run pytest -m slow           # Performance tests

# Run specific test file
uv run pytest tests/test_image_utils.py -v
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

### MCP Server Deployment

```bash
# Run as MCP server (for Kiro integration)
uv run python main.py

# Run with specific configuration
MCP_LOG_LEVEL=DEBUG uv run python main.py

# Test with MCP Inspector (if available)
# Server runs on stdio, not HTTP ports
```

## Project Structure

```
src/
├── main.py              # FastMCP server with @mcp.tool() decorators
├── image_utils.py       # Base64 ↔ PIL Image conversion
├── parser.py            # Simple natural language parsing
├── transforms.py        # Albumentations transform logic
└── analysis.py          # Optional vision/classification analysis

tests/
├── test_tools.py        # Test MCP tools
├── test_parser.py       # Test prompt parsing
├── test_images.py       # Test image handling
└── fixtures/            # Test data

prompts/                 # Simple prompt templates (optional)
├── augmentation_examples.txt
└── transform_mappings.txt
```

## Configuration

### Environment Variables

```bash
# MCP Server Configuration
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
