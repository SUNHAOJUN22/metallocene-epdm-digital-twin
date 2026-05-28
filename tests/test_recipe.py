from epdm_sim.flowsheet import load_default_config
from epdm_sim.recipe import default_semibatch_recipe, recipe_event_log, recipe_from_dataframe, recipe_to_dataframe, recipe_to_ode_config
from epdm_sim.reactor import simulate_dynamic_semibatch_ode


def test_recipe_schema_and_roundtrip():
    recipe = default_semibatch_recipe(60)
    df = recipe_to_dataframe(recipe)
    loaded = recipe_from_dataframe(df)
    assert loaded.steps[0].name
    assert not recipe_event_log(loaded).empty


def test_recipe_quench_stops_catalyst_activity():
    cfg = load_default_config()
    recipe = default_semibatch_recipe(30)
    ode_cfg = recipe_to_ode_config(recipe, total_time_min=30, rpm=500) | {"n_eval": 25}
    result = simulate_dynamic_semibatch_ode(cfg, ode_cfg)
    assert (result.profile[["C_E_mol_L", "C_P_mol_L", "C_ENB_mol_L"]] >= 0).all().all()
    assert result.profile["catalyst_active"].iloc[-1] < result.profile["catalyst_active"].iloc[5]

