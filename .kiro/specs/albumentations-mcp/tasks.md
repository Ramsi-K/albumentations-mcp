# Implementation Plan

Production-ready PyPI package for natural language image augmentation via MCP protocol. Focus on easy installation (`uv add albumentations-mcp`) and seamless MCP client integration (`uvx albumentations-mcp`).

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

  **Quality Checklist (Manual - Kiro hooks not working):**

  - [x] File Summary & TODO tree added to docstring
  - [x] Code review findings documented in method docstrings
  - [x] Quality tools configured (ruff, black, mypy)
  - [x] Linting issues identified and addressed
  - [x] Tests written and passing (21 tests)
  - [x] Commit message generated

- [x] 4. Restructure for PyPI distribution

  - Restructure to `src/albumentations_mcp/` package layout
  - Create `__init__.py` with package exports and version info
  - Create `__main__.py` entry point for `uvx albumentations-mcp`
  - Move existing files to proper package structure with relative imports
  - Update `pyproject.toml` with proper package metadata and entry points
  - Test package installation and CLI command functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

- [ ] 5. Implement MCP tools with @mcp.tool() decorators

  - [ ] 5.1 Create augment_image tool

    - Use `@mcp.tool()` decorator in `server.py`
    - Accept `image_b64: str` and `prompt: str`
    - Parse prompt → create Albumentations pipeline → apply
    - Return augmented image as Base64 string
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 7.5_

  - [ ] 5.2 Add list_available_transforms tool

    - Use `@mcp.tool()` decorator
    - Return list of transforms with descriptions
    - Include parameter ranges and examples
    - _Requirements: 2.1, 2.2_

  - [ ] 5.3 Create validate_prompt tool
    - Use `@mcp.tool()` decorator
    - Parse prompt and return what would be applied
    - Show parameters and warnings
    - _Requirements: 1.4, 2.1, 2.2_

- [ ] 5. Add optional vision verification

  - Create simple vision analysis (mock for testing)
  - Compare original vs augmented images
  - Return confidence score and explanation
  - Make optional with graceful failure
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 6. Add optional classification check

  - Add simple classifier (mock for testing)
  - Compare before/after predictions
  - Return label changes and confidence delta
  - Make optional with graceful degradation
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [ ] 7. Create basic logging and output

  - Add simple logging with timestamps
  - Save images to output directory
  - Create JSON metadata files
  - Add session cleanup
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 8. Add testing and quality tools

  - Write unit tests for core functions
  - Set up pytest with basic coverage
  - Add black/ruff for code formatting
  - Create simple CI workflow
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 9. Prepare for PyPI publishing
  - Create comprehensive README.md with installation and usage examples
  - Add LICENSE file (MIT)
  - Test package build with `uv build`
  - Test local installation with `uv pip install dist/albumentations-mcp-*.whl`
  - Verify `uvx albumentations-mcp` command works correctly
  - Create GitHub repository with proper documentation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

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
│       └── hooks/                    # Hook system (Python files)
│           ├── __init__.py           # Hook registry
│           ├── vision_verify.py     # Vision verification hook
│           ├── classification.py    # Classification hook
│           └── metadata_logger.py   # Metadata logging hook
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
