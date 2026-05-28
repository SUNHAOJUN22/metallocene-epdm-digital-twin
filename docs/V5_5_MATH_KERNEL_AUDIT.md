# V5.5 Math Kernel Audit

## Scope

This audit covers the V5.5 upgrade from V5.4 / 0.6.4 to V5.5 / 0.6.5.  The focus is residual-driven closure, RHS-residual coupling, benchmark calibration, and API-compatible splitting of large mathematical modules.

## Large Modules With Mixed Responsibilities

- `epdm_sim/parameter_estimation.py`: still contains data residuals, objectives, optimization orchestration and reporting helpers.  V5.5 adds `epdm_sim/estimation/` helpers, but full migration remains V5.6 work.
- `epdm_sim/reactor.py`: still mixes EPDM compatibility, kinetics, material balance and product outputs.  V5.5 adds `epdm_sim/reactor_core/` helpers.
- `epdm_sim/flowsheet.py`: still owns default EPDM process sequencing.  V5.5 adds `epdm_sim/flowsheet_core/` wrappers for feed, sequence, recycle, KPI and residual builders.
- `epdm_sim/dynamic_template_reactor.py`: still contains solver driver, explicit fallback and profile construction.  V5.5 adds `epdm_sim/dynamic_core/` RHS/residual coupling helpers.
- `epdm_sim/fluid_props.py`: still combines density, heat capacity, viscosity and hydraulics.  V5.5 adds `epdm_sim/fluid_core/` wrappers.
- `epdm_sim/cfd/simple_solver.py`: remains a compact screening CFD solver; future split should separate mesh, numerical solve, diagnostics and field assembly.

## Residual Feedback Into Solving And Optimization

V5.4 residuals already influenced DOE/optimizer filtering through `residual_objective.py`.  V5.5 adds `residual_solver.py` with bounded correction and rejection helpers:

- recycle tear closure;
- flash mass closure;
- heat-balance reporting closure;
- residual acceptance summary;
- correction trace DataFrame.

Residual corrections are intentionally bounded.  If correction magnitude exceeds the threshold, the result is marked `error` or `critical` and must not be hidden as numerical cleanup.

## Unit Context And Naked Float Risk

Core unit-safe adapters already exist in `dimensioned.py`.  Remaining naked-float risks are mostly legacy public APIs where the default unit is implicit for backward compatibility:

- process config scalar fields;
- legacy `run_flowsheet()` EPDM adapter;
- compact CFD input constructors;
- empirical property model helper functions.

V5.5 keeps backward compatibility but continues exporting `unit_conversion_trace` and direct tests for MPa/Pa, C/K, cP/Pa.s and kJ/h/kW equivalence.

## Benchmark Calibration Gaps

`experimental_benchmarks.json` contains source-type metadata and confidence levels, but several records are still synthetic or regression-style placeholders.  V5.5 adds benchmark calibration scoring and data-gap recommendations.  Highest-value next datasets:

1. VLE / flash recovery data for C2/C3/H2/ENB/solvent;
2. reaction calorimetry and cooling-duty data;
3. solution rheology vs solids/Mw/shear/T;
4. GPC/Mooney endpoint validation;
5. semi-batch dynamic T/P/Q profiles.

## Dynamic ODE RHS-Residual Binding

V5.5 adds RHS term diagnostics with:

- `term_id`;
- `affected_state`;
- `value`;
- `unit`;
- `sign_convention`;
- `physical_meaning`;
- `source_equation_id`;
- `residual_id`.

The current coupling is profile-level and RHS-term-level.  V5.6 should push accumulation residual calculation into every accepted solver step.

## Optimizer, DOE And Posterior Residual Constraints

The optimizer, DOE and constrained-window paths already reject or penalize critical residuals.  V5.5 adds a residual-aware parameter objective helper and posterior residual-acceptance gate.  Full posterior sample rejection against step-level residuals remains a V5.6 priority.

## Report And Repro Audit Coverage

V5.5 report exports add:

- `residual_solver`;
- `residual_correction_trace`;
- `rhs_term_diagnostics`;
- `benchmark_calibration`;
- `benchmark_data_gaps`;
- `posterior_residual_acceptance`;
- `uncertainty_residual_risk`;
- `dynamic_residual_timeseries`.

Repro packages add benchmark residual and unit/residual traces without rerunning heavy tasks.

## V5.6 Priorities

1. Migrate implementation logic from large legacy files into the V5.5 core helper packages.
2. Couple dynamic residual calculations directly to solver step acceptance.
3. Extend residual solver from bounded correction to optional constrained least-squares closure.
4. Replace synthetic benchmark placeholders with real experimental/plant data.
5. Add posterior sample rejection based on residual criticality and benchmark validity.
