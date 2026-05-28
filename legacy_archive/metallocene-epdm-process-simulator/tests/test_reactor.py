from epdm_sim.flowsheet import build_feed_stream, load_default_config
from epdm_sim.reactor import simulate_reactor
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
