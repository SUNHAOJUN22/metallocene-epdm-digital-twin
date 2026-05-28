from epdm_sim.residual_aware_decision_engine import (
    residual_aware_decision_engine,
    residual_decision_engine_dataframe,
    residual_decision_engine_gate,
)
from epdm_sim.residual_system import ResidualSystem, make_residual


def test_decision_engine_accepts_default_and_rejects_outside_or_critical():
    ok = residual_aware_decision_engine({"candidate_id": "ok", "temperature_C": 100.0, "pressure_MPa": 1.5}, ResidualSystem())
    outside = residual_aware_decision_engine({"candidate_id": "bad", "temperature_C": 1000.0, "pressure_MPa": 1.5}, ResidualSystem())
    critical = ResidualSystem(mass_residuals=[make_residual("mass_bad", "in=out", 10.0, 0.0, "kg/h", 0.1, "reactor", "fix", "critical")])
    rejected = residual_aware_decision_engine({"candidate_id": "critical", "temperature_C": 100.0, "pressure_MPa": 1.5}, critical)
    df = residual_decision_engine_dataframe(result_or_system=ResidualSystem())
    gate = residual_decision_engine_gate(ResidualSystem())
    assert ok["passed"]
    assert outside["rejected"] and "outside_validity" in outside["rejected_reason"]
    assert rejected["rejected"]
    assert not df.empty and df["uncertainty_risk_probability"].between(0.0, 1.0).all()
    assert gate["passed"]

