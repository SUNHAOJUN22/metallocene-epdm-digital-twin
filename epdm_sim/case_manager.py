"""Case and scenario management for the digital twin."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from io import BytesIO
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from . import APP_VERSION
from .utils import DATA_DIR, load_json, model_dump_compat, write_json


CASE_DIR = DATA_DIR / "cases"


@dataclass
class CaseRecord:
    """Saved simulation case metadata and payload."""

    case_id: str
    case_name: str
    config: dict[str, Any]
    parameter_set_id: str = "default"
    kpis: dict[str, Any] | None = None
    notes: str = ""
    created_at: float = 0.0
    versions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable case data."""
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "config": self.config,
            "parameter_set_id": self.parameter_set_id,
            "kpis": self.kpis or {},
            "notes": self.notes,
            "created_at": self.created_at or time.time(),
            "versions": self.versions,
        }


def _safe_case_id(case_name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in case_name.strip())[:80] or f"case_{int(time.time())}"


def case_path(case_id: str, case_dir: str | Path | None = None) -> Path:
    """Return the JSON path for a case id."""
    root = Path(case_dir or CASE_DIR)
    return root / f"{_safe_case_id(case_id)}.json"


def save_case(
    case_name: str,
    config: Any,
    *,
    result: Any | None = None,
    parameter_set_id: str = "default",
    notes: str = "",
    case_dir: str | Path | None = None,
) -> CaseRecord:
    """Save a process case to a local JSON file."""
    root = Path(case_dir or CASE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    case_id = _safe_case_id(case_name)
    cfg = config if isinstance(config, dict) else model_dump_compat(config)
    kpis = {}
    if result is not None:
        kpis = {key: value for key, value in getattr(result, "kpis", {}).items() if isinstance(value, (int, float, str, bool))}
    path = case_path(case_id, root)
    versions: list[dict[str, Any]] = []
    if path.exists():
        try:
            previous = load_json(path)
            versions = list(previous.get("versions", []))
            versions.append(
                {
                    "saved_at": previous.get("created_at", time.time()),
                    "parameter_set_id": previous.get("parameter_set_id", "default"),
                    "config": previous.get("config", {}),
                    "kpis": previous.get("kpis", {}),
                    "notes": previous.get("notes", ""),
                }
            )
            versions = versions[-12:]
        except Exception:
            versions = []
    record = CaseRecord(
        case_id=case_id,
        case_name=case_name,
        config=cfg,
        parameter_set_id=parameter_set_id,
        kpis=kpis,
        notes=notes,
        created_at=time.time(),
        versions=versions,
    )
    write_json(path, record.to_dict())
    return record


def load_case(case_id: str, case_dir: str | Path | None = None) -> CaseRecord:
    """Load a saved case record."""
    payload = load_json(case_path(case_id, case_dir))
    return CaseRecord(**payload)


def list_cases(case_dir: str | Path | None = None) -> pd.DataFrame:
    """List saved cases."""
    root = Path(case_dir or CASE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = load_json(path)
            kpis = payload.get("kpis", {})
            rows.append(
                {
                    "case_id": payload.get("case_id", path.stem),
                    "case_name": payload.get("case_name", path.stem),
                    "parameter_set_id": payload.get("parameter_set_id", "default"),
                    "created_at": payload.get("created_at", 0.0),
                    "polymer_kg_h": kpis.get("polymer_kg_h"),
                    "C2_wt": kpis.get("C2_wt"),
                    "ENB_wt": kpis.get("ENB_wt"),
                    "Mooney": kpis.get("Mooney"),
                    "best_grade": kpis.get("best_grade"),
                }
            )
        except Exception:
            continue
    return pd.DataFrame(rows)


def duplicate_case(case_id: str, new_case_name: str, case_dir: str | Path | None = None) -> CaseRecord:
    """Duplicate an existing saved case with a new name."""
    root = Path(case_dir or CASE_DIR)
    source = case_path(case_id, root)
    record = load_case(case_id, root)
    record.case_name = new_case_name
    record.case_id = _safe_case_id(new_case_name)
    record.created_at = time.time()
    target = case_path(record.case_id, root)
    if source.resolve() != target.resolve():
        write_json(target, record.to_dict())
    else:
        shutil.copyfile(source, target)
    return record


def compare_cases(case_a: CaseRecord | dict[str, Any], case_b: CaseRecord | dict[str, Any]) -> pd.DataFrame:
    """Compare two cases across input and KPI deltas."""
    a = case_a.to_dict() if isinstance(case_a, CaseRecord) else case_a
    b = case_b.to_dict() if isinstance(case_b, CaseRecord) else case_b
    rows: list[dict[str, Any]] = []
    for group_name, key_name in [("input", "config"), ("result", "kpis")]:
        keys = sorted(set(a.get(key_name, {})) | set(b.get(key_name, {})))
        for key in keys:
            av = a.get(key_name, {}).get(key)
            bv = b.get(key_name, {}).get(key)
            if av == bv:
                continue
            delta = None
            if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                delta = bv - av
            rows.append({"group": group_name, "field": key, "case_a": av, "case_b": bv, "delta_b_minus_a": delta})
    return pd.DataFrame(rows)


def case_record_from_json_bytes(payload: bytes) -> CaseRecord:
    """Load a case from uploaded JSON bytes."""
    return CaseRecord(**json.loads(payload.decode("utf-8")))


def export_case_package(
    record: CaseRecord | dict[str, Any],
    *,
    dynamic_profile: pd.DataFrame | None = None,
    cfd_metrics: dict[str, Any] | pd.DataFrame | None = None,
    experiment_summary: dict[str, Any] | pd.DataFrame | None = None,
    report_metadata: dict[str, Any] | None = None,
    test_status: str = "not_run",
) -> bytes:
    """Export a reproducible case package as a zip archive."""
    payload = record.to_dict() if isinstance(record, CaseRecord) else dict(record)
    config_hash = sha256(json.dumps(payload.get("config", {}), sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    manifest = {
        "app_version": APP_VERSION,
        "created_at": time.time(),
        "config_hash": config_hash,
        "parameter_set_id": payload.get("parameter_set_id", "default"),
        "data_snapshot_id": f"case_{payload.get('case_id', 'unknown')}",
        "test_status": test_status,
        "contents": ["case.json", "report_metadata.json", "README_case_package.md"],
    }
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("case.json", json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        if dynamic_profile is not None and not dynamic_profile.empty:
            archive.writestr("dynamic_profile.csv", dynamic_profile.to_csv(index=False))
        if cfd_metrics is not None:
            archive.writestr("cfd_metrics.json", _json_from_any(cfd_metrics))
        if experiment_summary is not None:
            archive.writestr("experiment_summary.json", _json_from_any(experiment_summary))
        archive.writestr("report_metadata.json", json.dumps(report_metadata or {"exported_at": time.time()}, ensure_ascii=False, indent=2))
        archive.writestr(
            "README_case_package.md",
            "# EPDM digital twin case package\n\n"
            "This archive contains the saved SimulationState/config, parameter-set id, KPI snapshot, manifest and optional dynamic/CFD/report metadata.\n",
        )
    return buffer.getvalue()


def import_case_package_zip(payload: bytes, case_dir: str | Path | None = None) -> CaseRecord:
    """Import a case package zip and persist the contained case JSON."""
    with ZipFile(BytesIO(payload), "r") as archive:
        case_payload = json.loads(archive.read("case.json").decode("utf-8"))
    record = CaseRecord(**case_payload)
    root = Path(case_dir or CASE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    write_json(case_path(record.case_id, root), record.to_dict())
    return record


def _json_from_any(value: dict[str, Any] | pd.DataFrame) -> str:
    """Serialize dict/DataFrame payloads for case packages."""
    if isinstance(value, pd.DataFrame):
        payload: Any = value.to_dict(orient="records")
    else:
        payload = value
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
