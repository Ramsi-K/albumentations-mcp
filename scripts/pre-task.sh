#!/bin/bash
# Pre-task quality check script
# Run this before starting any implementation task

echo "🔍 Pre-Task Quality Checks"
echo "=========================="

echo "1. Checking existing implementation..."
echo "   - Search codebase for similar functionality"
echo "   - Verify architecture fit"
echo "   - Check dependencies"

echo "2. Quality tools status..."
uv run black --version
uv run ruff --version  
uv run mypy --version

echo "3. Current test status..."
uv run pytest --collect-only -q

echo "4. Linting current state..."
uv run ruff check src/ tests/ --statistics

echo ""
echo "✅ Pre-task checks complete"
echo "📝 Remember to:"
echo "   - Add file summary & TODO tree to new files"
echo "   - Document code review findings in docstrings"
echo "   - Write tests for new functionality"
echo "   - Run post-task.sh when complete"