@echo off
REM MCP Integration Testing Runner (Windows)
REM 
REM This script provides easy commands to run MCP integration tests
REM Usage:
REM   scripts\run_mcp_tests.bat [inspector|clients|regression|all]

setlocal

REM Default to all tests
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

echo 🧪 Running MCP Integration Tests (%TEST_TYPE%)...
echo ================================================

REM Ensure we're in the right directory
cd /d "%~dp0\.."

REM Run the Python test script
if "%TEST_TYPE%"=="inspector" (
    uv run python scripts/test_mcp_integration.py --inspector
) else if "%TEST_TYPE%"=="clients" (
    uv run python scripts/test_mcp_integration.py --clients
) else if "%TEST_TYPE%"=="regression" (
    uv run python scripts/test_mcp_integration.py --regression
) else (
    uv run python scripts/test_mcp_integration.py --all
)

echo.
echo ✅ MCP Integration Testing Complete!
echo 📊 Check mcp_test_results.json for detailed results
echo 📝 Tasks.md has been updated with test results

endlocal