# Albumentations-MCP

**An MCP-compliant image augmentation server for the Kiro Hackathon.**

This server implements the Model Context Protocol (MCP) to provide natural language-driven image augmentation using the [Albumentations](https://albumentations.ai/) library. Agents like Kiro can call tools to transform images, verify results with vision models, and check classification consistency.

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

---

This repo is for my entry in the [Kiro Hackathon](<[https://kiro.dev](https://kiro.devpost.com/?ref_feature=challenge&ref_medium=your-open-hackathons&ref_content=Submissions+open&_gl=1*ged24j*_gcl_au*NTk3MjQyNDAxLjE3NDk1Nzk1NzY.*_ga*MjAyNjgxNzE2MS4xNzQ5NTc5NTc3*_ga_0YHJK3Y10M*czE3NTQxMjU4ODgkbzUkZzAkdDE3NTQxMjU4ODgkajYwJGwwJGgw)>).  
I'm building an MCP-compliant image augmentation server using the [Albumentations](https://albumentations.ai/) library.

The goal is to expose configurable image transforms as callable tools via the Model Context Protocol (MCP), so agents like Claude—or IDEs like Kiro—can apply augmentations dynamically during runtime.

🗓️ **Hackathon Entry:** August 2025  
🚀 **Status:** Specification Complete - Ready for Implementation
