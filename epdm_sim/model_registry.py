"""Model registry for merged process-simulator and digital-twin capabilities.

The registry is intentionally data-driven. It records each major model's
engineering role, equations, validity range and trigger mode so UI pages can
explain what runs automatically and what requires an explicit user action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .utils import data_path, load_json


VALID_TRIGGER_MODES = {"auto_cached", "button_manual", "data_only", "export_only"}


@dataclass(frozen=True)
class ModelModule:
    """A registered simulation, data, visualization or export module."""

    module_id: str
    display_name: str
    category: str
    origin_project: str
    implementation: str
    trigger_mode: str
    equations: list[str]
    inputs: list[str]
    outputs: list[str]
    parameters: list[str] = field(default_factory=list)
    required_units: dict[str, str] = field(default_factory=dict)
    validity_range: dict[str, str] = field(default_factory=dict)
    mathematical_checks: list[str] = field(default_factory=list)
    chemical_engineering_checks: list[str] = field(default_factory=list)
    computational_cost: str = "low"
    ui_trigger_policy: str = ""
    ui_entry: str = ""
    engineering_logic: str = ""
    fallback: str = ""
    status: str = "active"

    @property
    def validity_summary(self) -> str:
        """Return a compact validity range summary for UI tables."""
        return "; ".join(f"{key}: {value}" for key, value in self.validity_range.items())

    @property
    def equation_summary(self) -> str:
        """Return compact equations for UI display."""
        return " | ".join(self.equations)


def load_model_registry(path: str | None = None) -> list[ModelModule]:
    """Load registered model modules from ``data/model_registry.json``."""
    registry_path = data_path("model_registry.json") if path is None else path
    payload: dict[str, Any] = load_json(registry_path)
    modules = payload.get("modules", [])
    return [ModelModule(**module) for module in modules]


def validate_model_registry(modules: list[ModelModule] | None = None) -> list[str]:
    """Return validation errors for registry entries.

    This is deliberately lightweight; it catches broken documentation/data
    contracts without pulling simulation code into the registry layer.
    """
    modules = load_model_registry() if modules is None else modules
    errors: list[str] = []
    seen: set[str] = set()
    for module in modules:
        if module.module_id in seen:
            errors.append(f"duplicate module_id: {module.module_id}")
        seen.add(module.module_id)
        if module.trigger_mode not in VALID_TRIGGER_MODES:
            errors.append(f"{module.module_id}: invalid trigger_mode {module.trigger_mode}")
        if not module.equations:
            errors.append(f"{module.module_id}: equations must not be empty")
        if not module.inputs:
            errors.append(f"{module.module_id}: inputs must not be empty")
        if not module.outputs:
            errors.append(f"{module.module_id}: outputs must not be empty")
        if not module.validity_range:
            errors.append(f"{module.module_id}: validity_range must not be empty")
        if module.status == "active" and not module.required_units:
            errors.append(f"{module.module_id}: required_units must not be empty")
        if module.status == "active" and not module.mathematical_checks:
            errors.append(f"{module.module_id}: mathematical_checks must not be empty")
        if module.status == "active" and not module.chemical_engineering_checks:
            errors.append(f"{module.module_id}: chemical_engineering_checks must not be empty")
        if module.computational_cost not in {"low", "medium", "high"}:
            errors.append(f"{module.module_id}: invalid computational_cost {module.computational_cost}")
        if module.trigger_mode == "button_manual" and module.computational_cost == "low":
            errors.append(f"{module.module_id}: button_manual modules should declare medium/high computational_cost")
        if module.trigger_mode == "auto_cached" and "hash" not in " ".join(module.mathematical_checks).lower():
            errors.append(f"{module.module_id}: auto_cached module must declare input-hash/cache check")
        if module.status not in {"active", "fallback", "archived"}:
            errors.append(f"{module.module_id}: invalid status {module.status}")
    return errors


def module_trigger_dataframe(modules: list[ModelModule] | None = None) -> pd.DataFrame:
    """Return a UI-ready table of module trigger modes and applicability."""
    modules = load_model_registry() if modules is None else modules
    rows = [
        {
            "module_id": module.module_id,
            "模块": module.display_name,
            "类别": module.category,
            "触发方式": module.trigger_mode,
            "计算成本": module.computational_cost,
            "实现位置": module.implementation,
            "适用范围": module.validity_summary,
            "UI入口": module.ui_entry,
        }
        for module in modules
    ]
    return pd.DataFrame(rows)


def registry_summary(modules: list[ModelModule] | None = None) -> dict[str, Any]:
    """Summarize registry coverage for diagnostics and reports."""
    modules = load_model_registry() if modules is None else modules
    by_trigger: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for module in modules:
        by_trigger[module.trigger_mode] = by_trigger.get(module.trigger_mode, 0) + 1
        by_category[module.category] = by_category.get(module.category, 0) + 1
    return {
        "module_count": len(modules),
        "by_trigger": by_trigger,
        "by_category": by_category,
        "validation_errors": validate_model_registry(modules),
    }
