"""Simple global seed management for MCP session-level seeding.

This module provides minimal seed management for session-level reproducibility
without reimplementing Albumentations' native seeding functionality.
"""

# Global session seed storage
_global_seed: int | None = None


def set_global_seed(seed: int | None) -> None:
    """Set global seed for the session.

    Args:
        seed: Seed value to use globally, or None to clear global seed
    """
    global _global_seed
    _global_seed = seed


def get_global_seed() -> int | None:
    """Get current global seed.

    Returns:
        Current global seed or None if not set
    """
    return _global_seed


def get_effective_seed(transform_seed: int | None) -> int | None:
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
    effective_seed: int | None,
    transform_seed: int | None,
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
            else "global"
            if global_seed is not None
            else "random"
        ),
    }
