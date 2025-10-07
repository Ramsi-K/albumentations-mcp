# Start Here - Contributing to Albumentations-MCP

Welcome to Albumentations-MCP! This guide will help you find the perfect way to contribute to our project.

## 🚀 Project Status

**Current Version:** Beta v0.1.0b3 (Published on PyPI)
**Test Coverage:** 97% (383/394 tests passing)
**Status:** Production-ready with room for expansion

## 🎯 Quick Start for Contributors

### 1. **First Time Contributors** (Good First Issues)

Perfect if you're new to open source or this project:

- **Documentation Improvements**: Fix typos, add examples, improve clarity
- **Test Coverage**: Add tests for edge cases or missing scenarios
- **Code Quality**: Fix linting issues, improve error messages
- **Examples**: Create more usage examples for different domains

### 2. **Expand Transform Mappings** (High Impact)

**Current Status:** ~20 natural language patterns supported
**Goal:** 50+ patterns for comprehensive coverage

**What we need:**

- More creative phrases like "make it vintage", "add film grain"
- Domain-specific patterns for medical, satellite, artistic use cases
- Better parameter extraction from natural language
- Synonym support and phrase variations

**Files to work with:** `src/albumentations_mcp/parser.py`

### 3. **New Preset Configurations** (High Impact)

**Current Presets:** `segmentation`, `portrait`, `lowlight`
**Goal:** 10+ domain-specific presets

**Needed presets:**

- **Medical**: X-ray, MRI, ultrasound augmentation
- **Satellite**: Aerial imagery, GIS applications
- **Document**: OCR, document scanning improvements
- **Artistic**: Creative effects, style transfer preparation
- **Scientific**: Microscopy, astronomy, research imagery

**Files to work with:** `src/albumentations_mcp/presets.py`

### 4. **Performance & Reliability** (Medium Complexity)

**Current Issues:** 11 failing tests, optimization opportunities

- Fix remaining test failures (file path processing, resource cleanup)
- Optimize processing for large images
- Improve MCP client timeout handling
- Add batch processing capabilities

### 5. **Advanced Features** (High Complexity)

For experienced contributors:

- GPU/CUDA acceleration support
- Classification consistency checking
- Custom hook development framework
- Advanced analytics and monitoring

## 🛠 How to Get Started

### Step 1: Set Up Development Environment

```bash
# Clone the repository
git clone https://github.com/ramsi-k/albumentations-mcp
cd albumentations-mcp

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests to ensure everything works
uv run pytest
```

### Step 2: Explore the Codebase

**Key Files:**

- `src/albumentations_mcp/server.py` - Main MCP server with tools
- `src/albumentations_mcp/parser.py` - Natural language processing
- `src/albumentations_mcp/presets.py` - Preset configurations
- `src/albumentations_mcp/hooks/` - Extensible hook system
- `tests/` - Comprehensive test suite

### Step 3: Choose Your Contribution

1. **Browse existing issues** or create a new one using our templates
2. **Check the areas above** that match your interests and skill level
3. **Start small** - even fixing a typo helps!
4. **Ask questions** - we're here to help

## 📋 Contribution Ideas by Skill Level

### Beginner (Good First Issues)

- [ ] Add more usage examples to README
- [ ] Improve error messages to be more user-friendly
- [ ] Add docstrings to functions missing them
- [ ] Fix typos or improve documentation clarity
- [ ] Add tests for existing functionality

### Intermediate

- [ ] Add 5-10 new natural language patterns to parser
- [ ] Create a new preset for a specific domain (medical, artistic, etc.)
- [ ] Improve parameter validation and error handling
- [ ] Add support for new image formats
- [ ] Optimize memory usage for large images

### Advanced

- [ ] Implement batch processing for multiple images
- [ ] Add GPU acceleration support
- [ ] Create custom hook development framework
- [ ] Implement classification consistency checking
- [ ] Add comprehensive performance monitoring

## 🎨 Specific Contribution Opportunities

### Transform Mappings Needed

```python
# Examples of patterns we'd love to support:
"make it vintage" → Sepia + Vignette + Noise
"simulate old photo" → Sepia + Blur + Noise + Vignette
"add film grain" → GaussNoise with specific parameters
"create HDR effect" → CLAHE + Contrast adjustments
"simulate rain" → Rain transform with droplets
"add lens flare" → LensFlare transform
"make it look painted" → Artistic blur + color adjustments
```

### Preset Ideas

```python
# Presets we need:
medical_preset = {
    "description": "Subtle augmentations preserving diagnostic information",
    "transforms": [
        {"name": "Rotate", "params": {"limit": 5, "p": 0.3}},
        {"name": "GaussNoise", "params": {"var_limit": (5, 15), "p": 0.2}},
        # ... more transforms
    ]
}

satellite_preset = {
    "description": "Augmentations for aerial and satellite imagery",
    "transforms": [
        {"name": "RandomBrightnessContrast", "params": {"p": 0.5}},
        {"name": "HueSaturationValue", "params": {"p": 0.3}},
        # ... more transforms
    ]
}
```

## 🤝 Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **GitHub Issues**: Report bugs, request features
- **Email**: [ramsi.kalia@gmail.com](mailto:ramsi.kalia@gmail.com)

## 📚 Resources

- [Contributing Guide](contributing.md) - Detailed development setup
- [Architecture Overview](architecture.md) - System design
- [API Documentation](examples.md) - Usage examples
- [Troubleshooting](troubleshooting.md) - Common issues

## 🏆 Recognition

All contributors are recognized in our README and release notes. We appreciate every contribution, no matter how small!

---

**Ready to contribute?** Pick an area that interests you and create an issue using our templates, or browse existing issues with the `good first issue` label.
