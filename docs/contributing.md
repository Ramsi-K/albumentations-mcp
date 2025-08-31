# Contributing

## Development Setup

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/ramsi-k/albumentations-mcp
cd albumentations-mcp

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Development Commands

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/ --fix

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Build package
uv build
```

## Code Standards

### Style Guidelines

- **Formatting**: Black with default settings
- **Linting**: Ruff with project configuration
- **Type Hints**: Full type annotations required
- **Docstrings**: Google-style docstrings for all public APIs
- **Import Organization**: isort for consistent import ordering

### Quality Requirements

- **Test Coverage**: Minimum 90% coverage required
- **Type Safety**: All code must pass mypy validation
- **Documentation**: All public functions must have docstrings
- **Error Handling**: Graceful error handling with proper logging

### Code Review Process

All contributions require:

1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer review
3. **Testing**: New features require comprehensive tests
4. **Documentation**: Updates to relevant documentation

## Project Structure

```
src/albumentations_mcp/
├── server.py              # MCP server with tools, prompts, and resources
├── parser.py              # Natural language parsing
├── pipeline.py            # Processing pipeline
├── processor.py           # Image processing engine
├── presets.py             # Preset configurations
├── hooks/                 # Hook system
├── utils/                 # Utility functions
└── config.py              # Configuration management

tests/                     # Test suite
├── test_*.py              # Unit tests
├── fixtures/              # Test data
└── integration/           # Integration tests

docs/                      # Documentation
├── setup.md               # Installation guide
├── api.md                 # API reference
├── examples.md            # Usage examples
├── troubleshooting.md     # Troubleshooting guide
└── contributing.md        # This file
```

## Areas for Contribution

### High Priority

- **Performance Optimization**: Faster processing for large images
- **Additional Transform Mappings**: More natural language patterns
- **GPU Acceleration**: CUDA-enabled transforms
- **Batch Processing**: Multi-image processing tools

### Medium Priority

- **New Presets**: Domain-specific augmentation presets
- **Enhanced Error Messages**: More helpful error guidance
- **Additional MCP Clients**: Support for more MCP implementations
- **Documentation**: Examples and tutorials

### Low Priority

- **UI Components**: Web interface for testing
- **Metrics and Analytics**: Processing statistics
- **Custom Hook Development**: Framework for user hooks
- **Cloud Integration**: S3/GCS support

## Testing Guidelines

### Test Categories

```bash
# Unit tests - Fast, isolated component tests
uv run pytest tests/unit/

# Integration tests - End-to-end workflow tests
uv run pytest tests/integration/

# Performance tests - Timing and resource usage
uv run pytest tests/performance/ -m slow
```

### Writing Tests

```python
# Example test structure
import pytest
from albumentations_mcp.parser import parse_prompt

class TestPromptParser:
    def test_simple_blur_parsing(self):
        """Test basic blur prompt parsing."""
        result = parse_prompt("add blur")

        assert result.success
        assert len(result.transforms) == 1
        assert result.transforms[0].name == "Blur"
        assert result.confidence > 0.8

    def test_invalid_prompt_handling(self):
        """Test graceful handling of invalid prompts."""
        result = parse_prompt("invalid nonsense")

        assert not result.success
        assert len(result.warnings) > 0
        assert "unrecognized" in result.message.lower()
```

### Test Data

- Use fixtures for consistent test data
- Include edge cases and error conditions
- Test with various image formats and sizes
- Validate both success and failure paths

## Documentation

### API Documentation

- All public functions require docstrings
- Include parameter types and descriptions
- Provide usage examples
- Document exceptions and error conditions

### User Documentation

- Keep examples practical and tested
- Include common use cases
- Provide troubleshooting guidance
- Update README for major changes

## Release Process

### Version Management

- Follow [Semantic Versioning](https://semver.org/)
- Update version in `pyproject.toml`
- Create release notes for changes
- Tag releases in Git

### Pre-Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version bumped appropriately
- [ ] Release notes prepared
- [ ] Breaking changes documented

### Release Steps

```bash
# Run full test suite
uv run pytest

# Build package
uv build

# Test installation
pip install dist/albumentations_mcp-*.whl

# Create release
git tag v0.1.0
git push origin v0.1.0

# Publish to PyPI
uv publish
```

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication

### Issue Reporting

When reporting issues:

1. **Search existing issues** first
2. **Provide minimal reproduction** case
3. **Include system information** (OS, Python version, etc.)
4. **Attach relevant logs** and error messages
5. **Describe expected vs actual** behavior

### Feature Requests

For new features:

1. **Describe the use case** and motivation
2. **Provide examples** of desired behavior
3. **Consider implementation** complexity
4. **Discuss alternatives** if applicable

## Getting Help

### Development Questions

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Email**: [ramsi.kalia@gmail.com](mailto:ramsi.kalia@gmail.com) for direct contact

### Code Review

We welcome code review from the community:

- **GitHub Pull Requests**: Standard review process
- **AI Code Review**: Tools like CodeRabbit, Codacy, SonarCloud
- **Professional Review**: Consider hiring experts for production use
- **Peer Review**: Share with Python/CV communities

### Resources

- **Python Style Guide**: [PEP 8](https://pep8.org/)
- **Type Hints**: [PEP 484](https://pep.python.org/pep-0484/)
- **Docstring Conventions**: [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- **Testing Best Practices**: [pytest documentation](https://docs.pytest.org/)

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.
