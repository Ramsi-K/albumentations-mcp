"""Async execution utilities to eliminate duplicate asyncio patterns."""

import asyncio
import concurrent.futures
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_async_safely(async_func: Callable, *args: Any) -> Any:
    """Helper to run async functions safely, handling event loop issues.

    This eliminates duplicate asyncio handling patterns across the codebase.

    Args:
        async_func: The async function to run
        *args: Arguments to pass to the async function

    Returns:
        Result from the async function
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args))
                return future.result()
        else:
            return asyncio.run(async_func(*args))
    except RuntimeError:
        return asyncio.run(async_func(*args))


def timed_operation(operation_name: str | None = None):
    """Decorator to time function execution and log performance.

    Args:
        operation_name: Optional name for the operation (defaults to function name)

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            from .logging_utils import log_error_with_context, log_performance

            name = operation_name or func.__name__
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_error_with_context(
                    e,
                    f"Timed operation {name} failed",
                    operation=name,
                    duration=duration,
                )
                raise

        return wrapper

    return decorator
