"""Hook system for extensible image augmentation pipeline.

This module provides the core hook registry and execution framework
for the 8-stage extensible pipeline.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class HookStage(str, Enum):
    """Stages in the augmentation pipeline where hooks can be executed."""

    PRE_MCP = "pre_mcp"
    POST_MCP = "post_mcp"
    PRE_TRANSFORM = "pre_transform"
    POST_TRANSFORM = "post_transform"
    POST_TRANSFORM_VERIFY = "post_transform_verify"
    POST_TRANSFORM_CLASSIFY = "post_transform_classify"
    PRE_SAVE = "pre_save"
    POST_SAVE = "post_save"


@dataclass
class HookContext:
    """Context passed between hooks containing pipeline state."""

    session_id: str
    original_prompt: str
    image_data: Optional[bytes] = None
    parsed_transforms: Optional[List[Dict[str, Any]]] = None
    augmented_image: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class HookResult:
    """Result of hook execution."""

    def __init__(
        self,
        success: bool = True,
        context: Optional[HookContext] = None,
        error: Optional[str] = None,
        should_continue: bool = True,
    ):
        self.success = success
        self.context = context
        self.error = error
        self.should_continue = should_continue


class BaseHook(ABC):
    """Base class for all hooks."""

    def __init__(self, name: str, critical: bool = False):
        self.name = name
        self.critical = critical  # If True, pipeline stops on hook failure

    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """Execute the hook with given context."""
        pass

    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"


class HookRegistry:
    """Registry for managing and executing hooks."""

    def __init__(self):
        self._hooks: Dict[HookStage, List[BaseHook]] = {
            stage: [] for stage in HookStage
        }

    def register_hook(self, stage: HookStage, hook: BaseHook) -> None:
        """Register a hook for a specific stage."""
        self._hooks[stage].append(hook)
        logger.debug(f"Registered hook {hook} for stage {stage}")

    def unregister_hook(self, stage: HookStage, hook_name: str) -> bool:
        """Unregister a hook by name."""
        hooks = self._hooks[stage]
        for i, hook in enumerate(hooks):
            if hook.name == hook_name:
                del hooks[i]
                logger.debug(
                    f"Unregistered hook {hook_name} from stage {stage}"
                )
                return True
        return False

    def get_hooks(self, stage: HookStage) -> List[BaseHook]:
        """Get all hooks for a stage."""
        return self._hooks[stage].copy()

    async def execute_stage(
        self, stage: HookStage, context: HookContext
    ) -> HookResult:
        """Execute all hooks for a given stage."""
        hooks = self._hooks[stage]

        if not hooks:
            logger.debug(f"No hooks registered for stage {stage}")
            return HookResult(success=True, context=context)

        logger.info(f"Executing {len(hooks)} hooks for stage {stage}")

        for hook in hooks:
            try:
                logger.debug(f"Executing hook: {hook}")
                result = await hook.execute(context)

                if not result.success:
                    error_msg = f"Hook {hook.name} failed: {result.error}"
                    logger.error(error_msg)
                    context.errors.append(error_msg)

                    if hook.critical:
                        logger.error(
                            f"Critical hook {hook.name} failed, stopping pipeline"
                        )
                        return HookResult(
                            success=False,
                            context=context,
                            error=error_msg,
                            should_continue=False,
                        )

                if result.context:
                    context = result.context

                if not result.should_continue:
                    logger.info(f"Hook {hook.name} requested pipeline stop")
                    return HookResult(
                        success=True, context=context, should_continue=False
                    )

            except Exception as e:
                error_msg = f"Hook {hook.name} raised exception: {str(e)}"
                logger.error(error_msg, exc_info=True)
                context.errors.append(error_msg)

                if hook.critical:
                    logger.error(
                        f"Critical hook {hook.name} failed with exception, stopping pipeline"
                    )
                    return HookResult(
                        success=False,
                        context=context,
                        error=error_msg,
                        should_continue=False,
                    )

        logger.info(f"Completed stage {stage} successfully")
        return HookResult(success=True, context=context)

    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks by stage."""
        return {
            stage.value: [hook.name for hook in hooks]
            for stage, hooks in self._hooks.items()
        }


# Global hook registry instance
_hook_registry = None


def get_hook_registry() -> HookRegistry:
    """Get the global hook registry instance."""
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = HookRegistry()
    return _hook_registry


def register_hook(stage: HookStage, hook: BaseHook) -> None:
    """Convenience function to register a hook."""
    get_hook_registry().register_hook(stage, hook)


async def execute_stage(stage: HookStage, context: HookContext) -> HookResult:
    """Convenience function to execute a stage."""
    return await get_hook_registry().execute_stage(stage, context)
