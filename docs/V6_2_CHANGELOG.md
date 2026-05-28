# V6.2 Changelog

## 2026-05-18 11:20 - V6.2 update 1

### Change
- Added `epdm_sim/solver_core/conservation_solve_path.py`.
- Added `epdm_sim/property_model_runtime.py`.
- Added `epdm_sim/dynamic_core/step_acceptance.py`.
- Added `epdm_sim/dynamic_core/solver_policy.py`.
- Added `epdm_sim/residual_aware_optimizer.py`.
- Added `epdm_sim/residual_aware_doe.py`.
- Added `epdm_sim/evidence_chain_score.py`.
- Added `tests/test_v6_2_math_core.py`.

### Reason
- V6.2 moves V6.1 governance from certificate/report tables toward explicit solve-path, runtime property-model, solver-policy, residual-aware optimizer/DOE and evidence-chain scoring APIs.

### Mathematical / Engineering Logic
- 守恒影响：small mass/energy/flash residuals can be closed only within tolerances; large residuals and polymer vapor remain critical.
- 单位影响：new runtime paths preserve explicit property units (`mol/L`, `Pa.s`, `kJ/h`, dimensionless K values).
- residual 影响：optimizer/DOE scoring now has explicit residual rejection and bounded risk paths.
- benchmark 影响：evidence scoring keeps source-type confidence and evidence gaps visible.

### Verification
- Targeted V6.2 tests pending at this log point.

### Remaining Risk
- The new solve path is still an explicit correction/acceptance layer; it does not replace every legacy nonlinear solve loop.

## 2026-05-18 11:25 - V6.2 update 2

### Change
- Updated `tests/test_v6_2_math_core.py` dynamic policy test to use the existing `simulate_template_semibatch_ode(total_time_min, dt_min)` API.

### Reason
- The first targeted V6.2 test run exposed a test-call mismatch: the dynamic reactor API does not accept `n_steps`.

### Mathematical / Engineering Logic
- 守恒影响：no model logic changed.
- 单位影响：no unit behavior changed.
- residual 影响：dynamic residual and step-acceptance test now exercises the real supported ODE time grid inputs.
- benchmark 影响：no benchmark target values changed.

### Verification
- `python -m pytest -q tests/test_v6_2_math_core.py`: 4 passed, 1 failed before this correction; rerun pending.

### Remaining Risk
- Full V6.2 quality gate verification is still pending.

## 2026-05-18 11:40 - V6.2 update 3

### Change
- Integrated V6.2 artifacts into Excel report export, report consistency checks and repro package export.
- Updated V6.2 manifest/export versions and test version expectations.

### Reason
- V6.2 requires conservation solve path, property runtime, dynamic solver policy, residual-aware optimizer/DOE and evidence-chain score to be audit-exported without triggering heavy tasks.

### Mathematical / Engineering Logic
- 守恒影响：`conservation_solve_path` and `conservation_solve_cert` sheets expose correction acceptance and rejection evidence.
- 单位影响：`property_model_runtime` exports property units and provenance for calibrated/default runtime values.
- residual 影响：`residual_aware_optimizer`, `residual_aware_doe`, dynamic policy and step acceptance artifacts are exported.
- benchmark 影响：`evidence_chain_score` and `evidence_gap_priority` make benchmark/source gaps visible in reports and repro packages.

### Verification
- `python -m pytest -q tests/test_v6_2_math_core.py`: 5 passed.
- `python -m pytest -q tests/test_v6_2_math_core.py tests/test_report_consistency.py tests/test_repro_package.py tests/test_audit_trail.py`: 8 passed.

### Remaining Risk
- Full release gate verification is still pending.

## 2026-05-18 12:05 - V6.2 update 4

### Change
- Updated `README.md` to V6.2 / 0.7.2.
- Updated `CHANGELOG.md` with the V6.2 release section.
- Added V6.2 static-contract expectations for report/repro audit artifacts and release gates.

### Reason
- V6.2 release gate requires README, registry versions, benchmark versions and changelog files to agree before the final full-quality verification can be trusted.

### Mathematical / Engineering Logic
- 守恒影响：documentation now describes conservation solve path as bounded correction/acceptance, not a replacement for full nonlinear equation-oriented solving.
- 单位影响：documentation keeps explicit unit/validity requirements for runtime calibrated property models.
- residual 影响：documentation states that residual-critical and outside-validity optimizer/DOE candidates must be rejected.
- benchmark 影响：documentation records evidence-chain score and data-gap priorities for benchmark/source confidence governance.

### Verification
- `python -m pytest -q tests/test_v6_2_math_core.py tests/test_report_consistency.py tests/test_repro_package.py tests/test_audit_trail.py`: passed before this documentation update.
- Full V6.2 quality gate verification pending.

### Remaining Risk
- Full release gate and UI smoke/workflow verification still need to be rerun after all documentation refreshes.

## 2026-05-18 15:38 - V6.2 update 5

### Change
- Refreshed `docs/TEST_REPORT.md`, `docs/QUALITY_BASELINE.md`, `docs/OPTIMIZATION_ROADMAP.md`, `docs/CONTINUOUS_IMPROVEMENT_LOG.md`, `tmp_smoke_outputs/release_gate_summary.json`, `tmp_smoke_outputs/performance_profile.csv` and `tmp_smoke_outputs/function_matrix.csv`.
- Verified V6.2 release gates after code, report, repro, registry and documentation updates.

### Reason
- V6.2 requires every新增内核能力 to be backed by reproducible gate output and Markdown release evidence.

### Mathematical / Engineering Logic
- 守恒影响：`conservation_solve_path_gate` passed with 11 rows; small residual closure remains bounded and critical residuals remain rejected.
- 单位影响：`dimensioned_input_gate`, `unit_conversion_trace_gate` and `property_model_runtime_gate` passed.
- residual 影响：`residual_aware_optimizer_gate`, `residual_aware_doe_v6_2_gate`, `dynamic_step_acceptance_gate` and `dynamic_solver_policy_gate` passed.
- benchmark 影响：`benchmark_acceptance_gate`, `experimental_benchmark_gate`, `benchmark_source_registry_gate` and `evidence_chain_score_gate` passed.

### Verification
- `python -m pytest -q`: 328 passed.
- `python scripts\\dev_tasks.py check-env`: passed.
- `python scripts\\dev_tasks.py quality-gate`: passed all gates.
- `python scripts\\dev_tasks.py generate-test-report`: passed, docs refreshed.
- `python scripts\\dev_tasks.py continuous-improve`: passed, latest callable direct coverage 902/902.
- `python scripts\\release_gate.py`: passed all gates.
- `python scripts\\performance_profile.py`: passed; report export, flowsheet, dynamic, CFD and cache profile generated.
- `python scripts\\ui_e2e_smoke.py`: passed, HTTP 200.
- `python scripts\\ui_e2e_workflow.py`: passed, manual heavy actions mapped and exports non-heavy.
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP_STATUS=200.

### Remaining Risk
- No P0/P1/P2 release blockers remain. Main residual risk is model fidelity: calibrated property/runtime evidence still needs more plant, experiment and literature datasets for industrial design accuracy.
