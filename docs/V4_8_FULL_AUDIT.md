# V4.8 Full Audit

## Scope

This audit was performed before upgrading V4.7 / 0.5.4 to V4.8 / 0.5.5. The goal is to move the existing template adapters into the canonical execution path while preserving EPDM/Vistalon compatibility as an application adapter.

## Project Structure

- Canonical runtime: `D:\codex\metallocene-epdm-digital-twin`
- Legacy archive: `D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator`
- Main app entry: `app.py`
- Core package: `epdm_sim`
- Tests: `tests`
- Registries: `data/model_registry.json`, `data/equation_registry.json`, `data/reaction_templates.json`

## Main Findings

1. V4.7 added `TemplateProcessConfig`, `feed_adapter`, `template_flowsheet`, `dynamic_template_reactor`, posterior sampling, constrained windows, audit trail, workflow wizard and CFD grid convergence.
2. `run_template_flowsheet()` existed, but EPDM still delegated to the legacy `run_flowsheet()` path. V4.8 changes the public `run_flowsheet()` API so the no-override path now routes through `TemplateProcessConfig -> run_template_flowsheet -> EPDM adapter`, while the legacy implementation is retained as `_run_epdm_flowsheet_impl()`.
3. `dynamic_template_reactor.py` supported solve_ivp modes only as capability probes. V4.8 adds `template_ode_rhs.py` and uses a real `solve_ivp` RHS for `solve_ivp_rk45` and `solve_ivp_bdf`, with explicit bounded fallback.
4. `data/model_registry.json` was still version `0.5.0`, and `data/equation_registry.json` was still `V4.6`. V4.8 updates both registries.

## Remaining EPDM Application Adapters

These are intentionally retained:

- `ProcessConfig.ethylene_kg_h`, `propylene_kg_h`, `enb_kg_h`, `hydrogen_g_h`
- EPDM KPI aliases: `C2_wt`, `C3_wt`, `ENB_wt`
- Vistalon-like target grade matching
- EPDM dashboard shortcuts

These should remain outside generic kernels. New generic calculations should consume `TemplateProcessConfig`, template monomer maps and template KPI lists.

## Mathematical and Engineering Checks

V4.8 strengthens:

- non-negative state projection for dynamic ODE states;
- bounded conversions;
- template segment mass closure;
- heat release proportional to monomer consumption;
- pressure and temperature finite checks;
- solve_ivp failure fallback.

## Current Risk Points

1. Some sensitivity, DOE and uncertainty modules still expose EPDM shortcut variables by default. They should remain EPDM application views while internal scoring migrates further to template KPI schema in future V4.9.
2. Generic template flowsheet is still a screening kernel, not a calibrated industrial model.
3. The solve_ivp RHS includes gas-liquid transfer and thermal proxies suitable for R&D trend analysis, not a validated reactor design package.
4. UI pages still need progressive replacement of C2/C3/ENB labels with template KPI tables where generic templates are selected.

## V4.9 Priority Suggestions

1. Make sensitivity, Bayesian DOE, uncertainty and constrained windows fully template-native internally.
2. Add UI controls to choose template and dynamically generate monomer feed widgets on all relevant pages.
3. Add template-specific report sections and hide Vistalon panels automatically for non-EPDM templates.
4. Add calibrated gas-liquid transfer and heat-transfer correlations once experimental kLa/UA data are available.

