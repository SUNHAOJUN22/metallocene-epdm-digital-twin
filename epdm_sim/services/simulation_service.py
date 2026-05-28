"""Simulation orchestration service used by Streamlit pages."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..flowsheet import ProcessConfig, run_flowsheet
from ..preflight import has_blocking_failures, run_preflight_for_flowsheet
from ..utils import model_dump_compat
from .cache_keys import config_cache_key


@dataclass
class TimedResult:
    """Result object plus wall-clock runtime metadata."""

    result: Any
    cache_key: str
    elapsed_s: float
    cache_hit: bool


def process_config_from_payload(payload: ProcessConfig | dict[str, Any]) -> ProcessConfig:
    """Normalize a configuration payload into ProcessConfig."""
    return payload if isinstance(payload, ProcessConfig) else ProcessConfig(**payload)


def run_flowsheet_with_store(config: ProcessConfig | dict[str, Any], store: Any | None = None) -> TimedResult:
    """Run or reuse a fast flowsheet result from a ResultsStore-like object."""
    cfg = process_config_from_payload(config)
    preflight = run_preflight_for_flowsheet(cfg)
    if has_blocking_failures(preflight):
        messages = "; ".join(item.message for item in preflight if not item.passed and item.severity == "error")
        raise ValueError(f"前置输入校验未通过，不运行flowsheet：{messages}")
    key = config_cache_key(model_dump_compat(cfg))
    if store is not None and getattr(store, "flowsheet_key", None) == key and getattr(store, "flowsheet", None) is not None:
        return TimedResult(store.flowsheet, key, 0.0, True)
    started = time.perf_counter()
    result = run_flowsheet(cfg)
    elapsed = time.perf_counter() - started
    if store is not None:
        store.flowsheet_key = key
        store.flowsheet = result
        store.metadata["flowsheet_elapsed_s"] = elapsed
        store.metadata["last_flowsheet_hash"] = key
    return TimedResult(result, key, elapsed, False)


def stale_flags(state: Any, store: Any | None = None) -> dict[str, bool]:
    """Return stale flags for fast and detail calculations."""
    current_key = config_cache_key(getattr(state, "config", {}))
    dirty = set(getattr(state, "dirty_modules", set()))
    return {
        "flowsheet": current_key != getattr(store, "flowsheet_key", None) or "flowsheet" in dirty,
        "dynamic": "dynamic_reactor" in dirty or current_key != getattr(store, "dynamic_key", None),
        "cfd": "cfd" in dirty or current_key != getattr(store, "cfd_key", None),
        "optimization": "optimization" in dirty or getattr(store, "optimization", None) is None,
        "report": "report" in dirty,
    }


def performance_rows(state: Any, store: Any | None = None, page_triggered: bool = False) -> list[dict[str, Any]]:
    """Return rows for the UI performance diagnostics expander."""
    flags = stale_flags(state, store)
    metadata = getattr(store, "metadata", {}) if store is not None else {}
    return [
        {"item": "flowsheet hash", "value": str(config_cache_key(getattr(state, "config", {})))},
        {"item": "dynamic stale", "value": str(flags["dynamic"])},
        {"item": "cfd stale", "value": str(flags["cfd"])},
        {"item": "optimization stale", "value": str(flags["optimization"])},
        {"item": "last flowsheet seconds", "value": f"{float(metadata.get('flowsheet_elapsed_s', 0.0)):.4f}"},
        {"item": "cache note", "value": "命中" if not flags["flowsheet"] else "待刷新"},
        {"item": "current page triggered recompute", "value": str(bool(page_triggered))},
    ]
