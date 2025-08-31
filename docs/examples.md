# Usage Examples

## Basic Image Augmentation

### File Path Mode (Recommended)

```python
# Simple blur and rotation
result = augment_image(
    image_path="path/to/your/image.jpg",
    prompt="add blur and rotate 15 degrees"
)

# Multiple transforms with custom output
result = augment_image(
    image_path="input/photo.png",
    prompt="increase brightness, add noise, and flip horizontally",
    output_dir="./my_results"
)

# Reproducible results
result = augment_image(
    image_path="test_image.jpg",
    prompt="add blur and rotate",
    seed=42  # Same seed = same result
)
```

### Base64 Mode (Backward Compatibility)

```python
# Traditional base64 mode
result = augment_image(
    image_b64=your_image_b64,
    prompt="add blur and rotate 15 degrees"
)

# With all parameters
result = augment_image(
    image_b64=your_image_b64,
    prompt="increase brightness",
    seed=42,
    output_dir="./outputs"
)
```

## Using Presets

### File Path Mode

```python
# Segmentation tasks
result = augment_image(
    image_path="dataset/image_001.jpg",
    preset="segmentation"
)

# Portrait photography
result = augment_image(
    image_path="photos/portrait.jpg",
    preset="portrait",
    output_dir="./enhanced_portraits"
)

# Low-light improvements
result = augment_image(
    image_path="lowlight/dark_image.png",
    preset="lowlight"
)
```

### Natural Language Preset Requests

```python
# These work reliably across all MCP clients
result = augment_image(
    image_path="image.jpg",
    prompt="apply segmentation preset"
)

result = augment_image(
    image_path="portrait.jpg",
    prompt="use portrait preset"
)

result = augment_image(
    image_path="dark.jpg",
    prompt="lowlight preset"
)
```

## Validation and Testing

### Prompt Validation

```python
# Test what transforms would be applied
validation = validate_prompt(prompt="add blur and rotate 15 degrees")
print(f"Confidence: {validation['confidence']}")
print(f"Transforms: {validation['transforms']}")
print(f"Warnings: {validation['warnings']}")
```

### Available Transforms

```python
# Get all supported transforms
transforms = list_available_transforms()
for transform in transforms['transforms']:
    print(f"{transform['name']}: {transform['description']}")
```

### Available Presets

```python
# Get all presets
presets = list_available_presets()
for preset in presets['presets']:
    print(f"{preset['name']}: {preset['description']}")
```

## Advanced Usage

### Seed Management

```python
# Set global default seed
set_default_seed(seed=42)

# All subsequent calls use this seed unless overridden
result1 = augment_image(image_path="img1.jpg", prompt="add blur")
result2 = augment_image(image_path="img2.jpg", prompt="rotate")

# Override global seed for specific call
result3 = augment_image(
    image_path="img3.jpg",
    prompt="add noise",
    seed=123  # Uses 123 instead of global 42
)

# Clear global seed
set_default_seed(seed=None)
```

### Pipeline Status

```python
# Check system health
status = get_pipeline_status()
print(f"Registered hooks: {status['registered_hooks']}")
print(f"Pipeline ready: {status['pipeline_ready']}")
```

## Natural Language Examples

### Blur Effects

```python
# Various ways to request blur
augment_image(image_path="img.jpg", prompt="add blur")
augment_image(image_path="img.jpg", prompt="make blurry")
augment_image(image_path="img.jpg", prompt="gaussian blur")
augment_image(image_path="img.jpg", prompt="blur by 5")
```

### Color Adjustments

```python
# Brightness and contrast
augment_image(image_path="img.jpg", prompt="increase brightness")
augment_image(image_path="img.jpg", prompt="make brighter")
augment_image(image_path="img.jpg", prompt="add contrast")
augment_image(image_path="img.jpg", prompt="brighten and increase contrast")
```

### Geometric Transforms

```python
# Rotation
augment_image(image_path="img.jpg", prompt="rotate 15 degrees")
augment_image(image_path="img.jpg", prompt="turn clockwise")
augment_image(image_path="img.jpg", prompt="rotate left")

# Flipping
augment_image(image_path="img.jpg", prompt="flip horizontally")
augment_image(image_path="img.jpg", prompt="mirror")
augment_image(image_path="img.jpg", prompt="flip vertical")
```

### Complex Combinations

```python
# Multiple transforms
augment_image(
    image_path="img.jpg",
    prompt="add blur, rotate 10 degrees, and increase brightness"
)

augment_image(
    image_path="img.jpg",
    prompt="flip horizontally, add noise, and make more contrasty"
)
```

## Error Handling

### Common Patterns

```python
# Always validate prompts first for important workflows
validation = validate_prompt(prompt="your complex prompt here")
if validation['valid'] and validation['confidence'] > 0.8:
    result = augment_image(image_path="img.jpg", prompt="your complex prompt here")
else:
    print(f"Prompt issues: {validation['warnings']}")
    print(f"Suggestions: {validation['suggestions']}")
```

### File Size Considerations

```python
# For large images, always use file path mode
# ❌ Avoid: Base64 with large images
large_base64 = convert_large_image_to_base64("huge_image.jpg")  # May crash
result = augment_image(image_b64=large_base64, prompt="add blur")

# ✅ Use: File path mode instead
result = augment_image(image_path="huge_image.jpg", prompt="add blur")
```

## Batch Processing Patterns

### Sequential Processing

```python
import os

# Process multiple images
image_dir = "input_images/"
output_dir = "processed_images/"

for filename in os.listdir(image_dir):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        input_path = os.path.join(image_dir, filename)
        result = augment_image(
            image_path=input_path,
            prompt="add blur and rotate",
            seed=42,  # Consistent transforms
            output_dir=output_dir
        )
        print(f"Processed: {filename}")
```

### Preset-Based Workflows

```python
# Apply different presets based on image type
def process_dataset(image_path, image_type):
    preset_map = {
        'medical': 'segmentation',
        'portrait': 'portrait',
        'night': 'lowlight'
    }

    preset = preset_map.get(image_type, 'segmentation')
    return augment_image(
        image_path=image_path,
        preset=preset,
        seed=42
    )

# Usage
result = process_dataset("scan.jpg", "medical")
result = process_dataset("selfie.jpg", "portrait")
result = process_dataset("night_photo.jpg", "night")
```
