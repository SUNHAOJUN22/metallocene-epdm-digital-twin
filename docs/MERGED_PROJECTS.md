# Project merge inventory

## Canonical runtime

`metallocene-epdm-digital-twin` is now the canonical runtime project. The older
`metallocene-epdm-process-simulator` project is treated as the process-simulation
baseline and archival source.

As of V4.1.1 / 0.4.5, the legacy project has an actual compatibility launcher:

- `D:\codex\metallocene-epdm-process-simulator\app.py` starts the canonical
  `D:\codex\metallocene-epdm-digital-twin\app.py`.
- `D:\codex\metallocene-epdm-process-simulator\legacy_app.py` preserves the
  original early MVP Streamlit application for audit/comparison.
- `D:\codex\metallocene-epdm-process-simulator\MERGED_INTO_DIGITAL_TWIN.md`
  documents the compatibility behavior.

As of V4.1.2 / 0.4.6, the two folders have been physically consolidated:

- The outer `D:\codex` workspace now keeps only
  `D:\codex\metallocene-epdm-digital-twin` as the active project folder.
- The full legacy simulator folder has been moved to:

```text
D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator
```

- The archived `app.py` remains a compatibility launcher for the canonical
  digital twin app.
- The archived `legacy_app.py` preserves the original early MVP code.

The merge policy is conservative:

- keep the V4 digital-twin implementation as the active application;
- do not overwrite newer calibrated, dynamic, CFD, case-management or report
  modules with older files;
- retain formulas and tests from the process-simulator layer where they remain
  the correct engineering baseline;
- document every active model in `data/model_registry.json`.

## Legacy process-simulator coverage

| Legacy capability | Active V4 location | Merge status |
| --- | --- | --- |
| Component data | `data/components.json` | Same schema retained and extended |
| Default config | `data/default_config.yaml` | Retained and extended with heat transfer, CFD and recipe fields |
| Internal experiments | `data/internal_experiments.csv` | Retained as calibration anchor |
| Target grades | `data/target_grades.json` | Expanded with Vistalon-like and internal targets |
| Wilson K / Rachford-Rice | `epdm_sim/thermo.py`, `epdm_sim/flash.py` | Retained as default robust flash mode |
| Apparent kinetics | `epdm_sim/kinetics.py`, `epdm_sim/reactor.py` | Retained and connected to parameter sets |
| Heat balance | `epdm_sim/heat_balance.py` | Retained and extended with safety/cooling margin |
| Fluid properties | `epdm_sim/fluid_props.py` | Retained and extended with non-Newtonian options |
| Flow sheet | `epdm_sim/flowsheet.py` | Retained and connected to session state/results store |
| CFD simple solver | `epdm_sim/cfd/` | Retained and extended with masks, diagnostics and OpenFOAM export |
| Report export | `epdm_sim/report.py` | Retained and extended with model cards, uncertainty and case manifest |
| Tests | `tests/` | Legacy tests retained where distinct; V4 tests cover supersets |

## Why code was not copied wholesale

Most file names overlap between the two projects. The digital-twin branch is a
strict superset for the active requirements: it already contains the older
process-simulator functions plus dynamic ODE, calibration, SQLite, case packages,
uncertainty, enhanced EOS/Henry solubility, 3D equipment and UI service layers.

Copying old files over current V4 files would remove these capabilities. The
actual merge therefore records provenance and applicability in the model
registry instead of replacing modules.

## UI and computation trigger policy

Fast deterministic calculations use cached automatic refresh:

- flowsheet material balance;
- heat balance;
- fluid properties;
- flash/recycle fast estimates;
- product-property estimates.

Heavy or exploratory calculations require explicit buttons:

- detailed ODE reactor model;
- CFD field generation;
- optimization and Pareto scans;
- parameter estimation;
- uncertainty analysis;
- report image export.

This keeps the application responsive while preserving the engineering logic of
the full model stack.
