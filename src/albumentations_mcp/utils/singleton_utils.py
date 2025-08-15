"""Singleton pattern management utilities."""

import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Thread lock for singleton management
_singleton_lock = threading.Lock()


def create_singleton(
    instance_var_name: str,
    factory_func: Callable[[], T],
    module_globals: dict[str, Any],
) -> T:
    """Create singleton instance with thread safety.

    Args:
        instance_var_name: Name of the global instance variable
        factory_func: Function to create new instance
        module_globals: Module's globals() dictionary

    Returns:
        Singleton instance
    """
    instance = module_globals.get(instance_var_name)
    if instance is None:
        with _singleton_lock:
            # Double-check locking pattern
            instance = module_globals.get(instance_var_name)
            if instance is None:
                instance = factory_func()
                module_globals[instance_var_name] = instance
    return instance


def singleton_getter(
    instance_var_name: str,
    factory_func: Callable[[], T],
) -> Callable[[], T]:
    """Create a singleton getter function.

    Args:
        instance_var_name: Name of the global instance variable
        factory_func: Function to create new instance

    Returns:
        Getter function that returns singleton instance
    """

    def getter() -> T:
        # Get the caller's globals
        import inspect

        frame = inspect.currentframe().f_back
        module_globals = frame.f_globals
        return create_singleton(instance_var_name, factory_func, module_globals)

    return getter
