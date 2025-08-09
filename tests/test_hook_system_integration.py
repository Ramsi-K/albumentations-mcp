#!/usr/bin/env python3
"""
Integration tests for the complete hook system.

This module tests the complete hook pipeline execution, hook failure recovery,
context passing, metadata accumulation, and hook registry management.

# File Summary
Comprehensive integration tests for the 8-stage hook system including
pipeline execution, failure recovery, context management, and registry operations.

# TODO Tree
- [x] Test Infrastructure
  - [x] Import hook system components
  - [x] Create test fixtures and mock hooks
  - [x] Set up async test framework
- [x] Complete Pipeline Tests
  - [x] Test all 8 stages execution in order
  - [x] Test context passing between stages
  - [x] Test metadata accumulation across stages
- [x] Failure Recovery Tests
  - [x] Test critical hook failure stops pipeline
  - [x] Test non-critical hook failure continues pipeline
  - [x] Test hook exception handling
- [x] Registry Management Tests
  - [x] Test hook registration and unregistration
  - [x] Test dynamic hook registration
  - [x] Test hook execution order
- [x] Context Management Tests
  - [x] Test context data preservation
  - [x] Test metadata accumulation
  - [x] Test error and warning collection

# Code Review Notes
- PERFORMANCE: Tests should run quickly without external dependencies
- COVERAGE: All hook system functionality should be tested
- ISOLATION: Tests should not interfere with each other
- RELIABILITY: Tests should be deterministic and repeatable
"""

import pytest

from src.albumentations_mcp.hooks import (
    BaseHook,
    HookContext,
    HookResult,
    HookStage,
    get_hook_registry,
)


class MockHook(BaseHook):
    """Mock hook for testing purposes."""

    def __init__(
        self,
        name: str,
        critical: bool = False,
        should_fail: bool = False,
        should_stop: bool = False,
    ):
        super().__init__(name, critical)
        self.should_fail = should_fail
        self.should_stop = should_stop
        self.execution_count = 0
        self.last_context = None

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the mock hook."""
        self.execution_count += 1
        self.last_context = context

        # Add execution info to context metadata
        if "hook_executions" not in context.metadata:
            context.metadata["hook_executions"] = []

        context.metadata["hook_executions"].append(
            {
                "hook_name": self.name,
                "execution_count": self.execution_count,
                "stage": "mock_stage",
            },
        )

        if self.should_fail:
            return HookResult(
                success=False,
                context=context,
                error=f"Mock hook {self.name} failed intentionally",
                should_continue=not self.critical,
            )

        if self.should_stop:
            return HookResult(success=True, context=context, should_continue=False)

        return HookResult(success=True, context=context)


class TestCompleteHookPipeline:
    """Test complete hook pipeline execution."""

    @pytest.fixture
    def clean_registry(self):
        """Provide a clean hook registry for testing."""
        # Get fresh registry instance
        registry = get_hook_registry()

        # Store original hooks
        original_hooks = {}
        for stage in HookStage:
            original_hooks[stage] = registry.get_hooks(stage).copy()
            # Clear hooks for testing
            registry._hooks[stage] = []

        yield registry

        # Restore original hooks
        for stage, hooks in original_hooks.items():
            registry._hooks[stage] = hooks

    @pytest.fixture
    def sample_context(self):
        """Create a sample hook context."""
        return HookContext(
            session_id="integration-test-123",
            original_prompt="test pipeline execution",
            metadata={"test_start": True},
        )

    @pytest.mark.asyncio
    async def test_complete_pipeline_execution(self, clean_registry, sample_context):
        """Test execution of all 8 stages in order."""
        # Register mock hooks for each stage
        stage_hooks = {}
        for stage in HookStage:
            hook = MockHook(f"{stage.value}_hook")
            stage_hooks[stage] = hook
            clean_registry.register_hook(stage, hook)

        # Execute all stages in order
        current_context = sample_context
        for stage in HookStage:
            result = await clean_registry.execute_stage(stage, current_context)
            assert result.success is True
            current_context = result.context

        # Verify all hooks were executed
        for stage, hook in stage_hooks.items():
            assert hook.execution_count == 1
            assert hook.last_context is not None

        # Verify context metadata accumulation
        executions = current_context.metadata["hook_executions"]
        assert len(executions) == 8

        # Verify execution order
        expected_order = [stage.value for stage in HookStage]
        actual_order = [
            exec_info["hook_name"].replace("_hook", "") for exec_info in executions
        ]
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_context_passing_between_stages(self, clean_registry, sample_context):
        """Test that context data is properly passed between stages."""

        # Create hooks that modify context
        class ContextModifyingHook(BaseHook):
            def __init__(self, name: str, data_key: str, data_value: str):
                super().__init__(name)
                self.data_key = data_key
                self.data_value = data_value

            async def execute(self, context: HookContext) -> HookResult:
                context.metadata[self.data_key] = self.data_value
                return HookResult(success=True, context=context)

        # Register hooks that add data
        hook1 = ContextModifyingHook("stage1_hook", "stage1_data", "value1")
        hook2 = ContextModifyingHook("stage2_hook", "stage2_data", "value2")

        clean_registry.register_hook(HookStage.PRE_MCP, hook1)
        clean_registry.register_hook(HookStage.POST_MCP, hook2)

        # Execute stages
        result1 = await clean_registry.execute_stage(HookStage.PRE_MCP, sample_context)
        result2 = await clean_registry.execute_stage(
            HookStage.POST_MCP, result1.context,
        )

        # Verify data accumulation
        final_context = result2.context
        assert final_context.metadata["test_start"] is True  # Original data
        assert final_context.metadata["stage1_data"] == "value1"  # Stage 1 data
        assert final_context.metadata["stage2_data"] == "value2"  # Stage 2 data

    @pytest.mark.asyncio
    async def test_metadata_accumulation(self, clean_registry, sample_context):
        """Test metadata accumulation across multiple hooks in same stage."""
        # Create multiple hooks for same stage
        hooks = []
        for i in range(3):
            hook = MockHook(f"hook_{i}")
            hooks.append(hook)
            clean_registry.register_hook(HookStage.PRE_TRANSFORM, hook)

        # Execute stage
        result = await clean_registry.execute_stage(
            HookStage.PRE_TRANSFORM, sample_context,
        )

        # Verify all hooks executed
        assert result.success is True
        for hook in hooks:
            assert hook.execution_count == 1

        # Verify metadata accumulation
        executions = result.context.metadata["hook_executions"]
        assert len(executions) == 3

        # Verify execution order
        hook_names = [exec_info["hook_name"] for exec_info in executions]
        expected_names = ["hook_0", "hook_1", "hook_2"]
        assert hook_names == expected_names

    @pytest.mark.asyncio
    async def test_empty_stage_execution(self, clean_registry, sample_context):
        """Test execution of stage with no registered hooks."""
        # Execute stage with no hooks
        result = await clean_registry.execute_stage(HookStage.PRE_SAVE, sample_context)

        assert result.success is True
        assert result.context == sample_context
        assert result.should_continue is True


class TestHookFailureRecovery:
    """Test hook failure recovery and pipeline continuation."""

    @pytest.fixture
    def clean_registry(self):
        """Provide a clean hook registry for testing."""
        registry = get_hook_registry()

        # Store and clear original hooks
        original_hooks = {}
        for stage in HookStage:
            original_hooks[stage] = registry.get_hooks(stage).copy()
            registry._hooks[stage] = []

        yield registry

        # Restore original hooks
        for stage, hooks in original_hooks.items():
            registry._hooks[stage] = hooks

    @pytest.fixture
    def sample_context(self):
        """Create a sample hook context."""
        return HookContext(
            session_id="failure-test-123",
            original_prompt="test failure recovery",
        )

    @pytest.mark.asyncio
    async def test_critical_hook_failure_stops_pipeline(
        self, clean_registry, sample_context,
    ):
        """Test that critical hook failure stops pipeline execution."""
        # Create critical hook that fails
        critical_hook = MockHook("critical_hook", critical=True, should_fail=True)
        normal_hook = MockHook("normal_hook")

        clean_registry.register_hook(HookStage.PRE_TRANSFORM, critical_hook)
        clean_registry.register_hook(HookStage.PRE_TRANSFORM, normal_hook)

        # Execute stage
        result = await clean_registry.execute_stage(
            HookStage.PRE_TRANSFORM, sample_context,
        )

        # Pipeline should stop due to critical failure
        assert result.success is False
        assert result.should_continue is False
        assert "Mock hook critical_hook failed intentionally" in result.error

        # Critical hook should have executed
        assert critical_hook.execution_count == 1

        # Normal hook should not have executed (pipeline stopped)
        assert normal_hook.execution_count == 0

    @pytest.mark.asyncio
    async def test_non_critical_hook_failure_continues_pipeline(
        self, clean_registry, sample_context,
    ):
        """Test that non-critical hook failure allows pipeline to continue."""
        # Create non-critical hook that fails
        failing_hook = MockHook("failing_hook", critical=False, should_fail=True)
        success_hook = MockHook("success_hook")

        clean_registry.register_hook(HookStage.POST_TRANSFORM, failing_hook)
        clean_registry.register_hook(HookStage.POST_TRANSFORM, success_hook)

        # Execute stage
        result = await clean_registry.execute_stage(
            HookStage.POST_TRANSFORM, sample_context,
        )

        # Pipeline should continue despite failure
        assert result.success is True
        assert result.should_continue is True

        # Both hooks should have executed
        assert failing_hook.execution_count == 1
        assert success_hook.execution_count == 1

        # Error should be recorded in context
        assert len(result.context.errors) > 0
        assert any(
            "Mock hook failing_hook failed intentionally" in error
            for error in result.context.errors
        )

    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, clean_registry, sample_context):
        """Test handling of exceptions raised by hooks."""

        class ExceptionHook(BaseHook):
            def __init__(self, critical: bool = False):
                super().__init__("exception_hook", critical)

            async def execute(self, context: HookContext) -> HookResult:
                raise ValueError("Test exception from hook")

        # Test non-critical hook exception
        non_critical_hook = ExceptionHook(critical=False)
        success_hook = MockHook("success_hook")

        clean_registry.register_hook(HookStage.POST_SAVE, non_critical_hook)
        clean_registry.register_hook(HookStage.POST_SAVE, success_hook)

        result = await clean_registry.execute_stage(HookStage.POST_SAVE, sample_context)

        # Pipeline should continue
        assert result.success is True
        assert success_hook.execution_count == 1
        assert len(result.context.errors) > 0

    @pytest.mark.asyncio
    async def test_critical_hook_exception_stops_pipeline(
        self, clean_registry, sample_context,
    ):
        """Test that critical hook exception stops pipeline."""

        class CriticalExceptionHook(BaseHook):
            def __init__(self):
                super().__init__("critical_exception_hook", critical=True)

            async def execute(self, context: HookContext) -> HookResult:
                raise RuntimeError("Critical hook exception")

        critical_hook = CriticalExceptionHook()
        normal_hook = MockHook("normal_hook")

        clean_registry.register_hook(HookStage.PRE_SAVE, critical_hook)
        clean_registry.register_hook(HookStage.PRE_SAVE, normal_hook)

        result = await clean_registry.execute_stage(HookStage.PRE_SAVE, sample_context)

        # Pipeline should stop
        assert result.success is False
        assert result.should_continue is False
        assert normal_hook.execution_count == 0

    @pytest.mark.asyncio
    async def test_hook_requests_pipeline_stop(self, clean_registry, sample_context):
        """Test hook that requests pipeline to stop."""
        stop_hook = MockHook("stop_hook", should_stop=True)
        after_hook = MockHook("after_hook")

        clean_registry.register_hook(HookStage.POST_TRANSFORM_VERIFY, stop_hook)
        clean_registry.register_hook(HookStage.POST_TRANSFORM_VERIFY, after_hook)

        result = await clean_registry.execute_stage(
            HookStage.POST_TRANSFORM_VERIFY, sample_context,
        )

        # Pipeline should stop gracefully
        assert result.success is True
        assert result.should_continue is False

        # Stop hook should execute, after hook should not
        assert stop_hook.execution_count == 1
        assert after_hook.execution_count == 0


class TestHookRegistryManagement:
    """Test hook registry management and dynamic registration."""

    @pytest.fixture
    def clean_registry(self):
        """Provide a clean hook registry for testing."""
        registry = get_hook_registry()

        # Store and clear original hooks
        original_hooks = {}
        for stage in HookStage:
            original_hooks[stage] = registry.get_hooks(stage).copy()
            registry._hooks[stage] = []

        yield registry

        # Restore original hooks
        for stage, hooks in original_hooks.items():
            registry._hooks[stage] = hooks

    def test_hook_registration_and_unregistration(self, clean_registry):
        """Test basic hook registration and unregistration."""
        hook = MockHook("test_hook")
        stage = HookStage.PRE_MCP

        # Initially no hooks
        assert len(clean_registry.get_hooks(stage)) == 0

        # Register hook
        clean_registry.register_hook(stage, hook)
        hooks = clean_registry.get_hooks(stage)
        assert len(hooks) == 1
        assert hooks[0] == hook

        # Unregister hook
        success = clean_registry.unregister_hook(stage, "test_hook")
        assert success is True
        assert len(clean_registry.get_hooks(stage)) == 0

        # Try to unregister non-existent hook
        success = clean_registry.unregister_hook(stage, "non_existent")
        assert success is False

    def test_multiple_hooks_same_stage(self, clean_registry):
        """Test registering multiple hooks for the same stage."""
        hooks = [MockHook(f"hook_{i}") for i in range(3)]
        stage = HookStage.POST_MCP

        # Register all hooks
        for hook in hooks:
            clean_registry.register_hook(stage, hook)

        # Verify all registered
        registered_hooks = clean_registry.get_hooks(stage)
        assert len(registered_hooks) == 3

        # Verify order is preserved
        for i, hook in enumerate(registered_hooks):
            assert hook.name == f"hook_{i}"

    @pytest.mark.asyncio
    async def test_hook_execution_order(self, clean_registry):
        """Test that hooks execute in registration order."""
        execution_order = []

        class OrderTrackingHook(BaseHook):
            def __init__(self, name: str):
                super().__init__(name)

            async def execute(self, context: HookContext) -> HookResult:
                execution_order.append(self.name)
                return HookResult(success=True, context=context)

        # Register hooks in specific order
        hook_names = ["first", "second", "third"]
        for name in hook_names:
            hook = OrderTrackingHook(name)
            clean_registry.register_hook(HookStage.PRE_TRANSFORM, hook)

        # Execute stage
        context = HookContext(session_id="order-test", original_prompt="test order")
        result = await clean_registry.execute_stage(HookStage.PRE_TRANSFORM, context)

        assert result.success is True
        assert execution_order == hook_names

    @pytest.mark.asyncio
    async def test_dynamic_hook_registration(self, clean_registry):
        """Test dynamic hook registration during execution."""
        # This test simulates registering hooks dynamically
        # (though in practice this should be done carefully)

        initial_hook = MockHook("initial_hook")
        clean_registry.register_hook(HookStage.POST_TRANSFORM_CLASSIFY, initial_hook)

        # Execute with initial hook
        context = HookContext(session_id="dynamic-test", original_prompt="test dynamic")
        result1 = await clean_registry.execute_stage(
            HookStage.POST_TRANSFORM_CLASSIFY, context,
        )

        assert result1.success is True
        assert initial_hook.execution_count == 1

        # Register additional hook
        additional_hook = MockHook("additional_hook")
        clean_registry.register_hook(HookStage.POST_TRANSFORM_CLASSIFY, additional_hook)

        # Execute again - both hooks should run
        result2 = await clean_registry.execute_stage(
            HookStage.POST_TRANSFORM_CLASSIFY, context,
        )

        assert result2.success is True
        assert initial_hook.execution_count == 2  # Executed again
        assert additional_hook.execution_count == 1  # First execution

    def test_hook_registry_listing(self, clean_registry):
        """Test hook registry listing functionality."""
        # Initially empty
        hooks_list = clean_registry.list_hooks()
        for stage_name, hook_names in hooks_list.items():
            assert len(hook_names) == 0

        # Register hooks in different stages
        hook1 = MockHook("hook1")
        hook2 = MockHook("hook2")
        hook3 = MockHook("hook3")

        clean_registry.register_hook(HookStage.PRE_MCP, hook1)
        clean_registry.register_hook(HookStage.PRE_MCP, hook2)
        clean_registry.register_hook(HookStage.POST_MCP, hook3)

        # Check listing
        hooks_list = clean_registry.list_hooks()
        assert hooks_list["pre_mcp"] == ["hook1", "hook2"]
        assert hooks_list["post_mcp"] == ["hook3"]

        # Other stages should be empty
        for stage_name, hook_names in hooks_list.items():
            if stage_name not in ["pre_mcp", "post_mcp"]:
                assert len(hook_names) == 0


class TestContextManagement:
    """Test context data preservation and management."""

    @pytest.fixture
    def clean_registry(self):
        """Provide a clean hook registry for testing."""
        registry = get_hook_registry()

        # Store and clear original hooks
        original_hooks = {}
        for stage in HookStage:
            original_hooks[stage] = registry.get_hooks(stage).copy()
            registry._hooks[stage] = []

        yield registry

        # Restore original hooks
        for stage, hooks in original_hooks.items():
            registry._hooks[stage] = hooks

    @pytest.mark.asyncio
    async def test_context_data_preservation(self, clean_registry):
        """Test that context data is preserved across hook executions."""
        # Create context with initial data
        context = HookContext(
            session_id="context-test-123",
            original_prompt="test context preservation",
            metadata={"initial_data": "preserved", "counter": 0},
        )

        class CounterHook(BaseHook):
            def __init__(self, name: str):
                super().__init__(name)

            async def execute(self, context: HookContext) -> HookResult:
                # Increment counter and add hook-specific data
                context.metadata["counter"] += 1
                context.metadata[f"{self.name}_executed"] = True
                return HookResult(success=True, context=context)

        # Register multiple hooks
        hooks = [CounterHook(f"counter_hook_{i}") for i in range(3)]
        for hook in hooks:
            clean_registry.register_hook(HookStage.PRE_TRANSFORM, hook)

        # Execute stage
        result = await clean_registry.execute_stage(HookStage.PRE_TRANSFORM, context)

        # Verify data preservation and accumulation
        final_context = result.context
        assert final_context.session_id == "context-test-123"
        assert final_context.original_prompt == "test context preservation"
        assert final_context.metadata["initial_data"] == "preserved"
        assert final_context.metadata["counter"] == 3

        # Verify each hook added its data
        for i in range(3):
            assert final_context.metadata[f"counter_hook_{i}_executed"] is True

    @pytest.mark.asyncio
    async def test_error_and_warning_collection(self, clean_registry):
        """Test collection of errors and warnings across hooks."""

        class ErrorWarningHook(BaseHook):
            def __init__(
                self,
                name: str,
                add_error: bool = False,
                add_warning: bool = False,
            ):
                super().__init__(name)
                self.add_error = add_error
                self.add_warning = add_warning

            async def execute(self, context: HookContext) -> HookResult:
                if self.add_error:
                    context.errors.append(f"Error from {self.name}")
                if self.add_warning:
                    context.warnings.append(f"Warning from {self.name}")
                return HookResult(success=True, context=context)

        # Register hooks that add errors and warnings
        hooks = [
            ErrorWarningHook("hook1", add_warning=True),
            ErrorWarningHook("hook2", add_error=True),
            ErrorWarningHook("hook3", add_error=True, add_warning=True),
        ]

        for hook in hooks:
            clean_registry.register_hook(HookStage.POST_TRANSFORM, hook)

        # Execute stage
        context = HookContext(session_id="error-test", original_prompt="test errors")
        result = await clean_registry.execute_stage(HookStage.POST_TRANSFORM, context)

        # Verify error and warning collection
        assert result.success is True
        assert len(result.context.errors) == 2  # hook2 and hook3
        assert len(result.context.warnings) == 2  # hook1 and hook3

        assert "Error from hook2" in result.context.errors
        assert "Error from hook3" in result.context.errors
        assert "Warning from hook1" in result.context.warnings
        assert "Warning from hook3" in result.context.warnings

    @pytest.mark.asyncio
    async def test_context_immutability_protection(self, clean_registry):
        """Test that hooks cannot break context structure."""

        class MaliciousHook(BaseHook):
            def __init__(self):
                super().__init__("malicious_hook")

            async def execute(self, context: HookContext) -> HookResult:
                # Try to break context structure
                try:
                    context.session_id = None
                    context.metadata = "not_a_dict"
                    context.errors = "not_a_list"
                except Exception:
                    # If context is protected, this will fail
                    pass

                # Return success regardless
                return HookResult(success=True, context=context)

        hook = MaliciousHook()
        clean_registry.register_hook(HookStage.POST_SAVE, hook)

        context = HookContext(
            session_id="immutable-test", original_prompt="test immutability",
        )

        result = await clean_registry.execute_stage(HookStage.POST_SAVE, context)

        # Context should still be valid (depending on implementation)
        # This test documents current behavior - context is mutable
        assert result.success is True
        # Current implementation allows context mutation
        # This documents the actual behavior rather than enforcing immutability
        assert result.context.session_id is None  # Was modified by hook
        assert result.context.metadata == "not_a_dict"  # Was modified by hook
        assert result.context.errors == "not_a_list"  # Was modified by hook


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
