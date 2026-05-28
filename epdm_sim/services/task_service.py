"""Lightweight long-task status service for Streamlit session state."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd


@dataclass
class TaskRecord:
    """State record for one manually triggered long task."""

    task_id: str
    status: str = "pending"
    parameter_hash: str = ""
    input_hash: str = ""
    dependency_hash: str = ""
    elapsed_s: float = 0.0
    cached: bool = False
    cache_hit: bool = False
    stale_reason: str = ""
    error: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-like task status row."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "parameter_hash": self.parameter_hash,
            "input_hash": self.input_hash or self.parameter_hash,
            "dependency_hash": self.dependency_hash,
            "elapsed_s": self.elapsed_s,
            "cached": self.cached,
            "cache_hit": self.cache_hit or self.cached,
            "stale_reason": self.stale_reason,
            "error": self.error,
            "last_error": self.error,
            "updated_at": self.updated_at,
        }


class TaskService:
    """In-process task status manager backed by a dictionary/session_state."""

    def __init__(self, state: dict[str, Any] | None = None):
        self.state = state if state is not None else {}
        self.state.setdefault("task_records", {})
        self.state.setdefault("task_results", {})

    def get(self, task_id: str) -> TaskRecord:
        """Return a task record, creating a pending one if needed."""
        payload = self.state["task_records"].get(task_id)
        if isinstance(payload, TaskRecord):
            return payload
        if isinstance(payload, dict):
            return TaskRecord(**payload)
        record = TaskRecord(task_id=task_id)
        self.state["task_records"][task_id] = record
        return record

    def run(
        self,
        task_id: str,
        parameter_hash: str,
        func: Callable[[], Any],
        *,
        use_cache: bool = True,
        dependency_hash: str = "",
        stale_reason: str = "",
        preflight: Callable[[], Any] | Any | None = None,
    ) -> Any:
        """Run a task with status capture and simple parameter-hash caching."""
        existing = self.get(task_id)
        result_key = f"{task_id}:{parameter_hash}"
        if use_cache and result_key in self.state["task_results"]:
            record = TaskRecord(
                task_id=task_id,
                status="cached",
                parameter_hash=parameter_hash,
                input_hash=parameter_hash,
                dependency_hash=dependency_hash,
                cached=True,
                cache_hit=True,
                elapsed_s=0.0,
                stale_reason="",
            )
            self.state["task_records"][task_id] = record
            return self.state["task_results"][result_key]
        record = TaskRecord(
            task_id=task_id,
            status="running",
            parameter_hash=parameter_hash,
            input_hash=parameter_hash,
            dependency_hash=dependency_hash,
            stale_reason=stale_reason,
        )
        self.state["task_records"][task_id] = record
        started = time.perf_counter()
        try:
            if preflight is not None:
                checks = preflight() if callable(preflight) else preflight
                failed = [item for item in checks if not getattr(item, "passed", True) and getattr(item, "severity", "") == "error"]
                if failed:
                    raise ValueError("Preflight failed: " + "; ".join(getattr(item, "message", str(item)) for item in failed))
            result = func()
            elapsed = time.perf_counter() - started
            record = TaskRecord(
                task_id=task_id,
                status="success",
                parameter_hash=parameter_hash,
                input_hash=parameter_hash,
                dependency_hash=dependency_hash,
                elapsed_s=elapsed,
                cached=False,
                cache_hit=False,
                stale_reason="",
            )
            self.state["task_records"][task_id] = record
            self.state["task_results"][result_key] = result
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - started
            record = TaskRecord(
                task_id=task_id,
                status="failed",
                parameter_hash=parameter_hash,
                input_hash=parameter_hash,
                dependency_hash=dependency_hash,
                elapsed_s=elapsed,
                error=str(exc),
                stale_reason=stale_reason,
            )
            self.state["task_records"][task_id] = record
            raise

    def as_dataframe(self) -> pd.DataFrame:
        """Return task records as a DataFrame for UI diagnostics."""
        rows = []
        for value in self.state.get("task_records", {}).values():
            record = value if isinstance(value, TaskRecord) else TaskRecord(**value)
            rows.append(record.to_dict())
        return pd.DataFrame(rows)


TASK_GRAPH = {
    "flowsheet_fast": {"trigger": "auto_cached", "depends_on": [], "estimated_s": "<0.5"},
    "dynamic_ode": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "1-5"},
    "dynamic_template_ode": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "1-5"},
    "cfd": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "1-4"},
    "parameter_estimation": {"trigger": "button_manual", "depends_on": ["experiment_data"], "estimated_s": "3-30"},
    "posterior_sampling": {"trigger": "button_manual", "depends_on": ["experiment_data"], "estimated_s": "3-20"},
    "time_series_fit": {"trigger": "button_manual", "depends_on": ["experiment_time_series", "dynamic_template_ode"], "estimated_s": "1-5"},
    "optimization": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "2-20"},
    "uncertainty": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "2-20"},
    "bayesian_doe": {"trigger": "button_manual", "depends_on": ["flowsheet_fast", "uncertainty"], "estimated_s": "1-8"},
    "constrained_window": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "1-8"},
    "surrogate_training": {"trigger": "button_manual", "depends_on": ["sensitivity_results"], "estimated_s": "1-3"},
    "surrogate_validation": {"trigger": "button_manual", "depends_on": ["surrogate_model"], "estimated_s": "<1"},
    "engineering_rules": {"trigger": "button_manual", "depends_on": ["flowsheet_fast"], "estimated_s": "1-5"},
    "conservation": {"trigger": "auto_cached", "depends_on": ["flowsheet_fast"], "estimated_s": "<0.2"},
    "report_export": {"trigger": "button_manual", "depends_on": ["current_results"], "estimated_s": "1-10"},
    "repro_package_export": {"trigger": "button_manual", "depends_on": ["current_results"], "estimated_s": "1-5"},
    "cfd_grid_convergence": {"trigger": "button_manual", "depends_on": ["cfd"], "estimated_s": "2-10"},
}


def task_graph_dataframe() -> pd.DataFrame:
    """Return the high-level task graph as a DataFrame for UI diagnostics."""
    return pd.DataFrame(
        [
            {
                "task_id": task_id,
                "trigger": meta["trigger"],
                "depends_on": ", ".join(meta["depends_on"]),
                "estimated_s": meta["estimated_s"],
            }
            for task_id, meta in TASK_GRAPH.items()
        ]
    )
