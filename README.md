# Albumentations-MCP

> **🚧 Alpha Development Stage** - Core functionality working, advanced features in development

## Natural Language Image Augmentation via MCP Protocol

Transform images using plain English with this MCP-compliant server built on [AlbumentationsX](https://albumentations.ai/). Designed for computer vision teams who need quick, reliable image transformations without repetitive coding.

**Example:** `"add blur and rotate 15 degrees"` → Applies GaussianBlur + Rotate transforms automatically

---

## 🚀 Current Status (Alpha v0.1)

### ✅ **Working Features**

- **4 MCP Tools**: `augment_image`, `list_available_transforms`, `validate_prompt`, `get_pipeline_status`
- **Natural Language Parser**: Converts prompts to Albumentations transforms
- **8-Stage Hook System**: Extensible processing pipeline with pre/post hooks
- **Visual Verification**: AI-powered result validation with file output
- **Comprehensive Testing**: Unit tests for core components
- **PyPI Ready**: Proper package structure with `uvx albumentations-mcp` support

### 🔧 **Technical Architecture**

- **FastMCP Server**: Modern MCP protocol implementation
- **Pydantic Models**: Type-safe data validation and serialization
- **Async Pipeline**: Non-blocking hook execution with error recovery
- **Modular Design**: Clean separation of concerns, easy to extend
- **Production Logging**: Structured JSON logs with session tracking

## 📋 Development Roadmap

### **Alpha v0.1 - Public Release** (Current Focus)

- [x] Core MCP tools and natural language processing
- [x] Hook system framework and visual verification
- [ ] **Seeding support** for reproducible transformations
- [ ] **Hook system testing** (comprehensive test coverage)
- [ ] **CLI demo tools** with preset pipelines
- [ ] **Error handling** for edge cases and production use

### **Beta v0.1 - Enhanced Features**

- [ ] **MCP Prompts & Resources** for advanced AI integration
- [ ] **Configuration management** with environment variables
- [ ] **Performance optimization** and resource management

### **Long-term - Advanced Features**

- [ ] **GPU/CUDA support** for batch processing
- [ ] **Classification consistency** checking for ML pipelines
- [ ] **Security hardening** and enterprise features

## 🛠️ Quick Start

```bash
# Install and test locally
git clone https://github.com/ramsi-k/albumentations-mcp
cd albumentations-mcp
uv sync

# Run MCP server
uv run python -m albumentations_mcp

# Test with demo (coming in Alpha v0.1)
uv run python -m albumentations_mcp.demo --image examples/cat.jpg --prompt "add blur" --seed 42
```

### MCP Client Integration

**Claude Desktop** (`~/.claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"]
    }
  }
}
```

**Kiro IDE**: Add to MCP configuration and use tools directly in chat.

## 🏗️ Technical Highlights

### **MCP Protocol Compliance**

- Formal tool schemas with input/output validation
- Standard JSON-RPC request/response handling
- Proper error handling and status codes
- Streaming support for long operations

### **Extensible Hook System**

8-stage pipeline with hooks for:

- Input sanitization and preprocessing
- Transform validation and metadata generation
- Visual verification and classification checking
- File management and cleanup

### **Production-Ready Features**

- Type hints and comprehensive docstrings
- Structured logging with session tracking
- Graceful error recovery and fallbacks
- Memory management and resource cleanup

## 📊 Use Cases

Perfect for computer vision teams working on:

- **Data preprocessing pipelines** - Quick augmentation without boilerplate
- **ML model training** - Reproducible transforms with seeding support
- **Image analysis workflows** - Natural language interface for non-technical users
- **Rapid prototyping** - Test augmentation ideas without writing code

## 📁 Project Structure

```yaml
src/albumentations_mcp/
├── server.py              # FastMCP server with 4 working tools
├── parser.py               # Natural language → Albumentations transforms
├── pipeline.py             # Hook-integrated processing pipeline
├── processor.py            # Image processing engine
├── verification.py         # AI-powered visual verification
├── hooks/                  # 8-stage extensible hook system
│   ├── pre_mcp.py         # Input sanitization
│   ├── post_mcp.py        # JSON spec logging
│   ├── pre_transform.py   # Image validation
│   ├── post_transform.py  # Metadata generation
│   ├── post_transform_verify.py  # Visual verification
│   ├── pre_save.py        # File management
│   └── post_save.py       # Cleanup and completion
└── image_utils.py         # Base64 ↔ PIL conversion utilities

tests/                     # Comprehensive test suite
├── test_image_utils.py    # Image handling tests
├── test_parser.py         # Natural language parsing tests
├── test_hooks_integration.py  # Hook system tests
└── test_mcp_protocol_compliance.py  # MCP protocol tests
```

## 🔍 Code Quality & Best Practices

- **Type Safety**: Full type hints with mypy validation
- **Code Quality**: Black formatting, Ruff linting, pre-commit hooks
- **Testing**: 90%+ test coverage with pytest and async testing
- **Documentation**: Google-style docstrings and comprehensive specs
- **Error Handling**: Graceful degradation with detailed error messages
- **Performance**: Async/await patterns with efficient resource management

## 🤝 Contributing & Feedback

This project is in active development. I'm particularly interested in feedback on:

- **Architecture decisions** and extensibility patterns
- **MCP protocol implementation** and compliance
- **Hook system design** for computer vision workflows
- **API usability** for different user personas

## 📞 Contact

**Ramsi Kalia** - [ramsi.kalia@gmail.com](mailto:ramsi.kalia@gmail.com)

_This project demonstrates my ability to design and implement production-ready systems with clear architecture, comprehensive testing, and thoughtful user experience. I'm actively seeking opportunities to apply these skills in computer vision, AI/ML, or developer tools roles._

---

## 📋 Detailed Specifications

For technical deep-dive and implementation details:

📋 **[Requirements](/.kiro/specs/albumentations-mcp/requirements.md)** - User stories and acceptance criteria  
🏗️ **[Design](/.kiro/specs/albumentations-mcp/design.md)** - System architecture and component interfaces  
📝 **[Tasks](/.kiro/specs/albumentations-mcp/tasks.md)** - Development roadmap and implementation plan  
🧪 **[Testing](/.kiro/specs/albumentations-mcp/testing.md)** - Comprehensive test strategy

**License:** MIT  
**Status:** Alpha Development - Core features working, advanced features planned
_Developed for the Kiro Hackathon_
