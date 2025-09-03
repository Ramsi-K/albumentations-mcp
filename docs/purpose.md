# Purpose

This MCP server is for rapid hypothesis testing of CV augmentation policies—not a full-scale training pipeline. It standardizes augmentation as tools so agents/IDEs can call them the same way in early R&D.

## Why base64 at the MCP boundary

- MCP is JSON-only. Base64 is the portable, client-agnostic way to move binary image data.
- Zero-trust / sandboxing. Many enterprise clients don’t allow arbitrary file-path access from agent tools. Base64 avoids leaking file system structure and works through gateways.
- Consistency across clients. Inspector, desktop IDEs, and headless agents can all send/receive base64 without sharing mounts.

## Why PIL/ndarray internally

- **Performance & control.** We decode once, resize/recompress, and work on arrays. Only if a downstream step needs base64 do we re-encode.
- **Determinism.** Seeds, hooks, and metadata are easier to maintain on in-memory images than opaque base64 strings.

## Transport vs Processing (design decision)

- **Transport sanity check (light):** cap absurd base64 inputs to prevent DoS.
- **Processing validation (real checks):** after decode → resize/recompress → proceed. This ensures large but valid images don’t get rejected before we can downscale.

## Preferred inputs

- **Preferred:** image_path (client passes a local path; server loads, resizes, then encodes once for the internal pipeline).
- **Compatible:** image_b64 (sanity-capped; auto downscaled after decode).
- **Rationale:** avoids client-side crashes where some UIs inline huge base64 before tools run.

## Security posture

- Base64 syntax validation and size guard before decode.
- Sanitized decode, then dimension/pixel caps and recompression (JPEG/WebP).
- Clear failures: `FILE_NOT_FOUND`, `B64_INVALID`, `B64_INPUT_TOO_LARGE`, `IMAGE_DIMENSIONS_TOO_LARGE`.

## Known limitations

- Base64 balloons payloads; for very large assets, prefer image_path.
- PNG can be larger than JPEG/WebP after recompression.
- v1 focuses on single-image augmentation; batch modes are planned.

## Roadmap

- **Handles:** support file:// and mcp://asset/<id> so clients can upload once, then pass references.
- **Multipart bridge:** optional side-channel for binary transfer (keeps JSON control plane).
- **Direct ndarray path**: allow internal pipeline to accept arrays to avoid the final base64 hop.
