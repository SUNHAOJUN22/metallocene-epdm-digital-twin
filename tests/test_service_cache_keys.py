from epdm_sim.flowsheet import load_default_config
from epdm_sim.services.cache_keys import config_cache_key, detail_cache_key, hash_payload, model_fingerprint, stable_json_dumps


def test_cache_keys_are_stable_and_sensitive_to_input_changes():
    cfg = load_default_config()
    first = config_cache_key(cfg)
    assert first == config_cache_key(cfg)
    changed = cfg.model_copy(update={"temperature_C": cfg.temperature_C + 1.0})
    assert first != config_cache_key(changed)
    assert detail_cache_key(cfg, {"mode": "cfd"}) == detail_cache_key(cfg, {"mode": "cfd"})
    assert hash_payload({"b": 2, "a": 1}) == hash_payload({"a": 1, "b": 2})
    assert stable_json_dumps({"b": 2, "a": 1}).startswith('{"a"')
    assert model_fingerprint("a", {"b": 1})
