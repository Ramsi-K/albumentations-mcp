# VLM (Nano Banana / Gemini) Integration

Integrates Google Gemini 2.5 Flash Image (preview) for semantic/contextual edits alongside Albumentations.

## Enable VLM (choose one; do not mix)

Option A — file (preferred)

1) Create `config/vlm.json` (non‑secret options):

```json
{
  "enabled": true,
  "provider": "google",
  "model": "gemini-2.5-flash-image-preview"
}
```

2) Provide your API key via OS env (one of): `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `VLM_API_KEY`, or `NANO_BANANA_API_KEY`.

Option B — inline env (no file)

```bash
ENABLE_VLM=true
VLM_PROVIDER=google
VLM_MODEL=gemini-2.5-flash-image-preview
# API key via OS env as above
```

Note: The loader auto‑discovers `config/vlm.json` if `VLM_CONFIG_PATH` is not set.

## Tools (quick reference)

- `check_vlm_config()` – readiness without exposing secrets
- `vlm_generate_preview(prompt)` – text→image exploration; saves under `outputs/vlm_tests/`; no session
- `vlm_edit_image(image_path|session_id, prompt, edit_type?)` – image‑conditioned edit; full session (original + edited, verification markdown, metadata, logs). `edit_type`: `edit`, `inpaint`, `style_transfer`, `compose`
- `vlm_suggest_recipe(task, constraints_json?, save?, output_dir?)` – planning only; returns Alb Compose + optional `VLMEdit` template; can save under `outputs/recipes/`

## MCP Env Examples (choose one)

File‑based config:

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "OUTPUT_DIR": "./outputs",
        "ENABLE_VLM": "true",
        "VLM_CONFIG_PATH": "config/vlm.json"
      }
    }
  }
}
```

Inline env:

```json
{
  "mcpServers": {
    "albumentations": {
      "command": "uvx",
      "args": ["albumentations-mcp"],
      "env": {
        "OUTPUT_DIR": "./outputs",
        "ENABLE_VLM": "true",
        "VLM_PROVIDER": "google",
        "VLM_MODEL": "gemini-2.5-flash-image-preview"
      }
    }
  }
}
```

## Example Flows

Preview (no session):

```python
vlm_generate_preview(prompt="Neon night street, cinematic moodboard")
```

Edit (session + verification):

```python
vlm_edit_image(
  image_path="examples/basic_images/cat.jpg",
  prompt=(
    "Using the provided photo of a cat, add a small, knitted wizard hat. "
    "Preserve identity, pose, lighting, and composition."
  ),
  edit_type="edit",
)
```

Plan + Save:

```python
plan = vlm_suggest_recipe(
  task="domain_shift",
  constraints_json='{"output_count": 1, "identity_preserve": true}',
  save=True,
)
print(plan["paths"])  # outputs/recipes/<timestamp>_<task>_<hash>/
```

## Example Recipe (shape)

```json
{
  "recipe": {
    "alb": {
      "Compose": [
        {"name": "RandomBrightnessContrast", "parameters": {"brightness_limit": 0.12, "contrast_limit": 0.12}, "probability": 0.7},
        {"name": "HueSaturationValue", "parameters": {"hue_shift_limit": 6, "sat_shift_limit": 12}, "probability": 0.5},
        {"name": "MotionBlur", "parameters": {"blur_limit": [3, 7]}, "probability": 0.3}
      ]
    },
    "vlm": {
      "VLMEdit": {
        "prompt_template": "Using the provided image of [subject], please [add/remove/modify] [element]. Preserve identity, pose, lighting, and composition.",
        "edit_type": "edit",
        "vlm_required": true
      }
    }
  },
  "execution_plan": {"order": "alb_then_vlm", "output_count": 3, "seed_strategy": "fixed_per_variant"},
  "recipe_hash": "<hash>"
}
```

## Where files are saved

- Preview images → `outputs/vlm_tests/`
- Edits (full session) → `outputs/<timestamp>_<id>/` (images/, analysis/, metadata/, logs/)
- Saved recipes → `outputs/recipes/<timestamp>_<task>_<hash>/` (see `examples/recipes_example/` for a sanitized example)
