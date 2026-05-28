"""V5.2 deterministic performance profile for core local tasks."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "tmp_smoke_outputs"


@dataclass
class PerformanceRecord:
    """One performance timing row."""

    task: str
    runtime_s: float
    passed: bool
    detail: str


def _time_task(name: str, func: Callable[[], object]) -> PerformanceRecord:
    started = time.perf_counter()
    try:
        value = func()
        runtime = time.perf_counter() - started
        return PerformanceRecord(name, runtime, True, str(value)[:300])
    except Exception as exc:  # pragma: no cover - reported as gate failure
        runtime = time.perf_counter() - started
        return PerformanceRecord(name, runtime, False, f"{type(exc).__name__}: {exc}")


def run_performance_profile() -> pd.DataFrame:
    """Run small deterministic performance checks and write CSV/JSON artifacts."""
    from epdm_sim.cfd.simple_solver import build_cfd_input_from_flowsheet, run_simple_cfd
    from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
    from epdm_sim.flowsheet import load_default_config, run_flowsheet
    from epdm_sim.report import export_excel
    from epdm_sim.services.cache_keys import config_cache_key
    from epdm_sim.template_config import process_config_to_template_config
    from epdm_sim.template_flowsheet import run_template_flowsheet

    cfg = load_default_config()
    result_holder: dict[str, object] = {}

    def flowsheet_task():
        result_holder["flowsheet"] = run_flowsheet(cfg)
        return result_holder["flowsheet"].kpis["polymer_kg_h"]  # type: ignore[index]

    def template_task():
        result = run_template_flowsheet(process_config_to_template_config(cfg))
        return result.application_kpis.get("polymer_kg_h")

    def dynamic_task():
        return len(simulate_template_semibatch_ode(total_time_min=3.0, dt_min=1.0, solver_mode="explicit_bounded").profile)

    def cfd_task():
        result = result_holder.get("flowsheet") or run_flowsheet(cfg)
        return run_simple_cfd(build_cfd_input_from_flowsheet(result, nx=24, ny=12)).diagnostics.dead_zone_fraction

    def report_task():
        result = result_holder.get("flowsheet") or run_flowsheet(cfg)
        return len(export_excel(result))

    def cache_key_task():
        return config_cache_key(cfg)

    rows = [
        _time_task("run_flowsheet", flowsheet_task),
        _time_task("run_template_flowsheet", template_task),
        _time_task("dynamic_explicit_bounded", dynamic_task),
        _time_task("small_cfd", cfd_task),
        _time_task("report_export_excel", report_task),
        _time_task("cache_key_generation", cache_key_task),
    ]
    df = pd.DataFrame([asdict(row) for row in rows])
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "performance_profile.csv", index=False, encoding="utf-8-sig")
    (OUT / "performance_profile.json").write_text(json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")
    return df


def main() -> int:
    df = run_performance_profile()
    print(df.to_string(index=False))
    return 0 if bool(df["passed"].all()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
