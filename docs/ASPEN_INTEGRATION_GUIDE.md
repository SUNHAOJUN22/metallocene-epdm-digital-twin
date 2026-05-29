# Aspen Integration Guide

Date: 2026-05-29

This guide describes the offline Aspen Plus/HYSYS exchange workflow added to the EPDM digital twin.

## Purpose

The Aspen bridge improves coupling experience without adding a hard dependency on Aspen COM automation. It provides:

- Aspen-ready stream export tables;
- EPDM-to-Aspen component aliases;
- variable mapping sheets for reactor, flash and stream data;
- unit context documentation;
- import validation for Aspen-returned tables;
- reconciliation tables comparing Aspen and EPDM values;
- a Python COM automation template for site-approved use.

The bridge does not replace the EPDM simulator, ResidualSystem, flash/EOS logic, benchmark gates or release gates.

## Runtime Module

Primary module:

- `epdm_sim/aspen_bridge.py`

Public functions:

- `build_aspen_stream_table(result)`
- `aspen_variable_mapping_dataframe()`
- `aspen_unit_context_dataframe()`
- `aspen_export_tables(result)`
- `validate_aspen_import_table(table)`
- `aspen_reconciliation_dataframe(result, aspen_table)`
- `aspen_bridge_summary(result, aspen_table=None)`
- `aspen_com_script_template(case_path, visible=True)`
- `export_aspen_exchange_workbook(result, path)`

## Excel Report Sheets

The main Excel report now includes:

- `aspen_stream_export`
- `aspen_variable_map`
- `aspen_unit_context`
- `aspen_component_aliases`
- `aspen_user_guide`
- `aspen_bridge_summary`

All sheet names remain within Excel's 31-character limit.

## Recommended Workflow

1. Run the EPDM digital twin and export the Excel report.
2. Open `aspen_stream_export`.
3. Map EPDM aliases to Aspen components using `aspen_component_aliases`.
4. Configure Aspen stream/block variables using `aspen_variable_map`.
5. Run the Aspen case manually or with a site-approved COM automation script.
6. Export Aspen stream results back into the same column schema.
7. Validate with `validate_aspen_import_table`.
8. Compare with `aspen_reconciliation_dataframe`.
9. Use deviations as engineering review inputs, not silent model corrections.

## Safety Boundary

- Report export does not run Aspen.
- COM automation is represented only as a template string.
- Negative flows, nonfinite values, pressure <= 0 and invalid temperatures are rejected.
- Polymer pseudo-component must remain nonvolatile; polymer vapor is critical in the residual system.
- Large Aspen/EPDM differences are warnings or errors, not automatic corrections.

## MCP Boundary

The MCP registry includes `prepare_aspen_exchange`. It defaults to dry-run and, when explicitly allowed, prepares Aspen exchange metadata from a governed EPDM flowsheet run. It does not execute Aspen COM.

## Validation

Covered by:

- `tests/test_aspen_bridge.py`
- `tests/test_mcp_interface.py`
- `tests/test_professional_skill_qa.py`
- `python scripts\dev_tasks.py professional-skill-qa`
- `python scripts\release_gate.py`
