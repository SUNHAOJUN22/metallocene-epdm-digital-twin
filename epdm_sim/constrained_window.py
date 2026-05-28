"""Engineering-constrained process-window recommendation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .residual_objective import residual_penalty_for_optimizer
from .residual_system import build_flowsheet_residual_system, residual_system_acceptance
from .utils import clamp, model_dump_compat


@dataclass
class WindowResult:
    """One robust process window candidate."""

    window_id: str
    variable_ranges: dict[str, tuple[float, float]]
    center_point: dict[str, float]
    predicted_kpis: dict[str, Any]
    constraint_margins: dict[str, float]
    robustness_score: float
    model_confidence_score: float
    recommended_next_validation: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        row = {
            "window_id": self.window_id,
            "robustness_score": self.robustness_score,
            "model_confidence_score": self.model_confidence_score,
            "recommended_next_validation": "; ".join(self.recommended_next_validation),
        }
        row.update({f"center_{key}": value for key, value in self.center_point.items()})
        row.update({f"margin_{key}": value for key, value in self.constraint_margins.items()})
        row.update({f"kpi_{key}": value for key, value in self.predicted_kpis.items() if isinstance(value, (int, float, str))})
        return row


def _evaluate_config(config: ProcessConfig) -> WindowResult | None:
    result = run_flowsheet(config)
    residual_system = build_flowsheet_residual_system(result)
    residual_acceptance = residual_system_acceptance(residual_system)
    if not residual_acceptance["passed"]:
        return None
    k = result.kpis
    margins = {
        "cooling_margin_kW": float(k.get("cooling_margin_kW", 0.0)),
        "fouling_margin": 3.0 - float(k.get("fouling_index", 99.0)),
        "pressure_drop_margin_kPa": 1000.0 - float(k.get("pipe_pressure_drop_kPa", 1.0e9)),
        "solids_margin_wt": 35.0 - float(k.get("solids_wt", 99.0)),
        "ENB_residue_margin_ppm": 50000.0 - float(k.get("ENB_residue_ppm", 1.0e9)),
        "residual_margin_score": 100.0 - residual_penalty_for_optimizer(residual_system),
    }
    if any(value < 0 for value in margins.values()):
        return None
    score = clamp(55.0 + 4.0 * margins["fouling_margin"] + 0.2 * min(margins["cooling_margin_kW"], 100.0), 0.0, 100.0)
    center = {
        "temperature_C": config.temperature_C,
        "pressure_MPa": config.pressure_MPa,
        "ENB_kg_h": config.enb_kg_h,
        "hydrogen_g_h": config.hydrogen_g_h,
        "residence_time_min": config.residence_time_min,
    }
    ranges = {
        key: (value * 0.95 if value else 0.0, value * 1.05 if value else 0.0)
        for key, value in center.items()
    }
    return WindowResult(
        window_id=f"window_T{config.temperature_C:.0f}_P{config.pressure_MPa:.1f}_D{config.enb_kg_h:.1f}",
        variable_ranges=ranges,
        center_point=center,
        predicted_kpis={key: k.get(key) for key in ["C2_wt", "ENB_wt", "Mooney", "Mw", "heat_duty_kW", "cooling_margin_kW", "fouling_index", "pipe_pressure_drop_kPa"]},
        constraint_margins=margins,
        robustness_score=score,
        model_confidence_score=clamp(score - (0.0 if k.get("parameter_set_id") != "default" else 12.0), 0.0, 100.0),
        recommended_next_validation=["Run one endpoint polymerization at center point.", "Verify viscosity and cooling margin experimentally."],
    )


def generate_feasible_windows(base_config: ProcessConfig | dict[str, Any] | None = None) -> list[WindowResult]:
    """Generate feasible windows by perturbing the current fast flowsheet."""
    cfg = base_config if isinstance(base_config, ProcessConfig) else ProcessConfig(**(base_config or {}))
    candidates: list[ProcessConfig] = []
    for name, updates in {
        "stable_low_risk_window": {"temperature_C": cfg.temperature_C - 5.0, "enb_kg_h": cfg.enb_kg_h * 0.9, "hydrogen_g_h": cfg.hydrogen_g_h * 1.1},
        "high_ENB_window": {"pressure_MPa": max(cfg.pressure_MPa * 0.8, 0.7), "enb_kg_h": cfg.enb_kg_h * 1.25},
        "Vistalon_like_match_window": {"temperature_C": cfg.temperature_C, "pressure_MPa": 0.9, "enb_kg_h": cfg.enb_kg_h * 1.05},
        "high_ethylene_window": {"ethylene_kg_h": cfg.ethylene_kg_h * 1.15, "propylene_kg_h": cfg.propylene_kg_h * 0.95},
        "low_residue_window": {"flash2_T_C": cfg.flash2_T_C + 10.0, "flash2_P_MPa": max(cfg.flash2_P_MPa * 0.8, 0.005)},
    }.items():
        payload = model_dump_compat(cfg)
        payload.update(updates)
        candidate = ProcessConfig(**payload)
        window = _evaluate_config(candidate)
        if window is not None:
            window.window_id = name
            candidates.append(candidate)
    windows = [_evaluate_config(candidate) for candidate in candidates]
    return [window for window in windows if window is not None]


def evaluate_window_robustness(window: WindowResult) -> float:
    """Return a bounded robustness score."""
    return clamp(window.robustness_score, 0.0, 100.0)


def rank_process_windows(windows: list[WindowResult]) -> list[WindowResult]:
    """Rank process windows by robustness and confidence."""
    return sorted(windows, key=lambda item: (item.robustness_score, item.model_confidence_score), reverse=True)


def recommend_validation_experiments_for_window(window: WindowResult) -> list[str]:
    """Return validation actions for one recommended process window."""
    return list(window.recommended_next_validation)


def constrained_windows_dataframe(windows: list[WindowResult] | None = None) -> pd.DataFrame:
    """Return process windows as a DataFrame."""
    windows = rank_process_windows(windows or generate_feasible_windows())
    return pd.DataFrame([window.as_dict() for window in windows])
