from pathlib import Path

import pandas as pd

from epdm_sim.aspen_bridge import (
    AspenExchangePackage,
    AspenMappingRecord,
    aspen_bridge_summary,
    aspen_com_script_template,
    aspen_component_aliases,
    aspen_export_tables,
    aspen_reconciliation_dataframe,
    aspen_unit_context_dataframe,
    aspen_user_guide_dataframe,
    aspen_variable_mapping_dataframe,
    build_aspen_stream_table,
    export_aspen_exchange_workbook,
    validate_aspen_import_table,
)
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.report import export_excel
from epdm_sim.report_consistency import check_excel_required_sheets, excel_sheet_names


def test_aspen_bridge_mapping_and_aliases_are_explicit():
    aliases = aspen_component_aliases()
    mapping = aspen_variable_mapping_dataframe()
    units = aspen_unit_context_dataframe()
    guide = aspen_user_guide_dataframe()
    record = AspenMappingRecord("a", "b", "c", "kg/h", "export", True, "note")

    assert aliases["ethylene"] == "ETHYLENE"
    assert not mapping.empty
    assert {"epdm_field", "aspen_object", "aspen_variable", "unit", "direction", "required"}.issubset(mapping.columns)
    assert {"quantity", "epdm_unit", "aspen_unit"}.issubset(units.columns)
    assert not guide.empty
    assert record.required is True


def test_aspen_stream_export_is_finite_nonnegative_and_validates():
    result = run_flowsheet()
    stream_table = build_aspen_stream_table(result)
    validation = validate_aspen_import_table(stream_table)

    assert not stream_table.empty
    assert {"stream_id", "aspen_stream", "temperature_C", "pressure_bar", "total_mass_kg_h"}.issubset(stream_table.columns)
    assert (stream_table["pressure_bar"] > 0).all()
    assert (stream_table["total_mass_kg_h"] >= 0).all()
    assert validation["passed"].astype(bool).all()


def test_aspen_reconciliation_flags_large_roundtrip_drift():
    result = run_flowsheet()
    exported = build_aspen_stream_table(result)
    identical = aspen_reconciliation_dataframe(result, exported)
    drifted = exported.copy()
    drifted.loc[0, "total_mass_kg_h"] *= 1.25
    reconciliation = aspen_reconciliation_dataframe(result, drifted)

    assert not identical.empty
    assert identical["passed"].astype(bool).all()
    assert not reconciliation[reconciliation["variable"] == "total_mass_kg_h"]["passed"].astype(bool).all()
    assert set(reconciliation["severity"]).issuperset({"warning"}) or set(reconciliation["severity"]).issuperset({"error"})


def test_aspen_exchange_package_and_excel_report_include_aspen_sheets(tmp_path: Path):
    result = run_flowsheet()
    tables = aspen_export_tables(result)
    package = export_aspen_exchange_workbook(result, tmp_path / "aspen_exchange.xlsx")
    excel_bytes = export_excel(result)
    sheet_names = excel_sheet_names(excel_bytes)
    required = check_excel_required_sheets(excel_bytes)

    assert isinstance(package, AspenExchangePackage)
    assert Path(package.workbook_path).exists()
    assert Path(package.manifest_path).exists()
    assert tables["aspen_stream_export"].shape[0] == package.stream_rows
    assert "aspen_stream_export" in sheet_names
    assert "aspen_variable_map" in sheet_names
    assert "aspen_unit_context" in sheet_names
    assert required[0].passed


def test_aspen_import_validation_rejects_bad_table_and_script_is_template_only():
    bad = pd.DataFrame([{"stream_id": "feed", "aspen_stream": "FEED", "temperature_C": -300.0}])
    validation = validate_aspen_import_table(bad)
    summary = aspen_bridge_summary(run_flowsheet(), bad)
    script = aspen_com_script_template("demo.bkp", visible=False)

    assert not validation["passed"].astype(bool).all()
    assert summary["status"] == "review"
    assert "win32com.client.Dispatch" in script
    assert "aspen.Engine.Run2()" in script
