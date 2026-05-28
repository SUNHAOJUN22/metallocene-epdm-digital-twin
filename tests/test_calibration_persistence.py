import pandas as pd

from epdm_sim.property_calibration import (
    calibrate_heat_release,
    calibrate_viscosity_model,
    property_calibration_score,
    save_property_calibration_result,
)
from epdm_sim.thermo_calibration import (
    calibrate_flash_k_correction,
    calibrate_henry_from_data,
    save_thermo_calibration_result,
    thermo_calibration_score,
)


def test_property_calibration_persistence_has_audit_metadata(tmp_path):
    viscosity_data = pd.DataFrame(
        {
            "temperature_K": [350.0, 360.0, 370.0, 380.0],
            "solids_wt": [5.0, 10.0, 15.0, 20.0],
            "Mw": [250000.0, 300000.0, 350000.0, 400000.0],
            "viscosity_Pa_s": [0.002, 0.006, 0.02, 0.08],
        }
    )
    result = calibrate_viscosity_model(viscosity_data, dataset_id="visc_v51")
    payload = save_property_calibration_result(result, path=tmp_path / "property.json")
    saved = next(iter(payload["sets"].values()))
    assert saved["dataset_id"] == "visc_v51"
    assert saved["metrics"]["RMSE"] >= 0
    assert saved["data_hash"]
    assert 0 <= property_calibration_score(result) <= 100

    heat = calibrate_heat_release(pd.DataFrame({"consumed_mol": [1.0, 2.0], "Q_rxn_kJ": [90.0, 180.0]}), dataset_id="cal_v51")
    assert heat.fitted_params["deltaH_kJ_mol"] < 0


def test_thermo_calibration_persistence_has_audit_metadata(tmp_path):
    henry_data = pd.DataFrame(
        {
            "temperature_K": [360.0, 370.0, 380.0],
            "partial_pressure_MPa": [0.5, 1.0, 1.5],
            "C_star_mol_L": [0.08, 0.17, 0.25],
        }
    )
    result = calibrate_henry_from_data(henry_data, dataset_id="henry_v51")
    payload = save_thermo_calibration_result(result, path=tmp_path / "thermo.json")
    saved = next(iter(payload["sets"].values()))
    assert saved["dataset_id"] == "henry_v51"
    assert saved["metrics"]["RMSE"] >= 0
    assert saved["data_hash"]
    flash = calibrate_flash_k_correction(
        pd.DataFrame({"predicted_vapor_recovery": [0.5, 0.8], "observed_vapor_recovery": [0.55, 0.76]}),
        dataset_id="flash_v51",
    )
    assert flash.fitted_params["K_correction"] > 0
    assert 0 <= thermo_calibration_score(result, flash) <= 100
