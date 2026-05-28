from dataclasses import dataclass, field

from epdm_sim.flowsheet import load_default_config
from epdm_sim.services.simulation_service import performance_rows, process_config_from_payload, run_flowsheet_with_store, stale_flags


@dataclass
class DummyStore:
    flowsheet_key: str | None = None
    flowsheet: object | None = None
    dynamic_key: str | None = None
    cfd_key: str | None = None
    optimization: object | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class DummyState:
    config: object
    dirty_modules: set = field(default_factory=set)


def test_simulation_service_cache_hit_and_stale_flags():
    cfg = load_default_config()
    assert process_config_from_payload(cfg.model_dump()).temperature_C == cfg.temperature_C
    store = DummyStore()
    first = run_flowsheet_with_store(cfg, store)
    second = run_flowsheet_with_store(cfg, store)
    assert not first.cache_hit
    assert second.cache_hit
    state = DummyState(cfg)
    flags = stale_flags(state, store)
    assert not flags["flowsheet"]
    rows = performance_rows(state, store)
    assert any(row["item"] == "flowsheet hash" for row in rows)
