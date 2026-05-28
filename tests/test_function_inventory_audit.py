from pathlib import Path

from scripts.function_inventory_audit import build_function_matrix, main, run_inventory_audit


def test_function_inventory_builds_feature_matrix():
    modules, callables = run_inventory_audit()
    matrix = build_function_matrix(callables)

    assert not modules.empty
    assert modules["imported"].all()
    assert not callables.empty
    assert not matrix.empty
    required_columns = {
        "function_name",
        "file_position",
        "module",
        "call_entry",
        "input_parameters",
        "output_result",
        "dependencies",
        "involves_ui",
        "involves_api",
        "involves_database",
        "involves_file_upload",
        "involves_file_export",
        "involves_visualization",
        "involves_scientific_calculation",
        "involves_unit_conversion",
        "involves_numerical_algorithm",
        "involves_state_management",
        "has_direct_test_or_audit_reference",
        "possible_exception_scenarios",
        "risk_level",
    }
    assert required_columns.issubset(matrix.columns)
    assert set(matrix["risk_level"]).issubset({"low", "medium", "high"})
    assert matrix["call_entry"].str.contains(".").all()


def test_function_inventory_main_writes_audit_artifacts():
    assert main() == 0
    out_dir = Path("tmp_smoke_outputs")
    expected = {
        "function_inventory_modules.csv",
        "function_inventory_callables.csv",
        "function_inventory_module_coverage.csv",
        "function_inventory_uncovered_top20.csv",
        "function_matrix.csv",
        "quality_gate_summary.csv",
    }
    missing = [name for name in expected if not (out_dir / name).exists()]
    assert not missing
    assert (out_dir / "function_matrix.csv").stat().st_size > 0
