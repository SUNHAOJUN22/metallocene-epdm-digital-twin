# V5.1 Full Audit

Version: V5.1 / 0.6.1

## Scope

This audit covers the V5.1 upgrade from V5.0.  The project remains a single
local Streamlit/Python workspace at `D:\codex\metallocene-epdm-digital-twin`.
The archived legacy simulator remains under `legacy_archive` and is not a
runtime entrypoint.

## Direct Coverage Gaps

V5.0 reported 397/570 public callables directly referenced by tests or audit
scripts.  V5.1 adds true-call tests for `fluid_props`, `flowsheet`,
`parameter_estimation`, `recipe`, `dimensional_checks`, `bayesian_doe`,
`constrained_window`, `digital_twin_3d`, `posterior`, `reactor`, `rheology`,
and `sensitivity`.  The V5.1 gate requires at least 450 direct references.

## Large Modules And Complexity

The largest files remain `report.py`, `parameter_estimation.py`, `flowsheet.py`,
`reactor.py`, `dynamic_template_reactor.py`, and `cfd/simple_solver.py`.
V5.1 keeps API compatibility and adds report-consistency and performance gates
before deeper V5.2 refactoring into `reporting/` and `estimation/` packages.

## Scientific Benchmark Closure

`data/golden_benchmarks.json` now records input, expected output, unit,
tolerance, model version, equation id, validity range, and rationale.  The
benchmark set covers EPDM flowsheet KPIs, generic template flowsheet, flash,
Rachford-Rice, Henry solubility, PR EOS K-value, rheology, pressure drop, heat
release, dynamic ODE smoke, CFD diagnostics, model audit score, constrained
windows, and Bayesian DOE ranking.

## Validity Envelope And Extrapolation Risk

V5.1 adds `epdm_sim.validity_envelope`, which combines registry, reaction
template, and property-source ranges to classify inputs as inside, near edge,
outside, or unknown.  These checks are exported to Excel and lower confidence
when users operate outside the screening range.

## UI E2E Coverage

The UI E2E layer remains intentionally non-destructive.  It verifies Streamlit
HTTP accessibility, page registry, workflow wizard/report page availability,
manual action mapping, and that page switching does not trigger heavy tasks.
Full Playwright click-through remains a V5.2+ option.

## Report And Repro Consistency

V5.1 adds `epdm_sim.report_consistency`, required Excel sheet checks,
export-metadata checks, heavy-task non-trigger contracts, and new report sheets:
`validity_envelope`, `performance_profile`, `report_consistency`, and
`calibration_scores`.

## Calibration Loop Gaps

Property and thermo calibration now persist dataset id, data hash, confidence
intervals, residuals, MAE/RMSE/R2, validity ranges, warnings, and creation time.
The model audit card exposes kinetic/property/thermo/validation score proxies.
These remain R&D calibration utilities until larger plant datasets are supplied.

## Numerical And Chemical Engineering Risk Points

- BDF ODE support still has explicit fallback for difficult cases; this is
  acceptable if the fallback reason is reported.
- PR/SRK EOS and Henry solubility are screening models and require VLE or
  solubility calibration for design use.
- Rheology and fouling predictions are trend models and require local gel
  solution viscosity data.
- Report export remains read-only with respect to heavy ODE/CFD/optimization.

## V5.2 Priorities

1. Split `report.py` into `epdm_sim/reporting/` while preserving imports.
2. Split `parameter_estimation.py` into objective/residual/confidence modules.
3. Add optional Playwright-driven UI workflow with guarded non-heavy clicks.
4. Expand validation datasets with real endpoint and time-series experiments.
5. Add performance thresholds to the release gate once baseline variance is
   known on the target workstation.
