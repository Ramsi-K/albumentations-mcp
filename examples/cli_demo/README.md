# Albumentations MCP CLI Demo

This demo CLI (`examples/cli_demo/cli.py`) calls functions directly from `src/albumentations_mcp/server.py` — no MCP server, no LLM, no network. It’s meant for quick local testing of tools, prompts, and resources.

## Usage

Run from the repository root:

```bash
python examples/cli_demo/cli.py --help
python examples/cli_demo/cli.py <subcommand> --help
```

## Core Commands

- augment: Apply augmentations using path/base64/session and prompt or preset.
  - Example (prompt): `python examples/cli_demo/cli.py augment --image-path examples/basic_images/cat.jpg --prompt "add gaussian blur and rotate 15 degrees"`
  - Example (preset): `python examples/cli_demo/cli.py augment --image-path examples/basic_images/test_image.jpg --preset portrait --seed 42`
  - Notes: Provide exactly one of `--image-path`, `--image-b64`, or `--session-id`; and either `--prompt` or `--preset`.

- validate: Preview transforms for a natural-language prompt.
  - `python examples/cli_demo/cli.py validate --prompt "increase brightness and add noise"`

- transforms: List available transforms and descriptions.
  - `python examples/cli_demo/cli.py transforms`

- presets: List built-in presets with details.
  - `python examples/cli_demo/cli.py presets`

- load: Load image (file/URL/base64) and get a `session_id` for reuse.
  - `python examples/cli_demo/cli.py load --image-source examples/basic_images/cat.jpg`

- set-seed: Set or clear a default seed used by `augment`.
  - Set: `python examples/cli_demo/cli.py set-seed --seed 1337`
  - Clear: `python examples/cli_demo/cli.py set-seed`

- status: Show pipeline status and registered hooks.
  - `python examples/cli_demo/cli.py status`

## References and Guides

- quick-ref: Condensed transform keywords.
  - `python examples/cli_demo/cli.py quick-ref`

- transforms-guide: JSON guide for transforms.
  - `python examples/cli_demo/cli.py transforms-guide`

- policy-presets: JSON for built-in presets.
  - `python examples/cli_demo/cli.py policy-presets`

- examples: Practical transform examples/patterns (JSON).
  - `python examples/cli_demo/cli.py examples`

- troubleshooting: Common issues and solutions (JSON).
  - `python examples/cli_demo/cli.py troubleshooting`

## Prompt Generators

- compose-preset: Generate a policy-building prompt from a base preset.
  - `python examples/cli_demo/cli.py compose-preset --base portrait --tweak-note "gentle color boost" --output-format json`

- explain-effects: Produce plain-English explanation of a pipeline JSON.
  - Inline: `python examples/cli_demo/cli.py explain-effects --pipeline-json '{"transforms": []}'`
  - From file: `python examples/cli_demo/cli.py explain-effects --pipeline-json-file examples/pipeline.json`

- augmentation-parser: Generate guidance to parse a user request.
  - `python examples/cli_demo/cli.py augmentation-parser --user-prompt "add blur and rotate 10 degrees"`

- vision-verification: Generate a prompt to verify augmentation results between two images.
  - `python examples/cli_demo/cli.py vision-verification --original-image-path path/to/original.png --augmented-image-path path/to/aug.png --requested-transforms "blur + rotate"`

- error-handler: Generate user-friendly error text.
  - `python examples/cli_demo/cli.py error-handler --error-type processing --error-message "B64_INVALID" --user-context "upload via base64"`

## Notes

- All commands call functions in `src/albumentations_mcp/server.py` directly.
- No MCP protocol, no LLM; outputs are printed to stdout.
- Artifacts from `augment` are saved under `outputs/` by default; use `--output-dir` to override.

## Where Things Live

- CLI demo: `examples/cli_demo/cli.py`
- Server tools/prompts/resources: `src/albumentations_mcp/server.py`
- Presets and pipeline: `src/albumentations_mcp/presets.py`, `src/albumentations_mcp/pipeline.py`
