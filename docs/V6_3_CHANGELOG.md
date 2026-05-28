# V6.3 Changelog

## 2026-05-18 16:10 - V6.3 update 1

### Change
- Added `epdm_sim/solver_core/conservation_jacobian.py`.
- Added `epdm_sim/solver_core/equation_oriented_solver.py`.
- Added `epdm_sim/calibration_data_package.py`.
- Added `epdm_sim/data_assimilation.py`.
- Added `epdm_sim/property_runtime_context.py`.
- Added `epdm_sim/dynamic_core/adaptive_step_control.py`.
- Added `epdm_sim/dynamic_core/event_detection.py`.
- Added `epdm_sim/residual_aware_sampling.py`.
- Added `epdm_sim/model_confidence_certificate.py`.
- Added `tests/test_v6_3_math_core.py`.

### Reason
- V6.3 moves V6.2 correction, runtime property, solver policy, residual-aware decision and evidence scoring into explicit equation-oriented, data-assimilation, adaptive-step and confidence-certificate APIs.

### Mathematical / Engineering Logic
- 守恒影响：bounded least-squares/Newton-style residual steps are exposed with Jacobian condition diagnostics and critical-residual rejection.
- 单位影响：calibration package unit validation and property runtime context keep units explicit before evidence enters calibrated models.
- residual 影响：residual-aware sampling and equation-oriented solver certificates reject critical residuals and outside-validity candidates.
- benchmark 影响：data assimilation and model confidence certificates use benchmark source type, source reference, validity and confidence in gate-ready rows.

### Verification
- Targeted V6.3 tests pending at this log point.

### Remaining Risk
- Equation-oriented solver remains a bounded residual-correction layer; it does not yet replace all legacy nonlinear solve loops.

## 2026-05-18 16:18 - V6.3 update 2

### Change
- Updated `epdm_sim/model_confidence_certificate.py` source-reference penalty logic.

### Reason
- The first V6.3 targeted test run showed that regression-snapshot evidence without a source reference was being treated like missing high-confidence plant/experiment/literature evidence.

### Mathematical / Engineering Logic
- 守恒影响：no conservation residual behavior changed.
- 单位影响：no unit conversion behavior changed.
- residual 影响：confidence certificate still requires the evidence chain and residual/equation status to pass.
- benchmark 影响：regression snapshots remain low-confidence evidence, but only plant/experiment/literature benchmarks without source references count as blocking source-lineage gaps.

### Verification
- `python -m pytest -q tests/test_v6_3_math_core.py`: 5 passed, 1 failed before this correction; rerun pending.

### Remaining Risk
- Full V6.3 quality gate verification is still pending.

## 2026-05-18 16:35 - V6.3 update 3

### Change
- Integrated V6.3 artifacts into Excel report export, report consistency checks and repro package export.
- Updated `scripts/auto_functional_audit.py`, `scripts/release_gate.py`, `scripts/dev_tasks.py`, `README.md`, `CHANGELOG.md` and `docs/V6_3_MATH_CORE_AUDIT.md`.
- Updated static version contracts to V6.3 / 0.7.3.

### Reason
- V6.3 capabilities must be visible in release gates, audit reports and repro packages, not only in direct unit tests.

### Mathematical / Engineering Logic
- 守恒影响：equation-oriented solver and conservation Jacobian are exported and gated.
- 单位影响：calibration data package unit validation and property runtime context are exported and gated.
- residual 影响：adaptive step control, residual-aware sampling and confidence certificate are included in audit outputs.
- benchmark 影响：data assimilation and validation upgrade plan connect benchmark evidence to confidence scoring.

### Verification
- `python -m pytest -q tests/test_v6_3_math_core.py`: passed after update 2.
- Full V6.3 quality gate verification pending after integration.

### Remaining Risk
- Full release gate and UI smoke/workflow verification still need to be rerun after all integration changes.

## 2026-05-18 16:45 - V6.3 update 4

### Change
- Updated `tests/test_v6_3_math_core.py` to directly reference `residual_vector_from_system()` and `detect_dynamic_events()`.

### Reason
- `function_inventory_audit.py` reported 933/935 public callables directly referenced after the first V6.3 integration pass.

### Mathematical / Engineering Logic
- 守恒影响：residual-vector extraction is now directly tested against the ResidualSystem residual count.
- 单位影响：no unit behavior changed.
- residual 影响：dynamic event detection and conservation residual vector helpers are included in direct-reference coverage.
- benchmark 影响：no benchmark values changed.

### Verification
- `python scripts\\auto_functional_audit.py`: 141/141 passed before this correction.
- `python scripts\\function_inventory_audit.py`: 933/935 before this correction; rerun pending.

### Remaining Risk
- Full V6.3 quality gate verification is still pending.

## 2026-05-18 16:55 - V6.3 update 5

### Change
- Refreshed `docs/TEST_REPORT.md`, `docs/QUALITY_BASELINE.md`, `docs/OPTIMIZATION_ROADMAP.md` and continuous-improvement outputs through `scripts/dev_tasks.py`.
- Updated `README.md`, `CHANGELOG.md` and this V6.3 changelog with final verification results.

### Reason
- V6.3 requires the code, generated QA reports, release-gate artifacts and Markdown changelogs to agree before the upgrade is considered complete.

### Mathematical / Engineering Logic
- 守恒影响：final gates confirm equation-oriented solver, conservation Jacobian, conservation solve path and residual critical gates are passing.
- 单位影响：final gates confirm calibration package units, property runtime context, DimensionedValue/static contracts and Excel sheet-name compatibility are passing.
- residual 影响：auto functional audit confirms residual-aware sampling, optimizer/DOE/posterior acceptance, adaptive step control and confidence certificate gates are passing.
- benchmark 影响：benchmark acceptance, data assimilation, evidence chain score and report/repro industrial audit gates are passing.

### Verification
- `python -m pytest -q`: 334 passed.
- `python scripts\dev_tasks.py check-env`: passed.
- `python scripts\dev_tasks.py quality-gate`: passed.
- `python scripts\dev_tasks.py generate-test-report`: passed.
- `python scripts\dev_tasks.py continuous-improve`: passed.
- `python scripts\release_gate.py`: passed.
- `python scripts\performance_profile.py`: passed.
- `python scripts\ui_e2e_smoke.py`: passed.
- `python scripts\ui_e2e_workflow.py`: passed.
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200.

### Remaining Risk
- V6.3 equation-oriented solving remains an auditable bounded residual-solve layer rather than a full replacement for all nonlinear recycle, flash and heat-balance solve loops.
