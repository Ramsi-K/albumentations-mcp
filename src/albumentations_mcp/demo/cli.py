#!/usr/bin/env python3
"""
CLI Demo Interface for Albumentations MCP

Provides a command-line interface for testing and demonstrating the
albumentations-mcp functionality without requiring MCP client setup.

Usage:
    python -m albumentations_mcp.demo --image examples/cat.jpg --prompt "add blur"
    python -m albumentations_mcp.demo --image test.png --prompt "increase brightness" --seed 42
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from PIL import Image

from ..pipeline import parse_prompt_with_hooks
from ..presets import get_available_presets, get_preset, preset_to_transforms
from ..processor import get_processor


def setup_logging(verbose: bool = False) -> None:
    """Set up logging for the demo."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def load_image(image_path: str) -> Image.Image:
    """Load an image from file path.

    Args:
        image_path: Path to the image file

    Returns:
        PIL Image object

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        image = Image.open(image_path)
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except Exception as e:
        raise ValueError(f"Failed to load image {image_path}: {e}") from e


def save_image(image: Image.Image, output_path: str) -> None:
    """Save an image to file path.

    Args:
        image: PIL Image object to save
        output_path: Path where to save the image
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"✓ Saved augmented image to: {output_path}")
    except Exception as e:
        print(f"✗ Failed to save image to {output_path}: {e}")


async def demo_augment_image(
    image_path: str,
    prompt: str,
    seed: int | None = None,
    output_dir: str = "outputs",
    verbose: bool = False,
    preset: str | None = None,
) -> bool:
    """Demonstrate image augmentation with the given parameters.

    Args:
        image_path: Path to input image
        prompt: Natural language augmentation prompt
        seed: Optional seed for reproducible results
        output_dir: Directory to save outputs
        verbose: Enable verbose logging
        preset: Optional preset name to use instead of parsing prompt

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Load input image
        print(f"📁 Loading image: {image_path}")
        image = load_image(image_path)
        print(f"✓ Loaded image: {image.size[0]}x{image.size[1]} pixels")

        # Handle preset or parse prompt
        if preset:
            print(f"🎯 Using preset: '{preset}'")
            preset_config = get_preset(preset)
            if not preset_config:
                print(f"✗ Unknown preset: {preset}")
                available_presets = list(get_available_presets().keys())
                print(f"  Available presets: {', '.join(available_presets)}")
                return False

            print(f"✓ Loaded preset: {preset_config['name']}")
            print(f"  Description: {preset_config['description']}")

            transforms = preset_to_transforms(preset)
            parse_time = 0.0

            # Create a mock parse result for consistency
            parse_result = {
                "success": True,
                "transforms": transforms,
                "message": f"Using preset: {preset}",
                "warnings": [],
                "session_id": f"preset_{preset}_{int(time.time())}",
                "metadata": {
                    "preset_used": preset,
                    "preset_config": preset_config,
                },
            }
        else:
            # Parse prompt using hook-integrated pipeline
            print(f"🔍 Parsing prompt: '{prompt}'")
            start_time = time.time()

            parse_result = await parse_prompt_with_hooks(prompt)
            parse_time = time.time() - start_time

            if not parse_result["success"] or not parse_result["transforms"]:
                print(f"✗ Failed to parse prompt: {parse_result['message']}")
                if parse_result["warnings"]:
                    for warning in parse_result["warnings"]:
                        print(f"  ⚠️  {warning}")
                return False

            print(f"✓ Parsed prompt in {parse_time:.3f}s")
        print(f"  Found {len(parse_result['transforms'])} transforms:")
        for i, transform in enumerate(parse_result["transforms"], 1):
            print(f"    {i}. {transform['name']} - {transform.get('parameters', {})}")

        # Apply transforms using processor
        print("🎨 Applying transforms...")
        if seed is not None:
            print(f"  Using seed: {seed}")

        start_time = time.time()
        processor = get_processor()
        processing_result = processor.process_image(
            image,
            parse_result["transforms"],
            seed=seed,
        )
        process_time = time.time() - start_time

        if not processing_result.success or not processing_result.augmented_image:
            print(f"✗ Failed to process image: {processing_result.error_message}")
            return False

        print(f"✓ Processed image in {process_time:.3f}s")

        # Show processing statistics
        if verbose:
            print(f"  Applied transforms: {len(processing_result.applied_transforms)}")
            if processing_result.skipped_transforms:
                print(
                    f"  Skipped transforms: {len(processing_result.skipped_transforms)}",
                )
            if processing_result.metadata:
                for key, value in processing_result.metadata.items():
                    if key.startswith("seed_") or key in [
                        "effective_seed",
                        "reproducible",
                    ]:
                        print(f"  {key}: {value}")

        # Generate output filename
        input_name = Path(image_path).stem
        input_ext = Path(image_path).suffix or ".jpg"
        timestamp = int(time.time())
        seed_suffix = f"_seed{seed}" if seed is not None else ""
        output_filename = f"{input_name}_augmented_{timestamp}{seed_suffix}{input_ext}"
        output_path = os.path.join(output_dir, output_filename)

        # Save augmented image
        save_image(processing_result.augmented_image, output_path)

        # Save metadata if verbose
        if verbose:
            metadata_path = output_path.replace(input_ext, "_metadata.json")
            import json

            metadata = {
                "input_image": image_path,
                "prompt": prompt,
                "seed": seed,
                "transforms": parse_result["transforms"],
                "applied_transforms": [
                    {"name": t["name"], "parameters": t.get("parameters", {})}
                    for t in processing_result.applied_transforms
                ],
                "skipped_transforms": [
                    {"name": t["name"], "parameters": t.get("parameters", {})}
                    for t in processing_result.skipped_transforms
                ],
                "processing_time": process_time,
                "parse_time": parse_time,
                "session_id": parse_result["session_id"],
                "pipeline_metadata": processing_result.metadata,
            }

            try:
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2, default=str)
                print(f"✓ Saved metadata to: {metadata_path}")
            except Exception as e:
                print(f"⚠️  Failed to save metadata: {e}")

        print("🎉 Demo completed successfully!")
        print(f"   Total time: {parse_time + process_time:.3f}s")

        return True

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"✗ Demo failed: {e}")
        return False


def create_example_images(examples_dir: str = "examples") -> None:
    """Create example images for demo purposes.

    Args:
        examples_dir: Directory to create example images in
    """
    try:
        os.makedirs(examples_dir, exist_ok=True)

        # Create a simple test image
        from PIL import Image, ImageDraw

        # Create a colorful test image
        image = Image.new("RGB", (400, 300), color="white")
        draw = ImageDraw.Draw(image)

        # Draw some shapes for testing
        draw.rectangle([50, 50, 150, 150], fill="red", outline="black", width=2)
        draw.ellipse([200, 50, 300, 150], fill="blue", outline="black", width=2)
        draw.polygon(
            [(75, 200), (125, 175), (175, 200), (150, 250), (100, 250)],
            fill="green",
            outline="black",
        )

        # Add some text
        try:
            from PIL import ImageFont

            # Try to use a default font, fall back to basic if not available
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except OSError:
                font = ImageFont.load_default()
            draw.text((50, 260), "Test Image", fill="black", font=font)
        except ImportError:
            draw.text((50, 260), "Test Image", fill="black")

        # Save example image
        example_path = os.path.join(examples_dir, "test_image.jpg")
        image.save(example_path)
        print(f"✓ Created example image: {example_path}")

        # Create a simple cat-like image (geometric representation)
        cat_image = Image.new("RGB", (300, 300), color="lightgray")
        cat_draw = ImageDraw.Draw(cat_image)

        # Cat head (circle)
        cat_draw.ellipse([75, 75, 225, 225], fill="orange", outline="black", width=2)

        # Cat ears (triangles)
        cat_draw.polygon(
            [(100, 75), (125, 25), (150, 75)], fill="orange", outline="black",
        )
        cat_draw.polygon(
            [(150, 75), (175, 25), (200, 75)], fill="orange", outline="black",
        )

        # Cat eyes
        cat_draw.ellipse([110, 120, 130, 140], fill="green", outline="black")
        cat_draw.ellipse([170, 120, 190, 140], fill="green", outline="black")

        # Cat nose
        cat_draw.polygon(
            [(145, 150), (155, 150), (150, 160)], fill="pink", outline="black",
        )

        # Cat mouth
        cat_draw.arc([130, 160, 170, 180], 0, 180, fill="black", width=2)

        cat_path = os.path.join(examples_dir, "cat.jpg")
        cat_image.save(cat_path)
        print(f"✓ Created example cat image: {cat_path}")

    except Exception as e:
        print(f"⚠️  Failed to create example images: {e}")


def main() -> int:
    """Main entry point for the demo CLI."""
    parser = argparse.ArgumentParser(
        description="Albumentations MCP Demo - Test image augmentation with natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m albumentations_mcp.demo --image examples/cat.jpg --prompt "add blur"
  python -m albumentations_mcp.demo --image test.png --prompt "increase brightness" --seed 42
  python -m albumentations_mcp.demo --image examples/cat.jpg --preset portrait --seed 42
  python -m albumentations_mcp.demo --image dark_image.jpg --preset lowlight --verbose
  python -m albumentations_mcp.demo --create-examples
  python -m albumentations_mcp.demo --list-presets
        """,
    )

    parser.add_argument(
        "--image",
        type=str,
        help="Path to input image file",
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="Natural language description of desired augmentations",
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results (0 to 4294967295)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save output files (default: outputs)",
    )

    parser.add_argument(
        "--create-examples",
        action="store_true",
        help="Create example images in examples/ directory",
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="Use a predefined preset instead of parsing prompt (segmentation, portrait, lowlight)",
    )

    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available presets and exit",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output and save metadata",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Handle list presets
    if args.list_presets:
        print("📋 Available Presets:")
        print("=" * 40)
        presets = get_available_presets()
        for name, config in presets.items():
            print(f"\n🎯 {name}")
            print(f"   {config['description']}")
            if "use_cases" in config:
                print(f"   Use cases: {', '.join(config['use_cases'])}")
            print(f"   Transforms: {len(config['transforms'])}")
        return 0

    # Handle create examples
    if args.create_examples:
        print("🎨 Creating example images...")
        create_example_images()
        return 0

    # Validate required arguments
    if not args.image:
        parser.error(
            "--image is required (unless using --create-examples or --list-presets)",
        )

    if not args.prompt and not args.preset:
        parser.error("Either --prompt or --preset is required")

    if args.prompt and args.preset:
        parser.error("Cannot use both --prompt and --preset at the same time")

    # Validate seed range
    if args.seed is not None and not (0 <= args.seed <= 4294967295):
        parser.error("Seed must be between 0 and 4294967295")

    print("🚀 Albumentations MCP Demo")
    print("=" * 40)

    # Run the demo
    try:
        success = asyncio.run(
            demo_augment_image(
                image_path=args.image,
                prompt=args.prompt or "",
                seed=args.seed,
                output_dir=args.output_dir,
                verbose=args.verbose,
                preset=args.preset,
            ),
        )

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"✗ Demo failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
