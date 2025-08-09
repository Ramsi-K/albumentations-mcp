"""Simple global seed management for MCP session-level seeding.

This module provides minimal seed management for session-level reproducibility
without reimplementing Albumentations' native seeding functionality.
"""

from typing import Optional

# Global session seed storage
_global_seed: Optional[int] = None


def set_global_seed(seed: Optional[int]) -> None:
    """Set global seed for the session.

    Args:
        seed: Seed value to use globally, or None to clear global seed
    """
    global _global_seed
    _global_seed = seed


def get_global_seed() -> Optional[int]:
    """Get current global seed.

    Returns:
        Current global seed or None if not set
    """
    return _global_seed


def get_effective_seed(transform_seed: Optional[int]) -> Optional[int]:
    """Get the effective seed to use for transforms.

    Priority: transform_seed > global_seed > None (random)

    Args:
        transform_seed: Per-transform seed parameter

    Returns:
        Effective seed to use, or None for random
    """
    if transform_seed is not None:
        return transform_seed
    return _global_seed


def get_seed_metadata(
    effective_seed: Optional[int], transform_seed: Optional[int]
) -> dict:
    """Get seed metadata for tracking and reproducibility.

    Args:
        effective_seed: The actual seed used
        transform_seed: The per-transform seed provided

    Returns:
        Metadata dictionary for logging and reports
    """
    global_seed = get_global_seed()

    return {
        "seed_used": effective_seed is not None,
        "effective_seed": effective_seed,
        "transform_seed": transform_seed,
        "global_seed": global_seed,
        "reproducible": effective_seed is not None,
        "seed_source": (
            "transform"
            if transform_seed is not None
            else "global" if global_seed is not None else "random"
        ),
    }
