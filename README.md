🚧 Work in Progress (Beta Testing ongoing)

# Albumentations-MCP

Natural language image augmentation via MCP protocol. Transform images using plain English with this MCP-compliant server built on [Albumentations](https://albumentations.ai/).

**Example:** `"add blur and rotate 15 degrees"` → Applies GaussianBlur + Rotate transforms automatically

## Quick Start

```bash
# Install from PyPI
pip install albumentations-mcp

# Run as MCP server
uvx albumentations-mcp
```

## MCP Client Setup

### Claude Desktop

Copy [claude-desktop-config.json](docs/claude-desktop-config.json) to `~/.claude_desktop_config.json`

Or add manually:

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

Copy [kiro-mcp-config.json](docs/kiro-mcp-config.json) to `.kiro/settings/mcp.json`

Or add manually:

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

## Available Tools

- **`augment_image`** - Apply augmentations using natural language or presets
- **`list_available_transforms`** - Get supported transforms and parameters
- **`validate_prompt`** - Test prompts without processing images
- **`list_available_presets`** - Get available preset configurations
- **`set_default_seed`** - Set global seed for reproducible results
- **`get_pipeline_status`** - Check pipeline health and configuration

## Available Prompts

- **`compose_preset`** - Generate augmentation policies from presets with optional tweaks
- **`explain_effects`** - Analyze pipeline effects in plain English
- **`augmentation_parser`** - Parse natural language to structured transforms
- **`vision_verification`** - Compare original and augmented images
- **`error_handler`** - Generate user-friendly error messages and recovery suggestions

## Available Resources

- **`transforms_guide`** - Complete transform documentation with parameters and ranges
- **`policy_presets`** - Built-in preset configurations (segmentation, portrait, lowlight)
- **`available_transforms_examples`** - Usage examples and patterns organized by categories
- **`preset_pipelines_best_practices`** - Best practices guide for augmentation workflows
- **`troubleshooting_common_issues`** - Common issues, solutions, and diagnostic steps

## Usage Examples

```python
# Simple augmentation
augment_image(
    image_path="photo.jpg",
    prompt="add blur and rotate 15 degrees"
)

# Using presets
augment_image(
    image_path="dataset/image.jpg",
    preset="segmentation"
)

# Test prompts
validate_prompt(prompt="increase brightness and add noise")
```

## Features

- **Natural Language Processing** - Convert English descriptions to transforms
- **Preset Pipelines** - Pre-configured transforms for common use cases
- **Reproducible Results** - Seeding support for consistent outputs
- **MCP Protocol Compliant** - Full MCP implementation with tools, prompts, and resources
- **Comprehensive Documentation** - Built-in guides, examples, and troubleshooting resources
- **Production Ready** - Comprehensive testing, error handling, and structured logging

## Documentation

- [Installation & Setup](docs/setup.md)
- [API Reference](docs/API.md)
- [Usage Examples](docs/examples.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)

### Configuration Files

- [Claude Desktop Config](docs/claude-desktop-config.json)
- [Kiro IDE Config](docs/kiro-mcp-config.json)
- [All Configuration Examples](docs/mcp-config-examples.json)

## License

MIT License - see [LICENSE](LICENSE) for details.

**Contact:** [ramsi.kalia@gmail.com](mailto:ramsi.kalia@gmail.com)
