from scripts.release_gate import build_release_gate_steps, check_release_static_contracts


def test_release_gate_steps_include_required_quality_gates():
    gates = [name for name, _ in build_release_gate_steps()]
    for required in ["py_compile", "pytest", "smoke_app", "auto_functional_audit", "function_inventory_audit", "ui_e2e_smoke", "ui_e2e_workflow"]:
        assert required in gates


def test_release_gate_static_contract_returns_result_rows():
    rows = check_release_static_contracts()
    assert rows
    assert rows[0].gate == "static_contracts"
