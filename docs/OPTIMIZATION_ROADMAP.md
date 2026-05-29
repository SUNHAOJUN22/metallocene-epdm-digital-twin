# Optimization Roadmap

## Current Technical Debt

| module | public_callables | directly_referenced | uncovered_callables |
| --- | --- | --- | --- |
| epdm_sim.units | 24 | 24 | 0 |
| epdm_sim.dimensioned | 18 | 18 | 0 |
| epdm_sim.fluid_props | 18 | 18 | 0 |
| epdm_sim.utils | 18 | 18 | 0 |
| epdm_sim.conservation | 15 | 15 | 0 |
| epdm_sim.aspen_bridge | 13 | 13 | 0 |
| epdm_sim.mcp.schemas | 13 | 13 | 0 |
| epdm_sim.equipment_3d | 12 | 12 | 0 |
| epdm_sim.kinetics | 12 | 12 | 0 |
| epdm_sim.calibrated_property_models | 11 | 11 | 0 |
| epdm_sim.eos | 11 | 11 | 0 |
| epdm_sim.mcp.tools | 11 | 11 | 0 |
| epdm_sim.reaction_templates | 11 | 11 | 0 |
| epdm_sim.case_manager | 10 | 10 | 0 |
| epdm_sim.db | 9 | 9 | 0 |
| epdm_sim.numerics | 9 | 9 | 0 |
| epdm_sim.parameter_estimation | 9 | 9 | 0 |
| epdm_sim.plotting | 9 | 9 | 0 |
| epdm_sim.polymer_props | 9 | 9 | 0 |
| epdm_sim.recipe | 9 | 9 | 0 |

## Short Term

- Keep direct callable coverage at 100% when adding V6.4/V6.5 public APIs.
- Continue API-compatible splits for large modules only with targeted tests and changelog entries.
- Replace synthetic/regression benchmarks with reviewed experiment/literature/plant evidence.
- Deepen DimensionedValue use inside flash, heat balance, transport and optimizer internals.
- Add more real experimental validation datasets.
- Register every report Plotly figure in plot validation.
- Validate Aspen Plus/HYSYS stream mappings against a real site case tree, but keep COM execution outside report export and under explicit operator approval.
- Add round-trip examples for Aspen-imported results that remain reconciliation evidence rather than silent corrections to EPDM residuals.

## Medium Term

- Improve BDF scaling and sparse Jacobian support.
- Expand ResidualSystem to per-unit-operation UI diagnostics.
- Add richer browser E2E snapshots when Playwright is available.
- Expand property and thermodynamic calibration datasets.
- Add optional Aspen case adapters for site-specific component naming, stream paths and unit-operation variable paths.

## Long Term

- Move from screening correlations toward validated, uncertainty-aware digital twin model cards.
