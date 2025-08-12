# Preset Configurations

Albumentations MCP provides predefined preset configurations optimized for specific use cases. Each preset contains a curated set of transforms with parameters tuned for optimal results in that domain.

## Available Presets

### Segmentation

**Use Case**: Semantic segmentation, instance segmentation, object detection  
**Intensity**: Mild  
**Preserves Geometry**: Yes

Mild augmentations that preserve object boundaries, making them ideal for segmentation tasks where precise pixel-level accuracy is crucial.

**Transforms**:

- HorizontalFlip (50% probability)
- RandomBrightnessContrast (80% probability, ±10% brightness/contrast)
- HueSaturationValue (70% probability, mild color shifts)
- Rotate (60% probability, ±15 degrees)
- RandomScale (50% probability, ±10% scale)

**Example Usage**:

```bash
# CLI Demo
python -m albumentations_mcp.demo --image input.jpg --preset segmentation --seed 42

# MCP Tool
augment_image(image_b64="...", preset="segmentation", seed=42)
```

### Portrait

**Use Case**: Face recognition, portrait enhancement, facial analysis  
**Intensity**: Moderate  
**Preserves Geometry**: Partially

Transforms suitable for human faces and portrait photography, focusing on color enhancement and mild geometric changes that don't distort facial features significantly.

**Transforms**:

- RandomBrightnessContrast (80% probability, ±20% brightness/contrast)
- HueSaturationValue (70% probability, mild hue shifts, moderate saturation)
- CLAHE (60% probability, adaptive histogram equalization)
- Sharpen (50% probability, mild sharpening)
- Rotate (40% probability, ±10 degrees)
- GaussNoise (30% probability, low noise levels)

**Example Usage**:

```bash
# CLI Demo
python -m albumentations_mcp.demo --image portrait.jpg --preset portrait --verbose

# MCP Tool
augment_image(image_b64="...", preset="portrait")
```

### Low Light

**Use Case**: Night photography, indoor scenes, low-light enhancement  
**Intensity**: Strong  
**Preserves Geometry**: Yes

Enhancements specifically designed for low-light and dark images, focusing on brightness, contrast, and detail enhancement.

**Transforms**:

- RandomBrightnessContrast (90% probability, +10-40% brightness, +10-30% contrast)
- CLAHE (80% probability, strong adaptive histogram equalization)
- HueSaturationValue (70% probability, moderate color adjustments)
- Sharpen (60% probability, moderate sharpening)
- UnsharpMask (50% probability, detail enhancement)
- ToGray (10% probability, occasional grayscale conversion)

**Example Usage**:

```bash
# CLI Demo
python -m albumentations_mcp.demo --image dark_image.jpg --preset lowlight --seed 123

# MCP Tool
augment_image(image_b64="...", preset="lowlight", seed=123)
```

## Using Presets

### CLI Demo Interface

List available presets:

```bash
python -m albumentations_mcp.demo --list-presets
```

Use a preset:

```bash
python -m albumentations_mcp.demo --image input.jpg --preset PRESET_NAME [--seed SEED] [--verbose]
```

### MCP Tools

List presets via MCP:

```python
list_available_presets()
```

Apply preset via MCP:

```python
augment_image(image_b64="base64_image_data", preset="preset_name", seed=42)
```

## Preset Format

Presets are defined in JSON format with the following structure:

```json
{
  "name": "Preset Display Name",
  "description": "Description of the preset's purpose",
  "use_cases": ["use case 1", "use case 2"],
  "transforms": [
    {
      "name": "TransformName",
      "parameters": {
        "param1": "value1",
        "param2": "value2",
        "p": 0.8
      },
      "probability": 0.8
    }
  ],
  "metadata": {
    "category": "category_name",
    "intensity": "mild|moderate|strong",
    "preserves_geometry": true,
    "recommended_for": ["training", "enhancement"]
  }
}
```

## Custom Presets

You can create custom presets using the preset utilities:

```python
from albumentations_mcp.presets import create_custom_preset, save_preset_to_file

# Create custom preset
custom_preset = create_custom_preset(
    name="My Custom Preset",
    description="Custom augmentations for my use case",
    transforms=[
        {
            "name": "Blur",
            "parameters": {"blur_limit": 5, "p": 0.5},
            "probability": 0.5
        }
    ],
    use_cases=["custom processing"],
    metadata={"intensity": "mild"}
)

# Save to file
save_preset_to_file(custom_preset, "my_preset.json")
```

## Best Practices

1. **Choose the Right Preset**: Select presets based on your specific use case and data type
2. **Use Seeds for Reproducibility**: Always use seeds when you need consistent results
3. **Combine with Custom Prompts**: You cannot use both preset and prompt simultaneously - choose one approach
4. **Test Different Presets**: Experiment with different presets to find the best fit for your data
5. **Monitor Results**: Use verbose mode to understand which transforms are being applied

## Performance Considerations

- **Segmentation**: Fastest preset with mild transforms
- **Portrait**: Moderate performance with balanced transforms
- **Low Light**: Slowest preset due to intensive enhancement operations

## Troubleshooting

**Preset not found**: Check available presets with `--list-presets`
**Poor results**: Try a different preset or adjust parameters by creating a custom preset
**Performance issues**: Consider using segmentation preset for faster processing
