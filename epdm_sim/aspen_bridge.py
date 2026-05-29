"""Aspen Plus/HYSYS exchange helpers for the EPDM digital twin.

The bridge is intentionally offline and dependency-light.  It prepares clean
exchange tables and validation artifacts for Aspen workflows without requiring
Aspen COM automation to be installed on the test machine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import json
import math

import pandas as pd

from . import APP_VERSION


COMPONENT_ALIASES = {
    "ethylene": "ETHYLENE",
    "propylene": "PROPYLENE",
    "ENB": "ENB",
    "hydrogen": "HYDROGEN",
    "hexane": "N-HEXANE",
    "polymer_pseudo": "EPDM-POLYMER",
}

REQUIRED_ASPEN_STREAM_COLUMNS = {
    "stream_id",
    "aspen_stream",
    "temperature_C",
    "pressure_bar",
    "total_mass_kg_h",
}


@dataclass(frozen=True)
class AspenMappingRecord:
    """One auditable mapping between EPDM fields and Aspen variables."""

    epdm_field: str
    aspen_object: str
    aspen_variable: str
    unit: str
    direction: str
    required: bool
    note: str


@dataclass(frozen=True)
class AspenExchangePackage:
    """Paths and metadata generated for one Aspen exchange package."""

    workbook_path: str
    manifest_path: str
    stream_rows: int
    mapping_rows: int
    validation_status: str


def aspen_component_aliases() -> dict[str, str]:
    """Return EPDM-to-Aspen component aliases used by exchange tables."""
    return dict(COMPONENT_ALIASES)


def aspen_variable_mapping_dataframe() -> pd.DataFrame:
    """Return variable mappings for Aspen Plus/HYSYS manual or scripted setup."""
    rows = [
        AspenMappingRecord("config.temperature_C", "BLOCK:REACTOR", "TEMP", "C", "export", True, "reactor temperature setpoint"),
        AspenMappingRecord("config.pressure_MPa", "BLOCK:REACTOR", "PRES", "MPa", "export", True, "reactor pressure setpoint"),
        AspenMappingRecord("config.flash1_T_C", "BLOCK:FLASH1", "TEMP", "C", "export", True, "first flash temperature"),
        AspenMappingRecord("config.flash1_P_MPa", "BLOCK:FLASH1", "PRES", "MPa", "export", True, "first flash pressure"),
        AspenMappingRecord("config.flash2_T_C", "BLOCK:FLASH2", "TEMP", "C", "export", True, "second flash temperature"),
        AspenMappingRecord("config.flash2_P_MPa", "BLOCK:FLASH2", "PRES", "MPa", "export", True, "second flash pressure"),
        AspenMappingRecord("stream.temperature_C", "STREAM:*", "TEMP", "C", "export/import", True, "stream temperature"),
        AspenMappingRecord("stream.pressure_bar", "STREAM:*", "PRES", "bar", "export/import", True, "stream pressure"),
        AspenMappingRecord("stream.component_mass_kg_h", "STREAM:*", "MASSFLOW/MIXED", "kg/h", "export/import", True, "component mass flows"),
        AspenMappingRecord("stream.polymer_mass_kg_h", "STREAM:*", "SOLID/PSEUDO", "kg/h", "export/import", False, "polymer pseudo-component; must not enter vapor phase"),
        AspenMappingRecord("result.heat_balance.Q_rxn_kW", "BLOCK:REACTOR", "QCALC", "kW", "import", False, "Aspen heat duty comparison"),
        AspenMappingRecord("result.flash.vapor_fraction", "BLOCK:FLASH*", "VFRAC", "-", "import", False, "flash split comparison"),
    ]
    return pd.DataFrame([asdict(row) for row in rows])


def aspen_unit_context_dataframe() -> pd.DataFrame:
    """Return the preferred Aspen exchange unit set."""
    return pd.DataFrame(
        [
            {"quantity": "temperature", "epdm_unit": "C", "aspen_unit": "C", "required": True},
            {"quantity": "pressure", "epdm_unit": "MPa", "aspen_unit": "bar", "required": True},
            {"quantity": "mass_flow", "epdm_unit": "kg/h", "aspen_unit": "kg/h", "required": True},
            {"quantity": "molar_flow", "epdm_unit": "mol/h", "aspen_unit": "kmol/h", "required": False},
            {"quantity": "heat_duty", "epdm_unit": "kW", "aspen_unit": "kW", "required": False},
            {"quantity": "vapor_fraction", "epdm_unit": "-", "aspen_unit": "-", "required": False},
        ]
    )


def build_aspen_stream_table(result: Any) -> pd.DataFrame:
    """Build a stream table designed for Aspen import and round-trip comparison."""
    rows: list[dict[str, Any]] = []
    for stream_id, stream in getattr(result, "streams", {}).items():
        mass_flows = getattr(stream, "mass_flows", {}) or {}
        row: dict[str, Any] = {
            "stream_id": str(stream_id),
            "aspen_stream": str(stream_id).upper().replace(" ", "_").replace("-", "_")[:16],
            "phase_hint": getattr(stream, "phase", ""),
            "temperature_C": float(getattr(stream, "temperature_K", 273.15)) - 273.15,
            "pressure_bar": float(getattr(stream, "pressure_Pa", 101325.0)) / 1.0e5,
            "total_mass_kg_h": float(stream.total_mass_flow()) if hasattr(stream, "total_mass_flow") else 0.0,
            "polymer_mass_kg_h": float(getattr(stream, "polymer_mass_kg_h", 0.0)),
            "solids_wt": float(getattr(stream, "solids_wt", 0.0)),
            "source": "epdm_sim",
            "model_version": APP_VERSION,
        }
        for component, alias in COMPONENT_ALIASES.items():
            value = row["polymer_mass_kg_h"] if component == "polymer_pseudo" else float(mass_flows.get(component, 0.0))
            row[f"mass_kg_h__{alias}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def aspen_user_guide_dataframe() -> pd.DataFrame:
    """Return operator-facing workflow steps for Aspen coupling."""
    return pd.DataFrame(
        [
            {"step": 1, "action": "Export this workbook and open aspen_stream_export in Aspen or an Aspen preparation sheet.", "risk_control": "Do not edit units silently."},
            {"step": 2, "action": "Map component aliases using aspen_component_aliases and aspen_variable_map.", "risk_control": "Polymer pseudo-component must remain nonvolatile."},
            {"step": 3, "action": "Run Aspen case manually or through site-approved COM automation.", "risk_control": "COM execution is not triggered by report export."},
            {"step": 4, "action": "Paste Aspen stream results into the same column schema and run round-trip validation.", "risk_control": "Negative flows, nonfinite values and bad vapor fractions are rejected."},
            {"step": 5, "action": "Compare residuals in aspen_reconciliation before using Aspen results for calibration.", "risk_control": "Large deviations are warnings/errors, not silent corrections."},
        ]
    )


def aspen_export_tables(result: Any) -> dict[str, pd.DataFrame]:
    """Return all Aspen exchange tables without writing files."""
    return {
        "aspen_stream_export": build_aspen_stream_table(result),
        "aspen_variable_map": aspen_variable_mapping_dataframe(),
        "aspen_unit_context": aspen_unit_context_dataframe(),
        "aspen_component_aliases": pd.DataFrame(
            [{"epdm_component": key, "aspen_alias": value} for key, value in aspen_component_aliases().items()]
        ),
        "aspen_user_guide": aspen_user_guide_dataframe(),
    }


def validate_aspen_import_table(table: pd.DataFrame) -> pd.DataFrame:
    """Validate an Aspen-returned stream table before reconciliation."""
    rows: list[dict[str, Any]] = []
    missing = sorted(REQUIRED_ASPEN_STREAM_COLUMNS - set(table.columns))
    for column in missing:
        rows.append({"check": "required_column", "target": column, "passed": False, "severity": "error", "detail": "missing required Aspen stream column"})
    if missing:
        return pd.DataFrame(rows)

    numeric_columns = [column for column in table.columns if column.startswith("mass_kg_h__")]
    numeric_columns += ["temperature_C", "pressure_bar", "total_mass_kg_h", "polymer_mass_kg_h", "solids_wt"]
    for column in [item for item in numeric_columns if item in table.columns]:
        values = pd.to_numeric(table[column], errors="coerce")
        finite = bool(values.map(math.isfinite).all())
        rows.append({"check": "finite", "target": column, "passed": finite, "severity": "error" if not finite else "ok", "detail": ""})
        if column == "temperature_C":
            ok = bool((values > -273.15).all())
            rows.append({"check": "absolute_temperature", "target": column, "passed": ok, "severity": "error" if not ok else "ok", "detail": "temperature must be above absolute zero"})
        if column in {"pressure_bar", "total_mass_kg_h", "polymer_mass_kg_h"} or column.startswith("mass_kg_h__"):
            ok = bool((values >= 0.0).all())
            rows.append({"check": "nonnegative", "target": column, "passed": ok, "severity": "error" if not ok else "ok", "detail": "negative physical quantity"})
        if column == "solids_wt":
            ok = bool(((values >= 0.0) & (values <= 100.0)).all())
            rows.append({"check": "bounded", "target": column, "passed": ok, "severity": "warning" if not ok else "ok", "detail": "solids wt% should stay in [0, 100]"})
    return pd.DataFrame(rows)


def aspen_reconciliation_dataframe(result: Any, aspen_table: pd.DataFrame) -> pd.DataFrame:
    """Compare Aspen-returned streams with EPDM exported streams."""
    baseline = build_aspen_stream_table(result)
    if aspen_table.empty:
        return pd.DataFrame(
            [{"stream_id": "", "variable": "aspen_table", "epdm_value": 0.0, "aspen_value": 0.0, "absolute_error": 0.0, "relative_error_pct": 0.0, "unit": "", "severity": "warning", "passed": False, "detail": "Aspen table is empty"}]
        )
    merged = baseline.merge(aspen_table, on="stream_id", suffixes=("_epdm", "_aspen"))
    rows: list[dict[str, Any]] = []
    compare_units = {"temperature_C": "C", "pressure_bar": "bar", "total_mass_kg_h": "kg/h", "polymer_mass_kg_h": "kg/h"}
    component_columns = [column for column in baseline.columns if column.startswith("mass_kg_h__")]
    compare_units.update({column: "kg/h" for column in component_columns if column in aspen_table.columns})
    for _, row in merged.iterrows():
        for variable, unit in compare_units.items():
            left = float(row.get(f"{variable}_epdm", 0.0))
            right = float(row.get(f"{variable}_aspen", 0.0))
            abs_err = abs(left - right)
            denom = max(abs(left), abs(right), 1.0e-12)
            rel = 100.0 * abs_err / denom
            tolerance = 0.5 if variable == "temperature_C" else max(1.0e-6, 0.02 * denom)
            passed = bool(math.isfinite(abs_err) and abs_err <= tolerance)
            severity = "ok" if passed else ("warning" if rel <= 10.0 else "error")
            if variable == "mass_kg_h__EPDM-POLYMER" and right > 1.0e-12 and "vapor" in str(row.get("phase_hint_aspen", "")).lower():
                severity = "critical"
                passed = False
            rows.append(
                {
                    "stream_id": row["stream_id"],
                    "variable": variable,
                    "epdm_value": left,
                    "aspen_value": right,
                    "absolute_error": abs_err,
                    "relative_error_pct": rel,
                    "unit": unit,
                    "severity": severity,
                    "passed": passed,
                    "detail": "" if passed else "Review Aspen component mapping, units or thermodynamic property method.",
                }
            )
    return pd.DataFrame(rows)


def aspen_bridge_summary(result: Any, aspen_table: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return compact Aspen bridge readiness and reconciliation status."""
    stream_table = build_aspen_stream_table(result)
    validation = validate_aspen_import_table(aspen_table) if aspen_table is not None else pd.DataFrame()
    reconciliation = aspen_reconciliation_dataframe(result, aspen_table) if aspen_table is not None else pd.DataFrame()
    failed_validation = int((~validation.get("passed", pd.Series(dtype=bool)).astype(bool)).sum()) if not validation.empty else 0
    critical = int((reconciliation.get("severity", pd.Series(dtype=str)) == "critical").sum()) if not reconciliation.empty else 0
    return {
        "status": "ready" if failed_validation == 0 and critical == 0 else "review",
        "stream_rows": int(len(stream_table)),
        "mapping_rows": int(len(aspen_variable_mapping_dataframe())),
        "validation_failures": failed_validation,
        "critical_reconciliation_rows": critical,
        "model_version": APP_VERSION,
    }


def aspen_com_script_template(case_path: str = "case.bkp", visible: bool = True) -> str:
    """Return a Python COM automation template without executing Aspen."""
    visible_value = "True" if visible else "False"
    return f'''# Aspen COM automation template - review with site IT before use.
import win32com.client

aspen = win32com.client.Dispatch("Apwn.Document")
aspen.InitFromArchive2(r"{case_path}")
aspen.Visible = {visible_value}

# Example write path. Confirm exact Aspen tree paths in your case before use.
# aspen.Tree.FindNode(r"\\Data\\Streams\\FEED\\Input\\TEMP\\MIXED").Value = 100.0
# aspen.Engine.Run2()
# duty = aspen.Tree.FindNode(r"\\Data\\Blocks\\REACTOR\\Output\\QCALC").Value

# Keep exported values in the aspen_stream_export schema and validate before calibration.
'''


def export_aspen_exchange_workbook(result: Any, path: str | Path) -> AspenExchangePackage:
    """Write Aspen exchange workbook and manifest, returning package metadata."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tables = aspen_export_tables(result)
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            table.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    manifest = {
        "package_type": "aspen_exchange",
        "model_version": APP_VERSION,
        "workbook": str(target.name),
        "stream_rows": int(len(tables["aspen_stream_export"])),
        "mapping_rows": int(len(tables["aspen_variable_map"])),
        "validation_status": "not_run",
        "heavy_task_executed": False,
    }
    manifest_path = target.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return AspenExchangePackage(
        workbook_path=str(target),
        manifest_path=str(manifest_path),
        stream_rows=manifest["stream_rows"],
        mapping_rows=manifest["mapping_rows"],
        validation_status=manifest["validation_status"],
    )
