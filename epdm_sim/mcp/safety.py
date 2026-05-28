"""Safety preflight checks for MCP-style external tool calls."""

from __future__ import annotations

import math
from typing import Any

from .schemas import SimulationInput, ValidityStatus


ALLOWED_UNITS = {
    "pressure": {"Pa", "kPa", "MPa"},
    "temperature": {"K", "C", "degC", "°C"},
    "concentration": {"mol/L", "mol/m3"},
    "power": {"kJ/h", "kW"},
    "viscosity": {"cP", "Pa.s", "Pa·s"},
    "mass_flow": {"kg/h"},
    "molar_flow": {"mol/h", "kmol/h"},
}

VALIDITY_RANGES = {
    "temperature_C": (40.0, 220.0),
    "temperature_K": (273.15, 493.15),
    "T_K": (273.15, 493.15),
    "pressure_MPa": (0.001, 10.0),
    "pressure_Pa": (1.0e3, 1.0e7),
    "vapor_fraction": (0.0, 1.0),
}

HEAVY_TASK_IDS = {
    "dynamic_template_ode",
    "dynamic_ode",
    "cfd",
    "optimization",
    "posterior_sampling",
    "uncertainty",
    "bayesian_doe",
    "report_export",
    "repro_package_export",
}


def reject_invalid_units(units: dict[str, str]) -> list[str]:
    """Return unit-context violations for unsupported or missing units."""
    violations: list[str] = []
    for dimension, allowed in ALLOWED_UNITS.items():
        value = str(units.get(dimension, "")).strip()
        if not value:
            violations.append(f"missing unit for {dimension}")
        elif value not in allowed:
            violations.append(f"unsupported {dimension} unit {value!r}; expected one of {sorted(allowed)}")
    return violations


def reject_nan_inf_input(payload: Any, path: str = "payload") -> list[str]:
    """Return locations of NaN or infinite numeric values in nested payloads."""
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            violations.extend(reject_nan_inf_input(value, f"{path}.{key}"))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            violations.extend(reject_nan_inf_input(value, f"{path}[{index}]"))
    elif isinstance(payload, (int, float)) and not isinstance(payload, bool):
        if not math.isfinite(float(payload)):
            violations.append(f"{path} is not finite")
    return violations


def reject_negative_absolute_temperature(payload: dict[str, Any], units: dict[str, str] | None = None) -> list[str]:
    """Return violations for temperatures below absolute zero."""
    violations: list[str] = []
    unit_context = units or {}
    default_temperature_unit = str(unit_context.get("temperature", "C"))
    for key, value in payload.items():
        if isinstance(value, dict):
            violations.extend(reject_negative_absolute_temperature(value, unit_context))
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        key_lower = str(key).lower()
        if key in {"T_K", "temperature_K"} or key_lower.endswith("_k"):
            if float(value) <= 0.0:
                violations.append(f"{key} must be above 0 K")
        elif "temperature" in key_lower or key_lower in {"t_c", "temperature_c"}:
            unit = "K" if key in {"temperature_K"} else default_temperature_unit
            if unit == "K" and float(value) <= 0.0:
                violations.append(f"{key} must be above 0 K")
            if unit in {"C", "degC", "°C"} and float(value) <= -273.15:
                violations.append(f"{key} must be above -273.15 C")
    return violations


def reject_outside_validity_if_required(payload: dict[str, Any], require_validity: bool = True) -> ValidityStatus:
    """Return validity-envelope status for common external-tool fields."""
    messages: list[str] = []
    if not require_validity:
        return ValidityStatus(passed=True, outside_validity=False, messages=messages)
    for key, bounds in VALIDITY_RANGES.items():
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        lower, upper = bounds
        if float(value) < lower or float(value) > upper:
            messages.append(f"{key}={value} outside [{lower}, {upper}]")
    return ValidityStatus(passed=not messages, outside_validity=bool(messages), messages=messages)


def reject_heavy_task_without_explicit_permission(task_id: str, run_heavy_task: bool, dry_run: bool) -> list[str]:
    """Return violations when a heavy task would run without explicit permission."""
    if task_id in HEAVY_TASK_IDS and not dry_run and not run_heavy_task:
        return [f"heavy task {task_id!r} requires run_heavy_task=True"]
    return []


def mcp_preflight_check(request: SimulationInput, task_id: str) -> tuple[bool, list[str], ValidityStatus]:
    """Run unit, finite, absolute-temperature, validity and heavy-task preflight."""
    units = request.units.model_dump() if hasattr(request.units, "model_dump") else request.units.dict()
    violations = []
    violations.extend(reject_invalid_units(units))
    violations.extend(reject_nan_inf_input(request.payload))
    violations.extend(reject_negative_absolute_temperature(request.payload, units))
    violations.extend(reject_heavy_task_without_explicit_permission(task_id, request.run_heavy_task, request.dry_run))
    validity = reject_outside_validity_if_required(request.payload, request.require_validity)
    violations.extend(validity.messages)
    return not violations, violations, validity
