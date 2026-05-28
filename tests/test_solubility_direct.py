import pandas as pd

from epdm_sim.solubility import (
    calibrate_henry_parameters,
    gas_liquid_saturation_table,
    gas_mole_fractions_from_feeds,
    henry_cstar_comparison,
    liquid_saturation_concentration_mol_L,
    load_solubility_records,
    solubility_records_dataframe,
)


def test_solubility_direct_pressure_and_calibration():
    records = load_solubility_records()
    assert ("ethylene", "hexane") in records
    assert not solubility_records_dataframe().empty
    low = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 0.5)
    high = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 1.5)
    assert high > low >= 0
    y = gas_mole_fractions_from_feeds(2, 1, 0.1)
    assert abs(sum(y.values()) - 1.0) < 1e-12
    assert not gas_liquid_saturation_table(373.15, 1.0, y).empty
    assert not henry_cstar_comparison(373.15, 1.0, y, catalyst_family="CGC-like").empty
    fitted = calibrate_henry_parameters(
        pd.DataFrame({"temperature_K": [373.15], "partial_pressure_MPa": [1.0], "C_star_mol_L": [0.2]}),
        component="ethylene",
        solvent="hexane",
    )
    assert fitted.solubility_ref_mol_L_MPa > 0
