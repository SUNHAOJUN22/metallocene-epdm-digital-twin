"""Model confidence scoring for R&D digital-twin outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .conservation import ConservationResult
from .engineering_checks import EngineeringCheckResult, run_engineering_checks
from .engineering_rules import EngineeringRuleResult
from .preflight import PreflightResult
from .model_registry import registry_summary
from .numerics import bounded


@dataclass(frozen=True)
class ModelConfidenceCard:
    """A compact scorecard for model credibility and freshness."""

    overall_score: float
    data_score: float
    model_score: float
    numerical_score: float
    engineering_score: float
    calibration_score: float
    freshness_score: float
    preflight_score: float = 100.0
    conservation_score: float = 100.0
    engineering_rule_score: float = 100.0
    identifiability_score: float = 80.0
    uncertainty_score: float = 70.0
    validation_data_score: float = 80.0
    risk_flags: list[str] = field(default_factory=list)
    recommended_next_data: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return a report-friendly dictionary."""
        return {
            "overall_score": self.overall_score,
            "data_score": self.data_score,
            "model_score": self.model_score,
            "numerical_score": self.numerical_score,
            "engineering_score": self.engineering_score,
            "calibration_score": self.calibration_score,
            "freshness_score": self.freshness_score,
            "preflight_score": self.preflight_score,
            "conservation_score": self.conservation_score,
            "engineering_rule_score": self.engineering_rule_score,
            "identifiability_score": self.identifiability_score,
            "uncertainty_score": self.uncertainty_score,
            "validation_data_score": self.validation_data_score,
            "risk_flags": "; ".join(self.risk_flags),
            "recommended_next_data": "; ".join(self.recommended_next_data),
        }

    def as_dataframe(self) -> pd.DataFrame:
        """Return the scorecard as a DataFrame."""
        return pd.DataFrame([self.as_dict()])


def _score_from_failures(base: float, failure_count: int, warning_count: int = 0, penalty: float = 18.0) -> float:
    """Return a bounded score after failure/warning penalties."""
    return bounded(base - penalty * failure_count - 6.0 * warning_count, 0.0, 100.0)


def build_model_confidence_card(
    result: Any | None = None,
    engineering_checks: list[EngineeringCheckResult] | None = None,
    conservation_results: list[ConservationResult] | None = None,
    uncertainty: Any | None = None,
    calibration_metrics: dict[str, Any] | None = None,
    data_quality: dict[str, Any] | None = None,
    parameter_set_source: str = "default",
    task_log: dict[str, Any] | None = None,
    preflight_results: list[PreflightResult] | None = None,
    engineering_rule_results: list[EngineeringRuleResult] | None = None,
    identifiability: Any | None = None,
) -> ModelConfidenceCard:
    """Build a weighted model confidence card.

    This is a transparent screening score, not a statistical guarantee.
    It penalizes missing calibration, stale tasks, failed conservation and
    failed engineering checks so users know which result needs more evidence.
    """
    risk_flags: list[str] = []
    next_data: list[str] = []
    registry = registry_summary()
    model_score = _score_from_failures(100.0, len(registry.get("validation_errors", [])), 0, 12.0)
    if registry.get("validation_errors"):
        risk_flags.append("模型注册表存在未闭合元数据")

    if engineering_checks is None and result is not None:
        engineering_checks = run_engineering_checks(result)
    engineering_checks = engineering_checks or []
    eng_failures = sum(1 for item in engineering_checks if not item.passed and getattr(item, "severity", "") in {"error", "high"})
    eng_warnings = sum(1 for item in engineering_checks if not item.passed) - eng_failures
    engineering_score = _score_from_failures(100.0, eng_failures, eng_warnings)
    if eng_failures or eng_warnings:
        risk_flags.append("存在工程逻辑警告或失败")

    conservation_results = conservation_results or []
    cons_failures = sum(1 for item in conservation_results if not item.passed and item.severity == "error")
    cons_warnings = sum(1 for item in conservation_results if not item.passed) - cons_failures
    conservation_score = _score_from_failures(100.0, cons_failures, cons_warnings)
    preflight_results = preflight_results or []
    preflight_failures = sum(1 for item in preflight_results if not item.passed and item.severity == "error")
    preflight_warnings = sum(1 for item in preflight_results if not item.passed) - preflight_failures
    preflight_score = _score_from_failures(100.0, preflight_failures, preflight_warnings)
    numerical_score = round(0.55 * conservation_score + 0.45 * preflight_score, 1)
    if cons_failures:
        risk_flags.append("守恒闭合失败")
    if preflight_failures:
        risk_flags.append("前置输入校验失败")

    data_score = 95.0
    if data_quality:
        missing = len(data_quality.get("missing_fields", []) or [])
        outliers = len(data_quality.get("outliers", []) or [])
        data_score = _score_from_failures(100.0, missing, outliers, 8.0)
    else:
        data_score = 82.0
        next_data.append("补充带单位和催化剂编号的实验数据表")

    calibration_score = 75.0 if parameter_set_source == "default" else 90.0
    if calibration_metrics:
        mae = float(calibration_metrics.get("mae", 0.0) or 0.0)
        calibration_score = bounded(95.0 - min(mae, 50.0), 25.0, 100.0)
    elif parameter_set_source == "default":
        risk_flags.append("当前参数集未由本地实验重新校准")
        next_data.append("增加压力、ENB、H2、Al/Ti正交实验用于参数估计")

    freshness_score = 100.0
    if task_log:
        stale: list[str] = []
        for task_id, item in task_log.items():
            stale_reason = item.get("stale_reason", "") if isinstance(item, dict) else getattr(item, "stale_reason", "")
            if stale_reason:
                stale.append(task_id)
        freshness_score = bounded(100.0 - 10.0 * len(stale), 0.0, 100.0)
        if stale:
            risk_flags.append("部分重任务结果已过期")
    elif uncertainty is None:
        freshness_score = 90.0

    if uncertainty is None:
        next_data.append("运行不确定性分析以获得KPI置信区间")
    uncertainty_score = 90.0 if uncertainty is not None else 65.0
    if uncertainty is None:
        risk_flags.append("尚未运行不确定性分析")

    engineering_rule_results = engineering_rule_results or []
    rule_failures = sum(1 for item in engineering_rule_results if not item.passed and item.severity == "error")
    rule_warnings = sum(1 for item in engineering_rule_results if not item.passed) - rule_failures
    engineering_rule_score = _score_from_failures(100.0, rule_failures, rule_warnings)

    identifiability_score = 80.0
    if identifiability is not None and hasattr(identifiability, "status"):
        statuses = identifiability.status
        weak = int((statuses["status"] == "weakly_identifiable").sum()) if "status" in statuses else 0
        not_id = int((statuses["status"] == "not_identifiable").sum()) if "status" in statuses else 0
        identifiability_score = _score_from_failures(100.0, not_id, weak, 20.0)
        if weak or not_id:
            risk_flags.append("存在弱可辨识参数")
            next_data.append("补充压力、H2、ENB和停留时间梯度实验")

    validation_data_score = data_score

    overall = (
        0.12 * data_score
        + 0.13 * model_score
        + 0.16 * numerical_score
        + 0.13 * engineering_score
        + 0.11 * calibration_score
        + 0.10 * freshness_score
        + 0.09 * engineering_rule_score
        + 0.08 * identifiability_score
        + 0.08 * uncertainty_score
    )
    return ModelConfidenceCard(
        overall_score=round(bounded(overall, 0.0, 100.0), 1),
        data_score=round(data_score, 1),
        model_score=round(model_score, 1),
        numerical_score=round(numerical_score, 1),
        engineering_score=round(engineering_score, 1),
        calibration_score=round(calibration_score, 1),
        freshness_score=round(freshness_score, 1),
        preflight_score=round(preflight_score, 1),
        conservation_score=round(conservation_score, 1),
        engineering_rule_score=round(engineering_rule_score, 1),
        identifiability_score=round(identifiability_score, 1),
        uncertainty_score=round(uncertainty_score, 1),
        validation_data_score=round(validation_data_score, 1),
        risk_flags=risk_flags or ["未发现高优先级模型可信度风险"],
        recommended_next_data=next_data or ["维持当前校准数据集并补充重复实验"],
    )
