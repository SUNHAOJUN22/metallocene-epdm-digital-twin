import numpy as np

from epdm_sim.flash import diagnose_flash_result
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.rheology import calculate_rheology
from epdm_sim.units import c_to_k, k_to_c, mpa_to_pa, pa_to_mpa
from epdm_sim.utils import kg_h_to_mol_h, mol_h_to_kg_h


def test_core_property_invariants_with_seeded_samples():
    rng = np.random.default_rng(49)
    for _ in range(12):
        mw = float(rng.uniform(50000, 900000))
        solids = float(rng.uniform(0, 35))
        temp = float(rng.uniform(330, 430))
        rheo = calculate_rheology(temp, solids, mw, 10.0, "hexane")
        assert rheo.apparent_viscosity_Pa_s > 0
        assert np.isfinite(rheo.apparent_viscosity_Pa_s)
        kg = float(rng.uniform(0, 100))
        mw_g = float(rng.uniform(20, 200))
        assert abs(mol_h_to_kg_h(kg_h_to_mol_h(kg, mw_g), mw_g) - kg) < 1e-9
        c = float(rng.uniform(-20, 180))
        assert abs(k_to_c(c_to_k(c)) - c) < 1e-12
        p = float(rng.uniform(0.1, 5.0))
        assert abs(pa_to_mpa(mpa_to_pa(p)) - p) < 1e-12

    result = run_flowsheet(load_default_config())
    assert 0 <= diagnose_flash_result(result.flash1).vapor_fraction <= 1
    assert abs(result.kpis["C2_wt"] + result.kpis["C3_wt"] + result.kpis["ENB_wt"] - 100) < 1e-9
    for key in ("C2_conversion_pct", "C3_conversion_pct", "ENB_conversion_pct"):
        assert 0 <= result.kpis[key] <= 100
    assert result.kpis["liquid_density_kg_m3"] > 0
    assert result.kpis["Cp_liq_kJ_kgK"] > 0
    assert result.kpis["thermal_conductivity_W_mK"] > 0
