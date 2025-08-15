"""Memory management and resource utilities."""


def format_bytes(size_bytes: int) -> str:
    """Format byte size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def estimate_memory_usage(width: int, height: int, channels: int = 3) -> int:
    """Estimate memory usage for image processing.

    Args:
        width: Image width
        height: Image height
        channels: Number of channels (default: 3 for RGB)

    Returns:
        Estimated memory usage in bytes
    """
    # Base memory for image data
    base_memory = width * height * channels

    # Processing overhead (2x for intermediate results)
    processing_overhead = base_memory * 2

    return base_memory + processing_overhead
