# Installation & Setup

## Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Installation

### From PyPI (Recommended)

```bash
pip install albumentations-mcp
```

### From Source

```bash
git clone https://github.com/ramsi-k/albumentations-mcp
cd albumentations-mcp
uv sync
```

## MCP Client Configuration

### Claude Desktop

Add to your `~/.claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "MCP_LOG_LEVEL": "INFO",
        "OUTPUT_DIR": "./outputs",
        "ENABLE_VISION_VERIFICATION": "true",
        "DEFAULT_SEED": "42"
      }
    }
  }
}
```

### Kiro IDE

Add to your `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "MCP_LOG_LEVEL": "INFO",
        "OUTPUT_DIR": "./outputs",
        "ENABLE_VISION_VERIFICATION": "true",
        "DEFAULT_SEED": "42"
      },
      "disabled": false,
      "autoApprove": ["augment_image", "list_available_transforms"]
    }
  }
}
```

### Additional Configuration Examples

See [MCP Configuration Examples](mcp-config-examples.json) for more configuration options including:

- Minimal configuration
- Development setup with debug logging
- Production configuration with optimized settings
- Complete environment variable reference

## Environment Variables

- `MCP_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `OUTPUT_DIR` - Directory for output files (default: ./outputs)
- `ENABLE_VISION_VERIFICATION` - Enable AI-powered result validation
- `DEFAULT_SEED` - Default seed for reproducible results
- `MAX_FILE_SIZE_MB` - Maximum file size limit (default: 50MB)
- `PROCESSING_TIMEOUT_SECONDS` - Processing timeout (default: 300s)

## Development Setup

```bash
# Clone and install
git clone https://github.com/ramsi-k/albumentations-mcp
cd albumentations-mcp
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run server
uv run python -m albumentations_mcp
```

## Verification

Test your installation:

```bash
# Test MCP server
uvx albumentations-mcp

# Test with CLI demo
uv run python -m albumentations_mcp.demo --image examples/cat.jpg --prompt "add blur"
```
