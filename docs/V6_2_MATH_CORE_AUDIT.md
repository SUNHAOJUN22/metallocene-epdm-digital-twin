# V6.2 Math Core Audit

This audit covers the upgrade from V6.1 / 0.7.1 to V6.2 / 0.7.2.  The focus is moving correction, calibrated-property, dynamic-solver and residual-aware decision logic closer to explicit calculation paths while preserving the existing Streamlit workflows and legacy public APIs.

## 1. Conservation Correction Still Outside Full Nonlinear Solve

V6.1 correction certificates were primarily report and gate artifacts.  V6.2 adds `solver_core.conservation_solve_path` so small mass, energy, flash and recycle residuals can be evaluated as a solve-path certificate.  It still does not replace every recycle/flash nonlinear solve loop.  Large corrections, heat-duty sign/unit mistakes and polymer vapor remain critical and are not hidden by projection.

## 2. Calibrated Property Runtime Impact

V6.1 property bridge demonstrated calibrated/default value provenance.  V6.2 adds `property_model_runtime` for runtime Henry Cstar, rheology viscosity, flash K correction and deltaH/heat-release effects.  Default estimates remain the standard path unless calibrated models are explicitly enabled and inside validity range.

## 3. Dynamic Solver Decision Versus Step Acceptance

V6.1 dynamic solver decision was a diagnostic table.  V6.2 adds `dynamic_core.step_acceptance` and `dynamic_core.solver_policy` so stiffness, residual acceptance, state invariant and event-risk signals produce an auditable solver policy and step acceptance table.  This remains a policy layer, not a full industrial DAE solver.

## 4. Residual-Aware Optimizer / DOE Coverage

Residual acceptance already gated several wrapper paths.  V6.2 adds `residual_aware_optimizer` and `residual_aware_doe` to expose objective penalties, candidate rejection, validity rejection and DOE prioritization.  Remaining work is to thread these helpers through every internal optimizer objective evaluation.

## 5. Benchmark Source and Evidence Gaps

Evidence-chain completeness is available, but benchmark source quality still depends on local JSON metadata.  V6.2 adds `evidence_chain_score` and prioritized evidence gaps, including plant mass-balance reconciliation, but real plant/experiment/literature packages remain the main V6.3 data-quality priority.

## 6. Report / Repro Chain Completeness

V6.2 report and repro artifacts add conservation solve path, property runtime, dynamic solver policy, step acceptance, residual-aware optimizer/DOE, evidence-chain score and evidence-gap priority.  Exports remain read-only and must not trigger ODE, CFD, optimizer, posterior, DOE or uncertainty tasks.

## 7. Large Modules

The main large API-compatible modules remain `flowsheet.py`, `reactor.py`, `parameter_estimation.py`, `dynamic_template_reactor.py`, `fluid_props.py`, `cfd/simple_solver.py` and `reporting/excel.py`.  V6.2 continues additive helper extraction.  V6.3 should split only when behavior is already protected by direct tests and release gates.

## 8. V6.3 Priorities

1. Thread conservation solve-path certificates into recycle, flash and heat-balance solve loops instead of only report/gate generation.
2. Add reviewed plant/experiment/literature benchmark packages with raw-data preprocessing records and reviewer metadata.
3. Expand calibrated property runtime overrides into every property-dependent main-flow calculation path.
4. Use dynamic step acceptance to drive adaptive step-size rejection where mathematically safe.
5. Replace remaining proxy residuals with first-principles equation-specific residual equations.
