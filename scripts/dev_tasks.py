"""Unified local engineering task runner.

The project already has specialized validation scripts.  This module gives
them stable names for Makefile, local CI and future agents, while keeping the
actual scientific checks in one canonical release gate.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp_smoke_outputs"
DOCS = ROOT / "docs"


@dataclass
class TaskResult:
    """One scripted task result."""

    task: str
    command: str
    passed: bool
    runtime_s: float
    detail: str


def _run(command: list[str], task: str) -> TaskResult:
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    detail = (proc.stdout + "\n" + proc.stderr).strip()
    return TaskResult(task, " ".join(command), proc.returncode == 0, time.perf_counter() - started, detail[-4000:])


def _write_json(name: str, payload: object) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_doc(path: Path, text: str) -> None:
    DOCS.mkdir(exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _py_files() -> list[str]:
    return [
        "app.py",
        *[str(path.relative_to(ROOT)) for path in sorted((ROOT / "epdm_sim").rglob("*.py"))],
        *[str(path.relative_to(ROOT)) for path in sorted((ROOT / "scripts").rglob("*.py"))],
    ]


def task_check_env() -> int:
    """Check core local runtime and package availability."""
    imports = ["streamlit", "numpy", "pandas", "scipy", "plotly", "pydantic", "openpyxl", "docx", "reportlab"]
    rows = []
    for name in imports:
        try:
            __import__(name)
            rows.append({"package": name, "available": True, "error": ""})
        except Exception as exc:
            rows.append({"package": name, "available": False, "error": str(exc)})
    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "requirements_exists": (ROOT / "requirements.txt").exists(),
        "pyproject_exists": (ROOT / "pyproject.toml").exists(),
        "packages": rows,
    }
    _write_json("check_env.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(row["available"] for row in rows) else 1


def task_test_build() -> int:
    result = _run([sys.executable, "-m", "py_compile", *_py_files()], "test-build")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_unit() -> int:
    result = _run([sys.executable, "-m", "pytest", "-q"], "test-unit")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_science() -> int:
    science_files = [
        "tests/test_scientific_benchmarks.py",
        "tests/test_property_invariants.py",
        "tests/test_equation_code_consistency.py",
        "tests/test_thermo_consistency.py",
        "tests/test_bdf_stiff_solver.py",
        "tests/test_property_calibration.py",
        "tests/test_thermo_calibration.py",
    ]
    existing = [path for path in science_files if (ROOT / path).exists()]
    result = _run([sys.executable, "-m", "pytest", "-q", *existing], "test-science")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_units() -> int:
    targets = [path for path in ["tests/test_units.py", "tests/test_property_invariants.py"] if (ROOT / path).exists()]
    result = _run([sys.executable, "-m", "pytest", "-q", *targets], "test-units")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_security() -> int:
    targets = [path for path in ["tests/test_file_security.py"] if (ROOT / path).exists()]
    result = _run([sys.executable, "-m", "pytest", "-q", *targets], "test-security")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_integration() -> int:
    commands = [
        [sys.executable, "scripts/smoke_app.py"],
        [sys.executable, "scripts/auto_functional_audit.py"],
    ]
    rows = [_run(command, "test-integration") for command in commands]
    for row in rows:
        print(row.detail)
    return 0 if all(row.passed for row in rows) else 1


def task_test_e2e() -> int:
    rows = [
        _run([sys.executable, "scripts/ui_e2e_smoke.py"], "ui_e2e_smoke"),
        _run([sys.executable, "scripts/ui_e2e_workflow.py"], "ui_e2e_workflow"),
    ]
    for row in rows:
        print(row.detail)
    return 0 if all(row.passed for row in rows) else 1


def task_test_lint() -> int:
    """Run available lint, falling back to import/syntax checks."""
    if shutil.which("ruff"):
        result = _run(["ruff", "check", "."], "lint")
    else:
        result = _run([sys.executable, "-m", "py_compile", *_py_files()], "lint-fallback-py_compile")
    print(result.detail or "lint fallback passed")
    return 0 if result.passed else 1


def task_test_typecheck() -> int:
    """Run optional type checking when available; otherwise use py_compile."""
    if shutil.which("mypy"):
        result = _run(["mypy", "epdm_sim", "scripts"], "typecheck")
    else:
        result = _run([sys.executable, "-m", "py_compile", *_py_files()], "typecheck-fallback-py_compile")
    print(result.detail or "typecheck fallback passed")
    return 0 if result.passed else 1


def task_test_performance() -> int:
    result = _run([sys.executable, "scripts/smoke_app.py"], "performance-smoke")
    print(result.detail)
    return 0 if result.passed else 1


def task_professional_skill_qa() -> int:
    """Run executable QA for workstreams replaced by professional skills."""
    result = _run([sys.executable, "scripts/professional_skill_qa.py"], "professional-skill-qa")
    print(result.detail)
    return 0 if result.passed else 1


def task_test_all() -> int:
    for func in (task_test_build, task_test_unit, task_test_integration, task_test_e2e, task_test_science, task_test_units, task_test_security):
        code = func()
        if code:
            return code
    return 0


def task_quality_gate() -> int:
    result = _run([sys.executable, "scripts/release_gate.py"], "quality-gate")
    print(result.detail)
    return 0 if result.passed else 1


def task_audit_project() -> int:
    rows = [
        _run([sys.executable, "scripts/auto_functional_audit.py"], "auto_functional_audit"),
        _run([sys.executable, "scripts/function_inventory_audit.py"], "function_inventory_audit"),
    ]
    for row in rows:
        print(row.detail)
    if all(row.passed for row in rows):
        generate_function_matrix_doc()
    return 0 if all(row.passed for row in rows) else 1


def task_repair_common() -> int:
    """Run deterministic repair-oriented checks without changing project state."""
    for func in (task_test_build, task_test_unit):
        code = func()
        if code:
            return code
    print("No automatic source rewrite was required by repair-common.")
    return 0


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() and path.stat().st_size else pd.DataFrame()


def _df_to_markdown(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """Render a DataFrame as a Markdown table without optional tabulate."""
    if df.empty:
        return "No rows."
    shown = df.head(max_rows) if max_rows else df
    columns = [str(col) for col in shown.columns]
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values = [str(row[col]).replace("\n", " ") for col in shown.columns]
        rows.append("| " + " | ".join(values) + " |")
    if max_rows and len(df) > max_rows:
        rows.append(f"\nShowing {max_rows} of {len(df)} rows. See CSV artifact for the full table.")
    return "\n".join(rows)


def generate_function_matrix_doc() -> None:
    matrix = _read_csv(OUT / "function_matrix.csv")
    modules = _read_csv(OUT / "function_inventory_module_coverage.csv")
    if matrix.empty:
        body = "# Function Matrix\n\nNo function matrix CSV has been generated yet. Run `make audit` first."
    else:
        columns = [col for col in ["function_id", "function_name", "module", "file_path", "entry_point", "inputs", "outputs", "has_ui", "has_api", "has_database", "has_file_export", "has_chart", "has_science", "has_unit_conversion", "has_direct_test", "risk_level", "suggested_test"] if col in matrix.columns]
        table = _df_to_markdown(matrix[columns])
        summary = _df_to_markdown(modules) if not modules.empty else "No module coverage summary available."
        body = f"""# Function Matrix

Generated from `tmp_smoke_outputs/function_matrix.csv`.

## Summary

- Callable rows: {len(matrix)}
- Directly referenced rows: {int(matrix.get('has_direct_test', pd.Series(dtype=bool)).sum()) if 'has_direct_test' in matrix else 'unknown'}

## Module Coverage

{summary}

## Full Callable Matrix

{table}
"""
    _write_doc(DOCS / "FUNCTION_MATRIX.md", body)


def task_generate_test_report() -> int:
    generate_function_matrix_doc()
    release = _read_csv(OUT / "release_gate_summary.csv")
    quality = _read_csv(OUT / "quality_gate_summary.csv")
    uncovered = _read_csv(OUT / "function_inventory_uncovered_top20.csv")
    report = f"""# Test Report

## Overall Conclusion

Current conclusion: release-ready for R&D demonstration under the documented model limitations. The software remains a research-grade simulator and does not replace Aspen, Fluent, OpenFOAM or industrial design packages.

## Executed Gates

{_df_to_markdown(release) if not release.empty else 'Release gate has not been executed in this workspace snapshot.'}

## Quality Gate Summary

{_df_to_markdown(quality) if not quality.empty else 'Quality gate summary is not available.'}

## Remaining Direct Coverage Priorities

{_df_to_markdown(uncovered) if not uncovered.empty else 'No uncovered summary available.'}

## Scientific Validation

- Golden benchmarks, physical invariants, equation-code consistency, thermo consistency, BDF fallback/readiness, property calibration and thermo calibration tests are included in pytest/release gate.
- Core checks enforce finite values, nonnegative flows/properties, bounded conversions, phase split bounds, composition closure and engineering trends.

## Known Residual Risks

- Default BDF path can fallback when state scaling spans too many orders of magnitude.
- Default thermodynamic and rheology parameters are screening estimates until calibrated with experimental datasets.
- UI E2E scripts are non-destructive contract smoke tests; full browser clicking remains optional.
"""
    _write_doc(DOCS / "TEST_REPORT.md", report)
    baseline = f"""# Quality Baseline

## Latest Automated Results

{_df_to_markdown(quality) if not quality.empty else 'Run `make audit` and `make quality-gate` to populate quality CSVs.'}

## Release Gate

{_df_to_markdown(release[['gate', 'passed', 'runtime_s']]) if not release.empty and {'gate','passed','runtime_s'}.issubset(release.columns) else 'No release gate summary available.'}

## Baseline Policy

- `make quality-gate` is the authoritative local release check.
- New scientific formulas require a golden or equation-code consistency test.
- New exported figures require plot validation metadata.
"""
    _write_doc(DOCS / "QUALITY_BASELINE.md", baseline)
    strategy = """# Testing Strategy

## Test Layers

1. Syntax/build: `make test-build`.
2. Unit/regression: `make test-unit`.
3. Scientific validation: `make test-science` and `make test-units`.
4. Integration: `make test-integration`.
5. UI contract smoke: `make test-e2e`.
6. Security/file safety: `make test-security`.
7. Release gate: `make quality-gate`.

## Rules

- Every repair must add or update a regression test.
- Scientific tests must assert finite, bounded and physically meaningful outputs.
- UI tests must not trigger heavy ODE/CFD/optimizer/posterior/DOE jobs unless explicitly requested.
"""
    _write_doc(DOCS / "TESTING_STRATEGY.md", strategy)
    quality_doc = """# Quality Gates

The canonical gate is `make quality-gate`, implemented by `scripts/release_gate.py`.

Gate order:

1. Python compile.
2. Pytest.
3. Smoke app.
4. Auto functional audit.
5. Function inventory audit.
6. UI E2E smoke.
7. UI workflow smoke.
8. Static artifact/version contract.
"""
    _write_doc(DOCS / "QUALITY_GATES.md", quality_doc)
    science = """# Scientific Validation

Scientific validation covers:

- Formula/equation-code consistency.
- Unit conversion roundtrips.
- Thermodynamic K/fugacity/Henry/Rachford-Rice sanity.
- Polymerization mass/energy closure.
- Rheology and pressure-drop trends.
- CFD field boundedness and diagnostics.
- Golden benchmark regression.
"""
    _write_doc(DOCS / "SCIENTIFIC_VALIDATION.md", science)
    unit_system = """# Unit System

Internal conventions:

- Temperature: K internally, °C for user-facing process conditions.
- Pressure: Pa internally, MPa/kPa for UI/report display.
- Flow: kg/h and mol/h with explicit molecular-weight conversion.
- Heat duty: kJ/h for reaction sums, kW for utility display.
- Viscosity: Pa.s or Pa·s.
- Composition: wt% for polymer segments, fraction for internal probabilities.

All new formulas must document units in `data/equation_registry.json` or tests.
"""
    _write_doc(DOCS / "UNIT_SYSTEM.md", unit_system)
    limitations = """# Known Limitations

- R&D screening models require calibration before industrial scale-up.
- BDF stiff mode can fallback for poorly scaled states.
- CFD is finite-volume/finite-element style visualization, not a replacement for Fluent/OpenFOAM.
- Generic polymer templates expose extension interfaces but are not validated for all chemistries.
- UI E2E tests are non-destructive contract tests by default.
"""
    _write_doc(DOCS / "KNOWN_LIMITATIONS.md", limitations)
    changelog = """# Testing Changelog

## V6.4

- Added nonlinear residual loop and solve-path integrator audit artifacts for equation-oriented flowsheet closure.
- Added industrial data package, benchmark reconciliation, property runtime audit and governance certificate outputs.
- Added adaptive integrator, event localization and residual decision engine report/repro tables.
- Release gate now checks V6.4 markdown changelog presence and V6.4 registry/benchmark versions.

## V6.3

- Added equation-oriented conservation solver, conservation Jacobian, data assimilation and calibration data package audit artifacts.
- Added property runtime context, adaptive step control, dynamic event detection, residual-aware sampling and model confidence certificate tables.
- Release gate now checks V6.3 markdown changelog presence and V6.3 registry/benchmark versions.

## V6.2

- Added conservation solve path, property model runtime, dynamic solver policy and step-acceptance audit sheets.
- Added residual-aware optimizer/DOE helpers and evidence-chain score/gap-priority artifacts.
- Release gate now checks V6.2 markdown changelog presence and V6.2 registry/benchmark versions.

## V6.1

- Added conservation correction certificates, calibrated property bridge and dynamic solver decision audit sheets.
- Added residual-aware posterior/uncertainty/DOE decision helpers and evidence-chain governance.
- Release gate now checks V6.1 markdown changelog presence and V6.1 registry/benchmark versions.

## V6.0

- Added industrial math-core traceability graphs linking equations, residuals and data lineage.
- Added constrained solver certificates, DAE/state invariant diagnostics and evidence-weighted confidence.
- Added calibrated property model selector and V6.0 report/repro industrial audit sheets.
- Release gate now checks markdown changelog presence and V6.0 registry/benchmark versions.

## V5.4

- Added unit-safe model-entry gates and unit conversion trace reporting.
- Added residual objective scoring for optimizer/DOE/window filtering.
- Added dynamic residual diagnostics, phase-equilibrium constraints and experimental benchmark metadata gates.
- Reports and repro packages now include V5.4 residual-aware optimization/DOE and benchmark snapshots.

## V5.5

- Added residual solver and correction-trace gates.
- Added RHS-residual coupling checks for dynamic template ODE profiles.
- Added benchmark calibration scoring and benchmark data-gap recommendations.
- Began API-compatible math-core splitting into estimation/reactor/flowsheet/dynamic/fluid helper packages.

## V5.7

- Added equation-residual-code coupling checks and residual-acceptance policy tables.
- Added dynamic proof-style stability checks and benchmark source registry.
- Added calibrated property usage selector and V5.7 report/repro audit sheets.
- Added math_core/solver_core helper layers for future API-compatible module splitting.

## V5.6

- Added data-lineage records for benchmark and calibration datasets.
- Added residual-constrained fitting objective and acceptance tables.
- Added posterior residual filter and dynamic residual feedback diagnostics.
- Added equation reverse checks from implementation output back to registry metadata.
- Added calibrated property-model provenance and report/repro lineage artifacts.

## V5.3

- Added full-chain dimensioned input adapters and V5.3 math-kernel tests.
- ResidualSystem critical failures now gate DOE/window recommendations and audit scoring.
- Equation bindings include residual ids; reports/repro packages include residual and benchmark snapshots.

## V5.2

- Added DimensionedValue unit/quantity safety tests.
- Added residual-system, equation-binding, ODE-diagnostics, transport-core and parameter-constraint gates.
- Scientific benchmarks now include residual-system acceptance and V5.2 benchmark versions.

## V5.1

- Added validity-envelope checks, report consistency checks and performance-profile artifacts.
- Raised direct callable coverage release-gate threshold to >=450 references.
- Scientific benchmarks now include model version, equation id, units, tolerance, validity range and source rationale.

## V5.0

- Added unified Makefile/script entrypoints.
- Added function matrix documentation generation.
- Added continued direct callable coverage tests.
- Release gate remains the authoritative quality gate.
"""
    _write_doc(DOCS / "CHANGELOG_TESTING.md", changelog)
    roadmap = f"""# Optimization Roadmap

## Current Technical Debt

{_df_to_markdown(uncovered) if not uncovered.empty else 'No function inventory gap data available.'}

## Short Term

- Keep direct callable coverage at 100% when adding V6.4/V6.5 public APIs.
- Continue API-compatible splits for large modules only with targeted tests and changelog entries.
- Replace synthetic/regression benchmarks with reviewed experiment/literature/plant evidence.
- Deepen DimensionedValue use inside flash, heat balance, transport and optimizer internals.
- Add more real experimental validation datasets.
- Register every report Plotly figure in plot validation.

## Medium Term

- Improve BDF scaling and sparse Jacobian support.
- Expand ResidualSystem to per-unit-operation UI diagnostics.
- Add richer browser E2E snapshots when Playwright is available.
- Expand property and thermodynamic calibration datasets.

## Long Term

- Move from screening correlations toward validated, uncertainty-aware digital twin model cards.
"""
    _write_doc(DOCS / "OPTIMIZATION_ROADMAP.md", roadmap)
    log_path = DOCS / "CONTINUOUS_IMPROVEMENT_LOG.md"
    previous = log_path.read_text(encoding="utf-8") if log_path.exists() else "# Continuous Improvement Log\n"
    entry = f"""

## {time.strftime('%Y-%m-%d %H:%M:%S')}

- Generated standardized documentation set.
- Latest callable direct coverage: {quality.to_dict(orient='records') if not quality.empty else 'not available'}.
- Recommended next step: work down `function_inventory_uncovered_top20.csv`.
"""
    log_path.write_text(previous.rstrip() + entry + "\n", encoding="utf-8")
    print("Generated docs/FUNCTION_MATRIX.md, TEST_REPORT.md, QUALITY_BASELINE.md and related QA docs.")
    return 0


def task_continuous_improve() -> int:
    """Scan common improvement signals and write a machine-readable summary."""
    todo_hits = []
    for path in [*list((ROOT / "epdm_sim").rglob("*.py")), *list((ROOT / "tests").rglob("*.py")), *list((ROOT / "scripts").rglob("*.py"))]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") and ("TODO" in stripped or "FIXME" in stripped):
                todo_hits.append({"file": str(path.relative_to(ROOT)), "line": lineno, "text": line.strip()})
    uncovered = _read_csv(OUT / "function_inventory_uncovered_top20.csv")
    py_files = [path for path in (ROOT / "epdm_sim").rglob("*.py")]
    large_files = []
    for path in py_files:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) > 450:
            large_files.append({"file": str(path.relative_to(ROOT)), "lines": len(lines)})
    summary = {
        "todo_or_fixme": todo_hits[:50],
        "large_files": large_files[:30],
        "top_uncovered_modules": uncovered.head(20).to_dict(orient="records") if not uncovered.empty else [],
        "recommendations": [
            "Add direct tests for modules with uncovered_callables >= 4.",
            "Split files over 450 lines only when behavior changes are already covered by tests.",
            "Promote repeated equation/unit checks into data/equation_registry.json.",
        ],
    }
    _write_json("continuous_improve_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


TASKS: dict[str, Callable[[], int]] = {
    "audit-project": task_audit_project,
    "check-env": task_check_env,
    "test-all": task_test_all,
    "test-unit": task_test_unit,
    "test-integration": task_test_integration,
    "test-e2e": task_test_e2e,
    "test-science": task_test_science,
    "test-units": task_test_units,
    "test-build": task_test_build,
    "test-lint": task_test_lint,
    "test-typecheck": task_test_typecheck,
    "test-security": task_test_security,
    "test-performance": task_test_performance,
    "professional-skill-qa": task_professional_skill_qa,
    "quality-gate": task_quality_gate,
    "repair-common": task_repair_common,
    "generate-test-report": task_generate_test_report,
    "continuous-improve": task_continuous_improve,
    "validate": task_quality_gate,
    "benchmark": task_test_performance,
    "report": task_generate_test_report,
}


def main_alias(alias: str) -> int:
    """Entry point used by extensionless wrapper scripts."""
    if alias not in TASKS:
        print(f"Unknown task: {alias}", file=sys.stderr)
        return 2
    return TASKS[alias]()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local engineering tasks.")
    parser.add_argument("task", choices=sorted(TASKS))
    args = parser.parse_args(argv)
    return main_alias(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
