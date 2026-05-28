"""Calibration persistence metadata helpers."""

from __future__ import annotations

from typing import Any
import hashlib
import json


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def calibrated_set_record(parameter_set_id: str, parameters: dict[str, Any], *, source_dataset_id: str = "not_supplied") -> dict[str, Any]:
    """Return a non-mutating calibrated parameter-set record."""
    return {
        "parameter_set_id": str(parameter_set_id),
        "source_dataset_id": str(source_dataset_id),
        "parameter_hash": _stable_hash(parameters),
        "parameters": dict(parameters),
        "status": "calibrated_candidate",
    }
