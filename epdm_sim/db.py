"""Local SQLite data warehouse for reproducible EPDM digital-twin runs."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import DATA_DIR


DEFAULT_DB_PATH = DATA_DIR / "epdm_digital_twin.sqlite"


SCHEMA = {
    "experiments": """
        CREATE TABLE IF NOT EXISTS experiments (
            run_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "parameter_sets": """
        CREATE TABLE IF NOT EXISTS parameter_sets (
            set_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "cases": """
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "model_runs": """
        CREATE TABLE IF NOT EXISTS model_runs (
            run_id TEXT PRIMARY KEY,
            run_type TEXT NOT NULL,
            config_hash TEXT,
            payload_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "reports": """
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "cfd_runs": """
        CREATE TABLE IF NOT EXISTS cfd_runs (
            run_id TEXT PRIMARY KEY,
            config_hash TEXT,
            metrics_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
}


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection and initialize tables."""
    path = Path(db_path or DEFAULT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    init_database(conn)
    return conn


def init_database(conn_or_path: sqlite3.Connection | str | Path | None = None) -> sqlite3.Connection:
    """Create all V4 local data-warehouse tables."""
    if isinstance(conn_or_path, sqlite3.Connection):
        conn = conn_or_path
    else:
        path = Path(conn_or_path or DEFAULT_DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
    for ddl in SCHEMA.values():
        conn.execute(ddl)
    conn.commit()
    return conn


def insert_experiment(record: dict[str, Any], db_path: str | Path | None = None) -> None:
    """Insert or replace an experiment record."""
    run_id = str(record.get("run_id") or f"run_{int(time.time())}")
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO experiments(run_id, payload_json, created_at) VALUES (?, ?, ?)",
            (run_id, json.dumps(record, ensure_ascii=False, default=str), time.time()),
        )
        conn.commit()


def import_experiments_dataframe(df: pd.DataFrame, db_path: str | Path | None = None) -> int:
    """Import experiments from a DataFrame into SQLite."""
    count = 0
    for _, row in df.iterrows():
        payload = row.dropna().to_dict()
        if not payload.get("run_id"):
            continue
        insert_experiment(payload, db_path)
        count += 1
    return count


def query_experiments(db_path: str | Path | None = None, limit: int = 500) -> pd.DataFrame:
    """Query experiments from SQLite as a normalized DataFrame."""
    with connect(db_path) as conn:
        rows = conn.execute("SELECT payload_json FROM experiments ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    payloads = [json.loads(row[0]) for row in rows]
    return pd.DataFrame(payloads)


def save_model_run(run_id: str, run_type: str, payload: dict[str, Any], config_hash: str = "", db_path: str | Path | None = None) -> None:
    """Persist one model run with config hash and payload."""
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO model_runs(run_id, run_type, config_hash, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, run_type, config_hash, json.dumps(payload, ensure_ascii=False, default=str), time.time()),
        )
        conn.commit()


def load_model_run(run_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """Load a stored model run payload by id."""
    with connect(db_path) as conn:
        row = conn.execute("SELECT payload_json FROM model_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(f"Unknown model_run: {run_id}")
    return json.loads(row[0])


def list_model_runs(db_path: str | Path | None = None, limit: int = 100) -> pd.DataFrame:
    """List model-run metadata."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT run_id, run_type, config_hash, created_at FROM model_runs ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return pd.DataFrame(rows, columns=["run_id", "run_type", "config_hash", "created_at"])


def save_json_record(table: str, key: str, payload: dict[str, Any], db_path: str | Path | None = None) -> None:
    """Save a generic JSON record to parameter_sets, cases, reports or cfd_runs."""
    if table not in {"parameter_sets", "cases", "reports", "cfd_runs"}:
        raise ValueError(f"Unsupported table: {table}")
    key_column = {
        "parameter_sets": "set_id",
        "cases": "case_id",
        "reports": "report_id",
        "cfd_runs": "run_id",
    }[table]
    value_column = {
        "parameter_sets": "payload_json",
        "cases": "payload_json",
        "reports": "metadata_json",
        "cfd_runs": "metrics_json",
    }[table]
    with connect(db_path) as conn:
        if table == "reports":
            conn.execute(
                f"INSERT OR REPLACE INTO {table}({key_column}, report_type, {value_column}, created_at) VALUES (?, ?, ?, ?)",
                (key, str(payload.get("report_type", "word")), json.dumps(payload, ensure_ascii=False, default=str), time.time()),
            )
        elif table == "cfd_runs":
            conn.execute(
                f"INSERT OR REPLACE INTO {table}({key_column}, config_hash, {value_column}, created_at) VALUES (?, ?, ?, ?)",
                (key, str(payload.get("config_hash", "")), json.dumps(payload, ensure_ascii=False, default=str), time.time()),
            )
        else:
            conn.execute(
                f"INSERT OR REPLACE INTO {table}({key_column}, {value_column}, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(payload, ensure_ascii=False, default=str), time.time()),
            )
        conn.commit()
