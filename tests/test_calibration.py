import math

from epdm_sim.calibration import (
    calibrate_from_internal_data,
    catalyst_dataframe,
    hydrogen_tuning_recommendation,
    recommend_doe,
)
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_catalyst_knowledge_base_loads_pdf_rules():
    df = catalyst_dataframe()
    assert "C3-3-TiMe2" in set(df["catalyst_id"])
    assert df["notes"].str.contains("0.7").any()


def test_calibration_returns_finite_parameters_and_residuals():
    result = calibrate_from_internal_data()
    for key in ["k_E_ref", "k_P_ref", "k_ENB_ref", "beta_P", "beta_E", "Mw0", "ktr_H2", "kd_h"]:
        assert key in result.params
        assert math.isfinite(result.params[key])
        assert result.params[key] > 0.0
    assert not result.residuals.empty
    assert {"target", "observed", "predicted", "residual"}.issubset(result.residuals.columns)


def test_doe_and_hydrogen_recommendation_are_actionable():
    cfg = load_default_config()
    doe = recommend_doe("ENB wt%", cfg, n=6)
    assert len(doe) == 6
    assert {"pressure_MPa", "ENB_kg_h", "rationale"}.issubset(doe.columns)
    flowsheet = run_flowsheet(cfg)
    rec = hydrogen_tuning_recommendation(300000.0, 65.0, cfg, flowsheet.kpis)
    assert rec["recommended_H2_g_h"] >= 0.0
    assert "warning" in rec
