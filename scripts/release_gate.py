"""V6.4 release quality gate runner for Windows/local CI."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class GateResult:
    """One release-gate command result."""

    gate: str
    command: str
    passed: bool
    runtime_s: float
    stdout_tail: str
    stderr_tail: str


def _tail(text: str, limit: int = 3000) -> str:
    return text[-limit:] if len(text) > limit else text


def build_release_gate_steps() -> list[tuple[str, list[str]]]:
    """Return release-gate command steps."""
    py_files = ["app.py", *[str(path) for path in sorted((ROOT / "epdm_sim").rglob("*.py"))], *[str(path) for path in sorted((ROOT / "scripts").rglob("*.py"))]]
    return [
        ("py_compile", [sys.executable, "-m", "py_compile", *py_files]),
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("smoke_app", [sys.executable, "scripts/smoke_app.py"]),
        ("auto_functional_audit", [sys.executable, "scripts/auto_functional_audit.py"]),
        ("function_inventory_audit", [sys.executable, "scripts/function_inventory_audit.py"]),
        ("performance_profile", [sys.executable, "scripts/performance_profile.py"]),
        ("ui_e2e_smoke", [sys.executable, "scripts/ui_e2e_smoke.py"]),
        ("ui_e2e_workflow", [sys.executable, "scripts/ui_e2e_workflow.py"]),
    ]


def check_release_static_contracts() -> list[GateResult]:
    """Check generated artifacts and version consistency without rerunning heavy models."""
    started = time.perf_counter()
    required = [
        ROOT / "tmp_smoke_outputs" / "auto_functional_audit.csv",
        ROOT / "tmp_smoke_outputs" / "function_matrix.csv",
        ROOT / "tmp_smoke_outputs" / "quality_gate_summary.csv",
        ROOT / "docs" / "V6_4_MATH_CORE_AUDIT.md",
        ROOT / "tmp_smoke_outputs" / "performance_profile.csv",
        ROOT / "tmp_smoke_outputs" / "performance_profile.json",
        ROOT / "docs" / "TEST_REPORT.md",
        ROOT / "docs" / "QUALITY_BASELINE.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists() or path.stat().st_size == 0]
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    registry = json.loads((ROOT / "data" / "model_registry.json").read_text(encoding="utf-8"))
    equation_registry = json.loads((ROOT / "data" / "equation_registry.json").read_text(encoding="utf-8"))
    callable_inventory = ROOT / "tmp_smoke_outputs" / "function_inventory_callables.csv"
    direct_count = 0
    total_count = 0
    if callable_inventory.exists():
        df = pd.read_csv(callable_inventory)
        total_count = int(len(df))
        direct_count = int(df["directly_referenced_by_tests_or_audits"].astype(bool).sum())
    direct_reference_ok = direct_count >= 450
    direct_reference_detail = f"{direct_count}/{total_count} public callables directly referenced; V6.4 gate requires 100%"
    benchmark_version_ok = True
    benchmark_path = ROOT / "data" / "golden_benchmarks.json"
    if benchmark_path.exists():
        benchmarks = json.loads(benchmark_path.read_text(encoding="utf-8"))
        benchmark_version_ok = all(str(item.get("model_version", "")).startswith("V6.4") for item in benchmarks)
    direct_reference_ok = total_count > 0 and direct_count == total_count
    changelog_ok = (ROOT / "CHANGELOG.md").exists() and (ROOT / "docs" / "V6_4_CHANGELOG.md").exists()
    version_ok = (
        "V6.4" in readme
        and str(registry.get("version")) == "0.7.4"
        and str(equation_registry.get("version")) == "V6.4"
        and benchmark_version_ok
        and changelog_ok
    )
    passed = not missing and version_ok and direct_reference_ok
    detail = {
        "missing": missing,
        "readme_has_v6_4": "V6.4" in readme,
        "registry_version": registry.get("version"),
        "equation_registry_version": equation_registry.get("version"),
        "benchmark_version_ok": benchmark_version_ok,
        "markdown_changelog_ok": changelog_ok,
        "direct_reference_count": direct_count,
        "direct_reference_total": total_count,
        "direct_reference_detail": direct_reference_detail,
    }
    return [
        GateResult(
            "static_contracts",
            "README/model_registry/artifacts",
            passed,
            time.perf_counter() - started,
            json.dumps(detail, ensure_ascii=False),
            "",
        )
    ]


def run_release_gate() -> tuple[list[GateResult], int]:
    """Run all release-gate commands and write summaries."""
    rows: list[GateResult] = []
    for gate, command in build_release_gate_steps():
        started = time.perf_counter()
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        rows.append(
            GateResult(
                gate=gate,
                command=" ".join(command),
                passed=proc.returncode == 0,
                runtime_s=time.perf_counter() - started,
                stdout_tail=_tail(proc.stdout),
                stderr_tail=_tail(proc.stderr),
            )
        )
        if proc.returncode != 0:
            break
    if all(row.passed for row in rows):
        rows.extend(check_release_static_contracts())
    out_dir = ROOT / "tmp_smoke_outputs"
    out_dir.mkdir(exist_ok=True)
    payload = [asdict(row) for row in rows]
    (out_dir / "release_gate_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(payload).to_csv(out_dir / "release_gate_summary.csv", index=False, encoding="utf-8-sig")
    return rows, 0 if all(row.passed for row in rows) else 1


def main() -> int:
    rows, code = run_release_gate()
    for row in rows:
        status = "PASS" if row.passed else "FAIL"
        print(f"[{status}] {row.gate} ({row.runtime_s:.2f}s)")
        if not row.passed:
            print(row.stdout_tail)
            print(row.stderr_tail, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
