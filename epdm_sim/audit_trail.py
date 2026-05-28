"""Audit trail records for task and report reproducibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import datetime as _dt
import hashlib
import json

import pandas as pd


def _hash(payload: Any) -> str:
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class AuditTrailRecord:
    """One reproducible action/task record."""

    record_id: str
    timestamp: str
    action_id: str
    task_id: str
    input_hash: str
    output_hash: str
    parameter_set_id: str
    template_id: str
    status: str
    runtime_s: float
    error: str = ""
    report_path_or_package_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def create_audit_record(
    action_id: str,
    task_id: str,
    inputs: Any,
    outputs: Any,
    *,
    parameter_set_id: str = "default",
    template_id: str = "EPDM_EPM_metallocene_solution",
    status: str = "success",
    runtime_s: float = 0.0,
    error: str = "",
    report_path_or_package_id: str = "",
) -> AuditTrailRecord:
    """Create a stable audit record from task inputs and outputs."""
    input_hash = _hash(inputs)
    output_hash = _hash(outputs)
    timestamp = _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record_id = _hash({"timestamp": timestamp, "action_id": action_id, "task_id": task_id, "input_hash": input_hash, "output_hash": output_hash})
    return AuditTrailRecord(
        record_id=record_id,
        timestamp=timestamp,
        action_id=action_id,
        task_id=task_id,
        input_hash=input_hash,
        output_hash=output_hash,
        parameter_set_id=parameter_set_id,
        template_id=template_id,
        status=status,
        runtime_s=float(runtime_s),
        error=error,
        report_path_or_package_id=report_path_or_package_id,
    )


def audit_trail_dataframe(records: list[AuditTrailRecord] | None = None) -> pd.DataFrame:
    """Return audit trail rows as a DataFrame."""
    if records is None:
        records = [
            create_audit_record(
                "run_fast_flowsheet",
                "flowsheet_fast",
                {"default": True},
                {"status": "not_run_in_this_report"},
                status="not_run",
            )
        ]
    return pd.DataFrame([record.as_dict() for record in records])


def save_audit_to_sqlite(records: list[AuditTrailRecord], db_path: str) -> int:
    """Append audit records to the local SQLite warehouse."""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_trail (
                record_id TEXT PRIMARY KEY,
                timestamp TEXT,
                action_id TEXT,
                task_id TEXT,
                input_hash TEXT,
                output_hash TEXT,
                parameter_set_id TEXT,
                template_id TEXT,
                status TEXT,
                runtime_s REAL,
                error TEXT,
                report_path_or_package_id TEXT
            )
            """
        )
        rows = [record.as_dict() for record in records]
        conn.executemany(
            """
            INSERT OR REPLACE INTO audit_trail VALUES (
                :record_id, :timestamp, :action_id, :task_id, :input_hash, :output_hash,
                :parameter_set_id, :template_id, :status, :runtime_s, :error, :report_path_or_package_id
            )
            """,
            rows,
        )
    return len(records)


def compare_repro_package_manifest(left: dict[str, Any], right: dict[str, Any]) -> pd.DataFrame:
    """Compare two reproducibility manifests by key."""
    keys = sorted(set(left) | set(right))
    return pd.DataFrame(
        [{"field": key, "left": left.get(key), "right": right.get(key), "same": left.get(key) == right.get(key)} for key in keys]
    )

