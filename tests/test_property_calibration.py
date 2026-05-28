import numpy as np
import pandas as pd

from epdm_sim.property_calibration import calibrate_heat_release, calibrate_viscosity_model


def test_viscosity_calibration_returns_finite_positive_parameters():
    df = pd.DataFrame(
        {
            "temperature_K": [353.15, 373.15, 393.15, 373.15],
            "solids_wt": [8.0, 12.0, 16.0, 20.0],
            "Mw": [250000.0, 300000.0, 360000.0, 420000.0],
            "viscosity_Pa_s": [0.0022, 0.0042, 0.0095, 0.021],
        }
    )
    result = calibrate_viscosity_model(df)
    assert result.fitted_params["A_mu"] > 0
    assert result.fitted_params["B_mu"] >= 0
    assert result.fitted_params["alpha_Mw"] >= 0
    assert np.isfinite(list(result.fitted_params.values())).all()
    assert not result.residuals.empty
    assert result.validity_range["temperature_K"][0] == 353.15


def test_heat_release_calibration_preserves_exothermic_sign_convention():
    df = pd.DataFrame(
        {
            "consumed_mol": [1.0, 2.0, 3.0, 4.0],
            "Q_rxn_kJ": [90.0, 180.0, 270.0, 360.0],
        }
    )
    result = calibrate_heat_release(df)
    assert result.fitted_params["deltaH_kJ_mol"] < 0
    assert abs(result.fitted_params["deltaH_kJ_mol"] + 90.0) < 1e-9
    assert float(result.residuals["residual"].abs().max()) < 1e-9
