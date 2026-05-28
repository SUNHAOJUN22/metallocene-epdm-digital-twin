# Market Skill Actual Replacement Audit

Date: 2026-05-20

Purpose: verify which installed professional market/plugin skills have actually taken over workstream checks for the EPDM digital twin project, and which workstreams remain repo-native because they encode mathematical and physical model logic.

## Available Professional Skills Checked

System skills present:

- `imagegen`
- `openai-docs`
- `plugin-creator`
- `skill-creator`
- `skill-installer`

Plugin/market skills present:

- `browser`
- `spreadsheets`
- `documents`
- `presentations`
- `github`
- `gh-address-comments`
- `gh-fix-ci`
- `yeet`

Remote curated/experimental skill list check:

- `skill-installer` market listing returned HTTP 403 because the GitHub API rate limit was exceeded.
- The OpenAI skills repository was reachable through git, so curated skill names were checked through a sparse clone.
- Additional market skills were installed from `openai/skills` using git mode.

## Market Skills Installed During Strict Replacement

Installed into `C:\Users\resj6\.codex\skills`:

- `playwright`
- `playwright-interactive`
- `screenshot`
- `pdf`
- `security-best-practices`
- `security-threat-model`
- `security-ownership-map`
- `sentry`
- `jupyter-notebook`
- `chatgpt-apps`

These are professional workflow skills. They extend the replacement surface for UI automation, visual QA, PDF QA, security review, threat modeling, calibration notebooks and future ChatGPT Apps integration. They may require restarting Codex before automatic trigger metadata is available in a new conversation.

## Actual Replacement Status

| Workstream | Professional Skill | Actual Status | Evidence |
| --- | --- | --- | --- |
| Streamlit UI inspection | `browser` | actually used | Opened `http://127.0.0.1:8501/`, page title `Metallocene EPDM Digital Twin`, navigation and controls visible. |
| Excel report QA | `spreadsheets` | actually used | Imported `tmp_smoke_outputs/smoke.xlsx`; 173 sheets; 0 sheet names over 31 characters; required sheets present; formula-error search matched 0 entries. |
| Word report QA | `documents` | actually used | Rendered `tmp_smoke_outputs/smoke.docx` into 12 PNG pages with artifact-tool renderer. |
| GitHub PR/CI | `github` / `yeet` | partially replaced | Project is now a Git repository published to `SUNHAOJUN22/metallocene-epdm-digital-twin`; full `gh`/PR workflow remains pending because GitHub CLI is not installed locally. |
| OpenAI API/Agents lookup | `openai-docs` | not used | No OpenAI API implementation task was requested in this replacement audit. |
| Slide deck generation | `presentations` | not used | No presentation artifact was requested in this replacement audit. |
| Browser-flow automation extension | `playwright`, `playwright-interactive` | installed, pending restart/use | Installed from market for future deeper UI flow and screenshot validation. |
| PDF report QA | `pdf` | installed, pending use | Installed from market for future PDF artifact rendering and extraction QA. |
| Security review | `security-best-practices`, `security-threat-model` | installed, pending use | Installed from market for future app security reviews and threat models. |
| Security ownership and bus factor | `security-ownership-map` | installed, blocked by non-git folder | Requires git history; current project path is not a git repository. |
| Production error observability | `sentry` | installed, pending Sentry CLI/auth | Requires local Sentry CLI and authentication before use. |
| Calibration notebooks | `jupyter-notebook` | installed, pending use | Installed from market for future experiment/calibration notebooks. |
| ChatGPT Apps integration | `chatgpt-apps` | installed, pending use | Installed from market for future MCP/widget app integration, with `openai-docs` as docs-first prerequisite. |
| Raster visual generation | `imagegen` | not used | No bitmap visual asset was requested; scientific plots must remain code-generated. |

## Browser Skill Result

- URL: `http://127.0.0.1:8501/`
- Title: `Metallocene EPDM Digital Twin`
- Visible workflow signals:
  - 15-page navigation present in the app body.
  - `模型治理与可信度证书` page entry visible.
  - `报告导出` page entry visible.
  - `运行快速流程模拟` button visible.
  - Temperature, pressure, feed and reactor-mode inputs visible.

Interpretation: Browser skill has replaced manual first-pass UI presence inspection. Repo-native `ui_e2e_smoke.py`, `ui_e2e_workflow.py` and `ui_action_usability_gate` still provide executable heavy-task and action-registry contracts.

## Spreadsheets Skill Result

Workbook: `tmp_smoke_outputs/smoke.xlsx`

- Sheet count: 173.
- Sheet names over 31 characters: 0.
- Required sheets checked:
  - `residual_system`
  - `unit_conversion_trace`
  - `benchmark_acceptance`
  - `evidence_chain`
  - `property_model_runtime`
  - `dynamic_solver_policy`
- Missing required sheets: none.
- Formula error search: 0 entries.

Interpretation: Spreadsheets skill has replaced manual workbook inspection for sheet inventory and representative scientific/audit sheet content. Repo-native `excel_required_sheets`, `excel_sheet_name_compatibility_gate` and `report_repro_industrial_audit_gate` remain authoritative release checks.

## Documents Skill Result

Document: `tmp_smoke_outputs/smoke.docx`

- Rendered pages: 12.
- Renderer: artifact-tool through the Documents skill render workflow.
- Output directory: `tmp_smoke_outputs/docx_render_skill_qa`.
- Render status: successful.

Observed report-layout risks:

- Some pages are section-title or sparse pages, which is acceptable for a smoke report but not ideal for a polished customer report.
- Several audit-table pages use very narrow columns. This is a P3 readability issue, not a mathematical/physical model failure.

Interpretation: Documents skill has replaced text-only DOCX checks with rendered page QA. It surfaced report-layout improvement opportunities that repo release gates do not catch. This does not justify modifying scientific model logic.

## Mathematical And Physical Logic Boundary

The following remain repo-native and must not be replaced by generic professional skills:

- Conservation residual logic.
- Unit and dimension conversion.
- EOS, flash, Henry, Wilson and Rachford-Rice calculations.
- Heat-balance and transport correlations.
- Dynamic ODE/DAE RHS and state invariants.
- Residual-aware optimizer, DOE, posterior and uncertainty logic.
- Equation registry, benchmark registry and data-lineage acceptance.

Advanced engineering practice applied:

1. Keep scientific truth in executable code and tests.
2. Use professional skills for artifact, UI, document and workflow QA.
3. Do not let visual/manual QA replace release gates.
4. Treat market skills as independent inspection surfaces, not scientific authorities.
5. Preserve traceability from equation to residual to benchmark to lineage.

## Replacement Conclusion

Actual replacement has now started for eligible professional workstreams:

- UI inspection: replaced by `browser` skill for first-pass visual QA.
- Excel report QA: replaced by `spreadsheets` skill for workbook-level inspection.
- Word report QA: replaced by `documents` skill for render-based page QA.
- Additional professional market skills have been installed for future UI automation, PDF QA, security review, threat modeling, notebook and ChatGPT Apps workflows.
- Additional security/observability market skills have been installed for ownership mapping and Sentry inspection, but they require git history and Sentry auth respectively.

Not replaced:

- Runtime math/physics kernel.
- Repro package consistency gates.
- GitHub PR/CI, because the current directory is not a git repository.
- Runtime math/physics kernel, because replacing scientific truth with a generic skill would violate engineering validity.
- Automatic activation of newly installed market skills in the current session; a Codex restart may be required.
- `security-ownership-map` execution, because current project path has no `.git` history.
- `sentry` execution, because no Sentry CLI/auth target is configured in this local audit.

## Remaining Risks

- P3: Word smoke report table layout should be improved for customer-facing polish.
- P3: Browser skill validation should be expanded to click-path timing and page-level screenshots.
- P3: More real plant/experiment/literature evidence is still needed for industrial validation depth.

## 2026-05-20 14:38 Re-Verification

Current session skill status:

- Active in this session: `browser`, `spreadsheets`, `documents`, `pdf`, `playwright`, `playwright-interactive`, `screenshot`, `security-best-practices`, `security-threat-model`, `security-ownership-map`, `sentry`, `jupyter-notebook`, `chatgpt-apps`, `openai-docs`, `imagegen`, `presentations`, `github`, `gh-fix-ci`, `gh-address-comments`, `yeet`.
- Actually used in this run: `browser`, `spreadsheets`, `documents`.
- Not triggered because the current task did not request them or prerequisites are absent: `security-best-practices`, `security-threat-model`, `security-ownership-map`, `sentry`, `jupyter-notebook`, `chatgpt-apps`, `openai-docs`, `presentations`, `imagegen`, `github`.

Updated results:

- Browser: app loaded with title `Metallocene EPDM Digital Twin`; navigation labels for `模型治理与可信度证书` and `报告导出` were visible; quick simulation button and process inputs were visible. A direct radio-click attempt hit Streamlit hidden-radio visibility behavior in the browser runtime, but repo-native `ui_e2e_workflow.py` passed and confirmed 15 pages, 18 manual actions, no missing TaskService mapping and no heavy export actions.
- Spreadsheets: latest `tmp_smoke_outputs/smoke.xlsx` contained 173 sheets, no sheet names over 31 characters, all required V6.5 audit sheets present and 0 formula error matches.
- Documents: latest `tmp_smoke_outputs/smoke.docx` rendered successfully to 12 page PNGs in `tmp_smoke_outputs/docx_render_v6_5_rigor`; no missing report content was observed, but narrow audit tables remain a P3 readability issue.

Strict conclusion:

- Eligible peripheral QA has been partially replaced by professional skills and verified again.
- Runtime math/physics modules are intentionally not replaced by market skills because they encode conservation, unit, phase-equilibrium, residual, benchmark and validity logic.

## 2026-05-20 14:59 Professional Skill QA Rerun

- Browser: Streamlit loaded at `http://127.0.0.1:8501/`; title `Metallocene EPDM Digital Twin`; navigation signals for model governance, report export, dashboard, optimization and experiment data were visible; quick simulation button and core inputs were visible; no heavy-running signal was observed during page presence inspection.
- Spreadsheets: latest `tmp_smoke_outputs/smoke.xlsx` had 173 sheets, 0 names over 31 characters, required audit sheets present and 0 formula error matches.
- Documents: latest `tmp_smoke_outputs/smoke.docx` rendered to 12 PNG pages in `tmp_smoke_outputs/docx_render_v6_5_rigor_latest`.
- PDF: no PDF report artifact was present in `tmp_smoke_outputs`; PDF QA was not applicable.

Conclusion: professional skills continue to cover eligible peripheral QA. They do not replace runtime math/physics logic.

## 2026-05-28 Executable Replacement Harness

The eligible peripheral replacement surface is now backed by an executable repo command:

```powershell
python scripts\dev_tasks.py professional-skill-qa
```

Command result:

- `excel_report_qa` via `spreadsheets`: PASS; latest smoke workbook has 173 sheets, no sheet names over 31 characters, required audit sheets present and no formula-error tokens.
- `word_report_qa` via `documents`: PASS; latest smoke Word report has nonempty paragraphs, 11 tables, 620 table text cells and risk/residual/governance content.
- `ui_browser_contract_qa` via `browser/playwright`: PASS; UI artifacts report 15 registered pages, 18 manual actions, no missing task mappings and no heavy export actions.
- `github_workflow_qa` via `github/yeet`: PASS; repository has GitHub origin `https://github.com/SUNHAOJUN22/metallocene-epdm-digital-twin.git` and remote `main` exists.

New artifacts:

- `tmp_smoke_outputs/professional_skill_qa.json`
- `tmp_smoke_outputs/professional_skill_qa.csv`

Interpretation:

- The parts that should be replaced are now replaced at the workflow level and have a repeatable command.
- Math/physics runtime code remains repo-native by design.
