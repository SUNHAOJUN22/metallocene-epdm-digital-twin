from epdm_sim.calibrated_property_models import CalibratedPropertyModel
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.property_runtime_audit import property_runtime_audit_dataframe, property_runtime_audit_gate, property_runtime_audit_summary


def _models():
    return [
        CalibratedPropertyModel("v64_henry", "henry", {"henry_multiplier": 1.2}, "plant_vle", "hash1", {"temperature_C": [80, 130], "pressure_MPa": [0.5, 2.0]}, {"relative_pct": 0.05}, "plant", 92.0),
        CalibratedPropertyModel("v64_visc", "viscosity", {"viscosity_multiplier": 1.1}, "plant_rheo", "hash2", {"temperature_C": [80, 130], "solids_wt": [5, 25]}, {"relative_pct": 0.05}, "experiment", 88.0),
        CalibratedPropertyModel("v64_deltaH", "deltaH", {"deltaH_kJ_mol": 110.0}, "plant_cal", "hash3", {"temperature_C": [80, 130]}, {"relative_pct": 0.05}, "experiment", 90.0),
    ]


def test_property_runtime_audit_passes_and_records_changes():
    result = run_flowsheet()
    df = property_runtime_audit_dataframe(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0, "solids_wt": 10.0}, models=_models())
    summary = property_runtime_audit_summary(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0, "solids_wt": 10.0}, models=_models())
    gate = property_runtime_audit_gate(result)
    assert not df.empty
    assert df["passed"].astype(bool).all()
    assert summary["passed"]
    assert gate["passed"]
    assert df["critical_residual_count"].max() == 0

