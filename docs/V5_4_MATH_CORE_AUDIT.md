# V5.4 Math Core Audit

## Scope

This audit covers the V5.4 upgrade path from V5.3 / 0.6.3 to V5.4 / 0.6.4.  The focus is the mathematical and chemical-engineering kernel, not UI decoration.

## 1. Bare Float Entry Points

Remaining legacy public APIs still accept bare `float` values for compatibility:

- `Flash.calculate(inlet, temperature_K, pressure_Pa)`
- `calculate_heat_balance(..., preheat_kJ_h, devol_kJ_h, sensible_heat_kJ_h)`
- `calculate_rheology(temperature_K, solids_wt, Mw, shear_rate_s, ...)`
- `calculate_fluid_properties(stream, Mw, temperature_K, pressure_Pa)`
- `calculate_pipe_hydraulics(density, viscosity, flow, length, diameter, ...)`

V5.4 adds unit-safe adapters at these entrances.  Old floats still work, but each path now declares a default unit and accepts `DimensionedValue`, `(value, unit)`, or `{"value": ..., "unit": ...}` payloads.

## 2. Residuals Feeding Optimization

V5.3 residuals were already used in audit/DOE/window filtering.  V5.4 adds `residual_objective.py`:

- `residual_objective_score`
- `residual_penalty_for_optimizer`
- `residual_filter_for_doe`
- `residual_diagnostics_dataframe`

Optimizer objectives now include residual penalty, DOE rejects failed residual payloads, and constrained windows expose residual margins.

## 3. Benchmark Status

`data/golden_benchmarks.json` remains the release-gate regression benchmark table.  V5.4 adds `data/experimental_benchmarks.json` with source type, confidence level, validity range, linked equation, linked residual and hash metadata.

Current benchmark limitations:

- Several values remain regression snapshots.
- Plant and literature records are metadata placeholders until raw datasets are imported.
- Confidence scoring is audit-level, not industrial statistical validation.

## 4. Dynamic ODE Residuals

V5.4 adds profile-level residual diagnostics:

- finite state residual
- polymer mass monotonic residual
- quench reaction residual
- heat generation sign residual
- pressure positivity residual

These are post-solve profile residuals.  V5.5 should bind accumulation residuals directly to RHS step terms.

## 5. Fallback Diagnostics

Fallbacks are now visible in:

- ODE solver summary
- `fallback_diagnostics` report sheet
- phase-equilibrium constraint rows
- repro package metadata

Remaining gap: BDF fallback still needs deeper sparse-Jacobian diagnostics for stiff industrial recipes.

## 6. Thermo/Rheology/Heat Model Fidelity

The thermo and transport cores are still R&D screening models:

- Wilson/PR/SRK K-values are trend checks, not plant VLE regression.
- Henry solubility is monotonic and bounded, not fitted to local solvent/comonomer data.
- Carreau/PowerLaw rheology is empirical and needs measured viscosity curves.
- Heat balance uses template deltaH and screening UA assumptions.

## 7. V5.5 Priorities

1. Replace more regression snapshots with measured VLE, solubility, rheology, calorimetry, GPC and Mooney data.
2. Bind dynamic residuals to RHS accumulation terms and event handling.
3. Add residual-aware posterior acceptance and parameter-estimation penalties.
4. Expand phase-equilibrium constraints across pressure/temperature grids.
5. Split large legacy files only after behavior remains protected by tests.

