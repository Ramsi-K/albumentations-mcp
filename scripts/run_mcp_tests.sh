#!/bin/bash
# MCP Integration Testing Runner
# 
# This script provides easy commands to run MCP integration tests
# Usage:
#   ./scripts/run_mcp_tests.sh [inspector|clients|regression|all]

set -e

# Default to all tests
TEST_TYPE=${1:-all}

echo "🧪 Running MCP Integration Tests ($TEST_TYPE)..."
echo "================================================"

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Run the Python test script
case $TEST_TYPE in
    "inspector")
        uv run python scripts/test_mcp_integration.py --inspector
        ;;
    "clients")
        uv run python scripts/test_mcp_integration.py --clients
        ;;
    "regression")
        uv run python scripts/test_mcp_integration.py --regression
        ;;
    "all"|*)
        uv run python scripts/test_mcp_integration.py --all
        ;;
esac

echo ""
echo "✅ MCP Integration Testing Complete!"
echo "📊 Check mcp_test_results.json for detailed results"
echo "📝 Tasks.md has been updated with test results"