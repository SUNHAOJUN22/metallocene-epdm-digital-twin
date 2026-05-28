"""Stable cache-key helpers for simulation services."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..utils import model_dump_compat


def stable_json_dumps(value: Any) -> str:
    """Return deterministic JSON for cache and case fingerprints."""
    try:
        payload = model_dump_compat(value)
    except Exception:
        payload = value
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def hash_payload(value: Any, length: int = 12) -> str:
    """Return a short stable SHA1 hash for a payload."""
    return hashlib.sha1(stable_json_dumps(value).encode("utf-8")).hexdigest()[:length]


def config_cache_key(config: Any) -> str:
    """Return the flowsheet cache key for a process configuration."""
    return hash_payload(config)


def detail_cache_key(config: Any, extra: Any | None = None) -> str:
    """Return a cache key for detail calculations such as CFD or ODE."""
    return hash_payload({"config": model_dump_compat(config), "extra": extra or {}})


def model_fingerprint(*parts: Any) -> str:
    """Return a compact fingerprint for multiple model inputs."""
    return hash_payload(list(parts), length=16)

