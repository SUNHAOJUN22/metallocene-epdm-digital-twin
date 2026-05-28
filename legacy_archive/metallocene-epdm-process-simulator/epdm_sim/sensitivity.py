"""Sensitivity analysis helpers."""

from __future__ import annotations

from itertools import product
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .utils import model_dump_compat, positive


VARIABLE_LABELS = {
    "temperature_C": "反应温度",
    "pressure_MPa": "反应压力",
    "ENB feed": "ENB进料",
    "E/P ratio": "E/P质量比",
    "hydrogen": "氢气进料",
    "Al/Ti": "Al/Ti比",
    "residence_time": "停留时间",
    "num_cstr": "串联釜数",
}


TARGET_LABELS = {
    "maximize ENB wt%": "最大化ENB含量",
    "minimize ENB residue": "最小化ENB残留",
    "target Mooney": "目标门尼",
    "target C2 wt%": "目标乙烯含量",
    "minimize fouling": "最小化挂胶风险",
    "maximize productivity": "最大化催化剂生产率",
}


def _config_with_variable(base: ProcessConfig, variable: str, value: float) -> ProcessConfig:
    """Return a copied config with one sensitivity variable changed."""
    cfg = ProcessConfig(**model_dump_compat(base))
    if variable == "ENB feed":
        cfg.enb_kg_h = max(value, 0.0)
    elif variable == "E/P ratio":
        total = positive(cfg.ethylene_kg_h + cfg.propylene_kg_h)
        ratio = max(value, 0.02)
        cfg.ethylene_kg_h = total * ratio / (1.0 + ratio)
        cfg.propylene_kg_h = total / (1.0 + ratio)
    elif variable == "hydrogen":
        cfg.hydrogen_g_h = max(value, 0.0)
    elif variable == "Al/Ti":
        cfg.AlTi_ratio = max(value, 1.0)
    elif variable == "residence_time":
        cfg.residence_time_min = max(value, 0.1)
    elif variable == "num_cstr":
        cfg.num_cstr = int(max(round(value), 1))
        cfg.reactor_mode = "CSTR series"
    else:
        setattr(cfg, variable, value)
    return cfg


def _row_from_result(variable: str, value: float, result: Any) -> dict[str, Any]:
    """Build a KPI row from a flowsheet result."""
    k = result.kpis
    return {
        "variable": variable,
        "value": value,
        "polymer_kg_h": k["polymer_kg_h"],
        "C2_conversion_pct": k["C2_conversion_pct"],
        "C3_conversion_pct": k["C3_conversion_pct"],
        "ENB_conversion_pct": k["ENB_conversion_pct"],
        "C2_wt": k["C2_wt"],
        "ENB_wt": k["ENB_wt"],
        "Mooney": k["Mooney"],
        "Mw": k["Mw"],
        "heat_duty_kW": k["heat_duty_kW"],
        "ENB_residue_ppm": k["ENB_residue_ppm"],
        "fouling_index": k["fouling_index"],
        "productivity": k["catalyst_productivity_g_mol_h"],
    }


def scan_single_variable(base: ProcessConfig, variable: str, values: Iterable[float]) -> pd.DataFrame:
    """Run a one-dimensional sensitivity scan."""
    rows = []
    for value in values:
        cfg = _config_with_variable(base, variable, float(value))
        result = run_flowsheet(cfg)
        rows.append(_row_from_result(variable, float(value), result))
    return pd.DataFrame(rows)


def scan_two_variables(
    base: ProcessConfig,
    variable_x: str,
    values_x: Iterable[float],
    variable_y: str,
    values_y: Iterable[float],
) -> pd.DataFrame:
    """Run a two-dimensional sensitivity scan."""
    rows = []
    for value_x, value_y in product(values_x, values_y):
        cfg = _config_with_variable(base, variable_x, float(value_x))
        cfg = _config_with_variable(cfg, variable_y, float(value_y))
        result = run_flowsheet(cfg)
        row = _row_from_result(f"{variable_x}/{variable_y}", float(value_x), result)
        row[variable_x] = float(value_x)
        row[variable_y] = float(value_y)
        rows.append(row)
    return pd.DataFrame(rows)


def default_values_for_variable(base: ProcessConfig, variable: str, points: int = 9) -> np.ndarray:
    """Return sensible default scan values for a variable."""
    if variable == "temperature_C":
        return np.linspace(80.0, 130.0, points)
    if variable == "pressure_MPa":
        return np.linspace(0.5, 2.0, points)
    if variable == "ENB feed":
        return np.linspace(max(base.enb_kg_h * 0.3, 0.0), max(base.enb_kg_h * 2.5, 0.5), points)
    if variable == "E/P ratio":
        return np.linspace(0.4, 2.8, points)
    if variable == "hydrogen":
        return np.linspace(0.0, max(base.hydrogen_g_h * 3.0, 3.0), points)
    if variable == "Al/Ti":
        return np.linspace(200.0, 3000.0, points)
    if variable == "residence_time":
        return np.linspace(10.0, 90.0, points)
    if variable == "num_cstr":
        return np.arange(1, min(points, 6) + 1)
    return np.linspace(0.5, 1.5, points)
