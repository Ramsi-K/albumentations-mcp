# VLM Integration (Nano Banana) + Visual Verification — MVP Plan

This plan adds Google Gemini 2.5 Flash Image Preview support to Albumentations MCP for semantic/contextual augmentations, reusing the existing verification pipeline. (The “Nano Banana” hackathon refers to using Gemini 2.5; provider is `google`, model is `gemini-2.5-flash-image-preview`). It’s structured in small, verifiable phases.

## Goals

- Add VLM tools gated by environment/config (no secrets in JSON).
- Produce VLM artifacts inside the existing session folder and run visual verification.
- Keep Albumentations flow intact and backward compatible (no MCP JSON schema/version bump).

---

## Phase 0 — Touchpoints & Structure

- Config
  - `src/albumentations_mcp/config.py` (add VLM getters)
  - New: `src/albumentations_mcp/vlm/config.py` (optional helper)
- VLM Adapter (scaffold)
  - New: `src/albumentations_mcp/vlm/base.py`
  - New: `src/albumentations_mcp/vlm/google_gemini.py`
- Server (MCP tools + conditional registration)
  - `src/albumentations_mcp/server.py`
- Hooks and artifacts
  - `src/albumentations_mcp/hooks/pre_save.py` (add VLM file paths)
  - `src/albumentations_mcp/hooks/post_save.py` (persist VLM artifacts)
  - `src/albumentations_mcp/hooks/post_transform_verify.py` (recognize VLM outputs)
  - `src/albumentations_mcp/verification.py` (no change, already good)
- Docs & prompts
  - `README.md`, `docs/` (quickstart, examples, env)

---

## Phase 1 — Config & Env Detection

Checklist

- [ ] Add non-secret toggles to runtime (can be set via OS env or client JSON env map):
  - `ENABLE_VLM=true`
  - `VLM_PROVIDER=google`
  - `VLM_MODEL=gemini-2.5-flash-image-preview`
  - Optional: `VLM_CONFIG_PATH=./config/vlm.json` (no secrets)
- [ ] Keep secrets only in OS environment (never in JSON):
  - `NANO_BANANA_API_KEY=<secret>`
- [ ] In `config.py`, add accessors:
  - `is_vlm_enabled()` → bool
  - `get_vlm_provider()` → str | None
  - `get_vlm_model()` → str | None
  - `get_vlm_config_path()` → str | None
  - `has_vlm_api_key()` → bool (only presence check)
- [ ] Add a small loader in `vlm/config.py` (optional): merges ENV and optional JSON file; never returns the API key value, only presence.

Acceptance

- `check_vlm_config` (Phase 3) reports `status=ready` when `ENABLE_VLM=true` and API key present; `partial` otherwise; `disabled` when `ENABLE_VLM` not true.

---

## Phase 2 — VLM Adapter Scaffold

Files

- `src/albumentations_mcp/vlm/base.py`
  - Interface: `class VLMClient` with methods:
    - `suggest_recipe(image, task, constraints) -> {recipe, rationale}` (optional for MVP)
    - `apply(image, prompt_or_recipe, *, model, seed=None, timeout=None) -> PIL.Image`
  - Utility: simple retry/backoff wrapper.
- `src/albumentations_mcp/vlm/google_gemini.py`
  - Adapter for Google Gemini 2.5 Flash Image Preview.
  - Reads provider/model from config; API key from config file or env.
  - Minimal error mapping and timeouts.

Acceptance

- Unit smoke: Importable classes; constructing the client without a key raises a clear error.

---

## Phase 3 — MCP Tools

Tools to add in `server.py` (conditionally registered when VLM ready):

- `check_vlm_config() -> { status, provider, model, api_key_present, source, suggestions }`
  - Always registered; never leaks secret values.
- `get_gemini_prompt_templates() -> JSON` (also exposed as a resource)
  - Curated prompt patterns, usage notes, and response parsing tips aligned with Gemini docs.
- `vlm_suggest_recipe(image_path|session_id, task, constraints_json) -> { recipe, rationale }`
  - Hybrid allowed: Alb ops plus `{ "type": "VLMEdit", "prompt": "...", "vlm_required": true }`.
  - Validate recipe structure (basic clamping only for MVP).
- `vlm_apply(image_path|session_id, prompt|recipe_json, seed?) -> { paths, metadata }`
  - Loads image (reuses existing loaders), calls adapter, writes `vlm_augmented.png` under session.
  - Adds minimal `vlm_metadata.json` (model, prompt/recipe hash, timestamp) without secrets.
  - Triggers visual verification (Phase 4) so a `vlm_visual_eval.md` is produced.

Registration logic

- On startup, detect config:
  - If ready → register `vlm_suggest_recipe`, `vlm_apply`, and `check_vlm_config`.
  - If not ready → register only `check_vlm_config` (returns suggestions).

Acceptance

- Calling `check_vlm_config` shows accurate status.
- `get_gemini_prompt_templates` returns structured guidance without network.
- With key present, `vlm_apply` returns paths inside the active session folder.

---

## Phase 4 — Artifacts & Verification

Updates

- `pre_save.py`
  - Add VLM file names to `filename_info` and `file_paths`:
    - `vlm_augmented.png` → images
    - `vlm_visual_eval.md` → analysis
    - `vlm_metadata.json` → metadata
- `post_save.py`
  - If `context.metadata["vlm_verification_report_content"]` exists, write it to `vlm_visual_eval.md`.
  - If `context.metadata["vlm_metadata"]` exists, write it to `vlm_metadata.json`.
- `post_transform_verify.py`
  - Extend to check for `context.metadata["vlm_augmented_image"]` in addition to Alb.
  - When present, generate a second verification report comparing original vs VLM output, and store:
    - `verification_report_path_vlm`
    - `verification_report_content_vlm`
    - `verification_files_vlm`

Acceptance

- After `vlm_apply`, session contains `images/vlm_augmented.png`, `analysis/vlm_visual_eval.md`, and `metadata/vlm_metadata.json`.
- `get_pipeline_status()` still lists hooks; normal Alb runs unaffected.

---

## Phase 5 — Wiring Into Server

- Image input handling
  - Reuse existing `_detect_input_mode`, `_load_image_from_input` pathways for VLM tools.
- Session handling
  - Reuse `_create_session_directory` (pipeline) or `pre_save` to ensure artifacts go in the same session.
- Verification
  - Use the existing verification manager to render markdown for VLM comparisons.

Acceptance

- Both Alb and VLM flows write into the same session structure and verification artifacts are generated.

---

## Phase 6 — Documentation & Prompts

- README
  - Quickstart for VLM: env vars, example `check_vlm_config`, `vlm_apply` usage.
  - Security note: secrets via OS env only.
  - Example outputs and where to find verification artifacts.
- Prompt presets (docs)
  - 2D robustness
  - 3D-like context

Acceptance

- New README section renders and guides a successful demo run.

---

## Phase 7 — Demo Validation

Checklist

- [ ] Set `ENABLE_VLM=true`, `VLM_PROVIDER=google`, `VLM_MODEL=gemini-2.5-flash-image-preview` in env/launcher.
- [ ] Export `NANO_BANANA_API_KEY` in the OS environment.
- [ ] Run `check_vlm_config` → status ready.
- [ ] Call `get_gemini_prompt_templates` to pick a prompt.
- [ ] Run an Alb baseline (`augment_image`) → verify artifacts.
- [ ] Run `vlm_apply` with a semantic prompt → verify VLM artifacts.
- [ ] Confirm both sessions include verification markdown and images.

Success Criteria

- Alb-only augmentation works as before.
- VLM semantic augmentation runs, saves `vlm_augmented.png`, and creates a verification report.

---

## Phase 8 — (Optional) Stretch Items (Post-MVP)

- Budget tracking and cost caps per run.
- Simple cache by `(image_hash, prompt|recipe_hash, model)`.
- `list_verification_artifacts(session_id)` tool using `verification.list_verification_files()`.
- Safety policy report (recorded in `vlm_metadata.json`).

---

## Notes on Config and Security

- No MCP JSON schema/version bump required. The `env` map in client configs only passes environment variables to the server process.
- Keep API keys out of JSON. Prefer OS env; optionally reference a local config file path (`VLM_CONFIG_PATH`) for non-secret model options.
- `check_vlm_config` exists to let assistants validate readiness without reading the filesystem or exposing secrets.
