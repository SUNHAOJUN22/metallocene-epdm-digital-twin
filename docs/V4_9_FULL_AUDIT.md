# V4.9 Full Audit

Audit date: 2026-05-08 Asia/Shanghai

Project: `metallocene-epdm-digital-twin`

Version: V4.9 / 0.5.6

## 1. Scope

V4.9 audits the V4.8 template-native EPDM/EPM and generic solution-polymerization digital twin, with emphasis on release-grade quality gates, direct callable coverage, plot-unit validation, file safety, ODE BDF technical-debt tracking, and scientific benchmark regression.

Reviewed areas:

- `app.py`, Streamlit page registry and service layer.
- `epdm_sim/` scientific modules: flowsheet, template flowsheet, kinetics, reactor, dynamic template reactor, thermodynamics, EOS, flash, rheology, CFD, optimization, posterior, DOE, audit and report.
- `data/` registries: model registry, equation registry, reaction templates and golden benchmarks.
- `scripts/` smoke, functional audit, inventory audit and release gate.
- `tests/` direct unit tests, science tests and quality gate tests.
- `legacy_archive/` physically merged simulator archive; kept read-only for provenance.

## 2. Public Callable Coverage Gap

The V4.8 inventory identified these modules as the largest direct-reference gaps:

| Module | Gap in V4.8 | V4.9 action |
|---|---:|---|
| `epdm_sim.fluid_props` | 13 | Added direct rheology/hydraulics/property tests. |
| `epdm_sim.equipment_3d` | 12 | Added direct Plotly primitive tests. |
| `epdm_sim.utils` | 10 | Added direct numerical helper tests. |
| `epdm_sim.ui_theme` | 7 | Added CSS/status helper tests. |
| `epdm_sim.kinetics` | 6 | Added direct kinetics/template rate tests. |
| `epdm_sim.solubility` | 6 | Added Henry/direct table tests. |
| `epdm_sim.template_flowsheet` | 6 | Added EPDM/generic direct flowsheet tests. |
| `epdm_sim.plotting` | 5 | Added plot-unit validation tests. |
| `epdm_sim.services.cache_keys` | 5 | Added stable/sensitive hash tests. |
| `epdm_sim.services.simulation_service` | 5 | Added cache/stale service tests. |

The inventory audit remains a prioritization tool rather than a line-coverage metric. V4.9 increases callable direct references without weakening physics, conservation or UI task checks.

## 3. High and Medium Risk Callable Areas

High/medium risk areas in the function matrix remain:

- Scientific kernels: kinetics, flash, EOS, Henry solubility, rheology, heat release and dynamic reactor RHS.
- Heavy task pathways: dynamic ODE, CFD, posterior, DOE, optimization, report/repro export.
- File flows: experiment import, report export, repro-package zip export, OpenFOAM/VTK export.
- UI task governance: manual actions must remain routed through `TaskService` and not run on page switch.

V4.9 adds direct tests, plot validation, file safety and release gate scripts to reduce release risk.

## 4. UI E2E Coverage Gap

V4.8 had browser smoke and HTTP 200 checks, but no scriptable UI contract. V4.9 adds `scripts/ui_e2e_smoke.py` and `tests/test_ui_e2e_static_contract.py`.

The UI E2E smoke is intentionally non-destructive:

- Verifies app HTTP entry.
- Verifies key text and page registry terms are present.
- Verifies manual heavy actions are registered but not auto-triggered.
- Does not click ODE, CFD, posterior, DOE, optimization or export heavy actions.

## 5. Plot Units and Scientific Visualization Gap

V4.9 adds `epdm_sim/plot_validation.py`.

Checks:

- Plotly figure has non-empty data.
- Numeric x/y axes have titles for cartesian charts.
- Composition/conversion charts contain `%` or `wt%`.
- Temperature charts contain `°C` or `K`.
- Pressure charts contain `Pa`, `kPa` or `MPa`.
- Viscosity charts contain `Pa.s` or `Pa·s`.
- Heat-duty charts contain `kW`.
- Contour/surface/heatmap plots expose colorbar/hover labels when applicable.

3D industrial schematics and Sankey figures are checked for non-empty figure data and are exempt from conventional cartesian axis-title rules.

## 6. File Import/Export Safety Gap

V4.9 adds `epdm_sim/file_security.py`.

Checks:

- Reject path traversal and absolute-path escape outside a declared base directory.
- Validate safe filenames.
- Validate upload/export extensions.
- Validate maximum file size.
- Generate export metadata with version, timestamp, config hash, parameter set, template, registry hashes, warnings and unrun heavy tasks.

Report and repro-package exports now include explicit metadata objects without triggering hidden heavy computations.

## 7. BDF solve_ivp Technical Debt

V4.8 intentionally falls back from `solve_ivp_bdf` to `explicit_bounded` to avoid hanging automatic audits. V4.9 does not claim industrial stiff integration readiness. Instead it adds `epdm_sim/ode_scaling.py`:

- State-vector scaling and unscaling.
- Positive finite scale estimation.
- BDF readiness check returning `ready`, `fallback_recommended` and reason.

Current status: BDF readiness is auditable, but the release path still treats BDF as a controlled fallback unless the state scale and recipe are suitable.

## 8. Scientific Benchmark and Property Invariants

V4.9 adds `data/golden_benchmarks.json` and `epdm_sim/scientific_benchmarks.py`.

Benchmarks include:

- Default EPDM polymer production and composition closure.
- Generic template polymer production.
- Flash vapor fraction and Rachford-Rice standard case.
- Henry pressure response.
- Rheology viscosity positivity.
- Heat duty.
- Dynamic template reactor final rate snapshot.
- CFD dead-zone fraction boundedness.

Property invariants include:

- Conversion, vapor fraction and risk probabilities bounded.
- Composition closure near 100 wt%.
- kg/h to mol/h roundtrip.
- Celsius/Kelvin and MPa/Pa roundtrip.
- Density, Cp, conductivity and viscosity positive.

These are release regression checks. They are not industrial calibration references.

## 9. File and Report Metadata

V4.9 report and repro-package exports include:

- `export_metadata`
- model/equation registry hashes where available
- missing heavy task list
- warnings
- software version and generation timestamp

Excel reports include `plot_validation` and `export_metadata` sheets.

## 10. Release Gate

V4.9 adds `scripts/release_gate.py`.

The release gate executes:

1. Python compilation.
2. Full `pytest -q`.
3. `scripts/smoke_app.py`.
4. `scripts/auto_functional_audit.py`.
5. `scripts/function_inventory_audit.py`.
6. `scripts/ui_e2e_smoke.py`.
7. Static artifact checks.

Outputs:

- `tmp_smoke_outputs/release_gate_summary.json`
- `tmp_smoke_outputs/release_gate_summary.csv`

Any failed gate exits non-zero.

## 11. Numerical and Chemical-Engineering Risk Review

Current V4.9 risk areas:

- Dynamic kLa, UA and pressure dynamics remain R&D proxies.
- Cubic EOS implementation is a local screening enhancement, not a rigorous phase-equilibrium package.
- Generic template calculations are apparent models and need experimental calibration before quantitative use.
- CFD fields remain finite-volume-style visualization and diagnostics, not a verified CFD solver.
- Surrogate models are screening tools and must be checked by real flowsheet/dynamic models before use.

Mitigations:

- Preflight, conservation, engineering rules, equation-code consistency, plot validation, file security, model audit and release gate.

## 12. V5.0 Priorities

Recommended V5.0 work:

1. Replace BDF fallback with scaled stiff ODE integration and event handling for validated recipes.
2. Add a rigorous optional VLE/solubility data calibration workflow.
3. Add real UI E2E via Playwright when a stable browser test runtime is available.
4. Add coverage reporting and mutation-style checks for critical scientific invariants.
5. Convert plot-unit validation into a report quality gate for every generated figure.
6. Expand property-source confidence with laboratory-calibrated rheology and calorimetry datasets.

## 13. Final V4.9 Gate Snapshot

Final local verification on 2026-05-08:

- `pytest -q`: 212 passed.
- `auto_functional_audit`: 74/74 checks passed.
- `function_inventory_audit`: 117/117 modules imported; 339/554 public callables directly referenced.
- `release_gate.py`: all gates passed.
- HTTP entry: 200.
- In-app browser smoke: title present, temperature/pressure controls visible, console errors/warnings = 0.

Current largest direct-reference gaps after V4.9:

| Module | Uncovered public callables |
|---|---:|
| `epdm_sim.fluid_props` | 10 |
| `epdm_sim.conservation` | 6 |
| `epdm_sim.utils` | 5 |
| `epdm_sim.plotting` | 5 |
| `epdm_sim.polymer_props` | 5 |
| `epdm_sim.thermo` | 5 |
| `epdm_sim.ui_theme` | 5 |
| `epdm_sim.cfd.fields` | 4 |

These gaps are not release blockers because full module import, functional audits, conservation/trend checks, scientific benchmarks and release gates passed. They should guide V5.0 direct-callable coverage work.
