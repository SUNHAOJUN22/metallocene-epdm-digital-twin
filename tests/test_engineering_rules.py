from epdm_sim.engineering_rules import (
    load_engineering_rules,
    rule_results_dataframe,
    rules_dataframe,
    run_all_engineering_rules,
    run_engineering_rule,
)
from epdm_sim.flowsheet import load_default_config


def test_engineering_rules_json_schema_loads():
    rules = load_engineering_rules()
    assert len(rules) >= 10
    assert all(rule.rule_id and rule.expected_trend for rule in rules)
    assert not rules_dataframe(rules).empty


def test_all_default_engineering_rules_pass():
    results = run_all_engineering_rules(load_default_config())
    assert results
    assert all(result.passed for result in results)
    assert not rule_results_dataframe(results).empty


def test_single_rule_runs_without_heavy_detail_tasks():
    result = run_engineering_rule("h2_mw_decreases", load_default_config())
    assert result.passed
    assert "Mw" in str(result.observed_values) or result.observed_values


def test_unknown_rule_is_readable_error():
    try:
        run_engineering_rule("missing_rule")
    except KeyError as exc:
        assert "missing_rule" in str(exc)
    else:
        raise AssertionError("missing rule should raise KeyError")
