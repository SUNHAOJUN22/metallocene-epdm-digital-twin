# Metallocene EPDM Digital Twin

Language: **English** | [中文](README.zh-CN.md)

Industrial research software for metallocene EPM/EPDM solution-polymerization modeling, residual-aware process simulation, model governance, report generation, and reproducible validation.

Current formal release: **V6.4 / 0.7.4**
V6.5 status: **quality sprint and math-rigor audit record, no formal version bump**

Repository: [SUNHAOJUN22/metallocene-epdm-digital-twin](https://github.com/SUNHAOJUN22/metallocene-epdm-digital-twin)

---

## 1. Purpose

This project is a Streamlit-based digital twin and scientific software workbench for metallocene EPM/EPDM and related solution-polymerization process studies.

It is designed to support:

- flowsheet simulation with mass and energy residual checks;
- reactor, flash, heat-balance, recycle, property, and transport calculations;
- dynamic ODE/DAE diagnostics and stability checks;
- residual-aware optimization, DOE, posterior filtering, and uncertainty assessment;
- benchmark, data-lineage, evidence-chain, and model-confidence governance;
- Excel, Word/PDF-oriented, and reproducibility package exports;
- UI-driven workflows where heavy computations are explicitly triggered through task actions.

The project is not a black-box production APC/DCS controller. It is a research and engineering decision-support platform with explicit audit trails, benchmark boundaries, and validation gates.

---

## 2. Current Quality Baseline

The latest recorded V6.5 quality sprint on the V6.4 / 0.7.4 formal baseline reports:

| Gate | Recorded Result |
| --- | --- |
| `pytest` | 361 passed |
| `auto_functional_audit` | 151/151 passed |
| `function_inventory_audit` | 1007/1007 public callable direct references |
| `release_gate` | passed |
| Streamlit | HTTP 200 |

See:

- [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- [docs/QUALITY_BASELINE.md](docs/QUALITY_BASELINE.md)
- [docs/V6_5_MATH_RIGOR_AUDIT.md](docs/V6_5_MATH_RIGOR_AUDIT.md)
- [docs/V6_5_CHANGELOG.md](docs/V6_5_CHANGELOG.md)

---

## 3. Core Capabilities

### Process and Reactor Modeling

- EPDM/EPM solution-polymerization process simulation
- reactor kinetics and polymer property prediction
- template flowsheet simulation
- flash, recycle, solubility, heat-balance, and transport calculations
- CFD-oriented helper modules and visualization contracts

### Mathematical Kernel

- explicit unit handling through dimensioned inputs and unit conversion traces
- finite, nonnegative, bounded, and trend-aware checks
- ResidualSystem-based mass, component, energy, flash, heat, recycle, and dynamic residual diagnostics
- equation registry, equation binding, reverse checks, and equation-residual coupling
- conservation correction, equation-oriented solver certificates, and nonlinear residual loop audits

### Dynamic and Stability Diagnostics

- dynamic template reactor
- ODE/DAE state invariant checks
- adaptive step and event localization diagnostics
- quench, cooling-failure, runaway-risk, and residual-triggered fallback reporting

### Calibration and Evidence Governance

- experimental benchmark registry
- benchmark source registry with confidence classes:
  `plant > experiment > literature > synthetic > regression_snapshot`
- data-lineage graph
- evidence-chain score
- model-confidence certificate
- calibrated property model runtime and audit layers

### Decision Workflows

- residual-aware optimizer
- residual-aware DOE
- posterior residual filtering
- uncertainty risk bounds
- validation data gap recommendations

### Reporting and Reproducibility

- Excel report export
- Word/PDF-oriented report helpers
- reproducibility package manifest
- report consistency checks
- audit snapshots for residuals, equations, benchmarks, lineages, property models, and governance certificates

---

## 4. Repository Layout

```text
.
├── app.py                         # Streamlit application entry point
├── epdm_sim/                      # Runtime package
│   ├── math_core/                 # equations, constraints, residual abstractions
│   ├── solver_core/               # constrained solvers, certificates, residual loops
│   ├── dynamic_core/              # ODE/DAE policies, invariants, adaptive diagnostics
│   ├── flowsheet_core/            # material/energy closure and flowsheet helpers
│   ├── reactor_core/              # reactor balances, heat release, polymer moments
│   ├── fluid_core/                # density, heat capacity, viscosity, hydraulics
│   ├── mcp/                       # governed MCP-style tool contracts
│   ├── reporting/                 # Excel/PDF/Word report support
│   └── pages/                     # Streamlit page modules
├── data/                          # registries, benchmark data, model/config data
├── docs/                          # audit reports, quality records, roadmaps
├── scripts/                       # quality gates, audits, test/report commands
├── tests/                         # unit, integration, scientific, UI-contract tests
└── requirements.txt               # runtime dependencies
```

Generated outputs, local databases, smoke artifacts, rendered images, logs, and office exports are intentionally ignored by Git.

---

## 5. Requirements

- Python **3.11+**
- Windows, Linux, or macOS
- Recommended: isolated virtual environment

Core Python dependencies are listed in [requirements.txt](requirements.txt) and [pyproject.toml](pyproject.toml).

---

## 6. Installation

```powershell
git clone https://github.com/SUNHAOJUN22/metallocene-epdm-digital-twin.git
cd metallocene-epdm-digital-twin

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 7. Run the Application

```powershell
python -m streamlit run app.py --server.headless true --server.port 8501
```

Open:

```text
http://127.0.0.1:8501/
```

The UI exposes dashboard, reactor, separation, heat/fluid, dynamic reactor, calibration, experiment data, sensitivity/optimization, model governance, report, and workflow pages.

Heavy tasks must be launched through explicit UI actions and TaskService mappings. Page navigation and report export are not intended to trigger ODE, CFD, optimizer, posterior, DOE, or uncertainty-heavy runs automatically.

---

## 8. Quality Gate Commands

Run the standard environment check:

```powershell
python scripts\dev_tasks.py check-env
```

Run the full test suite:

```powershell
python -m pytest -q tests
```

Run functional and inventory audits:

```powershell
python scripts\auto_functional_audit.py
python scripts\function_inventory_audit.py
```

Run performance and UI smoke checks:

```powershell
python scripts\performance_profile.py
python scripts\ui_e2e_smoke.py
python scripts\ui_e2e_workflow.py
```

Run executable professional-skill peripheral QA:

```powershell
python scripts\dev_tasks.py professional-skill-qa
```

This command checks the artifacts that are appropriate for professional workflow-skill replacement: Excel report structure, Word report content, UI contract artifacts, and GitHub workflow readiness. It does not replace the scientific kernel gates.

Run the MCP-style integration contract QA through the same professional-skill harness:

```powershell
python scripts\dev_tasks.py professional-skill-qa
```

The MCP interface in `epdm_sim/mcp/` is an in-process, tool-only boundary for future scientific workflow integrations. It defaults to `dry_run=True`, requires explicit unit context, rejects invalid units/NaN/inf/negative absolute temperature/outside-validity fields, and refuses heavy task execution unless explicitly permitted. It does not replace ResidualSystem, flash/EOS, ODE/DAE, benchmark validation, or release gates.

Run the full quality and release gates:

```powershell
python scripts\dev_tasks.py quality-gate
python scripts\dev_tasks.py generate-test-report
python scripts\dev_tasks.py continuous-improve
python scripts\release_gate.py
```

---

## 9. Scientific Validation Contract

The platform is governed by the following engineering contract:

- all core outputs must be finite;
- physical quantities must remain nonnegative where required;
- pressure, temperature, density, viscosity, flow, risk probability, and vapor fraction must stay bounded;
- total mass, component mass, energy, flash, heat-balance, recycle, and dynamic accumulation residuals must be finite and accepted;
- large residuals must not be hidden by correction logic;
- polymer vapor is treated as physically critical unless explicitly zero or guarded;
- optimizer, DOE, posterior, and uncertainty decisions must reject or penalize residual-critical and outside-validity candidates;
- unit conversions must be explicit and traceable.

The math runtime is validated by repository-native code, benchmarks, ResidualSystem checks, pytest, audits, and release gates. Generic external skills or visual QA tools do not replace the scientific kernel.

---

## 10. Data and Evidence Policy

Benchmark and calibration evidence is classified by source confidence:

1. plant
2. experiment
3. literature
4. synthetic
5. regression_snapshot

Critical release evidence should include:

- `source_reference`
- `measurement_unit`
- `uncertainty`
- `validity_range`
- `data_hash`
- `confidence_level`
- `review_status`

Out-of-validity or low-confidence evidence may remain useful for regression and diagnostics, but it should not be promoted to high-confidence critical validation.

---

## 11. Reports and Reproducibility

Reports and reproducibility packages are expected to preserve:

- residual snapshots;
- equation registry snapshots;
- model registry snapshots;
- benchmark source snapshots;
- data-lineage snapshots;
- calibrated property usage;
- unit conversion traces;
- solver certificates;
- governance and confidence artifacts.

Report export must not rerun heavy computations. Missing heavy-task outputs should be represented as `not_run` rather than silently recomputed.

---

## 12. Documentation Index

Primary documents:

- [docs/QUALITY_BASELINE.md](docs/QUALITY_BASELINE.md)
- [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- [docs/FUNCTION_MATRIX.md](docs/FUNCTION_MATRIX.md)
- [docs/UNIT_SYSTEM.md](docs/UNIT_SYSTEM.md)
- [docs/SCIENTIFIC_VALIDATION.md](docs/SCIENTIFIC_VALIDATION.md)
- [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)
- [docs/OPTIMIZATION_ROADMAP.md](docs/OPTIMIZATION_ROADMAP.md)
- [docs/CONTINUOUS_IMPROVEMENT_LOG.md](docs/CONTINUOUS_IMPROVEMENT_LOG.md)
- [docs/MCP_INTERFACE_DESIGN.md](docs/MCP_INTERFACE_DESIGN.md)
- [docs/MCP_TOOL_CONTRACT.md](docs/MCP_TOOL_CONTRACT.md)
- [docs/MCP_SAFETY_POLICY.md](docs/MCP_SAFETY_POLICY.md)

Detailed generated/manual references:

- [README.zh-CN.md](README.zh-CN.md)
- [README_Manual_And_Tech.md](README_Manual_And_Tech.md)
- [README_Deep_Technical.md](README_Deep_Technical.md)
- [README_technical.md](README_technical.md)

---

## 13. Known Limitations

- Some benchmark records remain synthetic or regression-oriented and should be replaced with reviewed plant, experiment, or literature evidence before high-stakes engineering use.
- The project is a research-grade digital twin, not a certified plant safety system.
- Industrial deployment requires independent validation, cybersecurity review, data-governance review, HAZOP/LOPA alignment, and site-specific model calibration.
- Local generated artifacts and SQLite working data are intentionally excluded from source control.
- No open-source license file is currently included in this repository.

---

## 14. Development Rules

Contributors should preserve the existing validation contract:

- do not delete tests to pass gates;
- do not skip failing checks;
- do not relax residual severity or tolerances without a documented engineering reason;
- do not mask NaN, infinite, negative physical quantities, or critical residuals;
- do not replace runtime math, physics, or validation logic with generic tooling;
- update changelog and quality documents when changing runtime behavior or release gates.
- use `professional-skill-qa` for peripheral UI/report/GitHub artifact checks that are suitable for professional workflow-skill replacement.
- use `epdm_sim.mcp` only as a governed external-tool boundary; keep scientific calculations and residual acceptance inside repo-native gates.

Recommended pre-push command:

```powershell
python scripts\dev_tasks.py quality-gate
python scripts\release_gate.py
python scripts\dev_tasks.py professional-skill-qa
```

---

## 15. Roadmap

Near-term priorities:

- deeper reviewed plant/experiment/literature evidence coverage;
- more realistic plant/LIMS/ELN data ingestion;
- continued API-compatible decomposition of very large modules;
- deeper nonlinear residual-loop integration into recycle, flash, and heat-balance solve paths;
- improved report readability for wide audit tables;
- optional CI hardening for long-running scientific gates.
- production MCP/ChatGPT Apps transport around the current in-process `epdm_sim.mcp` registry, with auth, schema discovery and hosted connector review.
