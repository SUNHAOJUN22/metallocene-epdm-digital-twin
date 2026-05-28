# Market Skill Replacement Plan

Date: 2026-05-20

Purpose: replace repetitive project workstreams with installed market/plugin skills where appropriate, while keeping the EPDM digital twin runtime math core inside the repository.

## Boundary

Market skills replace workflow labor, not runtime scientific code.

Do not replace these runtime modules with skills:

- `epdm_sim/residual_system.py`
- `epdm_sim/residual_solver.py`
- `epdm_sim/flash.py`
- `epdm_sim/eos.py`
- `epdm_sim/thermo.py`
- `epdm_sim/heat_balance.py`
- `epdm_sim/rheology.py`
- `epdm_sim/dynamic_template_reactor.py`
- `epdm_sim/dynamic_core/`
- `epdm_sim/solver_core/`
- `epdm_sim/parameter_estimation.py`
- `epdm_sim/posterior.py`
- `epdm_sim/uncertainty.py`
- `data/equation_registry.json`
- `data/golden_benchmarks.json`
- `data/experimental_benchmarks.json`

These modules encode project-specific chemistry, units, conservation residuals, equation bindings, benchmarks and validation logic. Market skills can inspect, test, report and help repair them, but the model code remains in the project.

## Installed Market Skill Coverage

| Workstream | Replacement Skill | Status | Notes |
| --- | --- | --- | --- |
| Streamlit UI inspection | `browser` | replace manual UI checks | Use for localhost navigation, screenshots, page checks and no-heavy-task navigation validation. |
| Excel report QA | `spreadsheets` | replace manual workbook inspection | Use for `.xlsx` sheet presence, sheet-name limits, formulas, tables and metadata inspection. |
| Word/report QA | `documents` | replace manual `.docx` inspection | Use for rendered page QA, table overflow checks and report layout validation. |
| Slide/reporting packs | `presentations` | replace manual slide generation | Use for version review decks and management summaries. |
| GitHub PR/CI work | `github` | replace manual PR/CI triage | Use for PR summaries, CI failures, review comments and publishing workflows. |
| OpenAI API/Agents work | `openai-docs` | replace ad hoc API lookup | Use only for OpenAI API, Agents SDK and ChatGPT Apps design questions. |
| Raster visual assets | `imagegen` | replace manual bitmap generation | Use for report covers, concept visuals or bitmap mockups, not for scientific plots. |
| Skill installation | `skill-installer` | replace manual skill installation | Use to install curated or GitHub-hosted skills when the market endpoint is available. |
| Custom workflow creation | `skill-creator` | fallback when no market skill exists | Use only for EPDM-specific workflows that market skills do not cover. |
| Plugin scaffolding | `plugin-creator` | replace manual plugin boilerplate | Use if the digital twin needs to be exposed as a Codex plugin. |

## Additional Skills Installed From The Market

The GitHub API listing path was rate-limited, but the OpenAI skills repository was reachable through git. The following curated market skills were installed from `openai/skills` into `C:\Users\resj6\.codex\skills` on 2026-05-20:

| Installed skill | Intended replacement workstream | Math/physics boundary |
| --- | --- | --- |
| `playwright` | terminal-driven browser automation, UI-flow debugging, screenshots and data extraction | May validate UI behavior, but cannot replace residual or benchmark gates. |
| `playwright-interactive` | persistent browser/Electron debugging for iterative UI QA | May inspect Streamlit interactions, but heavy tasks must still go through TaskService. |
| `screenshot` | OS-level screenshot fallback for visual QA | Only for visual capture; not scientific evidence. |
| `pdf` | PDF reading, generation, rendering and layout QA | Useful for report artifacts; not a substitute for report/repro consistency gates. |
| `security-best-practices` | Python/JS secure-by-default code review | Can review app/security posture; not a math-core validator. |
| `security-threat-model` | repository-grounded AppSec threat modeling | Can document trust boundaries and mitigations; not a process-model validator. |
| `security-ownership-map` | git-history grounded security ownership and bus-factor analysis | Useful after the project is in a git repo; not usable for the current non-git folder. |
| `sentry` | read-only production error and issue inspection through Sentry CLI | Useful after Sentry CLI/auth is configured; not a local math validator. |
| `jupyter-notebook` | notebook scaffolding for experiments and calibration analysis | Useful for calibration notebooks; production model logic remains in repo modules. |
| `chatgpt-apps` | ChatGPT Apps SDK and MCP/widget integration work | Useful for future app integration; must use `openai-docs` first for docs-aligned implementation. |

These newly installed skills may require restarting Codex before they appear in the active skill list for automatic triggering.

## Replacement Matrix

| Project Work Module | Use Market Skill | Required Project Gate |
| --- | --- | --- |
| UI page navigation and governance page visibility | `browser` | `python scripts\ui_e2e_smoke.py`, `python scripts\ui_e2e_workflow.py` |
| UI action registry usability | `browser` for visual inspection, repo tests for contract | `ui_action_usability_gate`, `tests/test_ui_action_usability.py` |
| Excel report audit | `spreadsheets` | `excel_required_sheets`, `excel_sheet_name_compatibility_gate` |
| Word report audit | `documents` | `word_export_nonempty` and rendered report QA |
| Repro package audit | no direct market replacement; use repo gates | `report_repro_industrial_audit_gate` |
| GitHub PR release workflow | `github` | repo-local `release_gate.py` before PR |
| OpenAI agent/app integration design | `openai-docs` | no code change until official docs are checked |
| Version summary deck | `presentations` | release facts from `docs/TEST_REPORT.md` and `docs/QUALITY_BASELINE.md` |
| Visual explanation assets | `imagegen` | keep scientific charts generated by code, not imagegen |

## Standard Skill-Based Prompts

### Browser

```text
使用 browser skill 打开 http://127.0.0.1:8501，检查首页、诊断页、报告页和 model governance page。确认页面切换不触发 ODE/CFD/optimizer/posterior/DOE，导出按钮存在且不会自动重跑重任务。
```

### Spreadsheets

```text
使用 spreadsheets skill 检查最新 Excel 报告。验证 required sheets 存在，sheet name <= 31，metadata hash 一致，residual_system、unit_conversion_trace、benchmark_acceptance、evidence_chain、property_model_runtime、dynamic_solver_policy sheets 非空。
```

### Documents

```text
使用 documents skill 渲染并检查最新 Word 报告。确认标题、表格、风险摘要、residual diagnostics、benchmark evidence、model confidence certificate 排版正常，没有空页、表格溢出或缺失图。
```

### GitHub

```text
使用 GitHub skill，基于当前本地修改创建质量审计 PR。PR 描述必须包含 pytest、auto_functional_audit、function_inventory、release_gate、Streamlit HTTP 和剩余 P3 风险。
```

### OpenAI Docs

```text
使用 openai-docs skill 查官方最新 OpenAI Agents SDK / Apps SDK 文档，给出把本项目 TaskService、UI action registry 和 report/repro package 接入智能实验助手的实现方案。
```

## Non-Replacement Rules

- Do not outsource conservation logic to a generic market skill.
- Do not use generated text or image assets as scientific evidence.
- Do not replace equation registry, benchmark registry or residual gates with prose review.
- Do not let UI/browser checks replace pytest, auto functional audit or release gate.
- Do not let spreadsheets/documents QA replace report/repro consistency gates.

## Operational Use

For future work, call skills explicitly in the user prompt:

```text
使用 browser + spreadsheets + documents，对 D:\codex\metallocene-epdm-digital-twin 做 report/repro/UI 可用性验收。保持数理模型不变，失败则小步修复并更新 changelog。
```

For math-core development, continue using repo-native tests and release gates first. Add market skills only for UI/report/document/GitHub/OpenAI-facing workstreams.

## Actual Replacement Audit

See `docs/MARKET_SKILL_ACTUAL_REPLACEMENT_AUDIT.md` for the first actual execution pass:

- `browser` was used to open and inspect the Streamlit app.
- `spreadsheets` was used to import and inspect the latest Excel report.
- `documents` was used to render and visually inspect the latest Word report.

The audit confirmed that professional skills can replace eligible peripheral QA workflows, while runtime math/physics logic remains repo-native and release-gated.
