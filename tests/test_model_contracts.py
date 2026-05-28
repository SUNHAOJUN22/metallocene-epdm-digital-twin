from epdm_sim.model_contracts import contracts_dataframe, get_model_contract, load_model_contracts


def test_contracts_load_from_registry():
    contracts = load_model_contracts()
    ids = {contract.model_id for contract in contracts}

    assert len(contracts) >= 12
    assert "flowsheet" in ids
    assert "dynamic_semibatch_ode" in ids
    assert get_model_contract("heat_balance").required_units


def test_contracts_include_validation_and_fallbacks():
    for contract in load_model_contracts():
        assert contract.inputs
        assert contract.outputs
        assert contract.required_units
        assert contract.validation_rules
        assert contract.fallback_mode


def test_contract_dataframe_is_report_ready():
    df = contracts_dataframe()
    assert not df.empty
    assert {"model_id", "inputs", "outputs", "required_units", "trigger_mode"}.issubset(df.columns)
