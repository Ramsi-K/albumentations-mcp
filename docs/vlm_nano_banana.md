# VLM (Nano Banana / Gemini) Integration

This server integrates Google Gemini 2.5 Flash Image (preview) for semantic/contextual edits alongside Albumentations.

## Enable VLM

Use environment variables or a config file. The loader auto‑discovers `config/vlm.json`.

Env:

```bash
ENABLE_VLM=true
VLM_PROVIDER=google
VLM_MODEL=gemini-2.5-flash-image-preview
GOOGLE_API_KEY=...  # or GEMINI_API_KEY / VLM_API_KEY / NANO_BANANA_API_KEY
```

File (`config/vlm.json`):

```json
{
  "enabled": true,
  "provider": "google",
  "model": "gemini-2.5-flash-image-preview",
  "api_key": "..."  // optional; can be provided via env
}
```

Check readiness:

```python
check_vlm_config()  # -> { status: ready|partial|disabled, ... }
```

## Tools

- `vlm_generate_preview(prompt)`: text→image prompt exploration; saves under `outputs/vlm_tests/`; no session.
- `vlm_edit_image(image_path|session_id, prompt, edit_type?)`: image‑conditioned edit; runs full session (original + edited, verification markdown, metadata, logs).
- `vlm_suggest_recipe(task, constraints_json?, save?, output_dir?)`: planning‑only; returns Alb Compose + optional VLMEdit prompt template and can save under `outputs/recipes/`.

Supported `edit_type`: `edit`, `inpaint`, `style_transfer`, `compose`.

## Prompting

Use `get_gemini_prompt_templates()` for editing templates and best‑practices.

Example edit prompt:

```
Using the provided photograph of a cat, add a small, knitted wizard hat that sits naturally on its head.
Preserve identity, pose, lighting, and composition. Photorealistic look, natural colors.
```

Tip: Be explicit (“return only an edited image; no text”) when needed.

## Workflow Examples

Preview (no session):

```python
vlm_generate_preview(prompt="Neon night street, cinematic moodboard")
```

Edit (session + verification):

```python
vlm_edit_image(
  image_path="examples/basic_images/cat.jpg",
  prompt="Using the provided photo of a cat, add a small, knitted wizard hat. Preserve identity, pose, lighting, composition.",
  edit_type="edit",
)
```

Plan + Save + Run:

```python
plan = vlm_suggest_recipe(
  task="domain_shift",
  constraints_json='{"output_count": 1, "identity_preserve": true}',
  save=True,
)
paths = plan["paths"]  # outputs/recipes/<timestamp>_<task>_<hash>/
```

## Results

Example outputs (preview + edit). Filenames kept from generation time.

Preview (text→image):

![Neon moodboard preview](../assets/Generated%20Image%20September%2008,%202025%20-%209_35AM.png)

Edit (image + prompt; cat with wizard hat):

![Cat edit result](../assets/Generated%20Image%20September%2008,%202025%20-%209_36AM.png)

Alternate VLM output (Nano Banana branding):

![Nano Banana sample](../assets/nano%20banana.jpeg)

## Outputs & Verification

Edits create a session under `outputs/` with:

- `images/`: original + edited PNGs
- `analysis/`: visual verification markdown (prompt for client VLM to evaluate)
- `metadata/`: metadata JSON (transforms, timings, warnings)
- `logs/`: processing log

## Limitations (MVP)

- Multi‑image composition not wired yet (single input image).
- Verification is prompt+assets for client VLM; no server‑side judgment.
- The preview API surfaces may change; keep your SDK up to date.

## Acceptance Criteria (MVP)

- `check_vlm_config` reports `ready` when provider/model/enabled/key are present (env or config file).
- `vlm_edit_image` produces edited image plus session artifacts (original + edited under images/, visual_eval.md under analysis/, metadata + logs).
- `vlm_generate_preview` saves a preview image under `outputs/vlm_tests/`.
- `vlm_suggest_recipe` returns a structured plan and can save it under `outputs/recipes/`.
