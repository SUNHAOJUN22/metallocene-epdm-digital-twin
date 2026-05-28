# V5.3 Math Kernel Roadmap

## Current V5.3 Focus

V5.3 upgrades the project from V5.2 math-core reporting into equation-driven physical constraints:

- Unit-aware adapters are available for core scalar inputs.
- ResidualSystem includes critical severity and acceptance logic.
- Equation bindings include implementation functions, benchmark ids, dimensional signatures and residual ids.
- RHS diagnostics expose physical terms with units and finite checks.
- Thermodynamic and transport physical-constraint tables are reportable.
- DOE and constrained windows filter candidates with failed residual-system acceptance.

## Core Functions Still Receiving Bare Floats

The following paths remain compatible with legacy float inputs and should be migrated gradually rather than rewritten blindly:

- `flash.Flash.calculate(temperature_K, pressure_Pa)`
- `heat_balance.calculate_heat_balance(...)`
- `rheology.calculate_rheology(temperature_K, solids_wt, Mw, shear_rate_s)`
- `fluid_props.calculate_pipe_hydraulics(...)`
- `optimizer` and `pareto` bound payloads

V5.3 adds adapters so callers can pass `(value, unit)` or `DimensionedValue` in new tests, while preserving old APIs.

## Equation Binding Gaps

Critical equations are bound through `epdm_sim/equation_binding.py`. Registry records now carry:

- `implementation_function`
- `input_units`
- `output_unit`
- `dimensional_signature`
- `expected_trends`
- `benchmark_id`
- `fallback_policy`
- `residual_id`

Remaining V5.4 work is to make every noncritical registry formula equally executable.

## Residual Closure Status

ResidualSystem currently covers:

- total mass balance
- flash phase mass proxy
- polymer pseudo vapor = 0
- monomer-to-polymer mass
- product composition closure
- heat release proxy
- dynamic finite/monotonic accumulation proxy

V5.4 should split residual diagnostics by reactor, flash1, flash2, recycle, product and dynamic state equations.

## Fallback Diagnostics

Fallbacks remain acceptable only when explicit:

- BDF can fallback to explicit bounded mode with reason.
- EOS/flash fallback must be reflected in thermo/flash diagnostics.
- Report export must write `not_run` instead of triggering heavy tasks.
- Failed model runs in fitting/posterior must return finite penalties.

## Benchmark Status

`data/golden_benchmarks.json` is versioned to `V5.3 / 0.6.3` and now records `residual_id` and `expected_output` fields. Some records remain regression snapshots, not independently reviewed physical standards.

## V5.4 Priorities

1. Replace more regression-snapshot benchmarks with experimental/literature reference cases.
2. Carry DimensionedValue metadata through intermediate calculations, not only function boundaries.
3. Add sparse/analytic Jacobian support for stiff dynamic ODE.
4. Expose residual critical/warning sources in the Streamlit diagnostic panels.
5. Add calibrated property/thermo/kinetic datasets to close the validation loop.
