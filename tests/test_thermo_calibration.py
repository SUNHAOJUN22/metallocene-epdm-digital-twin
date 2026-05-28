import numpy as np
import pandas as pd

from epdm_sim.thermo_calibration import (
    calibrate_flash_k_correction,
    calibrate_henry_from_data,
    thermo_calibration_score,
)


def test_henry_calibration_returns_validity_and_residuals():
    df = pd.DataFrame(
        {
            "component": ["ethylene", "ethylene", "ethylene"],
            "solvent": ["hexane", "hexane", "hexane"],
            "temperature_K": [343.15, 363.15, 383.15],
            "partial_pressure_MPa": [0.35, 0.50, 0.75],
            "C_star_mol_L": [0.18, 0.24, 0.34],
        }
    )
    result = calibrate_henry_from_data(df)
    assert result.fitted_params["solubility_ref_mol_L_MPa"] > 0
    assert np.isfinite(list(result.fitted_params.values())).all()
    assert len(result.residuals) == 3
    assert result.validity_range["partial_pressure_MPa"] == (0.35, 0.75)


def test_flash_k_correction_and_score_are_bounded():
    df = pd.DataFrame({"predicted_vapor_recovery": [0.4, 0.6, 0.8], "observed_vapor_recovery": [0.44, 0.66, 0.88]})
    result = calibrate_flash_k_correction(df)
    score = thermo_calibration_score(result)
    assert 0.0 <= score <= 100.0
    assert result.fitted_params["K_correction"] > 0
    assert np.isfinite(result.residuals.to_numpy(dtype=float)).all()
