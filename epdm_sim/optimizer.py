"""Process optimizer for target EPDM/EPM grades."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import differential_evolution

from .flowsheet import ProcessConfig, run_flowsheet
from .polymer_props import grade_match, load_target_grades
from .residual_objective import residual_penalty_for_optimizer
from .utils import clamp, mid_range, model_dump_compat, positive


@dataclass
class OptimizationResult:
    """Optimization output for Streamlit and reports."""

    grade_id: str
    success: bool
    feasible: bool
    score: float
    objective: float
    config: ProcessConfig
    kpis: dict[str, Any]
    history: list[dict[str, float]] = field(default_factory=list)
    message: str = ""


def _set_decision_variables(base: ProcessConfig, x: np.ndarray) -> ProcessConfig:
    """Map optimizer vector to process configuration."""
    cfg = ProcessConfig(**model_dump_compat(base))
    cfg.temperature_C = float(x[0])
    cfg.pressure_MPa = float(x[1])
    ep_ratio = max(float(x[2]), 0.05)
    total_ep = positive(base.ethylene_kg_h + base.propylene_kg_h)
    cfg.ethylene_kg_h = total_ep * ep_ratio / (1.0 + ep_ratio)
    cfg.propylene_kg_h = total_ep / (1.0 + ep_ratio)
    cfg.enb_kg_h = float(x[3])
    cfg.hydrogen_g_h = float(x[4])
    cfg.residence_time_min = float(x[5])
    cfg.num_cstr = int(round(clamp(float(x[6]), 1.0, 4.0)))
    cfg.reactor_mode = "CSTR series"
    return cfg


def _objective(base: ProcessConfig, grade_id: str, enb_residue_threshold_ppm: float, history: list[dict[str, float]]):
    """Build an objective function closure."""
    grade = load_target_grades()[grade_id]
    c2_mid = mid_range(grade["C2_min"], grade["C2_max"])
    enb_mid = mid_range(grade["ENB_min"], grade["ENB_max"])
    ml_mid = mid_range(grade["ML_min"], grade["ML_max"])

    def func(x: np.ndarray) -> float:
        cfg = _set_decision_variables(base, x)
        result = run_flowsheet(cfg)
        k = result.kpis
        c2_span = max(grade["C2_max"] - grade["C2_min"], 1.0)
        enb_span = max(grade["ENB_max"] - grade["ENB_min"], 0.5)
        ml_span = max(grade["ML_max"] - grade["ML_min"], 5.0)
        value = (
            ((k["C2_wt"] - c2_mid) / c2_span) ** 2
            + ((k["ENB_wt"] - enb_mid) / enb_span) ** 2
            + ((k["Mooney"] - ml_mid) / ml_span) ** 2
        )
        value += 2.0 * max(k["fouling_index"] - 3.0, 0.0) ** 2
        value += 1.5 * max(k["ENB_residue_ppm"] - enb_residue_threshold_ppm, 0.0) / max(enb_residue_threshold_ppm, 1.0)
        value += 0.01 * residual_penalty_for_optimizer(result)
        value -= 0.05 * np.log1p(max(k["catalyst_productivity_g_mol_h"], 0.0) / 1.0e6)
        history.append({"iteration": len(history), "objective": float(value), "score": grade_match(k, grade_id)["score"]})
        return float(value)

    return func


def optimize_for_grade(
    base: ProcessConfig,
    grade_id: str = "A",
    maxiter: int = 20,
    enb_residue_threshold_ppm: float = 80000.0,
) -> OptimizationResult:
    """Optimize operating window for a target grade using differential evolution."""
    grade_id = grade_id if grade_id in load_target_grades() else "A"
    history: list[dict[str, float]] = []
    bounds = [
        (80.0, 130.0),
        (0.5, 1.8),
        (0.35, 3.0),
        (0.0, max(base.enb_kg_h * 3.0, 8.0)),
        (0.0, max(base.hydrogen_g_h * 4.0, 20.0)),
        (10.0, 90.0),
        (1.0, 4.0),
    ]
    try:
        opt = differential_evolution(
            _objective(base, grade_id, enb_residue_threshold_ppm, history),
            bounds=bounds,
            maxiter=maxiter,
            popsize=6,
            tol=0.02,
            polish=True,
            seed=7,
            updating="immediate",
            workers=1,
        )
        cfg = _set_decision_variables(base, opt.x)
        result = run_flowsheet(cfg)
        match = grade_match(result.kpis, grade_id)
        feasible = (
            match["score"] >= 55.0
            and result.kpis["fouling_index"] < 3.0
            and result.kpis["ENB_residue_ppm"] <= enb_residue_threshold_ppm
        )
        return OptimizationResult(
            grade_id=grade_id,
            success=bool(opt.success or match["score"] >= 55.0),
            feasible=feasible,
            score=match["score"],
            objective=float(opt.fun),
            config=cfg,
            kpis=result.kpis,
            history=history,
            message=str(opt.message),
        )
    except Exception as exc:
        result = run_flowsheet(base)
        match = grade_match(result.kpis, grade_id)
        return OptimizationResult(
            grade_id=grade_id,
            success=False,
            feasible=False,
            score=match["score"],
            objective=1.0e9,
            config=base,
            kpis=result.kpis,
            history=history,
            message=f"优化失败: {exc}",
        )
