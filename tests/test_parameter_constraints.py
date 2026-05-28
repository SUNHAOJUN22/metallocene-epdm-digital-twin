from epdm_sim.parameter_constraints import (
    PARAMETER_CONSTRAINTS,
    ParameterConstraintResult,
    parameter_constraint_results_dataframe,
    parameter_constraints_dataframe,
    validate_parameter_set,
    validate_parameter_value,
)


def test_parameter_constraint_catalog_and_validation():
    catalog = parameter_constraints_dataframe()
    assert not catalog.empty
    assert "unit" in catalog.columns
    assert "k_E_ref" in PARAMETER_CONSTRAINTS
    ok = validate_parameter_value("k_E_ref", 100.0)
    bad = validate_parameter_value("k_E_ref", -1.0)
    assert isinstance(ok, ParameterConstraintResult)
    assert ok.passed
    assert not bad.passed
    assert bad.severity == "error"


def test_parameter_set_dataframe_and_unknown_warning():
    rows = validate_parameter_set({"k_E_ref": 100.0, "Mw0": 350000.0, "custom_param": 1.0})
    assert len(rows) == 3
    df = parameter_constraint_results_dataframe({"ktr_H2": 0.2, "beta_P": 0.5})
    assert df["passed"].all()
    unknown = [row for row in rows if row.parameter == "custom_param"][0]
    assert unknown.severity == "warning"
