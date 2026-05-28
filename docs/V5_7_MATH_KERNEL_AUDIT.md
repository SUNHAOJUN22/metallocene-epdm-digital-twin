# V5.7 Math Kernel Audit

This audit covers the V5.7 upgrade from V5.6 / 0.6.6 to V5.7 / 0.6.7.  The focus is equation-residual-code coupling, residual acceptance, dynamic proof-style stability checks, benchmark source registry, calibrated property usage and layered math/solver core separation.

## 1. Large Modules With Mixed Mathematical Responsibilities

The following files remain intentionally API-compatible large entry points: `parameter_estimation.py`, `reactor.py`, `flowsheet.py`, `dynamic_template_reactor.py`, `fluid_props.py` and `cfd/simple_solver.py`.  V5.7 adds `math_core/` and `solver_core/` to isolate acceptance, diagnostics, bounded updates, residual projection and fallback policy without breaking those imports.  Full migration should continue incrementally.

## 2. Equations With Trend Checks But Limited Residual Coupling

V5.6 already had equation bindings and reverse checks.  V5.7 adds `equation_residual_coupling.py`, which requires every registered equation row to expose an implementation function, benchmark id, residual id and dimensional signature.  The remaining limitation is depth: some residual ids are governance-level proxies rather than first-principles per-term residual equations.

## 3. Residual Feedback Into Optimizer / DOE / Posterior

`ResidualSystem` already blocks critical DOE/window candidates and penalizes objectives.  V5.7 adds `residual_acceptance.py` to provide one acceptance table for calibration, optimizer, DOE, posterior and uncertainty consumers.  Remaining work is to embed these records deeper into every optimizer objective evaluation rather than only release-gate and helper paths.

## 4. Benchmark Source And Uncertainty Gaps

`data/benchmark_sources.json` now records source type, source reference, measurement unit, uncertainty, validity range, confidence level, data hash and review status.  Plant and experiment references remain metadata placeholders; real raw plant historian, ELN/LIMS and laboratory files are still not bundled.

## 5. Calibration Data Lineage

Benchmark and calibration lineage are exported in reports and repro packages.  Calibrated property models include dataset id, data hash, source type, validity range, uncertainty and confidence.  Remaining gap: calibrated property usage is a selector/helper path and still needs broader direct integration into solubility, flash, rheology and heat-balance runtime parameter dispatch.

## 6. ODE Residuals And Solver Decisions

V5.6 added residual feedback.  V5.7 adds proof-style dynamic stability checks for finite states, nonnegative T/P/polymer, nondecreasing polymer/segments, residual feedback and stiffness indicator.  Remaining gap: BDF/RK fallback should eventually use step-level residual severity as a native solver decision input, not only a post-run diagnostic.

## 7. Report/Repro Audit Consistency

Excel reports and repro packages now include equation-residual coupling, residual acceptance, dynamic stability checks, benchmark source/lineage and calibrated property usage.  Export remains read-only and must not trigger ODE/CFD/optimizer/posterior/DOE.

## 8. V5.8 Priorities

1. Push `math_core.acceptance` directly into optimizer, DOE and posterior runtime loops.
2. Route calibrated Henry / viscosity / flash-K / deltaH models into solubility, flash, rheology and heat-balance model selection.
3. Replace metadata-only plant benchmarks with raw measured datasets and preprocessing lineage.
4. Make dynamic residual feedback part of the BDF/RK solver fallback decision instead of only release diagnostics.
5. Continue splitting large entry-point modules after coverage remains at 100%.
