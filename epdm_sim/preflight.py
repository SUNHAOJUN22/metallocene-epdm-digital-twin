"""Pre-run dimensional and physical input validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .components import load_components
from .flowsheet import ProcessConfig
from .io_schema import get_io_schema
from .polymer_props import load_target_grades


@dataclass(frozen=True)
class PreflightResult:
    """One pre-run validation item."""

    model_id: str
    passed: bool
    severity: str
    message: str
    input_name: str
    value: Any
    unit: str
    expected_range: str
    suggested_fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def preflight_dataframe(results: list[PreflightResult]) -> pd.DataFrame:
    """Return preflight results as a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in results])


def has_blocking_failures(results: list[PreflightResult]) -> bool:
    """Return True when any preflight result blocks execution."""
    return any((not item.passed) and item.severity == "error" for item in results)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _check(model_id: str, input_name: str, value: Any, unit: str, condition: bool, expected_range: str, message: str, suggested_fix: str, severity: str = "error") -> PreflightResult:
    return PreflightResult(
        model_id=model_id,
        passed=bool(condition),
        severity="ok" if condition else severity,
        message=message if condition else f"{message} 不满足：{value}",
        input_name=input_name,
        value=value,
        unit=unit,
        expected_range=expected_range,
        suggested_fix="" if condition else suggested_fix,
    )


def run_preflight_for_model(model_id: str, inputs: dict[str, Any]) -> list[PreflightResult]:
    """Validate a model input payload against IO schema numeric bounds."""
    schema = get_io_schema(model_id)
    results: list[PreflightResult] = []
    for spec in schema.inputs:
        value = inputs.get(spec.name)
        if spec.required and spec.name not in inputs:
            results.append(_check(model_id, spec.name, None, spec.unit, False, "required", "必填输入缺失", "补齐该模型输入。"))
            continue
        if value is None or not isinstance(value, (int, float)):
            results.append(_check(model_id, spec.name, value, spec.unit, value is not None, "finite or structured", "输入存在", "补齐或检查输入格式。", "warning"))
            continue
        valid = _finite(value)
        if spec.min_value is not None:
            valid = valid and float(value) >= spec.min_value
        if spec.max_value is not None:
            valid = valid and float(value) <= spec.max_value
        expected = f"{spec.min_value if spec.min_value is not None else '-inf'} to {spec.max_value if spec.max_value is not None else '+inf'}"
        results.append(_check(model_id, spec.name, value, spec.unit, valid, expected, "输入数值范围检查", "检查单位、符号和模型适用范围。"))
    return results


def run_preflight_for_flowsheet(config: ProcessConfig | dict[str, Any]) -> list[PreflightResult]:
    """Validate flowsheet inputs before running the fast model."""
    cfg = config if isinstance(config, ProcessConfig) else ProcessConfig(**config)
    components = load_components()
    solvent = cfg.solvent if cfg.solvent in components else None
    feed_flows = [cfg.solvent_mass_kg_h, cfg.ethylene_kg_h, cfg.propylene_kg_h, cfg.enb_kg_h, cfg.hydrogen_g_h]
    return [
        _check("flowsheet", "temperature_C", cfg.temperature_C, "degC", _finite(cfg.temperature_C) and cfg.temperature_C > -273.15, "> -273.15", "反应温度高于绝对零度", "检查摄氏/K单位。"),
        _check("flowsheet", "pressure_MPa", cfg.pressure_MPa, "MPa", _finite(cfg.pressure_MPa) and cfg.pressure_MPa > 0.0, "> 0", "反应压力为正", "压力必须为正。"),
        _check("flowsheet", "feed_flows", min(feed_flows), "kg/h or g/h", all(_finite(v) and v >= 0.0 for v in feed_flows), ">= 0", "所有进料非负", "检查负流量输入。"),
        _check("flowsheet", "residence_time_min", cfg.residence_time_min, "min", cfg.residence_time_min > 0.0, "> 0", "停留时间为正", "提高停留时间。"),
        _check("flowsheet", "solvent", cfg.solvent, "-", solvent is not None, "known component", "溶剂在组件库中", "改用hexane/heptane/toluene或补齐物性。"),
        _check("flowsheet", "num_cstr", cfg.num_cstr, "count", cfg.num_cstr >= 1, ">= 1", "CSTR数量至少为1", "设置num_cstr>=1。"),
        _check("flowsheet", "purge_fraction", cfg.purge_fraction, "fraction", 0.0 <= cfg.purge_fraction <= 1.0, "0-1", "purge fraction位于0-1", "检查purge比例。"),
        _check("flowsheet", "heat_transfer_U_W_m2K", cfg.heat_transfer_U_W_m2K, "W/m2/K", cfg.heat_transfer_U_W_m2K > 0.0, "> 0", "传热系数为正", "检查U值。"),
        _check("flowsheet", "heat_transfer_area_m2", cfg.heat_transfer_area_m2, "m2", cfg.heat_transfer_area_m2 > 0.0, "> 0", "换热面积为正", "检查A值。"),
        _check("flowsheet", "pipe_diameter_m", cfg.pipe_diameter_m, "m", cfg.pipe_diameter_m > 0.0, "> 0", "管径为正", "检查管径。"),
    ]


def run_preflight_for_cfd(inputs: dict[str, Any]) -> list[PreflightResult]:
    """Validate CFD inputs."""
    nx = int(inputs.get("Nx", 80))
    ny = int(inputs.get("Ny", 40))
    checks = [
        _check("cfd_simple", "Nx", nx, "count", 10 <= nx <= 200, "10-200", "CFD Nx合理", "降低或提高网格数量。"),
        _check("cfd_simple", "Ny", ny, "count", 10 <= ny <= 120, "10-120", "CFD Ny合理", "降低或提高网格数量。"),
    ]
    for key, unit in [("viscosity_Pa_s", "Pa*s"), ("density_kg_m3", "kg/m3"), ("Cp_kJ_kgK", "kJ/kg/K"), ("thermal_conductivity_W_mK", "W/m/K"), ("diameter_m", "m"), ("length_m", "m")]:
        value = inputs.get(key, 1.0)
        checks.append(_check("cfd_simple", key, value, unit, _finite(value) and float(value) > 0.0, "> 0", f"{key}为正", "检查CFD输入单位和值。"))
    rpm = inputs.get("rpm", 0.0)
    checks.append(_check("cfd_simple", "rpm", rpm, "rpm", _finite(rpm) and float(rpm) >= 0.0, ">= 0", "搅拌转速非负", "检查rpm。"))
    heat = inputs.get("heat_generation_W_m3", 0.0)
    checks.append(_check("cfd_simple", "heat_generation_W_m3", heat, "W/m3", _finite(heat), "finite", "热源有限", "检查热源项。"))
    return checks


def run_preflight_for_optimizer(bounds: dict[str, tuple[float, float]], target_grade: str = "Internal_1109_2_commercial_candidate") -> list[PreflightResult]:
    """Validate optimization bounds and target grade."""
    results: list[PreflightResult] = []
    for name, pair in bounds.items():
        low, high = pair
        results.append(_check("optimizer_pareto", name, pair, "model units", _finite(low) and _finite(high) and low < high, "lower < upper", "优化变量上下限有效", "检查bounds顺序和值。"))
    grades = load_target_grades()
    results.append(_check("optimizer_pareto", "target_grade", target_grade, "-", target_grade in grades, "known target grade", "目标牌号存在", "检查target_grades.json。"))
    return results
