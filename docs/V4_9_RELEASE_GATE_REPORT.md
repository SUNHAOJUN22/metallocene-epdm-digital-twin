# V4.9 Release Gate Report

Report date: 2026-05-08 Asia/Shanghai

Project: `metallocene-epdm-digital-twin`

Version: V4.9 / 0.5.6

## 1. Purpose

This report documents the V4.9 release gate for the EPDM/EPM solution-polymerization digital twin. V4.9 focuses on publication-grade quality gates rather than adding more process pages.

## 2. Gate Definition

The V4.9 release gate is implemented in:

```powershell
python scripts\release_gate.py
```

It runs:

- Python compilation for `app.py`, `epdm_sim/**/*.py` and `scripts/**/*.py`.
- Full pytest suite.
- Smoke app report generation.
- Automated functional audit.
- Function inventory/function matrix audit.
- Non-destructive UI E2E smoke.
- Static release contract checks for README, model registry, audit docs and generated CSV/JSON artifacts.

## 3. Added V4.9 Quality Controls

- Direct callable tests for previously under-covered utility, theme, fluid property, equipment, kinetics, solubility, template flowsheet, plotting and service modules.
- Golden scientific benchmarks with model-versioned expected values.
- Property-invariant tests for finite, bounded and positive physical outputs.
- Plotly figure unit and non-empty-data validation.
- File security checks for filename safety, path traversal, extension filtering and export metadata.
- ODE scaling and BDF readiness diagnostics.
- Release gate summary JSON/CSV export.

## 4. Expected Output Artifacts

The release gate should create or verify:

- `tmp_smoke_outputs/release_gate_summary.json`
- `tmp_smoke_outputs/release_gate_summary.csv`
- `tmp_smoke_outputs/auto_functional_audit.csv`
- `tmp_smoke_outputs/function_inventory_modules.csv`
- `tmp_smoke_outputs/function_inventory_callables.csv`
- `tmp_smoke_outputs/function_inventory_module_coverage.csv`
- `tmp_smoke_outputs/function_inventory_uncovered_top20.csv`
- `tmp_smoke_outputs/function_matrix.csv`
- `tmp_smoke_outputs/quality_gate_summary.csv`
- `tmp_smoke_outputs/ui_e2e_smoke.json`

## 5. Scientific Acceptance Criteria

V4.9 release is acceptable only if:

- All major numerical outputs are finite.
- Physical fractions and probabilities are bounded in `[0,1]`.
- Product compositions close to 100 wt% where applicable.
- Polymer pseudo-components do not enter vapor phase.
- Fluid properties remain positive.
- Rheology and pressure-drop trends are chemically and mathematically reasonable.
- Heavy tasks remain manually triggered through UI workflow and task service contracts.

## 6. Current Status

Final local run: 2026-05-08 10:56 Asia/Shanghai.

| Gate | Result | Runtime |
|---|---:|---:|
| py_compile | PASS | 0.35 s |
| pytest -q | PASS, 212 passed | 27.40 s |
| smoke_app | PASS | 2.86 s |
| auto_functional_audit | PASS, 74/74 | 9.63 s |
| function_inventory_audit | PASS, 117/117 modules imported; 339/554 public callables directly referenced | 2.14 s |
| ui_e2e_smoke | PASS | 1.69 s |
| static contracts | PASS | <0.01 s |

Generated release artifacts:

- `tmp_smoke_outputs/release_gate_summary.json`
- `tmp_smoke_outputs/release_gate_summary.csv`
- `tmp_smoke_outputs/auto_functional_audit.csv`
- `tmp_smoke_outputs/function_inventory_modules.csv`
- `tmp_smoke_outputs/function_inventory_callables.csv`
- `tmp_smoke_outputs/function_inventory_module_coverage.csv`
- `tmp_smoke_outputs/function_inventory_uncovered_top20.csv`
- `tmp_smoke_outputs/function_matrix.csv`
- `tmp_smoke_outputs/quality_gate_summary.csv`
- `tmp_smoke_outputs/ui_e2e_smoke.json`

HTTP and browser status:

- `http://127.0.0.1:8501/` returned HTTP 200.
- In-app browser title: `Metallocene EPDM Digital Twin`.
- Temperature and pressure controls were visible.
- Browser console error/warning count: 0.

## 7. Known Limitations

- The release gate is a local Windows/PowerShell-compatible quality gate, not a hosted CI pipeline.
- UI E2E is intentionally non-destructive and does not click heavy compute buttons.
- BDF stiff ODE is tracked by readiness diagnostics but remains controlled fallback in this release line.
- Scientific benchmarks are regression anchors, not industrial calibration references.
