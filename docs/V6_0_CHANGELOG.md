# V6.0 Changelog

## 2026-05-15 11:00 - V6.0 update 1

### Change
- Added `epdm_sim/math_core/balance_laws.py`, `thermodynamic_identities.py`, `kinetic_identities.py`, `dimension_signatures.py`, `equation_graph.py`, `residual_graph.py`, and `model_confidence.py`.
- Added `epdm_sim/solver_core/constrained_solver.py`, `residual_minimizer.py`, `solver_certificates.py`, `dae_solver.py`, and `stability_region.py`.
- Added `epdm_sim/dynamic_core/dae_constraints.py` and `state_invariants.py`.

### Reason
- V6.0 needs a layered industrial math-core namespace for equations, units, residuals, constraints, solver certificates and dynamic state invariants without breaking legacy imports.

### Mathematical / Engineering Logic
- 守恒影响：ResidualSystem now feeds balance-law records and constrained solver certificates.
- 单位影响：new identity tests keep thermodynamic/kinetic formulas on explicit SI units.
- residual 影响：solver certificate records residual norm and constraint violations.
- benchmark 影响：dimension signatures and equation graph reuse the executable equation registry and benchmark ids.

### Verification
- `python -m pytest -q tests/test_v6_0_industrial_math_core.py tests/test_v5_7_math_kernel.py tests/test_report_consistency.py tests/test_repro_package.py`: passed after one traceability fallback fix.

### Remaining Risk
- Constrained solver is still a certificate/correction layer, not a full nonlinear process solver replacement.

## 2026-05-15 11:20 - V6.0 update 2

### Change
- Added `epdm_sim/model_graph.py`, `residual_graph.py`, `data_lineage_graph.py`, `validation_evidence.py`, `model_confidence_engine.py`, and `property_model_selector.py`.
- Updated `epdm_sim/reporting/excel.py`, `repro_package.py`, `report_consistency.py`, `io_schema.py`, `scripts/auto_functional_audit.py`, and `scripts/release_gate.py`.

### Reason
- V6.0 requires equation-residual-data lineage traceability, evidence-weighted confidence, calibrated property selection, and report/repro industrial audit artifacts.

### Mathematical / Engineering Logic
- 守恒影响：residual graph and constrained solver output expose suspected sources and correction certificates.
- 单位影响：property selector keeps calibrated/default property usage explicit and validity-aware.
- residual 影响：auto audit adds model traceability, DAE/state invariant, constrained solver and solver certificate gates.
- benchmark 影响：benchmark lineage and golden benchmark fallback are linked into traceability tables.

### Verification
- Targeted V6.0 regression passed; full quality gate pending at this log point.

### Remaining Risk
- Real plant/experiment benchmark ingestion remains metadata based until V6.1.

## 2026-05-15 11:30 - V6.0 update 3

### Change
- Shortened the Excel report sheet name `dynamic_residual_feedback_status` to `dyn_resid_feedback_status`.
- Added a regression assertion in `tests/test_report_consistency.py` that all exported Excel sheet names are at most 31 characters.

### Reason
- `openpyxl` warned that one worksheet title exceeded Excel's 31-character interoperability limit during `performance_profile.py`.

### Mathematical / Engineering Logic
- 守恒影响：none; residual feedback content is unchanged.
- 单位影响：none; report metadata and unit traces are unchanged.
- residual 影响：dynamic residual feedback status remains exported under a shorter audit-safe sheet name.
- benchmark 影响：none; benchmark acceptance and lineage sheets are unchanged.

### Verification
- `python scripts/dev_tasks.py quality-gate`: passed before this correction.
- Targeted report consistency and full release-gate verification were scheduled immediately after the change.

### Remaining Risk
- The workbook still contains many audit sheets by design; future additions should keep worksheet names short enough for Excel compatibility.

## 2026-05-18 10:05 - V6.0 update 4

### Change
- Refreshed V6.0 QA documentation through `scripts/dev_tasks.py generate-test-report`.
- Re-ran the V6.0 release workflow and Streamlit HTTP acceptance check without code changes.

### Reason
- The current workspace was already upgraded to V6.0 / 0.7.0; this update records the requested full re-verification pass and confirms no P0/P1/P2 math-core defects were found.

### Mathematical / Engineering Logic
- 守恒影响：ResidualSystem, constrained solver, DAE/state invariant, and report/repro industrial audit gates remain passing.
- 单位影响：DimensionedValue and unit-safe entry gates remain passing; no silent Pa/MPa, K/°C, mol/L/mol/m3, or kJ/h/kW regression was detected.
- residual 影响：model traceability, residual graph, residual-aware DOE/posterior/calibration, and solver certificate gates remain passing.
- benchmark 影响：benchmark source registry, data lineage, experimental benchmark and confidence-engine checks remain passing.

### Verification
- `python scripts/dev_tasks.py check-env`: passed.
- `python scripts/dev_tasks.py quality-gate`: passed.
- `python scripts/release_gate.py`: passed.
- `python scripts/performance_profile.py`: passed.
- `python scripts/ui_e2e_smoke.py`: passed.
- `python scripts/ui_e2e_workflow.py`: passed.
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200.

### Remaining Risk
- Remaining risks are P3 maintainability items: API-compatible splits for `parameter_estimation.py`, `reactor.py`, `flowsheet.py`, `dynamic_template_reactor.py`, `fluid_props.py`, and `cfd/simple_solver.py`.
