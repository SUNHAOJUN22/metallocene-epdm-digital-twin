from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import load_default_config
from epdm_sim.template_config import TemplateProcessConfig


def test_epdm_dynamic_template_reactor_runs_and_exports_compatibility_columns():
    cfg = load_default_config()
    result = simulate_template_semibatch_ode("EPDM_EPM_metallocene_solution", config=cfg, total_time_min=12, dt_min=2)
    profile = result.profile
    assert {"C_E", "C_P", "C_ENB", "conversion_E", "conversion_P", "conversion_ENB", "C2_wt", "C3_wt", "ENB_wt"}.issubset(profile.columns)
    assert (profile[["polymer_mass_kg", "T_K", "P_Pa"]] >= 0).all().all()
    assert profile["polymer_mass_kg"].diff().dropna().ge(-1e-12).all()
    assert result.summary["quench_stopped_reaction"] is True


def test_generic_dynamic_template_reactor_does_not_require_enb_fields():
    cfg = load_default_config()
    result = simulate_template_semibatch_ode("generic_terpolymerization_apparent", config=cfg, total_time_min=10, dt_min=2)
    assert "C_ENB" not in result.profile.columns
    assert "C_monomer_A_mol_L" in result.profile.columns
    assert result.profile["polymer_mass_kg"].iloc[-1] >= 0


def test_generic_dynamic_template_reactor_accepts_template_process_config():
    cfg = TemplateProcessConfig(
        template_id="generic_terpolymerization_apparent",
        monomer_feeds_kg_h={"monomer_A": 2.0, "monomer_B": 1.5, "monomer_C": 0.8},
        solvent_mass_kg_h=20.0,
    )
    result = simulate_template_semibatch_ode("generic_terpolymerization_apparent", config=cfg, total_time_min=6, dt_min=2)
    assert not result.profile.empty
    assert "C_ENB" not in result.profile.columns
    assert result.profile["polymer_mass_kg"].diff().dropna().ge(-1e-12).all()


def test_h2_increase_does_not_raise_mw():
    cfg_low = load_default_config()
    cfg_high = cfg_low.model_copy(deep=True)
    cfg_low.hydrogen_g_h = 0.1
    cfg_high.hydrogen_g_h = 50.0
    low = simulate_template_semibatch_ode(config=cfg_low, total_time_min=10, dt_min=2).profile["Mw"].iloc[-1]
    high = simulate_template_semibatch_ode(config=cfg_high, total_time_min=10, dt_min=2).profile["Mw"].iloc[-1]
    assert high <= low


def test_cooling_failure_heats_or_warns():
    cfg = load_default_config()
    result = simulate_template_semibatch_ode(config=cfg, total_time_min=10, dt_min=2, cooling_failure=True)
    profile = result.profile
    assert profile["T_K"].iloc[-1] >= profile["T_K"].iloc[0] or result.warnings


def test_bdf_mode_falls_back_without_stalling():
    cfg = load_default_config()
    result = simulate_template_semibatch_ode(config=cfg, total_time_min=4, dt_min=2, solver_mode="solve_ivp_bdf")
    assert not result.profile.empty
    if result.summary["fallback_used"]:
        assert result.summary["solver_mode_used"] == "explicit_bounded"
        assert result.summary["fallback_reason"]
    else:
        assert result.summary["solver_mode_used"] == "solve_ivp_bdf"
        assert result.summary["nfev"] > 0
    assert (result.profile[["polymer_mass_kg", "T_K", "P_Pa"]] >= 0).all().all()
