#!/usr/bin/env python3
"""
Simple CLI demo that calls functions directly from src/albumentations_mcp/server.py.

- No MCP server, LLM, or external APIs invoked.
- Uses argparse with subcommands for key functions.
- Prints results to stdout with clear, human-friendly output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Ensure src/ is on sys.path for local usage (src layout)
def _ensure_src_on_path() -> None:
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # <repo>/examples/cli_demo/cli.py -> <repo>
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_src_on_path()


# Import server functions directly (no MCP runtime)
try:
    from albumentations_mcp.server import (
        augment_image,
        validate_prompt,
        list_available_transforms,
        list_available_presets,
        load_image_for_processing,
        set_default_seed,
        get_pipeline_status,
        get_quick_transform_reference,
        transforms_guide,
        policy_presets,
        available_transforms_examples,
        troubleshooting_common_issues,
        compose_preset,
        explain_effects,
        augmentation_parser,
        vision_verification,
        error_handler,
    )
except Exception as e:  # pragma: no cover - import-time guard for local runs
    print(f"Failed to import server functions: {e}", file=sys.stderr)
    raise SystemExit(1)


def _print_json(obj: object) -> None:
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except TypeError:
        # Fallback for non-serializable objects
        print(str(obj))


def _print_json_or_text(maybe_json: str) -> None:
    try:
        parsed = json.loads(maybe_json)
        _print_json(parsed)
    except Exception:
        print(maybe_json)


# Subcommand handlers
def cmd_augment(args: argparse.Namespace) -> int:
    # Enforce mutual exclusivity
    input_count = sum(
        bool(x) for x in [args.image_path, args.image_b64, args.session_id]
    )
    if input_count != 1:
        print(
            "Error: Provide exactly one of --image-path, --image-b64, or --session-id",
            file=sys.stderr,
        )
        return 2

    if bool(args.prompt) == bool(args.preset):
        print(
            "Error: Provide either --prompt or --preset (but not both)", file=sys.stderr
        )
        return 2

    result = augment_image(
        image_path=args.image_path or "",
        image_b64=args.image_b64 or "",
        session_id=args.session_id or "",
        prompt=args.prompt or "",
        seed=args.seed,
        preset=args.preset,
        output_dir=args.output_dir,
    )
    # augment_image returns a string message
    print(result)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    res = validate_prompt(args.prompt)
    _print_json(res)
    return 0


def cmd_transforms(_: argparse.Namespace) -> int:
    res = list_available_transforms()
    _print_json(res)
    return 0


def cmd_presets(_: argparse.Namespace) -> int:
    res = list_available_presets()
    _print_json(res)
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    res = load_image_for_processing(args.image_source)
    print(res)
    return 0


def cmd_set_seed(args: argparse.Namespace) -> int:
    # If --seed is omitted, clear the default seed
    seed = args.seed
    res = set_default_seed(seed)
    _print_json(res)
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    res = get_pipeline_status()
    _print_json(res)
    return 0


def cmd_quick_ref(_: argparse.Namespace) -> int:
    res = get_quick_transform_reference()
    _print_json(res)
    return 0


def cmd_transforms_guide(_: argparse.Namespace) -> int:
    res = transforms_guide()  # returns JSON string
    _print_json_or_text(res)
    return 0


def cmd_policy_presets(_: argparse.Namespace) -> int:
    res = policy_presets()  # returns JSON string
    _print_json_or_text(res)
    return 0


def cmd_examples(_: argparse.Namespace) -> int:
    res = available_transforms_examples()  # returns JSON string
    _print_json_or_text(res)
    return 0


def cmd_troubleshooting(_: argparse.Namespace) -> int:
    res = troubleshooting_common_issues()  # returns JSON string
    _print_json_or_text(res)
    return 0


def cmd_compose_preset(args: argparse.Namespace) -> int:
    text = compose_preset(args.base, args.tweak_note or "", args.output_format)
    print(text)
    return 0


def cmd_explain_effects(args: argparse.Namespace) -> int:
    pipeline_json: str
    if args.pipeline_json_file:
        p = Path(args.pipeline_json_file)
        pipeline_json = p.read_text(encoding="utf-8")
    else:
        pipeline_json = args.pipeline_json
    text = explain_effects(pipeline_json, args.image_context or "")
    print(text)
    return 0


def cmd_augmentation_parser(args: argparse.Namespace) -> int:
    # This returns a prompt (string) for LLM parsing guidance; we just print it
    text = augmentation_parser(args.user_prompt)
    print(text)
    return 0


def cmd_vision_verification(args: argparse.Namespace) -> int:
    text = vision_verification(
        args.original_image_path, args.augmented_image_path, args.requested_transforms
    )
    print(text)
    return 0


def cmd_error_handler(args: argparse.Namespace) -> int:
    text = error_handler(args.error_type, args.error_message, args.user_context or "")
    print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="albumentations-mcp-demo",
        description="CLI demo: call functions from albumentations_mcp.server directly",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # augment
    p_aug = sub.add_parser("augment", help="Run augment_image on an input")
    p_aug.add_argument("--image-path", help="Path to an image file")
    p_aug.add_argument("--image-b64", help="Base64-encoded image data")
    p_aug.add_argument("--session-id", help="Existing session ID from load")
    p_aug.add_argument("--prompt", help="Natural language prompt for transforms")
    p_aug.add_argument(
        "--preset",
        choices=["segmentation", "portrait", "lowlight"],
        help="Preset name (mutually exclusive with --prompt)",
    )
    p_aug.add_argument("--seed", type=int, help="Random seed for reproducibility")
    p_aug.add_argument(
        "--output-dir", help="Output directory for artifacts (default: outputs)"
    )
    p_aug.set_defaults(func=cmd_augment)

    # validate
    p_val = sub.add_parser("validate", help="Call validate_prompt and show results")
    p_val.add_argument("--prompt", required=True, help="Prompt to validate")
    p_val.set_defaults(func=cmd_validate)

    # transforms
    p_tr = sub.add_parser("transforms", help="List available transforms")
    p_tr.set_defaults(func=cmd_transforms)

    # presets
    p_pr = sub.add_parser("presets", help="List available presets")
    p_pr.set_defaults(func=cmd_presets)

    # load image (session)
    p_load = sub.add_parser(
        "load", help="Load image (path/URL/base64) and get a session_id"
    )
    p_load.add_argument(
        "--image-source", required=True, help="File path, URL, or base64 image data"
    )
    p_load.set_defaults(func=cmd_load)

    # set default seed
    p_seed = sub.add_parser("set-seed", help="Set or clear the default seed")
    p_seed.add_argument(
        "--seed", type=int, help="Seed value; omit to clear the default seed"
    )
    p_seed.set_defaults(func=cmd_set_seed)

    # status
    p_st = sub.add_parser("status", help="Show pipeline status and registered hooks")
    p_st.set_defaults(func=cmd_status)

    # quick reference
    p_qr = sub.add_parser("quick-ref", help="Condensed transform keywords reference")
    p_qr.set_defaults(func=cmd_quick_ref)

    # resource-like data (JSON strings)
    p_tg = sub.add_parser("transforms-guide", help="JSON guide for transforms")
    p_tg.set_defaults(func=cmd_transforms_guide)

    p_pp = sub.add_parser("policy-presets", help="JSON of built-in presets")
    p_pp.set_defaults(func=cmd_policy_presets)

    p_ex = sub.add_parser("examples", help="Examples and usage patterns")
    p_ex.set_defaults(func=cmd_examples)

    p_tb = sub.add_parser("troubleshooting", help="Common issues and solutions")
    p_tb.set_defaults(func=cmd_troubleshooting)

    # prompt-generating helpers
    p_cp = sub.add_parser(
        "compose-preset", help="Generate a policy prompt from a preset"
    )
    p_cp.add_argument(
        "--base",
        required=True,
        choices=["segmentation", "portrait", "lowlight"],
        help="Base preset name",
    )
    p_cp.add_argument("--tweak-note", help="Optional tweaks/notes to apply")
    p_cp.add_argument(
        "--output-format",
        default="json",
        choices=["json", "yaml", "text"],
        help="Output format for the generated policy prompt",
    )
    p_cp.set_defaults(func=cmd_compose_preset)

    p_ee = sub.add_parser(
        "explain-effects",
        help="Generate natural-language explanation of a pipeline JSON",
    )
    group = p_ee.add_mutually_exclusive_group(required=True)
    group.add_argument("--pipeline-json", help="Pipeline JSON string")
    group.add_argument(
        "--pipeline-json-file", help="Path to a file containing pipeline JSON"
    )
    p_ee.add_argument("--image-context", help="Optional image/use-case context")
    p_ee.set_defaults(func=cmd_explain_effects)

    p_ap = sub.add_parser(
        "augmentation-parser", help="Generate a parsing prompt for a user request"
    )
    p_ap.add_argument(
        "--user-prompt", required=True, help="User's natural language request"
    )
    p_ap.set_defaults(func=cmd_augmentation_parser)

    p_vv = sub.add_parser(
        "vision-verification",
        help="Generate a verification prompt for comparing two images",
    )
    p_vv.add_argument(
        "--original-image-path", required=True, help="Path to the original image"
    )
    p_vv.add_argument(
        "--augmented-image-path", required=True, help="Path to the augmented image"
    )
    p_vv.add_argument(
        "--requested-transforms",
        required=True,
        help="Description of requested transforms",
    )
    p_vv.set_defaults(func=cmd_vision_verification)

    p_err = sub.add_parser(
        "error-handler", help="Generate helpful error messaging text"
    )
    p_err.add_argument(
        "--error-type",
        required=True,
        help="Error category (parsing, processing, validation, etc.)",
    )
    p_err.add_argument("--error-message", required=True, help="Technical error message")
    p_err.add_argument(
        "--user-context", help="Optional description of what the user was doing"
    )
    p_err.set_defaults(func=cmd_error_handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
