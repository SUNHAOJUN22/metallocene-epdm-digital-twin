# V6.4 Changelog

## 2026-05-19 09:49 - V6.4 update 1

### Change
- Added V6.4 nonlinear residual-loop, solve-path integration, industrial data package, benchmark reconciliation, property runtime audit, adaptive integrator, event localization, residual-aware decision engine and governance certificate modules.
- Added targeted V6.4 tests for each new capability.

### Reason
- V6.4 moves V6.3 certificates toward auditable solve-loop, industrial evidence, runtime property, adaptive DAE and governance UI paths without deleting or rewriting existing functionality.

### Mathematical / Engineering Logic
- 守恒影响：small residuals can be reduced by bounded iteration; critical residuals, polymer vapor and heat-unit errors remain rejected.
- 单位影响：industrial data packages and benchmark reconciliation validate measurement units before evidence enters confidence scoring.
- residual 影响：optimizer/DOE/posterior decisions now expose a unified rejected_reason path.
- benchmark 影响：benchmark reconciliation records source type, uncertainty and normalized residuals.

### Verification
- `python -m pytest -q tests\test_nonlinear_residual_loop.py tests\test_solve_path_integrator.py tests\test_industrial_data_package.py tests\test_benchmark_reconciliation.py tests\test_property_runtime_audit.py tests\test_dynamic_adaptive_integrator.py tests\test_dynamic_event_localization.py tests\test_residual_aware_decision_engine.py tests\test_model_governance_page.py`: 10 passed.

### Remaining Risk
- The nonlinear residual loop is still a bounded integration layer; deeper recycle/flash/heat-balance solver replacement must be expanded in later iterations.

## 2026-05-19 10:03 - V6.4 update 2

### Change
- Integrated V6.4 gates into `scripts/auto_functional_audit.py`.
- Updated `scripts/release_gate.py`, `scripts/dev_tasks.py`, registries, benchmarks, README and changelog version metadata to V6.4 / 0.7.4.
- Added V6.4 report/repro artifacts for nonlinear residual loop, solve path integrator, industrial data package, benchmark reconciliation, property runtime audit, adaptive integrator, event localization, residual decision engine and governance certificate.

### Reason
- Release-gate and generated QA artifacts must verify the new V6.4 math-core capabilities instead of only importing standalone modules.

### Mathematical / Engineering Logic
- 守恒影响：V6.4 nonlinear residual loop and solve-path integrator now enter the automated audit and report/repro evidence path.
- 单位影响：industrial dataset and benchmark reconciliation unit validation now enters the gate path.
- residual 影响：residual decision engine and governance certificate become release-gated artifacts.
- benchmark 影响：benchmark reconciliation is checked with confidence/source/uncertainty metadata.

### Verification
- `python scripts\auto_functional_audit.py`: 150/150 passed after V6.4 gate integration fixes.
- `python scripts\dev_tasks.py quality-gate`: passed.
- `python scripts\release_gate.py`: passed.

### Remaining Risk
- Full regression may reveal public callable inventory or report/repro schema gaps from the new modules.

## 2026-05-19 10:04 - V6.4 update 3

### Change
- Updated `scripts/auto_functional_audit.py` to validate `residual_decision_engine_dataframe()` against the actual `uncertainty_risk_probability` output column.

### Reason
- The first V6.4 auto audit run surfaced a schema mismatch between the new residual decision engine and the audit gate.

### Mathematical / Engineering Logic
- 守恒影响：no equation or correction behavior changed.
- 单位影响：no unit conversion behavior changed.
- residual 影响：the gate now checks the residual-aware decision engine's bounded uncertainty risk probability and rejected status.
- benchmark 影响：no benchmark metadata changed.

### Verification
- `python scripts\auto_functional_audit.py`: failed before this fix with `KeyError: 'risk_probability'`; rerun passed 150/150.

### Remaining Risk
- Additional audit checks may reveal further report/repro or gate schema mismatches.

## 2026-05-19 10:05 - V6.4 update 4

### Change
- Updated `scripts/auto_functional_audit.py` to call `governance_certificate_dataframe(result)` using the implemented V6.4 API.

### Reason
- The governance certificate module builds its own residual, confidence, property and decision tables from the flowsheet result and does not accept separate keyword inputs.

### Mathematical / Engineering Logic
- 守恒影响：governance certificate now receives the full flowsheet result and can construct the matching ResidualSystem internally.
- 单位影响：no unit logic changed.
- residual 影响：governance certificate gate now uses the same residual path as report/UI governance data.
- benchmark 影响：evidence-chain scoring remains unchanged.

### Verification
- `python scripts\auto_functional_audit.py`: failed before this fix with `TypeError: unexpected keyword argument 'residual_system'`; rerun passed 150/150.

### Remaining Risk
- Report/repro export may still reveal required sheet or manifest mismatches during the next audit rerun.

## 2026-05-19 10:14 - V6.4 verification

### Change
- Refreshed generated QA documents after full V6.4 quality gate and release gate execution.

### Reason
- V6.4 acceptance requires README, CHANGELOG, V6.4 changelog, test report, quality baseline, optimization roadmap and continuous-improvement log to reflect the latest gate facts.

### Mathematical / Engineering Logic
- 守恒影响：`nonlinear_residual_loop_gate`, `solve_path_integrator_gate`, `conservation_solve_path_gate`, `residual_system_gate` and `residual_critical_gate` passed.
- 单位影响：`dimensioned_input_gate`, `unit_conversion_trace_gate`, industrial dataset unit validation and benchmark reconciliation unit checks passed.
- residual 影响：optimizer/DOE/posterior/sampling/decision-engine residual gates passed and no critical residual was accepted.
- benchmark 影响：scientific, experimental, source-registry, reconciliation and evidence-chain gates passed.

### Verification
- `python scripts\dev_tasks.py check-env`: passed.
- `python scripts\dev_tasks.py quality-gate`: passed; pytest reported 344 passed.
- `python scripts\dev_tasks.py generate-test-report`: passed.
- `python scripts\dev_tasks.py continuous-improve`: passed.
- `python scripts\release_gate.py`: passed.
- `python scripts\performance_profile.py`: passed.
- `python scripts\ui_e2e_smoke.py`: passed.
- `python scripts\ui_e2e_workflow.py`: passed.
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200 after starting Streamlit.
- Browser smoke check: local app loaded as `Metallocene EPDM Digital Twin`, navigation registered 15 pages, no browser console errors.

### Remaining Risk
- Remaining P3 work is large-file/API-compatible splitting for `parameter_estimation.py`, `reactor.py`, `flowsheet.py`, `dynamic_template_reactor.py`, `fluid_props.py`, `cfd/simple_solver.py` and `reporting/excel.py`; no P0/P1/P2 blocker remained after V6.4 gates.
