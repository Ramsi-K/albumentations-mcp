# Implementation Plan

Simple MCP server using FastMCP library for image augmentation tools.

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

- [ ] 3. Build natural language parser

  - Create simple prompt parser using string matching
  - Map phrases to Albumentations transforms ("blur" → Blur)
  - Add parameter extraction with defaults
  - Handle basic errors and provide suggestions
  - _Requirements: 1.1, 1.4, 7.3_

- [ ] 4. Implement MCP tools with @mcp.tool() decorators

  - [ ] 4.1 Create augment_image tool

    - Use `@mcp.tool()` decorator
    - Accept `image_b64: str` and `prompt: str`
    - Parse prompt → create Albumentations pipeline → apply
    - Return augmented image as Base64 string
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 7.5_

  - [ ] 4.2 Add list_available_transforms tool

    - Use `@mcp.tool()` decorator
    - Return list of transforms with descriptions
    - Include parameter ranges and examples
    - _Requirements: 2.1, 2.2_

  - [ ] 4.3 Create validate_prompt tool
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

- [ ] 9. Create main server runner
  - Add `if __name__ == "__main__":` block
  - Use `mcp.run("stdio")` for Kiro integration
  - Add basic error handling
  - Create simple documentation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

## Simple Server Structure

```python
from mcp.server.fastmcp import FastMCP
import base64
from PIL import Image
import io
import albumentations as A

mcp = FastMCP("albumentations-mcp")

@mcp.tool()
def augment_image(image_b64: str, prompt: str) -> str:
    """Apply image augmentations based on natural language prompt."""
    # Convert base64 to PIL Image
    image_data = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_data))

    # Parse prompt and create transforms
    transforms = parse_prompt(prompt)  # Your parsing logic
    pipeline = A.Compose(transforms)

    # Apply transforms
    augmented = pipeline(image=np.array(image))['image']

    # Convert back to base64
    result_image = Image.fromarray(augmented)
    buffer = io.BytesIO()
    result_image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

@mcp.tool()
def list_available_transforms() -> dict:
    """List all available Albumentations transforms."""
    return {
        "transforms": [
            {"name": "Blur", "description": "Apply gaussian blur"},
            {"name": "Rotate", "description": "Rotate image"},
            # ... more transforms
        ]
    }

@mcp.tool()
def validate_prompt(prompt: str) -> dict:
    """Validate and preview what transforms would be applied."""
    try:
        transforms = parse_prompt(prompt)
        return {"valid": True, "transforms": transforms}
    except Exception as e:
        return {"valid": False, "error": str(e)}

if __name__ == "__main__":
    mcp.run("stdio")
```

That's it! Simple, clean, and exactly what you need for the hackathon.
