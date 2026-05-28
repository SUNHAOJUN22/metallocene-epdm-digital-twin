# V6.1 Math Core Audit

This audit covers the upgrade from V6.0 / 0.7.0 to V6.1 / 0.7.1.  The focus is deeper math-core decoupling, conservation correction certificates, calibrated-property runtime bridging, dynamic solver decision governance, residual-aware decision functions and industrial evidence-chain completeness.

## 1. Large Files With Mixed Mathematical Responsibilities

The largest compatibility-facing modules remain `epdm_sim/parameter_estimation.py`, `epdm_sim/reactor.py`, `epdm_sim/flowsheet.py`, `epdm_sim/dynamic_template_reactor.py`, `epdm_sim/fluid_props.py` and `epdm_sim/cfd/simple_solver.py`.  V6.1 does not remove these APIs.  Instead, it adds focused helper modules under `estimation`, `reactor_core`, `flowsheet_core`, `dynamic_core` and `fluid_core` so future refactors can move responsibilities without breaking existing imports.

## 2. Solver Layer: Certificate Versus Correction

V6.0 introduced solver certificates for residual norms, constraint violations and fallback reasons.  V6.1 adds `solver_core.conservation_correction` to separate small numerical closure from large physical errors.  Small mass, energy and flash split residuals can be corrected only within explicit tolerances, while large residuals and polymer vapor leakage remain critical and cannot be hidden by correction.

## 3. Calibrated Property Model Runtime Impact

Calibrated property models were already persisted and reported.  V6.1 adds `property_model_bridge` so calibrated Henry, viscosity, flash-K and heat-of-reaction factors can influence explicit runtime calculations when enabled and valid.  The default path remains `default_estimate`, and out-of-range calibrated models must warn or fall back.

## 4. Dynamic DAE / State Invariant Solver Decision

Dynamic residual feedback and state invariant checks already existed as diagnostics.  V6.1 adds `dynamic_core.solver_decision` so stiffness indicators, residual acceptance, invariant violations and event risk can contribute to BDF/RK45/explicit fallback decisions.  This is still a diagnostic and policy layer rather than a full industrial DAE integrator.

## 5. Residual-Aware Posterior, Uncertainty and DOE Decisions

V6.1 adds `residual_aware_decision` to centralize candidate rejection, residual risk, DOE scoring, posterior weighting and uncertainty risk bounding.  Residual-critical candidates are rejected or receive strong penalties, DOE scores combine residual source, identifiability, benchmark failure, validity-edge and data-lineage confidence signals, and all risk probabilities remain in `[0, 1]`.

## 6. Industrial Evidence Chain Coverage

V6.0 introduced equation, residual and data-lineage graphs.  V6.1 adds `evidence_chain` to validate that critical equations can trace to residuals, benchmarks, lineage and source references.  Missing source references reduce confidence; plant and experiment evidence remain higher weighted than literature, synthetic and regression snapshot records.

## 7. Report / Repro Evidence Chain

The V6.1 report and repro package add conservation correction, correction certificates, property model bridge, dynamic solver decision, residual-aware decision, evidence chain, evidence gaps and `V6_1_audit_summary` outputs.  Exports remain read-only and must not trigger ODE, CFD, optimizer, posterior or DOE tasks.

## 8. Remaining Benchmark Source Gaps

Several benchmarks still rely on synthetic or regression-snapshot source types.  These are acceptable for regression guarding but do not provide industrial calibration credibility.  The highest-value upgrades remain reviewed VLE, calorimetry, rheology, GPC/Mooney, flash recovery and dynamic T/P validation datasets with explicit uncertainty and validity ranges.

## 9. V6.2 Priorities

1. Move conservation correction hooks closer to the actual recycle, flash and heat-balance solve loops while preserving critical-residual rejection.
2. Expand calibrated property bridge coverage to every solubility, flash, rheology and heat-balance path that accepts property-model overrides.
3. Replace remaining governance-proxy residuals with equation-specific physical residual expressions.
4. Add plant/experiment benchmark ingestion workflow with reviewer metadata and raw-data preprocessing records.
5. Promote dynamic solver decision policies into adaptive time-step acceptance where mathematically safe.
