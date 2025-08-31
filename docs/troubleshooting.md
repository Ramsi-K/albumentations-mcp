# Troubleshooting

## Common Issues

### MCP Server Not Starting

**Symptoms:**

- Server fails to start
- "Command not found" errors
- Import errors

**Solutions:**

```bash
# Check if uv is installed
uv --version

# Ensure dependencies are installed
uv sync

# Run with debug logging
MCP_LOG_LEVEL=DEBUG uvx albumentations-mcp

# Try direct Python execution
uv run python -m albumentations_mcp
```

### Large Image Issues

**Symptoms:**

- Memory errors
- MCP client timeouts
- "Request timed out" messages

**Solutions:**

```python
# ❌ Avoid: Base64 mode with large images
augment_image(image_b64=large_base64_data, prompt="add blur")

# ✅ Use: File path mode instead
augment_image(image_path="large_image.jpg", prompt="add blur")
```

**File Size Limits:**

- Base64 input: 5MB (≈3.75MB actual image)
- File path mode: 50MB maximum
- Processing timeout: 300 seconds

### Natural Language Parsing Issues

**Symptoms:**

- Prompt not recognized
- No transforms applied
- Unexpected results

**Solutions:**

```python
# Use simple, clear descriptions
# ✅ Good
augment_image(image_path="img.jpg", prompt="add blur")
augment_image(image_path="img.jpg", prompt="rotate 15 degrees")

# ❌ Avoid ambiguous language
augment_image(image_path="img.jpg", prompt="make it look better")
augment_image(image_path="img.jpg", prompt="do something cool")

# Always validate first
validation = validate_prompt(prompt="your prompt here")
if validation['valid']:
    result = augment_image(image_path="img.jpg", prompt="your prompt here")
```

### MCP Client Timeout Issues

**Known Issue:** MCP clients may timeout on large images or complex transforms, but processing completes successfully.

**Symptoms:**

- "Request timed out" error after 30-60 seconds
- Files are actually created successfully
- Processing completes in <10 seconds

**Workarounds:**

```bash
# Check output directory even if timeout occurs
ls -la outputs/

# Use smaller images for testing
# Use single transforms instead of multiple
# Monitor with debug logging
MCP_LOG_LEVEL=DEBUG uvx albumentations-mcp
```

### Preset Parameter Issues

**Known Issue:** Direct preset parameter may not work in some MCP clients.

**Symptoms:**

- `preset="segmentation"` parameter ignored
- No transforms applied when using preset parameter

**Workarounds:**

```python
# ✅ Works reliably - Natural language
augment_image(image_path="img.jpg", prompt="apply segmentation preset")
augment_image(image_path="img.jpg", prompt="use portrait preset")

# ❌ May fail - Direct parameter
augment_image(image_path="img.jpg", preset="segmentation")
```

## File and Directory Issues

### Output Directory Problems

**Symptoms:**

- Files not saved
- Permission errors
- Directory not found

**Solutions:**

```bash
# Check permissions
ls -la outputs/

# Create directory manually
mkdir -p outputs

# Use custom output directory
export OUTPUT_DIR="/path/to/writable/directory"
```

### Resource Cleanup

**Automatic Cleanup:**

- Temporary files cleaned after processing
- Memory automatically garbage collected
- Session files preserved for debugging

**Manual Cleanup:**

```bash
# Clean old sessions (older than 7 days)
find outputs/ -name "20*" -type d -mtime +7 -exec rm -rf {} \;

# Clean all outputs
rm -rf outputs/

# Clean specific session
rm -rf outputs/20241230_143022_a1b2c3d4/
```

## Performance Issues

### Slow Processing

**Causes:**

- Large image files
- Complex transform pipelines
- Resource limitations

**Solutions:**

```python
# Resize images before processing if appropriate
# Use simpler transform combinations
# Process in smaller batches

# Monitor processing time
import time
start = time.time()
result = augment_image(image_path="img.jpg", prompt="add blur")
print(f"Processing took: {time.time() - start:.2f} seconds")
```

### Memory Issues

**Symptoms:**

- Out of memory errors
- System slowdown
- Process killed

**Solutions:**

```bash
# Monitor memory usage
# Use file path mode instead of base64
# Process images sequentially instead of parallel
# Reduce image size before processing
```

## Debugging

### Enable Debug Logging

```bash
# Set debug level
export MCP_LOG_LEVEL=DEBUG

# Run server with debug output
MCP_LOG_LEVEL=DEBUG uvx albumentations-mcp

# Check logs in output directory
cat outputs/*/processing_log.jsonl
```

### Test with CLI Demo

```bash
# Test processing without MCP client
uv run python -m albumentations_mcp.demo \
    --image examples/cat.jpg \
    --prompt "add blur" \
    --seed 42

# This isolates MCP vs processing issues
```

### Validate Configuration

```python
# Check pipeline status
status = get_pipeline_status()
print(f"Pipeline ready: {status.get('pipeline_ready', False)}")
print(f"Registered hooks: {status.get('registered_hooks', [])}")

# Test transforms
transforms = list_available_transforms()
print(f"Available transforms: {len(transforms['transforms'])}")

# Test presets
presets = list_available_presets()
print(f"Available presets: {len(presets['presets'])}")
```

## Environment Variables

### Configuration Options

```bash
# Logging
export MCP_LOG_LEVEL=DEBUG          # DEBUG, INFO, WARNING, ERROR

# File handling
export OUTPUT_DIR="./my_outputs"    # Custom output directory
export MAX_FILE_SIZE_MB=100         # Increase file size limit

# Processing
export PROCESSING_TIMEOUT_SECONDS=600  # Increase timeout
export DEFAULT_SEED=42              # Set default seed

# Features
export ENABLE_VISION_VERIFICATION=true  # Enable AI verification
```

### Validation

```bash
# Check environment
env | grep -E "(MCP_|OUTPUT_|MAX_|PROCESSING_|DEFAULT_|ENABLE_)"

# Test configuration
uv run python -c "
from src.albumentations_mcp.config import get_config_summary
print(get_config_summary())
"
```

## Getting Help

### Diagnostic Steps

1. **Test with validate_prompt** - Verify prompt understanding
2. **Check available transforms** - Use list_available_transforms
3. **Try a preset** - Use known-good preset to isolate issues
4. **Simplify the request** - Start with single transform
5. **Check logs** - Review error messages and warnings

### Information to Include in Bug Reports

- Operating system and Python version
- MCP client being used (Claude Desktop, Kiro IDE, etc.)
- Full error message and stack trace
- Image size and format
- Prompt or preset being used
- Environment variables set
- Debug logs if available

### Resources

- **GitHub Issues**: [Report bugs](https://github.com/ramsi-k/albumentations-mcp/issues)
- **Discussions**: [Ask questions](https://github.com/ramsi-k/albumentations-mcp/discussions)
- **Email**: [ramsi.kalia@gmail.com](mailto:ramsi.kalia@gmail.com)

### Self-Help Tools

```python
# Use built-in troubleshooting resource
# This provides comprehensive troubleshooting guide
troubleshooting_guide = troubleshooting_common_issues()
print(troubleshooting_guide)

# Get best practices
best_practices = preset_pipelines_best_practices()
print(best_practices)
```
