# V5.0 Full Audit

Version: V5.0 / 0.6.0

## Scope

This audit covers the V5.0 upgrade of `metallocene-epdm-digital-twin` from the V4.9 industrial validation baseline. The project remains a single merged workspace at `D:\codex\metallocene-epdm-digital-twin`; the archived `metallocene-epdm-process-simulator` code remains under `legacy_archive` and is not used as a second runtime entrypoint.

## Current Kernel Status

- Main entrypoint: `app.py`.
- Fast process simulation: `epdm_sim.flowsheet.run_flowsheet`, implemented as an EPDM application adapter over `epdm_sim.template_flowsheet.run_template_flowsheet`.
- Template process layer: `template_config`, `feed_adapter`, `template_flowsheet`, `kpi_adapter`.
- Dynamic reactor: `dynamic_template_reactor` with `explicit_bounded`, `solve_ivp_rk45`, and V5.0 `solve_ivp_bdf` stiff mode with state scaling and finite-difference Jacobian.
- Physical property layer: `thermo`, `eos`, `solubility`, `flash`, `rheology`, `fluid_props`, with V5.0 calibration helpers.
- Quality layer: `preflight`, `conservation`, `engineering_rules`, `model_validation`, `equation_tests`, `plot_validation`, `file_security`, `model_audit_report`.
- Reproducibility layer: `case_manager`, `audit_trail`, `repro_package`, `report`, `release_gate`.

## BDF Stiff Solver Audit

V4.9 treated BDF as an explicit technical debt item. V5.0 adds:

- `ode_scaling.estimate_state_scales()` for positive characteristic scales across moles, masses, temperature, pressure, and catalyst activity.
- `ode_jacobian.scaled_finite_difference_jacobian()` for a bounded finite-difference Jacobian in scaled coordinates.
- `dynamic_template_reactor._simulate_template_with_solve_ivp()` now uses SciPy BDF when `bdf_readiness_check()` passes. If the solver fails, the model returns an explicit bounded fallback profile with a clear `fallback_reason`.

Current risk: the BDF path is still an R&D-grade stiff integration path, not a production-grade polymerization DAE solver. Pressure control, gas-liquid transfer, and recipe events remain simplified.

## Thermodynamics and Property Calibration Audit

V5.0 introduces:

- `property_calibration.calibrate_viscosity_model()`.
- `property_calibration.calibrate_heat_release()`.
- `thermo_calibration.calibrate_henry_from_data()`.
- `thermo_calibration.calibrate_flash_k_correction()`.
- `validation_campaign.run_validation_campaign()`.

These routines do not overwrite defaults. They return fitted parameters, residuals, confidence interval proxies, validity ranges, and warnings. They are intended for experimental closure around solubility, VLE, rheology, calorimetry, and flash recovery data.

Remaining risk: the default EOS/Henry/flash/rheology parameters are still screening-level estimates unless calibrated against plant or lab data.

## Function Coverage Audit

V4.9 direct public callable coverage was 339 / 554. V5.0 adds direct tests for:

- `fluid_props`
- `conservation`
- `thermo`
- `cfd.fields`
- BDF/Jacobian helpers
- property and thermo calibration
- validation campaign
- UI E2E workflow contract

Expected result: direct reference count should increase after `scripts/function_inventory_audit.py`.

## Plot Quality Audit

V4.9 introduced plot validation. V5.0 extends report export with an `all_plot_validation` sheet. The current gate checks non-empty figures, axis labels for 2D scientific plots, and colorbar/hover unit labels for contour, heatmap, and surface figures.

Remaining risk: some schematic figures such as Sankey, 3D plant overview, and network diagrams are intentionally exempt from strict Cartesian axis-title checks. They still need hover labels and report metadata for final publication use.

## Conservation and Engineering Logic Audit

The following invariants are explicitly checked:

- Total and component mass closure.
- Reactor monomer-to-polymer closure.
- Product segment composition closure.
- Flash mass closure and polymer vapor exclusion.
- Heat release sign and conversion scaling.
- Fluid trends for solids, temperature, molecular weight, pipe diameter, and flow.
- Thermodynamic trends for Henry solubility, Wilson K values, and vapor fraction.

Remaining risk: recycle closure is still simplified relative to rigorous plant recycle convergence.

## UI and Task Governance Audit

Heavy tasks remain required to run through `TaskService` and `ui_workflow`:

- dynamic ODE
- CFD
- optimization/Pareto
- posterior sampling
- Bayesian DOE
- report/repro export

V5.0 adds `scripts/ui_e2e_workflow.py` as a non-destructive workflow smoke. It verifies page registry and action mapping without triggering heavy models.

## File and Report Audit

The file-safety gate rejects path traversal and unsafe extensions. Export metadata includes version, timestamp, config hash, template id, parameter set id, registry hashes, warnings, and not-run tasks. V5.0 keeps report export non-destructive with respect to heavy tasks.

## V5.1 Priorities

1. Replace remaining screening property defaults with calibrated per-solvent/per-catalyst parameter sets.
2. Add real plant or bench time-series datasets for dynamic ODE validation.
3. Extend BDF from ODE approximation toward DAE-ready pressure/energy control.
4. Tighten recycle convergence and purge-loss closure.
5. Add browser-level E2E with visual snapshots when Playwright is available.
6. Add experimental uncertainty propagation into report-ready confidence intervals.

## V5.0 Verification Snapshot

Recorded on 2026-05-08 Asia/Shanghai.

- `python -m py_compile ...`: passed.
- `python -m pytest -q`: 234 passed.
- `python scripts\smoke_app.py`: passed.
- `python scripts\auto_functional_audit.py`: 74/74 checks passed.
- `python scripts\function_inventory_audit.py`: 121/121 modules imported; 397/570 public callables directly referenced.
- `python scripts\ui_e2e_smoke.py`: passed.
- `python scripts\ui_e2e_workflow.py`: passed.
- `python scripts\release_gate.py`: all gates passed.
- `http://127.0.0.1:8501/`: HTTP 200.
