# Quality Checklist Template

**Use this checklist for every task since Kiro hooks may not be working properly**

## Pre-Implementation (Before writing any code)

- [ ] **Check Existing Implementation**: Search codebase for similar functionality
- [ ] **Architecture Review**: Ensure new code fits overall project structure
- [ ] **Dependency Check**: Verify all required imports and dependencies
- [ ] **Requirements Mapping**: Confirm implementation addresses specific requirements
- [ ] **Test Strategy**: Plan how the code will be tested

## During Implementation (For each file created/edited)

- [ ] **File Summary**: Add clear summary of file purpose to docstring
- [ ] **TODO Tree**: Create comprehensive TODO list in docstring (mark completed items)
- [ ] **Function Documentation**: Add docstrings with args, returns, raises
- [ ] **Type Hints**: Use modern type annotations (dict vs Dict, etc.)
- [ ] **Error Handling**: Proper exception handling with specific error types

## Code Review (For each function written)

- [ ] **Complexity Check**: Functions under 10 cyclomatic complexity
- [ ] **Single Responsibility**: Each function does one thing well
- [ ] **Input Validation**: Proper validation of parameters
- [ ] **Edge Cases**: Handle empty inputs, invalid data, etc.
- [ ] **Security**: No injection vulnerabilities, safe regex patterns
- [ ] **Performance**: Efficient algorithms, no obvious bottlenecks

## Code Refactoring Guidelines

**Only refactor code that truly needs improvement. If something works well and is readable, leave it as is.**

- [ ] **Code Duplication**: Look for repeated patterns that could be extracted to utilities
- [ ] **Function Complexity**: Identify functions >10 cyclomatic complexity that could be simplified
- [ ] **Error Handling**: Standardize error handling patterns and logging
- [ ] **Type Hints**: Update to modern Python type annotations (dict vs Dict, list vs List)
- [ ] **Documentation**: Improve docstrings only if they're unclear or missing important information
- [ ] **Performance**: Only optimize if there are clear performance issues
- [ ] **Security**: Address actual security vulnerabilities, not theoretical ones

## Post-Implementation (After code is written)

- [ ] **Quality Tools**: Run ruff, black, mypy
  ```bash
  uv run black src/
  uv run ruff check src/ --fix
  uv run mypy src/
  ```
- [ ] **Tests**: Write comprehensive tests covering:
  - [ ] Happy path scenarios
  - [ ] Error conditions
  - [ ] Edge cases
  - [ ] Parameter validation
- [ ] **Integration**: Verify code works with existing components
- [ ] **Documentation**: Update README, docstrings, comments

## Task Completion

- [ ] **All Tests Passing**: Run full test suite
- [ ] **Quality Metrics**: Address critical linting issues (ignore minor style preferences)
- [ ] **Commit Message**: Generate proper conventional commit message
- [ ] **Code Review Notes**: Document any technical debt or future improvements

## Quality Commands

```bash
# Install/update dependencies
uv sync

# Format code
uv run black src/ tests/

# Lint and fix issues
uv run ruff check src/ tests/ --fix

# Type checking
uv run mypy src/

# Run tests
uv run pytest tests/ -v

# Run all quality checks
uv run black src/ tests/ && uv run ruff check src/ tests/ --fix && uv run mypy src/ && uv run pytest tests/ -v
```

## Hook System Status

**Current Status**: Kiro hooks may not be executing properly due to IDE configuration issues.

**Attempted Fixes**:

- Simplified hook trigger conditions (removed complex patterns)
- Updated hook versions
- Created test hooks with minimal configuration
- Reduced trigger conflicts between hooks

**Fallback Strategy**: Use this manual checklist for quality assurance until hooks are working.

## Notes

- This checklist serves as a fallback for non-working Kiro hooks
- Check off items as you complete them
- Add task-specific items as needed
- Focus on meaningful improvements, not cosmetic changes
- Keep this updated as project evolves
