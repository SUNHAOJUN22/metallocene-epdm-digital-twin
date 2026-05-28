from epdm_sim.flowsheet import build_feed_stream, load_default_config
from epdm_sim.reactor import simulate_dynamic_semibatch_ode, simulate_reactor
from epdm_sim.utils import c_to_k


def test_reactor_conversion_non_negative_and_composition_sums():
    cfg = load_default_config()
    feed = build_feed_stream(cfg)
    result = simulate_reactor(
        feed,
        temperature_K=c_to_k(cfg.temperature_C),
        pressure_MPa=cfg.pressure_MPa,
        residence_time_min=cfg.residence_time_min,
        reactor_volume_L=cfg.reactor_volume_L,
        catalyst_umol_h=cfg.catalyst_umol_h,
        AlTi_ratio=cfg.AlTi_ratio,
        BHT_ratio=cfg.BHT_ratio,
        mode=cfg.reactor_mode,
        num_cstr=cfg.num_cstr,
    )
    assert all(value >= 0.0 for value in result.conversions.values())
    assert result.polymer_kg_h >= 0.0
    assert abs(sum(result.polymer_composition_wt.values()) - 100.0) < 1.0e-6


def test_dynamic_semibatch_ode_returns_finite_nonnegative_profile():
    cfg = load_default_config()
    result = simulate_dynamic_semibatch_ode(cfg, {"total_time_min": 30.0, "n_eval": 24})
    profile = result.time_profile()
    assert not profile.empty
    assert profile["T_C"].notna().all()
    assert (profile[["C_E_mol_L", "C_P_mol_L", "C_ENB_mol_L", "solids_wt"]] >= 0.0).all().all()
