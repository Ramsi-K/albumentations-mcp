# Session Folders: What Gets Generated and How To Use It

This document explains the artifacts created for each augmentation session under `outputs/`, what each file contains, and how they are produced by the hook pipeline.

A session folder name follows this pattern:

- `YYYYMMDD_HHMMSS_<session_id>` (example: `20250903_152934_354672f8`)

Inside, the pre-save hook prepares a stable directory layout so all hooks write to the same place.

## Layout

- `images/`
  - `<base>_original.png`: Original image saved early (pre-save)
  - `<base>_augmented.png`: Final augmented image (post-save)
- `metadata/`
  - `<base>_metadata.json`: Full session metadata snapshot (post-save)
  - `<base>_transforms.json`: Transform spec actually used (post-save)
  - `<base>_quality.json`: Quality and processing metrics (post-save)
  - `completion_manifest_<session>.json`: Job manifest summarizing key outputs (post-save)
- `logs/`
  - `<base>_processing.log`: Human-readable processing log (post-save)
- `analysis/`
  - `<base>_visual_eval.md`: Visual verification summary for VLM review (post-save if available)
  - `<base>_classification.json`: Placeholder for future analysis (post-save)
- `tmp/`
  - Temporary images/files created by pre-transform or loader; cleaned up by post-save when safe

`<base>` encodes time, the session short id, and a sanitized slice of the prompt so artifacts remain traceable but filesystem-safe.

## How artifacts are produced

- Pre-MCP (`pre_mcp.py`): sanitizes the prompt and records prompt stats.
- Post-MCP (`post_mcp.py`): logs/validates the parsed transform spec.
- Pre-Transform (`pre_transform.py`):
  - Validates image shape/mode/limits.
  - Auto-resizes if permissive mode is enabled; writes temp copies in `tmp/`.
  - Updates metadata with resize info and warnings.
- Post-Transform (`post_transform.py`):
  - Computes processing statistics, timing data, and quality metrics (size/format/mode deltas; similarity metrics when shapes match).
  - Produces a transformation summary and performance rating.
- Post-Transform Verify (`post_transform_verify.py`):
  - Optionally saves images for LLM review in a global temp folder (not in the session dir):
    - OS temp: `<tmp>/albumentations_verification/*` (see `verification.py`)
  - Generates a Markdown verification report and stores its path in metadata.
- Pre-Save (`pre_save.py`):
  - Creates (or reuses) the `outputs/YYYYMMDD_HHMMSS_<session>` folder and subfolders.
  - Saves the original image to `images/` immediately.
  - Prepares final file paths for all artifacts and exposes `session_dir` in metadata for downstream reuse.
- Post-Save (`post_save.py`):
  - Saves augmented image, writes metadata files, logs, and analysis files.
  - Generates a completion manifest under `metadata/`.
  - Cleans up `tmp/` files/directories when safe.

## Key files and schemas

- `images/<base>_original.png`
  - Original image as received (or normalized), saved early for debugging.
- `images/<base>_augmented.png`
  - Final augmented image produced by the pipeline.
  - Internally we choose compact encodings during processing (JPEG/WEBP) and ensure consistent output in this file.

- `metadata/<base>_metadata.json`
  - Snapshot of the full context at save time:
    - `session_id`, `original_prompt`
    - `transforms`: the parsed transform list
    - `metadata`: pipeline metadata (resize info, timing, stats, verification paths, etc.)
    - `warnings`, `errors`

- `metadata/<base>_transforms.json`
  - The transform spec applied:
    - Names, parameters, probabilities
    - Useful for re-running or auditing augmentation settings

- `metadata/<base>_quality.json`
  - Quality and processing metrics:
    - `quality_metrics` (size/mode/format preservation; similarity metrics when comparable)
    - `processing_statistics` (counts, rates, execution time)

- `metadata/completion_manifest_<session>.json`
  - High-level manifest for the session:
    - Output file list with sizes and existence flags
    - Selected metadata summaries (processing stats, quality, timing)

- `logs/<base>_processing.log`
  - Human-readable log with:
    - Session id and generation time
    - Prompt
    - Transform counts and execution time
    - Warnings and errors

- `analysis/<base>_visual_eval.md`
  - Markdown report intended for VLM review
  - Includes paths to saved images (in the global verification temp folder) and a structured findings summary

- `analysis/<base>_classification.json`
  - Placeholder for future classification/consistency checks

- `tmp/`
  - Working area for intermediate images (e.g., auto-resized copies, pasted/URL images staged by loader)
  - Post-save attempts to delete safe files and remove empty directories

## Where to find session_dir and reuse it

- The pipeline and hooks share a single `session_dir`, stored in metadata as `metadata["session_dir"]`.
- Pre-Save ensures this value is set; downstream hooks read it to avoid creating duplicate folders.

## How to consume these artifacts

- Programmatically:
  - Use `metadata/<base>_metadata.json` as the source of truth for the full run, with links to all other artifacts.
  - For audits or reproducibility, read `metadata/<base>_transforms.json`.
  - For performance/quality monitoring, read `metadata/<base>_quality.json` and `logs/<base>_processing.log`.
- Manually:
  - Start with `images/*_augmented.png` and `analysis/*_visual_eval.md`.
  - If something looks off, open the log and the full metadata JSON.

## Cleanup and safety rules

- The post-save hook removes temporary files in `tmp/` only when safe. It avoids deleting original/user files and never removes the session folder itself.
- Visual verification files live in a separate temp folder and can be cleaned via the verification manager when needed.

## Tips

- Reproducibility: set a seed via `set_default_seed` or tool parameters; seed info is included in metadata.
- Large images: we keep base64 at the MCP boundary, but decode early, downscale, and re-encode once to keep memory/size in check.
- Prefer `image_path` for very large inputs to avoid client-side base64 blowups.
