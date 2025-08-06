# Albumentations-MCP

**Natural language image augmentation via MCP protocol**

Transform images using plain English with this MCP-compliant server built on the [Albumentations](https://albumentations.ai/) library. Perfect for computer vision teams who need quick, reliable image transformations without writing repetitive code.

## Quick Start

```bash
# Install from PyPI
uv add albumentations-mcp

# Add to your MCP client (e.g., Claude Desktop)
# In your mcp.json configuration:
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "ENABLE_VISION_VERIFICATION": "true",
        "ENABLE_CLASSIFICATION_CHECK": "true"
      }
    }
  }
}
```

## For Computer Vision Teams

Streamline your daily image tasks - easier than writing Albumentations code each time:

- `"add blur and rotate 15 degrees"`
- `"increase contrast and add noise"`
- `"make it brighter and flip horizontally"`
- `"apply gaussian blur with medium intensity"`

## MCP Compliance

This server fulfills the MCP format through:

- **Tool Registration**: Formal tool schemas with input/output validation
- **Protocol Adherence**: Standard MCP request/response handling
- **JSON Serialization**: All data structures are MCP-compatible
- **Error Handling**: Proper MCP error response formatting
- **Streaming Support**: Progressive responses for long operations

## Specification Documents

📋 **[Requirements](/.kiro/specs/albumentations-mcp/requirements.md)** - User stories and acceptance criteria  
🏗️ **[Design](/.kiro/specs/albumentations-mcp/design.md)** - System architecture and component interfaces  
🔧 **[Tools](/.kiro/specs/albumentations-mcp/tools.md)** - MCP tool definitions with formal schemas  
💬 **[Prompts](/.kiro/specs/albumentations-mcp/prompts.md)** - Structured prompt templates for NLP  
🤖 **[System](/.kiro/specs/albumentations-mcp/system.md)** - Agent behavior and integration guidelines  
🧪 **[Testing](/.kiro/specs/albumentations-mcp/testing.md)** - Comprehensive test strategy and CI/CD

## Core MCP Tools

- **`augment_image`** - Apply transformations via natural language prompts
- **`list_available_transforms`** - Discover available augmentation options
- **`validate_prompt`** - Parse and validate prompts without processing

## Key Features

✅ **Natural Language Processing** - "add blur and increase contrast"  
✅ **Vision Model Verification** - AI-powered result validation  
✅ **Classification Consistency** - ML pipeline safety checks  
✅ **8-Stage Hook System** - Extensible processing pipeline  
✅ **Comprehensive Logging** - Structured metadata and analysis  
✅ **Error Recovery** - Graceful fallbacks and helpful suggestions

## Installation & Configuration

### PyPI Installation

```bash
uv add albumentations-mcp
# or
pip install albumentations-mcp
```

### MCP Client Setup

**Claude Desktop** (`~/.claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "ENABLE_VISION_VERIFICATION": "true",
        "ENABLE_CLASSIFICATION_CHECK": "true",
        "HOOK_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Other MCP Clients**: Use `uvx albumentations-mcp` as the command with stdio transport.

## Environment Variables

- `ENABLE_VISION_VERIFICATION`: Enable AI-powered result validation (default: true)
- `ENABLE_CLASSIFICATION_CHECK`: Enable ML pipeline safety checks (default: true)
- `ENABLE_PRE_MCP_HOOK`: Enable input sanitization (default: true)
- `ENABLE_POST_MCP_HOOK`: Enable JSON spec logging (default: true)
- `HOOK_LOG_LEVEL`: Logging level for hooks (default: INFO)

## Use Cases

Perfect for computer vision teams working on:

- **Data preprocessing pipelines** - Quick augmentation without boilerplate
- **ML model training** - Safe augmentations with classification consistency checks
- **Image analysis workflows** - Natural language interface for non-technical users
- **Rapid prototyping** - Test augmentation ideas without writing code

The goal is to expose configurable image transforms as callable tools via the Model Context Protocol (MCP), so agents like Claude—or IDEs like Kiro—can apply augmentations dynamically during runtime.

🗓️ **Hackathon Entry:** August 2025  
🚀 **Status:** Specification Complete - Ready for Implementation
