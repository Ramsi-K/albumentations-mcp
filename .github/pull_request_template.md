# Pull Request

## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code quality improvement (refactoring, formatting, etc.)

## Related Issues

Closes #(issue number)

## Changes Made

- [ ] List specific changes made
- [ ] Include any new files created
- [ ] Mention any files modified significantly

## Testing

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have tested this with actual MCP clients (Claude Desktop/Kiro)

### Test Commands Run

```bash
# List the commands you ran to test your changes
uv run pytest
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

## Quality Checklist

- [ ] My code follows the project's style guidelines (Black, Ruff, MyPy)
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Documentation

- [ ] I have updated relevant documentation (README, docs/, docstrings)
- [ ] I have added examples for new features
- [ ] I have updated the changelog (if applicable)

## Screenshots (if applicable)

Add screenshots or examples of the changes in action.

## Additional Notes

Any additional information that reviewers should know about this PR.

## Reviewer Notes

- [ ] Code review completed
- [ ] Tests pass in CI
- [ ] Documentation is adequate
- [ ] Breaking changes are documented
- [ ] Performance impact is acceptable
