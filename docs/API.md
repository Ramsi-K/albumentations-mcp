# API Documentation

## MCP Tools

### `augment_image`

Apply image augmentations based on natural language prompt or preset.

**Parameters:**

- `image_path` (str, optional): Path to image file (recommended for large images)
- `image_b64` (str, optional): Base64-encoded image data (for backward compatibility)
- `session_id` (str, optional): Session ID from load_image_for_processing (legacy mode)
- `prompt` (str, optional): Natural language description of desired augmentations
- `seed` (int, optional): Random seed for reproducible results (0 to 2^32-1)
- `preset` (str, optional): Use preset instead of prompt
- `output_dir` (str, optional): Directory to save output files (defaults to ./outputs)

**Input Modes:**

Provide exactly one of: `image_path`, `image_b64`, or `session_id`

- **File Path Mode** (recommended): Avoids base64 conversion crashes with large images
- **Base64 Mode**: Backward compatibility with existing code
- **Session Mode**: Legacy mode using load_image_for_processing

**Presets:**

- `"segmentation"`: Optimized for segmentation tasks (rotation, flipping, brightness)
- `"portrait"`: Portrait photography enhancements (brightness, contrast, blur)
- `"lowlight"`: Low-light image improvements (brightness, contrast, noise reduction)

**Returns:**

- `str`: Success message with file path where augmented image was saved

**Examples:**

```python
# File path mode (recommended)
result = augment_image(
    image_path="/path/to/image.jpg",
    prompt="add blur and rotate 15 degrees",
    seed=42,
    output_dir="./my_outputs"
)

# Base64 mode (backward compatibility)
result = augment_image(
    image_b64="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    prompt="add blur and rotate 15 degrees",
    seed=42
)

# Session mode (legacy)
session_id = load_image_for_processing("image.jpg")
result = augment_image(
    session_id=session_id,
    prompt="add blur and rotate 15 degrees"
)
```

### `list_available_transforms`

Get list of supported transforms with descriptions and parameters.

**Parameters:** None

**Returns:**

- `list`: Array of transform objects with:
  - `name` (str): Transform name
  - `description` (str): Human-readable description
  - `parameters` (dict): Available parameters and ranges
  - `examples` (list): Example usage phrases

**Example:**

```python
transforms = list_available_transforms()
# Returns: [
#   {
#     "name": "GaussianBlur",
#     "description": "Apply Gaussian blur to the image",
#     "parameters": {"blur_limit": [3, 7], "sigma_limit": [0, 0]},
#     "examples": ["add blur", "make blurry", "gaussian blur"]
#   },
#   ...
# ]
```

### `validate_prompt`

Parse and validate a natural language prompt without applying transforms.

**Parameters:**

- `prompt` (str, required): Natural language prompt to validate

**Returns:**

- `dict`: Validation result with:
  - `valid` (bool): Whether prompt is valid
  - `transforms` (list): Parsed transforms with parameters
  - `warnings` (list): Any warnings or suggestions
  - `errors` (list): Parse errors if any

**Example:**

```python
result = validate_prompt(prompt="add blur and rotate 15 degrees")
# Returns: {
#   "valid": true,
#   "transforms": [
#     {"name": "GaussianBlur", "params": {"blur_limit": [3, 7]}},
#     {"name": "Rotate", "params": {"limit": 15}}
#   ],
#   "warnings": [],
#   "errors": []
# }
```

### `get_pipeline_status`

Get current pipeline status and hook system information.

**Parameters:** None

**Returns:**

- `dict`: Pipeline status with:
  - `status` (str): Current pipeline status
  - `hooks` (list): Registered hooks and their status
  - `version` (str): Package version
  - `capabilities` (list): Available features

**Example:**

```python
status = get_pipeline_status()
# Returns: {
#   "status": "ready",
#   "hooks": [
#     {"name": "pre_mcp", "enabled": true, "stage": 1},
#     {"name": "post_mcp", "enabled": true, "stage": 2},
#     ...
#   ],
#   "version": "0.1.0",
#   "capabilities": ["natural_language", "presets", "seeding", "verification"]
# }
```

## Natural Language Parsing

The parser understands various ways to describe transforms:

### Blur

- "add blur", "make blurry", "gaussian blur"
- "blur with sigma 2", "strong blur"

### Rotation

- "rotate 15 degrees", "turn clockwise", "rotate left"
- "rotate randomly", "slight rotation"

### Brightness

- "increase brightness", "make brighter", "brighten"
- "brightness +20", "darker", "dim"

### Contrast

- "add contrast", "increase contrast", "make more contrasty"
- "contrast +30", "low contrast"

### Noise

- "add noise", "make noisy", "gaussian noise"
- "salt and pepper noise", "random noise"

### Flipping

- "flip horizontally", "mirror", "flip vertical"
- "horizontal flip", "vertical flip"

### Cropping

- "crop center", "random crop", "crop 224x224"
- "center crop", "crop to square"

### Color Adjustments

- "adjust hue", "change saturation", "color shift"
- "desaturate", "more colorful", "sepia"

## Error Handling

All tools return proper error responses for invalid inputs:

```python
# Invalid image data
{
  "error": "Invalid image data",
  "code": "INVALID_IMAGE",
  "details": "Could not decode Base64 image data"
}

# Invalid prompt
{
  "error": "Could not parse prompt",
  "code": "PARSE_ERROR",
  "details": "No recognized transforms in prompt",
  "suggestions": ["Try 'add blur'", "Try 'rotate 15 degrees'"]
}

# Invalid parameters
{
  "error": "Invalid parameter value",
  "code": "INVALID_PARAMETER",
  "details": "Seed must be between 0 and 4294967295"
}
```

## Environment Variables

### Core Configuration

- `MCP_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `OUTPUT_DIR`: Directory for temporary files (default: ./outputs)
- `ENABLE_VISION_VERIFICATION`: Enable visual verification hooks (default: true)
- `DEFAULT_SEED`: Default seed for reproducible testing

### Image Size Handling (New in v0.1)

- `STRICT_MODE`: Reject oversized images instead of auto-resizing (default: false)
- `MAX_IMAGE_SIZE`: Maximum image dimension in pixels (default: 4096)
- `MAX_PIXELS_IN`: Maximum total pixels allowed (default: 16000000)
- `MAX_BYTES_IN`: Maximum file size in bytes (default: 50000000)

**Image Size Behavior:**

- When `STRICT_MODE=false` (default): Oversized images are automatically resized while preserving aspect ratio
- When `STRICT_MODE=true`: Oversized images are rejected with a clear error message
- Auto-resize uses high-quality LANCZOS filter and preserves original format (JPEG→JPEG, PNG→PNG, etc.)
- Resized images are saved to `session_dir/tmp/` and cleaned up after processing
- EXIF orientation is normalized before measuring/resizing

**Example Configuration:**

```bash
# Strict mode - reject large images
export STRICT_MODE=true
export MAX_IMAGE_SIZE=2048

# Permissive mode - auto-resize large images
export STRICT_MODE=false
export MAX_IMAGE_SIZE=4096
export MAX_PIXELS_IN=20000000
export MAX_BYTES_IN=100000000
```

## Reproducibility

When using the `seed` parameter:

- Same seed + same image + same prompt = identical results
- Seed affects all random aspects: blur amounts, rotation angles, crop positions, noise levels
- Seed range: 0 to 2^32-1 (4,294,967,295)
- Omitting seed uses system randomness for varied results

## Performance Notes

- Images are processed in memory (no temporary files for basic operations)
- Large images (>10MB) may cause memory issues
- Hook system adds ~10-50ms overhead per image
- Visual verification (if enabled) adds ~1-3s per image
