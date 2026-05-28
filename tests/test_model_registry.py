from epdm_sim.model_registry import (
    VALID_TRIGGER_MODES,
    load_model_registry,
    module_trigger_dataframe,
    registry_summary,
    validate_model_registry,
)


def test_model_registry_is_complete_and_valid():
    modules = load_model_registry()
    errors = validate_model_registry(modules)
    module_ids = {module.module_id for module in modules}

    assert not errors
    assert len(modules) >= 12
    assert {
        "flowsheet",
        "template_config",
        "template_flowsheet",
        "template_ode_rhs",
        "thermo_flash",
        "reactor_kinetics",
        "dynamic_semibatch_ode",
        "heat_balance",
        "fluid_rheology_hydraulics",
        "cfd_simple",
        "optimizer_pareto",
    }.issubset(module_ids)


def test_model_registry_trigger_policy_is_explicit():
    modules = load_model_registry()
    by_id = {module.module_id: module for module in modules}

    assert by_id["flowsheet"].trigger_mode == "auto_cached"
    assert by_id["heat_balance"].trigger_mode == "auto_cached"
    assert by_id["dynamic_semibatch_ode"].trigger_mode == "button_manual"
    assert by_id["cfd_simple"].trigger_mode == "button_manual"
    assert by_id["parameter_estimation"].trigger_mode == "button_manual"
    assert {module.trigger_mode for module in modules}.issubset(VALID_TRIGGER_MODES)
    for module in modules:
        if module.status == "active":
            assert module.required_units
            assert module.mathematical_checks
            assert module.chemical_engineering_checks
            assert module.ui_trigger_policy
            assert module.computational_cost in {"low", "medium", "high"}
        if module.trigger_mode == "button_manual":
            assert module.computational_cost in {"medium", "high"}
        if module.trigger_mode == "auto_cached":
            assert "hash" in " ".join(module.mathematical_checks).lower()


def test_model_registry_ui_table_and_summary_are_stable():
    df = module_trigger_dataframe()
    summary = registry_summary()

    assert not df.empty
    assert {"模块", "类别", "触发方式", "计算成本", "适用范围", "UI入口"}.issubset(df.columns)
    assert summary["module_count"] == len(df)
    assert summary["validation_errors"] == []
    assert summary["by_trigger"]["button_manual"] >= 4
