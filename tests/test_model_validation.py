from epdm_sim.model_validation import validate_all_model_contracts, validation_dataframe


def test_model_validation_has_no_errors():
    issues = validate_all_model_contracts()
    errors = [issue for issue in issues if issue.severity == "error"]
    assert errors == []


def test_model_validation_dataframe_schema():
    df = validation_dataframe()
    assert {"model_id", "severity", "message", "suggested_fix"}.issubset(df.columns)
