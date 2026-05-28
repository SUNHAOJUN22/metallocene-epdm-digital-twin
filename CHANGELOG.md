# Changelog

## V6.5 half-hour quality sprint

- Ran a time-boxed V6.5 quality-enhancement audit on top of the V6.4 / 0.7.4 baseline.
- Verified `pytest` remains at 344 passed, `auto_functional_audit` remains 150/150 passed and `function_inventory_audit` remains 971/971 direct references.
- Verified performance profile, UI smoke/workflow, report/repro artifacts, Excel sheet-name compatibility, residual gates, unit gates and benchmark/evidence-chain gates.
- Re-ran the same V6.5 sprint on 2026-05-19 after the user requested another full automated pass; pytest, quality gate, release gate and Streamlit HTTP 200 remained green.
- Re-ran the V6.5+ automated sprint on 2026-05-20 after traversing the project tree; pytest, auto functional audit, function inventory, quality gate, release gate and Streamlit HTTP 200 remained green.
- Added a UI action registry usability gate to detect duplicate action signatures, duplicate same-page labels, incomplete action entries, missing user feedback and export actions without declared outputs.
- Re-ran the V6.5 quality sprint after the usability gate was integrated: pytest 346 passed, auto_functional_audit 151/151 passed, function inventory 972/972 direct references, release_gate passed and Streamlit HTTP 200.
- Re-ran a full V6.5 math-rigor sprint on 2026-05-20: unit/dimension, finite/nonnegative/bounded, conservation residual, equation/benchmark/lineage, thermo/flash/transport/rheology/heat, dynamic ODE/DAE, residual-aware optimizer/DOE/posterior, report/repro and UI gates all passed; added `docs/V6_5_MATH_RIGOR_AUDIT.md`.
- Added `docs/MARKET_SKILL_REPLACEMENT_PLAN.md` to replace eligible manual workstreams with installed market skills: Browser for UI inspection, Spreadsheets for Excel QA, Documents for Word report QA, GitHub for PR/CI workflows, openai-docs for OpenAI integration lookup, Presentations for decks and imagegen for bitmap assets. Runtime math-core modules remain repo-owned and release-gated.
- Started actual professional skill replacement for eligible peripheral QA: Browser inspected the Streamlit app, Spreadsheets imported and checked the latest Excel report, and Documents rendered the latest Word report; added `docs/MARKET_SKILL_ACTUAL_REPLACEMENT_AUDIT.md`.
- Installed additional professional market skills from `openai/skills` for future replacement workstreams: `playwright`, `playwright-interactive`, `screenshot`, `pdf`, `security-best-practices`, `security-threat-model`, `jupyter-notebook` and `chatgpt-apps`.
- Installed additional governance/observability market skills: `security-ownership-map` and `sentry`; ownership mapping is pending a git repository and Sentry inspection is pending local Sentry CLI/auth configuration.
- Re-ran the full V6.5 math-rigor and professional skill QA sprint on 2026-05-20 14:38: pytest 346 passed, auto_functional_audit 151/151 passed, function inventory 972/972 direct references, quality-gate passed, release_gate passed and Streamlit HTTP 200. Browser, Spreadsheets and Documents skills rechecked the Streamlit UI, Excel report and Word report.
- Re-ran the full V6.5 math-rigor and professional skill QA sprint on 2026-05-20 14:59: pytest 346 passed, auto_functional_audit 151/151 passed, function inventory 972/972 direct references, quality-gate passed, release_gate passed and Streamlit HTTP 200. Browser, Spreadsheets and Documents skills again verified UI, Excel and Word report artifacts.
- Aligned the package-level runtime metadata `epdm_sim.__version__` from the stale V4.8 value `0.5.5` to the active V6.4 package version `0.7.4`; no solver, residual, benchmark, property-model or report behavior was changed; pytest, auto_functional_audit, function_inventory_audit, quality-gate, release_gate and Streamlit HTTP checks remained green.
- Re-ran the large-scale stability and mathematical-logic traversal on 2026-05-20 15:59: 1222 core files scanned, `pytest` 346 passed, `auto_functional_audit` 151/151 passed, `function_inventory_audit` 972/972 direct references and `quality-gate` passed; no P0/P1/P2 issue was found.
- Replaced stale `V4` metadata in the UI report manifest and case-package manifest with shared `APP_VERSION`, and added a real case-package manifest version assertion.
- Re-ran the 2026-05-22 V6.5 automated stability/math-rigor sprint after the export metadata correction: 1222 files re-scanned, `pytest` 346 passed, `auto_functional_audit` 151/151 passed, direct references remained 972/972, quality/release gates passed and Streamlit remained HTTP 200; no additional P0/P1/P2 fix was required.
- Re-ran the same V6.5 automated traversal at 2026-05-22 14:36 with the formal V6.4 / 0.7.4 contract unchanged: version/risk scans, pytest, functional audit, direct-reference audit, performance/UI checks, quality gate, release gate and HTTP verification stayed green, so only QA documents were refreshed.
- Re-ran the user-requested V6.5 traversal at 2026-05-22 15:12: project file/risk scans, repo-native math gates, performance/UI checks, quality gate, release gate, Streamlit HTTP verification and Browser page inspection stayed green on the unchanged V6.4 / 0.7.4 formal baseline.
- Re-ran the V6.5 boundary/usability pass at 2026-05-22 15:42: math/stability gates, direct-reference coverage, report/repro/UI contracts and Browser navigation checks stayed green; no runtime fix was needed, while repeated report/repro audit-context assembly remains a P3 optimization target.
- Prepared the project for first GitHub publication to `SUNHAOJUN22/metallocene-epdm-digital-twin` by initializing a local Git repository and expanding `.gitignore` to keep generated smoke outputs, local SQLite data, logs, rendered documentation images and transient artifacts out of source control.
- Rewrote `README.md` into a standard industrial-software landing document with concise product scope, quality baseline, architecture, installation, operation, validation contract, data/evidence policy, report/reproducibility expectations, limitations and roadmap; the detailed generated manuals remain linked as supporting references.
- Added bilingual README navigation: `README.md` remains the English landing page and `README.zh-CN.md` provides a full Chinese version with reciprocal language-switch links.
- Added executable professional-skill peripheral QA via `scripts/professional_skill_qa.py`, `python scripts\dev_tasks.py professional-skill-qa` and Makefile target `professional-skill-qa`; this replaces eligible manual Excel/Word/UI/GitHub artifact checks while keeping the scientific runtime kernel repo-native.
- Added a governed MCP-style scientific simulation interface under `epdm_sim/mcp/`, including explicit unit context schemas, preflight safety checks, lineage snapshots, dry-run-by-default tool contracts, a minimal in-process tool registry and professional-skill QA coverage for future ChatGPT Apps/MCP integration.
- No P0/P1/P2 defect was found, so no model rewrite or version-contract bump was applied.
- Added `docs/V6_5_CHANGELOG.md` and `docs/V6_5_HALF_HOUR_AUDIT.md` to record test facts, remaining P3 risks and V6.6 recommendations.

## V6.4 / 0.7.4

- Added nonlinear residual-loop and solve-path integrator audit layers for equation-oriented flowsheet/recycle/flash/heat residual closure.
- Added industrial data package validation and benchmark reconciliation with source, unit, uncertainty, validity and confidence checks.
- Added property runtime audit so calibrated property usage is checked against residual safety and confidence evidence.
- Added adaptive integrator and event localization diagnostics for dynamic DAE/ODE solver governance.
- Added residual-aware decision engine for optimizer/DOE/posterior/uncertainty rejected-reason audit paths.
- Added model governance page and governance certificate artifacts for UI/report/repro traceability without triggering heavy tasks on navigation.
- Added V6.4 Excel/repro audit artifacts and release-gate checks for nonlinear residual loop, solve-path integrator, industrial data package, benchmark reconciliation, property runtime audit, adaptive integrator, event localization, residual decision engine and governance certificate.
- Verified V6.4 release workflow on 2026-05-19: 344 pytest tests passed, auto_functional_audit 150/150 passed, function inventory 971/971 direct references, release_gate passed, UI smoke/workflow passed and Streamlit HTTP 200.

## V6.3 / 0.7.3

- Added equation-oriented conservation solver and finite-difference conservation Jacobian diagnostics.
- Added calibration data package validation and benchmark data assimilation helpers.
- Added property runtime context to audit calibrated/default property-model impact with residual safety.
- Added dynamic adaptive step-control and event-detection diagnostics.
- Added residual-aware sampling decisions for posterior/DOE/optimizer audit paths.
- Added model confidence certificate and validation upgrade plan artifacts.
- Added V6.3 Excel/repro audit artifacts and release-gate checks for equation-oriented solver, conservation Jacobian, data assimilation, property runtime context, adaptive step control, event detection, residual-aware sampling and confidence certificate.
- Verified V6.3 release workflow on 2026-05-18: 334 pytest tests passed, auto_functional_audit 141/141 passed, function inventory 935/935 direct references, release_gate passed, UI smoke/workflow passed and Streamlit HTTP 200.

## V6.2 / 0.7.2

- Added conservation solve path APIs for flowsheet, flash, heat-balance and recycle residual acceptance certificates.
- Added property-model runtime hooks so calibrated Henry, viscosity, flash-K correction and deltaH can affect calculations inside validity range while preserving default estimates.
- Added dynamic solver policy and step-acceptance diagnostics driven by stiffness, residual acceptance, state invariants and event risk.
- Added residual-aware optimizer and DOE scoring with residual-critical and outside-validity rejection.
- Added evidence-chain score and evidence-gap priority tables for equation/residual/benchmark/data-lineage/source confidence governance.
- Added V6.2 Excel/repro audit artifacts and release-gate checks for conservation solve path, property runtime, dynamic solver policy, residual-aware optimizer/DOE, evidence-chain score, Excel sheet-name compatibility and markdown changelog enforcement.
- Added `tests/test_v6_2_math_core.py` and verified targeted V6.2 core/report/repro tests before full gate execution.
- Verified V6.2 release workflow on 2026-05-18: 328 pytest tests passed, auto_functional_audit 132/132 passed, function inventory 902/902 direct references, release_gate passed, UI smoke/workflow passed and Streamlit HTTP 200.

## V6.1 / 0.7.1

- Added conservation correction certificates for small residual closure and critical residual rejection.
- Added calibrated property model bridge, dynamic solver decision, residual-aware decision and evidence-chain governance.
- Added API-compatible helper splits for estimation, reactor, flowsheet, dynamic and fluid core responsibilities.
- Added V6.1 Excel/repro audit artifacts and release-gate checks for correction certificates, property bridge, solver decision, residual-aware decisions, evidence chain and Excel sheet-name compatibility.
- Fixed default flowsheet residual construction to resolve display-name streams (`Feed`, `Polymer product`) and restore total mass residual closure.
- Verified V6.1 release workflow on 2026-05-18: 323 pytest tests passed, auto_functional_audit 125/125 passed, function inventory 876/876 direct references, release_gate passed, UI smoke/workflow passed and Streamlit HTTP 200.

## V6.0 / 0.7.0

- Added industrial math-core traceability graph layer linking equation registry, ResidualSystem, benchmarks and data lineage.
- Added constrained solver certificates, bounded residual minimizer diagnostics, DAE constraint checks and dynamic state invariants.
- Added evidence-weighted model confidence engine and calibrated property model selector.
- Added V6.0 Excel/repro audit artifacts for traceability graphs, solver certificates, confidence decomposition and property model selection.
- Upgraded release gate static contracts to V6.0 / 0.7.0 with markdown changelog enforcement.
- Fixed Excel worksheet-name compatibility by shortening the dynamic residual feedback status sheet and adding a regression check for the 31-character Excel limit.
- Refreshed V6.0 release verification on 2026-05-18; quality gate, release gate, performance profile, UI smoke/workflow, and Streamlit HTTP 200 checks passed.

## V5.7 / 0.6.7

- Added equation-residual-code coupling checks and residual-acceptance policy tables.
- Added dynamic proof-style stability checks and benchmark source registry.
- Added calibrated property usage selector and V5.7 report/repro audit sheets.
- Added math_core/solver_core helper layers for future API-compatible module splitting.
