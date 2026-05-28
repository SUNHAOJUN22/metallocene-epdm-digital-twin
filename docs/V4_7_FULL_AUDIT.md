# V4.7 Full Audit

## Scope

This audit covers the V4.6 code base before the V4.7 upgrade and records the
changes made for the V4.7 template-main-flowsheet release.

## Current Project Structure

- Main project: `D:\codex\metallocene-epdm-digital-twin`
- Legacy physical merge: `legacy_archive\metallocene-epdm-process-simulator`
- Main app entry: `app.py`
- Model kernel: `epdm_sim`
- Streamlit pages: `epdm_sim/pages`
- Task/cache services: `epdm_sim/services`
- Tests: `tests`

## EPDM Hard-Coding Before V4.7

- `flowsheet.ProcessConfig` still exposes EPDM application fields:
  `ethylene_kg_h`, `propylene_kg_h`, `enb_kg_h`, `hydrogen_g_h`.
- `build_feed_stream()` builds an EPDM-specific feed stream.
- `run_flowsheet()` reports EPDM application KPIs such as `C2_wt`, `C3_wt`,
  `ENB_wt`, `C2_conversion_pct`, `ENB_conversion_pct` and Vistalon-like grade
  matching.
- UI pages still show EPDM shortcut inputs, which is acceptable for the EPDM
  application adapter but not for the generic model kernel.

## V4.7 Generalization Work

- Added `TemplateProcessConfig` and `feed_adapter` so model kernels can consume
  `monomer_feeds_kg_h` and `chain_transfer_feeds` dictionaries.
- Added `template_flowsheet` as the template-aware process contract.
  EPDM delegates to the validated legacy flowsheet; generic templates run a
  lightweight apparent polymerization path with explicit segment/mass closure.
- Added `solve_ivp` mode probe and event log support in
  `dynamic_template_reactor`. The explicit bounded integrator remains the
  fallback for speed and reliability.
- Added equation-code consistency checks for Arrhenius, ENB pressure factor,
  hydrogen chain transfer, reaction heat, Wilson K, Rachford-Rice, Henry
  solubility, viscosity, Darcy-Weisbach pressure drop, Fox Tg and grade score.
- Added lightweight posterior sampling, constrained process windows, audit
  trail records, workflow wizard metadata and CFD grid-convergence diagnostics.

## Dynamic Reactor Gap

`dynamic_template_reactor.py` is now template-aware and exposes solve_ivp modes,
but the detailed physical integration still uses the bounded explicit profile
as the reliable R&D baseline. `solve_ivp` is used as a local solver capability
probe and future integration hook. V4.8 should move the full state derivative
into the solve_ivp path.

## KPI Adapter Coverage

`kpi_adapter.py` covers EPDM compatibility KPIs and generic segment/conversion
KPIs. V4.7 adds `template_flowsheet` and `TemplateProcessConfig` reporting so
KPI outputs are no longer limited to the EPDM field list.

## Equation Registry Coverage

`equation_registry.json` covers the core kinetic, thermodynamic, heat,
rheology, pressure drop, fouling, Tg and grade-match equations. V4.7 adds
machine-executable trend checks through `equation_tests.py`.

## Surrogate Risk

The surrogate layer is for fast screening only. It must not replace real
flowsheet or dynamic verification. V4.7 process-window ranking keeps real
flowsheet checks in the loop for final hard constraints.

## Bayesian DOE Risk

The DOE layer still uses engineering proxy scoring for weak-parameter
information gain. It is mathematically bounded and reproducible, but it needs
new real time-series and physical-property data to become statistically strong.

## UI Trigger Path

Manual heavy tasks remain governed by `ui_workflow.py` and `TaskService`:

- dynamic ODE
- template dynamic ODE
- CFD
- CFD grid convergence
- optimization/Pareto
- parameter estimation
- posterior sampling
- Bayesian DOE
- uncertainty
- report/repro package export

Page navigation should not trigger ODE, CFD, optimization, posterior sampling
or DOE.

## Report Export Path

V4.7 report export only reads available results. Missing posterior, constrained
window, workflow or CFD grid-convergence results are written as `not_run`.
Report export does not intentionally rerun ODE, CFD, optimization, posterior
sampling or DOE.

## Mathematical Risks

- Generic template flowsheet is a conservative apparent model, not a calibrated
  industrial polymerization package.
- Generic monomers may not exist in `components.json`; V4.7 calculates molar
  feeds from template molecular weights to keep balances finite.
- solve_ivp integration is available as a mode/future hook, but the bounded
  explicit profile remains the default stable path.

## Chemical Engineering Risks

- EPDM/Vistalon grade matching is application-specific and should not be used
  for generic templates.
- Flash and rheology models remain simplified R&D trend models.
- Polymer pseudo-component is kept out of vapor flash logic by existing flash
  diagnostics and engineering rules, but industrial VLE requires calibrated
  data.

## V4.8 Priorities

1. Move the full template state derivative into true solve_ivp integration.
2. Add per-template UI feed editors instead of EPDM-only sidebar shortcuts.
3. Expand `components.json` or a template-property source table for generic
   monomers.
4. Tie posterior sampling to real `flowsheet_real` and `dynamic_ode_real`
   likelihoods under explicit compute budgets.
5. Add report and UI tests that assert exports never call heavy model functions.

