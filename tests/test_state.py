from epdm_sim.flowsheet import load_default_config
from epdm_sim.state import SimulationState


def test_simulation_state_hash_and_dirty_flags():
    state = SimulationState.from_process_config(load_default_config())
    first_hash = state.fingerprint()
    state.mark_clean("flowsheet")
    assert "flowsheet" not in state.dirty_modules
    cfg = load_default_config()
    cfg.temperature_C += 1.0
    state.update_config(cfg)
    assert state.fingerprint() != first_hash
    assert "flowsheet" in state.dirty_modules
