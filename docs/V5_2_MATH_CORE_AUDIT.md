# V5.2 Math Core Audit

## Scope

This audit covers the V5.2 math-core hardening work for the EPDM/EPM solution-polymerization digital twin. The reviewed modules are:

- `epdm_sim/flowsheet.py`
- `epdm_sim/template_flowsheet.py`
- `epdm_sim/reactor.py`
- `epdm_sim/kinetics.py`
- `epdm_sim/dynamic_template_reactor.py`
- `epdm_sim/template_ode_rhs.py`
- `epdm_sim/heat_balance.py`
- `epdm_sim/thermo.py`
- `epdm_sim/eos.py`
- `epdm_sim/flash.py`
- `epdm_sim/solubility.py`
- `epdm_sim/fluid_props.py`
- `epdm_sim/rheology.py`
- `epdm_sim/conservation.py`
- `epdm_sim/units.py`
- `epdm_sim/dimensional_checks.py`
- `epdm_sim/equation_registry.py`
- `epdm_sim/scientific_benchmarks.py`
- `epdm_sim/preflight.py`
- `epdm_sim/model_audit_report.py`

## Core Equations

The critical equation set is defined in `data/equation_registry.json` and machine-bound through `epdm_sim/equation_binding.py`.

| Equation | Implementation | Math/Engineering Gate |
|---|---|---|
| Arrhenius apparent rate | `epdm_sim.kinetics.arrhenius_factor` | temperature increase does not reduce rate |
| Catalyst activation factor | `epdm_sim.kinetics.activation_factor` | finite, bounded, nonnegative |
| ENB pressure factor | `epdm_sim.kinetics.pressure_enb_factor` | high pressure does not create abnormal ENB incorporation |
| H2 chain transfer | `epdm_sim.polymer_props.estimate_molecular_weight` | H2 increase does not increase Mw |
| Heat release | `epdm_sim.heat_balance.calculate_heat_balance` | consumed mol increase increases Q_rxn |
| Henry solubility | `epdm_sim.solubility.liquid_saturation_concentration_mol_L` | pressure increase increases Cstar |
| Rachford-Rice | `epdm_sim.thermo.solve_rachford_rice` | vapor fraction bounded in [0, 1] |
| Carreau viscosity | `epdm_sim.rheology.calculate_rheology` | solids/Mw increase viscosity, T increase lowers viscosity |
| Darcy pressure drop | `epdm_sim.fluid_props.estimate_pressure_drop_kPa` | diameter decrease and flow increase raise pressure drop |
| ODE accumulation | `epdm_sim.template_ode_rhs.evaluate_template_rhs` | finite derivatives and nonnegative projected states |

## Unit and Dimension Review

V5.2 introduces `epdm_sim/dimensioned.py` for lightweight unit-safe values. It does not replace the existing `units.py` API; it adds explicit unit/dimension metadata for new math-core gates.

Covered dimensions:

- temperature: K, degC
- pressure: Pa, kPa, MPa, bar, atm
- mass flow: kg/h, g/h
- molar flow: mol/h, kmol/h
- concentration: mol/L, mol/m3
- energy/power: J, kJ, W, kW, kJ/h
- viscosity: Pa.s, cP
- density: kg/m3
- length: m, mm
- time: s, min, h

Remaining risk: complex derived units are still checked through equation metadata and tests rather than full symbolic dimensional algebra.

## Conservation Residuals

`epdm_sim/residual_system.py` upgrades conservation from isolated checks to a unified residual system with:

- total mass residual
- polymer pseudo vapor residual
- product composition residual
- monomer-to-polymer reaction residual
- segment composition residual
- energy release residual
- dynamic ODE residual proxy

Default flowsheet residuals are accepted when critical residuals pass or only warning-level screening residuals remain. A failed residual records suspected source and suggested fix.

## Numerical Risk Points

| Risk | Current Mitigation |
|---|---|
| NaN/inf in KPI | `numerics`, `auto_functional_audit`, benchmark gates |
| Negative physical properties | preflight, units assertions, transport-core checks |
| BDF stiffness/failure | `ode_scaling`, BDF readiness, explicit bounded fallback with reason |
| State projection hiding mass error | residual-system score and ODE diagnostics |
| Flash all-liquid/all-vapor edge cases | bounded Rachford-Rice and flash diagnostics |
| Out-of-range DOE/optimizer candidate | validity envelope gate |

## Fallback Review

Fallbacks are allowed only when they are explicit and diagnostic:

- BDF can fallback to explicit bounded integration with `fallback_reason`.
- EOS/flash can fallback to bounded K/Rachford-Rice logic with diagnostics.
- Parameter fitting and posterior sampling penalize failed model runs instead of crashing.
- Reports write `not_run` for missing heavy-task results and do not rerun ODE/CFD/optimizer/posterior/DOE.

## Benchmark Review

`data/golden_benchmarks.json` is versioned to `V5.2 / 0.6.2`. Each benchmark records input, expected output, unit, tolerance, equation id, validity range, source rationale and last reviewed date. V5.2 adds a residual-system score benchmark.

## V5.3 Priorities

1. Push `DimensionedValue` deeper into the RHS, flash and heat-balance calculation path.
2. Add sparse/analytic Jacobian support for stiff BDF mode.
3. Add calibrated VLE, solubility, rheology and calorimetry datasets as benchmark sources.
4. Expand residual-system diagnostics to per-unit-operation residual decomposition in the UI.
5. Replace remaining screening thermodynamic constants with calibrated property-source records.
