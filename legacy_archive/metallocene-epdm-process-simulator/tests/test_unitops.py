from epdm_sim.flowsheet import build_feed_stream, load_default_config
from epdm_sim.unitops import Heater, Mixer, RecycleBlock, Splitter
from epdm_sim.utils import c_to_k


def test_unit_operation_wrappers_run():
    cfg = load_default_config()
    feed = build_feed_stream(cfg)
    mixer = Mixer(name="Mixer", inlet_streams=[feed])
    mixed = mixer.calculate()
    heater = Heater(name="Preheater", inlet_streams=[mixed], target_temperature_K=c_to_k(cfg.temperature_C))
    heated, results = heater.calculate()
    assert heated.temperature_K == c_to_k(cfg.temperature_C)
    assert results["Q_preheat_kJ_h"] > 0.0


def test_splitter_and_recycle_block_accounting():
    cfg = load_default_config()
    feed = build_feed_stream(cfg)
    splitter = Splitter(name="Purge splitter", inlet_streams=[feed], split_fraction=0.1)
    purge, recycle = splitter.calculate()
    assert abs(feed.total_mass_flow() - purge.total_mass_flow() - recycle.total_mass_flow()) < 1.0e-9
    block = RecycleBlock(name="Recycle", inlet_streams=[purge, recycle], purge_fraction=0.1)
    result = block.calculate()
    assert result["total_recoverable_kg_h"] > 0.0
