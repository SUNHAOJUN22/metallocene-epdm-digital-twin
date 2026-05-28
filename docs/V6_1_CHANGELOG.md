# V6.1 Changelog

## 2026-05-18 10:20 - V6.1 update 1

### Change
- Added `epdm_sim/solver_core/conservation_correction.py`.
- Added `epdm_sim/property_model_bridge.py`.
- Added `epdm_sim/dynamic_core/solver_decision.py`.
- Added `epdm_sim/residual_aware_decision.py`.
- Added `epdm_sim/evidence_chain.py`.
- Added API-compatible helper splits under `estimation/`, `reactor_core/`, `flowsheet_core/`, `dynamic_core/`, and `fluid_core/`.
- Added `tests/test_v6_1_math_core.py`.

### Reason
- V6.1 needs to move V6.0 governance from report-only certificates toward correction certificates, solver decision support, calibrated property bridging, residual-aware decision scoring and evidence-chain governance while keeping old APIs intact.

### Mathematical / Engineering Logic
- 守恒影响：small mass/energy/flash residuals can be certified for closure, while large or critical residuals remain rejected.
- 单位影响：property bridge keeps calibrated/default property provenance explicit and validity-aware; it does not silently mix units.
- residual 影响：posterior/uncertainty/DOE decisions now expose residual risk and bounded acceptance scores.
- benchmark 影响：evidence chain links equation, residual, benchmark, data lineage and source reference into one audit table.

### Verification
- `python -m pytest -q tests/test_v6_1_math_core.py`: passed.

### Remaining Risk
- Correction helpers are still certificate/correction layers and do not replace every internal nonlinear solver path.

## 2026-05-18 10:35 - V6.1 update 2

### Change
- Updated Excel report export, repro package export, report consistency checks, auto functional audit and release gate for V6.1 artifacts.
- Updated README, CHANGELOG, model/equation/benchmark versions and QA document generation templates.

### Reason
- V6.1 release requires audit artifacts and quality gates for conservation correction, property model bridge, dynamic solver decision, residual-aware decision, evidence chain and Excel sheet-name compatibility.

### Mathematical / Engineering Logic
- 守恒影响：`conservation_correction` and `correction_certificates` are exported and gated.
- 单位影响：property bridge rows preserve source, confidence and validity diagnostics.
- residual 影响：residual-aware decision and dynamic solver decision are exported and checked in `auto_functional_audit.py`.
- benchmark 影响：evidence chain and evidence gaps are exported to reports and repro packages.

### Verification
- Full release gate pending at this log point.

### Remaining Risk
- Real plant/experiment source ingestion still depends on local benchmark/source metadata.

## 2026-05-18 10:45 - V6.1 update 3

### Change
- Added `docs/V6_1_MATH_CORE_AUDIT.md`.
- Hardened `epdm_sim/estimation/fit_runner.py` with a safe default `ResidualSystem` for direct facade calls.

### Reason
- V6.1 requires a math-core audit before final release validation, and function-level direct coverage should not fail because a facade omitted an optional residual-system object.

### Mathematical / Engineering Logic
- 守恒影响：the default fit facade now evaluates against an explicit empty residual system instead of raising a non-physical call error.
- 单位影响：no unit conversion behavior changed.
- residual 影响：residual-aware fit remains bounded and explicit for default direct calls.
- benchmark 影响：no benchmark target values changed.

### Verification
- `python -m pytest -q tests/test_v6_1_math_core.py`: pending rerun after audit/document updates.

### Remaining Risk
- Full quality gate and release gate verification are still pending.

## 2026-05-18 11:05 - V6.1 update 5

### Change
- Completed V6.1 verification pass and refreshed generated QA documents.
- Updated `CHANGELOG.md` with V6.1 verification results.

### Reason
- V6.1 requires markdown changelog, QA baseline, release gate summary, performance profile and UI workflow evidence before completion.

### Mathematical / Engineering Logic
- 守恒影响：default flowsheet residual score is now 100 and conservation correction gate passes.
- 单位影响：unit-safe entry and unit conversion trace gates pass through the full release workflow.
- residual 影响：residual acceptance, correction, dynamic residual feedback, residual-aware decision and report/repro gates pass.
- benchmark 影响：benchmark acceptance, experimental benchmark, benchmark source registry and evidence-chain gates pass.

### Verification
- `python -m pytest -q tests/test_v6_1_math_core.py`: 6 passed.
- `python scripts/auto_functional_audit.py`: 125/125 passed.
- `python scripts/function_inventory_audit.py`: 228/228 modules imported, 876/876 public callables directly referenced.
- `python -m pytest -q`: 323 passed.
- `python scripts/dev_tasks.py quality-gate`: passed all gates.
- `python scripts/release_gate.py`: passed all gates.
- `python scripts/performance_profile.py`: passed all profiled tasks.
- `python scripts/ui_e2e_smoke.py`: passed, HTTP 200.
- `python scripts/ui_e2e_workflow.py`: passed, HTTP 200.
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200.

### Remaining Risk
- Remaining technical debt is not P0/P1/P2: several large API-compatible modules still need gradual split in V6.2, and more plant/experiment/literature benchmark sources are needed for industrial calibration confidence.

## 2026-05-18 10:55 - V6.1 update 4

### Change
- Fixed `epdm_sim/residual_system.py` to resolve flowsheet stream names case-insensitively and recognize `Polymer product` as the product stream.
- Updated `tests/test_v6_1_math_core.py` to assert default flowsheet correction certificates are not rejected and the total mass residual closes.
- Updated `epdm_sim/scientific_benchmarks.py` model version constant to `V6.1 / 0.7.1`.

### Reason
- `auto_functional_audit.py` found `conservation_correction_gate` failing because the residual builder looked for lowercase stream keys while the flowsheet emits display names such as `Feed` and `Polymer product`.

### Mathematical / Engineering Logic
- 守恒影响：default total mass residual now uses the actual feed and product streams, preventing a false 100% mass imbalance.
- 单位影响：no unit conversion behavior changed; residual units remain `kg/h`.
- residual 影响：conservation correction no longer attempts to correct a nonphysical artifact caused by stream-key mismatch.
- benchmark 影响：benchmark module version now matches the V6.1 release contract.

### Verification
- `python scripts/auto_functional_audit.py`: failed before this fix at `conservation_correction_gate`; rerun pending.

### Remaining Risk
- Full quality gate and release gate verification are still pending.
