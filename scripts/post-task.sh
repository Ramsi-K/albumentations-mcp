#!/bin/bash
# Post-task quality check script  
# Run this after completing any implementation task

echo "🔧 Post-Task Quality Checks"
echo "==========================="

echo "1. Formatting code..."
uv run black src/ tests/

echo "2. Linting and fixing issues..."
uv run ruff check src/ tests/ --fix

echo "3. Type checking..."
uv run mypy src/

echo "4. Running tests..."
uv run pytest tests/ -v

echo "5. Final quality report..."
echo "   Lines of code:"
find src/ -name "*.py" -exec wc -l {} + | tail -1

echo "   Test coverage:"
uv run pytest tests/ --quiet --tb=no | grep "passed"

echo "   Remaining linting issues:"
uv run ruff check src/ tests/ --statistics

echo ""
echo "✅ Post-task checks complete"
echo "📝 Next steps:"
echo "   - Review any remaining linting issues"
echo "   - Update documentation if needed"
echo "   - Generate commit message"
echo "   - Mark task as complete in tasks.md"