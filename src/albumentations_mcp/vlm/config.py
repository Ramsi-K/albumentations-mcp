"""Helpers for VLM configuration discovery (file-first with env fallback).

This module centralizes configuration for optional VLM integration.

Principles:
- Prefer a local JSON config file referenced by `VLM_CONFIG_PATH` (file-first).
- Fall back to environment variables for overrides or when file is absent.
- Never expose secret values (API keys) via returned structures; only report
  presence (`api_key_present = True/False`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _truthy(value: str | None) -> bool:
    v = (value or "").strip().lower()
    return v in ("true", "1", "yes", "on")


# Simple mtime-based cache for config file
_CACHE: dict[str, Any] = {
    "path": None,
    "mtime": None,
    "data": None,
}


def _load_file_safely(path: Path) -> tuple[dict[str, Any], float | None]:
    if not path.exists() or not path.is_file():
        return {}, None
    try:
        mtime = path.stat().st_mtime
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return (data if isinstance(data, dict) else {}), mtime
    except Exception:
        return {}, None


def _get_file_config(
    config_path: str | None,
) -> tuple[dict[str, Any], str | None]:
    if not config_path:
        return {}, None
    p = Path(config_path)
    # Use cache if unchanged
    cached_path = _CACHE.get("path")
    cached_mtime = _CACHE.get("mtime")
    if cached_path == str(p) and cached_mtime is not None:
        current_mtime = p.stat().st_mtime if p.exists() else None
        if current_mtime == cached_mtime:
            return (_CACHE.get("data") or {}), str(p)

    data, mtime = _load_file_safely(p)
    _CACHE["path"] = str(p)
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data
    return data, str(p)


def load_vlm_config() -> dict[str, Any]:
    """Aggregate VLM config (file-first, env fallback).

    Returns a dict with keys useful for readiness checks and client wiring:
      - enabled (bool)
      - provider (str|None)
      - model (str|None)
      - config_path (str|None)
      - api_key_present (bool)
      - source ("file"|"env"|"none")
      - raw_options (dict) non-secret options loaded from file (if any)
    """
    # Discover config path (env, then common defaults)
    config_path = (os.getenv("VLM_CONFIG_PATH") or "").strip() or None
    if not config_path:
        # Try common local defaults so users don't have to set env vars
        for cand in ("config/vlm.json", "./vlm.json"):
            p = Path(cand)
            if p.exists() and p.is_file():
                config_path = str(p)
                break

    # Read file first
    file_cfg, file_path = _get_file_config(config_path)

    # Fallback/env overrides
    env_enabled = _truthy(os.getenv("ENABLE_VLM")) if os.getenv("ENABLE_VLM") else None
    env_provider = (
        os.getenv("VLM_PROVIDER") or os.getenv("VLM_BACKEND") or ""
    ).strip() or None
    env_model = (
        os.getenv("VLM_MODEL") or os.getenv("GEMINI_MODEL") or ""
    ).strip() or None

    # Compose
    enabled = (
        bool(file_cfg.get("enabled")) if env_enabled is None else bool(env_enabled)
    )
    provider = file_cfg.get("provider") or None
    if env_provider:
        provider = env_provider
    model = file_cfg.get("model") or None
    if env_model:
        model = env_model

    # API key presence: file can carry a key under common fields, or env
    file_key_present = any(
        (file_cfg.get(k) or "").strip()
        for k in ("api_key", "key", "token")
        if isinstance(file_cfg.get(k), str)
    )
    env_key_present = any(
        ((os.getenv(name) or "").strip())
        for name in (
            "NANO_BANANA_API_KEY",
            "VLM_API_KEY",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
        )
    )
    api_key_present = bool(file_key_present or env_key_present)

    # Source
    source = "none"
    if file_path and file_cfg:
        source = "file"
    if any([env_enabled is not None, env_provider, env_model, env_key_present]):
        # If any env bits are set, note env as source of override
        source = "env" if source != "file" else "file"

    return {
        "enabled": bool(enabled),
        "provider": provider,
        "model": model,
        "config_path": config_path,
        "api_key_present": api_key_present,
        "source": source,
        "raw_options": file_cfg if isinstance(file_cfg, dict) else {},
    }


def get_vlm_api_key() -> str | None:
    """Internal helper: fetch API key value for adapter use.

    Precedence: file (api_key|key|token) > env (NANO_BANANA_API_KEY|...)
    This function is not exposed via MCP tools and should not be used to leak
    secrets. It is intended solely for adapter calls.
    """
    cfg = load_vlm_config()
    file_cfg = cfg.get("raw_options") or {}
    for k in ("api_key", "key", "token"):
        v = file_cfg.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for name in (
        "NANO_BANANA_API_KEY",
        "VLM_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        v = os.getenv(name)
        if v and v.strip():
            return v.strip()
    return None
