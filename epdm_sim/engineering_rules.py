"""Chemical-engineering trend rule registry and runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from .flash import Flash
from .flowsheet import ProcessConfig, load_default_config, run_flowsheet
from .fluid_props import calculate_pipe_hydraulics, polymer_solution_viscosity
from .heat_balance import calculate_reaction_heat
from .streams import Stream
from .utils import c_to_k, data_path, load_json, mpa_to_pa, positive


@dataclass(frozen=True)
class EngineeringRule:
    """One expected engineering trend rule."""

    rule_id: str
    description: str
    module_id: str
    independent_variable: str
    dependent_variable: str
    expected_trend: str
    condition: str
    test_points: list[float]
    tolerance: float
    rationale: str
    severity: str
    suggested_fix: str


@dataclass(frozen=True)
class EngineeringRuleResult:
    """Result of one engineering trend check."""

    rule_id: str
    passed: bool
    observed_values: dict[str, float]
    expected_trend: str
    severity: str
    message: str
    suggested_fix: str

    def as_dict(self) -> dict[str, Any]:
        """Return a UI/report friendly dictionary."""
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "observed_values": self.observed_values,
            "expected_trend": self.expected_trend,
            "severity": self.severity,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


def load_engineering_rules(path: str | None = None) -> list[EngineeringRule]:
    """Load engineering trend rules from JSON."""
    payload = load_json(data_path("engineering_rules.json") if path is None else path)
    return [EngineeringRule(**item) for item in payload.get("rules", [])]


def rules_dataframe(rules: list[EngineeringRule] | None = None) -> pd.DataFrame:
    """Return registered rules as a DataFrame."""
    rules = load_engineering_rules() if rules is None else rules
    return pd.DataFrame([rule.__dict__ for rule in rules])


def rule_results_dataframe(results: list[EngineeringRuleResult]) -> pd.DataFrame:
    """Return rule results as a DataFrame."""
    return pd.DataFrame([result.as_dict() for result in results])


def _cfg(base: ProcessConfig | None = None, **updates: Any) -> ProcessConfig:
    """Return a copy of the default/base configuration with updates."""
    cfg = (base or load_default_config()).model_copy(deep=True)
    for key, value in updates.items():
        setattr(cfg, key, value)
    return cfg


def _solution_stream() -> Stream:
    """Build a small generic solvent stream for rheology checks."""
    return Stream.from_mass_flows(
        "engineering-rule-solution",
        temperature_K=c_to_k(100.0),
        pressure_Pa=mpa_to_pa(1.0),
        mass_flows={"hexane": 100.0},
        phase="liquid",
    )


def _trend_pass(expected: str, values: list[float], tolerance: float) -> bool:
    """Evaluate a two-point trend with tolerance."""
    if len(values) < 2:
        return True
    first, second = values[0], values[-1]
    tol = abs(float(tolerance))
    if expected == "increases":
        return second > first + tol
    if expected == "decreases":
        return second < first - tol
    if expected == "nondecreasing":
        return second >= first - tol
    if expected == "nonincreasing":
        return second <= first + tol
    if expected == "bounded":
        return all(value == value and abs(value) < 1.0e30 for value in values)
    return True


def _result(rule: EngineeringRule, observed: dict[str, float], passed: bool) -> EngineeringRuleResult:
    """Build a rule result."""
    observed_text = ", ".join(f"{key}={value:.5g}" for key, value in observed.items())
    return EngineeringRuleResult(
        rule_id=rule.rule_id,
        passed=passed,
        observed_values=observed,
        expected_trend=rule.expected_trend,
        severity="ok" if passed else rule.severity,
        message=(f"{rule.description} 观测值: {observed_text}" if passed else f"{rule.description} 未满足。观测值: {observed_text}"),
        suggested_fix="" if passed else rule.suggested_fix,
    )


def _flowsheet_pair(rule: EngineeringRule, config: ProcessConfig | None, key: str) -> EngineeringRuleResult:
    low, high = rule.test_points[:2]
    low_result = run_flowsheet(_cfg(config, **{key: low}))
    high_result = run_flowsheet(_cfg(config, **{key: high}))
    observed = {f"{key}={low}": float(low_result.kpis[rule.dependent_variable]), f"{key}={high}": float(high_result.kpis[rule.dependent_variable])}
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_h2_mw(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    return _flowsheet_pair(rule, config, "hydrogen_g_h")


def _run_h2_mooney(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    return _flowsheet_pair(rule, config, "hydrogen_g_h")


def _run_solids_viscosity(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    stream = _solution_stream()
    low, high = rule.test_points[:2]
    observed = {
        f"solids={low}": polymer_solution_viscosity(stream, c_to_k(100.0), 300000.0, solids_wt_override=low),
        f"solids={high}": polymer_solution_viscosity(stream, c_to_k(100.0), 300000.0, solids_wt_override=high),
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_temperature_viscosity(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    stream = _solution_stream()
    low, high = rule.test_points[:2]
    observed = {
        f"T={low}": polymer_solution_viscosity(stream, c_to_k(low), 300000.0, solids_wt_override=20.0),
        f"T={high}": polymer_solution_viscosity(stream, c_to_k(high), 300000.0, solids_wt_override=20.0),
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_mw_viscosity(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    stream = _solution_stream()
    low, high = rule.test_points[:2]
    observed = {
        f"Mw={low}": polymer_solution_viscosity(stream, c_to_k(100.0), low, solids_wt_override=20.0),
        f"Mw={high}": polymer_solution_viscosity(stream, c_to_k(100.0), high, solids_wt_override=20.0),
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_pipe_diameter(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    low, high = rule.test_points[:2]
    observed = {
        f"D={low}": calculate_pipe_hydraulics(700.0, 0.01, 1.0, 10.0, low).pressure_drop_kPa,
        f"D={high}": calculate_pipe_hydraulics(700.0, 0.01, 1.0, 10.0, high).pressure_drop_kPa,
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_flow_drop(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    low, high = rule.test_points[:2]
    observed = {
        f"Q={low}": calculate_pipe_hydraulics(700.0, 0.01, low, 10.0, 0.05).pressure_drop_kPa,
        f"Q={high}": calculate_pipe_hydraulics(700.0, 0.01, high, 10.0, 0.05).pressure_drop_kPa,
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_conversion_heat(rule: EngineeringRule, _config: ProcessConfig | None) -> EngineeringRuleResult:
    low, high = rule.test_points[:2]
    observed = {
        f"scale={low}": calculate_reaction_heat({"ethylene": 10.0 * low, "propylene": 5.0 * low, "ENB": low}),
        f"scale={high}": calculate_reaction_heat({"ethylene": 10.0 * high, "propylene": 5.0 * high, "ENB": high}),
    }
    return _result(rule, observed, _trend_pass(rule.expected_trend, list(observed.values()), rule.tolerance))


def _run_flash_pressure(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    result = run_flowsheet(config or load_default_config())
    inlet = result.streams["Quenched solution"]
    high_p, low_p = rule.test_points[:2]
    high = Flash("rule-high").calculate(inlet, c_to_k(100.0), high_p)
    low = Flash("rule-low").calculate(inlet, c_to_k(100.0), low_p)
    observed = {f"P={high_p}": high.vapor_fraction, f"P={low_p}": low.vapor_fraction}
    # The rule lists pressure high->low; vapor fraction should nondecrease as pressure decreases.
    passed = low.vapor_fraction >= high.vapor_fraction - rule.tolerance
    return _result(rule, observed, passed)


def _run_polymer_stays_liquid(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    result = run_flowsheet(config or load_default_config())
    observed = {
        "flash1_polymer_vapor": positive(result.flash1.vapor.polymer_mass_kg_h),
        "flash2_polymer_vapor": positive(result.flash2.vapor.polymer_mass_kg_h),
    }
    passed = max(observed.values()) <= max(rule.tolerance, 1.0e-12)
    return _result(rule, observed, passed)


def _run_high_pressure_enb(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    return _flowsheet_pair(rule, config, "pressure_MPa")


def _run_enb_feed(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    return _flowsheet_pair(rule, config, "enb_kg_h")


def _run_alti(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    return _flowsheet_pair(rule, config, "AlTi_ratio")


def _run_bht(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    low, high = rule.test_points[:2]
    low_result = run_flowsheet(_cfg(config, BHT_ratio=low))
    high_result = run_flowsheet(_cfg(config, BHT_ratio=high))
    observed = {f"BHT={low}": low_result.kpis["polymer_kg_h"], f"BHT={high}": high_result.kpis["polymer_kg_h"]}
    passed = all(value >= -rule.tolerance for value in observed.values())
    return _result(rule, observed, passed)


def _run_composition(rule: EngineeringRule, config: ProcessConfig | None) -> EngineeringRuleResult:
    result = run_flowsheet(config or load_default_config())
    total = result.kpis["C2_wt"] + result.kpis["C3_wt"] + result.kpis["ENB_wt"]
    observed = {"C2+C3+ENB": total}
    passed = abs(total - 100.0) <= rule.tolerance
    return _result(rule, observed, passed)


RUNNERS: dict[str, Callable[[EngineeringRule, ProcessConfig | None], EngineeringRuleResult]] = {
    "h2_mw_decreases": _run_h2_mw,
    "h2_mooney_decreases": _run_h2_mooney,
    "solids_viscosity_increases": _run_solids_viscosity,
    "temperature_viscosity_decreases": _run_temperature_viscosity,
    "mw_viscosity_increases": _run_mw_viscosity,
    "pipe_diameter_drop_increases": _run_pipe_diameter,
    "flow_drop_increases": _run_flow_drop,
    "conversion_heat_increases": _run_conversion_heat,
    "flash_pressure_vapor_increases": _run_flash_pressure,
    "polymer_stays_liquid": _run_polymer_stays_liquid,
    "high_pressure_enb_not_raise": _run_high_pressure_enb,
    "enb_feed_enb_wt_increases": _run_enb_feed,
    "low_alti_activity_drops": _run_alti,
    "bht_activity_nonnegative": _run_bht,
    "product_composition_100": _run_composition,
}


def run_engineering_rule(rule_id: str, config: ProcessConfig | None = None) -> EngineeringRuleResult:
    """Run one registered engineering trend rule."""
    rules = {rule.rule_id: rule for rule in load_engineering_rules()}
    if rule_id not in rules:
        raise KeyError(f"Unknown engineering rule: {rule_id}")
    rule = rules[rule_id]
    runner = RUNNERS.get(rule_id)
    if runner is None:
        return _result(rule, {"runner_missing": 1.0}, False)
    try:
        return runner(rule, config)
    except Exception as exc:  # pragma: no cover - defensive UI path
        return EngineeringRuleResult(
            rule_id=rule.rule_id,
            passed=False,
            observed_values={"error": 1.0},
            expected_trend=rule.expected_trend,
            severity=rule.severity,
            message=f"{rule.description} 运行失败：{exc}",
            suggested_fix=rule.suggested_fix,
        )


def run_all_engineering_rules(config: ProcessConfig | None = None) -> list[EngineeringRuleResult]:
    """Run all default trend rules. This is intended for explicit button use."""
    return [run_engineering_rule(rule.rule_id, config) for rule in load_engineering_rules()]
