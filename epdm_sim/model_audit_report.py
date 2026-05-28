"""Audit-grade model credibility report assembly."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import pandas as pd

from .conservation import conservation_dataframe, run_conservation_checks
from .engineering_checks import checks_dataframe, run_engineering_checks
from .experimental_benchmark import benchmark_confidence_score
from .benchmark_calibration import update_model_confidence_from_benchmarks
from .calibrated_property_models import calibrated_property_model_score
from .data_lineage import lineage_confidence_score
from .identifiability import evaluate_identifiability
from .model_confidence import ModelConfidenceCard, build_model_confidence_card
from .preflight import preflight_dataframe, run_preflight_for_flowsheet
from .residual_system import build_flowsheet_residual_system, residual_system_acceptance


@dataclass
class ModelAuditReport:
    """Traceable model audit report used by UI and report exports."""

    model_confidence_card: ModelConfidenceCard
    preflight_summary: pd.DataFrame
    conservation_summary: pd.DataFrame
    engineering_rules_summary: pd.DataFrame
    identifiability_summary: pd.DataFrame
    uncertainty_summary: pd.DataFrame
    data_quality_summary: pd.DataFrame
    calibration_summary: pd.DataFrame
    task_freshness_summary: pd.DataFrame
    top_risks: pd.DataFrame
    recommended_next_actions: pd.DataFrame

    def as_dataframe(self) -> pd.DataFrame:
        """Return the confidence scorecard."""
        return self.model_confidence_card.as_dataframe()


def build_model_audit_report(
    result: Any,
    *,
    uncertainty: Any | None = None,
    data_quality: Any | None = None,
    calibration_metrics: dict[str, Any] | None = None,
    property_calibration_metrics: dict[str, Any] | None = None,
    thermo_calibration_metrics: dict[str, Any] | None = None,
    parameter_set_source: str = "default",
    task_log: dict[str, Any] | None = None,
) -> ModelAuditReport:
    """Build a reproducible audit report from existing results only."""
    preflight = run_preflight_for_flowsheet(result.config)
    conservation = run_conservation_checks(result)
    engineering = run_engineering_checks(result)
    ident = evaluate_identifiability(config=result.config)
    card = build_model_confidence_card(
        result,
        engineering_checks=engineering,
        conservation_results=conservation,
        uncertainty=uncertainty,
        calibration_metrics=calibration_metrics,
        data_quality=data_quality if isinstance(data_quality, dict) else None,
        parameter_set_source=parameter_set_source,
        task_log=task_log,
        preflight_results=preflight,
        identifiability=ident,
    )
    residual_system = build_flowsheet_residual_system(result)
    residual_acceptance = residual_system_acceptance(residual_system)
    benchmark_adjustment = update_model_confidence_from_benchmarks(card.overall_score, result.kpis)
    if benchmark_adjustment["adjusted_score"] < card.overall_score:
        card = replace(
            card,
            overall_score=round(float(benchmark_adjustment["adjusted_score"]), 1),
            risk_flags=[*card.risk_flags, "实验/标准 benchmark 残差降低模型可信度"],
            recommended_next_data=[*card.recommended_next_data, "补充 benchmark_calibration 中建议的数据缺口"],
        )
    if not residual_acceptance["passed"]:
        residual_penalty = 20.0 if residual_acceptance["critical_count"] else 8.0
        lowered_numerical = max(0.0, card.numerical_score - residual_penalty)
        lowered_overall = max(0.0, card.overall_score - 0.16 * residual_penalty)
        card = replace(
            card,
            numerical_score=round(lowered_numerical, 1),
            overall_score=round(lowered_overall, 1),
            risk_flags=[*card.risk_flags, f"守恒残差未达标: score={residual_system.overall_score:.1f}"],
            recommended_next_data=[*card.recommended_next_data, "优先定位 residual_system 中的 suspected_source"],
        )
    risks = [{"rank": idx + 1, "risk": risk} for idx, risk in enumerate(card.risk_flags[:5])]
    actions = [{"rank": idx + 1, "recommended_action": action} for idx, action in enumerate(card.recommended_next_data[:6])]
    calibration_payload = calibration_metrics or {"status": "not_run_or_default"}
    if property_calibration_metrics:
        calibration_payload = {**calibration_payload, **{f"property_{key}": value for key, value in property_calibration_metrics.items()}}
    if thermo_calibration_metrics:
        calibration_payload = {**calibration_payload, **{f"thermo_{key}": value for key, value in thermo_calibration_metrics.items()}}
    calibration_payload.setdefault("kinetic_calibration_score", 35.0 if parameter_set_source == "default" else 70.0)
    calibration_payload.setdefault("property_calibration_score", 35.0 if not property_calibration_metrics else 70.0)
    calibration_payload.setdefault("thermo_calibration_score", 35.0 if not thermo_calibration_metrics else 70.0)
    calibration_payload.setdefault("validation_data_score", max(35.0 if not data_quality else 60.0, lineage_confidence_score()))
    calibration_payload.setdefault("experimental_benchmark_score", benchmark_confidence_score())
    calibration_payload.setdefault("data_lineage_score", lineage_confidence_score())
    calibration_payload.setdefault("calibrated_property_model_score", calibrated_property_model_score())
    calibration_payload.setdefault("benchmark_adjusted_score", benchmark_adjustment["adjusted_score"])
    calibration_payload.setdefault("benchmark_pass_rate", benchmark_adjustment["benchmark_pass_rate"])
    calibration_payload.setdefault("residual_system_score", residual_system.overall_score)
    calibration_payload.setdefault("residual_critical_count", residual_acceptance["critical_count"])
    calibration_df = pd.DataFrame([calibration_payload])
    data_quality_df = pd.DataFrame([data_quality or {"status": "not_supplied"}]) if not hasattr(data_quality, "as_dataframe") else data_quality.as_dataframe()
    task_df = pd.DataFrame.from_dict(task_log or {"flowsheet_fast": {"status": "cached_or_current"}}, orient="index").reset_index(names="task_id")
    uncertainty_df = uncertainty.as_dataframe() if uncertainty is not None else pd.DataFrame([{"status": "not_run"}])
    return ModelAuditReport(
        model_confidence_card=card,
        preflight_summary=preflight_dataframe(preflight),
        conservation_summary=conservation_dataframe(conservation),
        engineering_rules_summary=checks_dataframe(engineering),
        identifiability_summary=ident.as_dataframe(),
        uncertainty_summary=uncertainty_df,
        data_quality_summary=data_quality_df,
        calibration_summary=calibration_df,
        task_freshness_summary=task_df,
        top_risks=pd.DataFrame(risks),
        recommended_next_actions=pd.DataFrame(actions),
    )
