# MCP-Style Scientific Simulation Interface Design

Date: 2026-05-28

This document defines the repository-native MCP-style interface added for external scientific workflow integrations.

## Scope

The interface is intentionally tool-only. It provides governed entry points for external clients and future ChatGPT Apps/MCP integrations without replacing the scientific runtime kernel.

The following runtime kernels remain repository-owned and release-gated:

- `ResidualSystem`
- flash/EOS and phase-equilibrium logic
- heat balance, recycle and flowsheet calculations
- dynamic ODE/DAE logic
- benchmark, data-lineage and evidence-chain gates
- optimizer/DOE/posterior residual acceptance

## Package Layout

- `epdm_sim/mcp/schemas.py`: pydantic request/response schemas and unit context.
- `epdm_sim/mcp/safety.py`: preflight checks for units, finite values, validity and heavy-task permission.
- `epdm_sim/mcp/lineage.py`: model-version and tool-call lineage snapshots.
- `epdm_sim/mcp/adapters.py`: adapters into existing ProcessConfig and ResidualSystem summaries.
- `epdm_sim/mcp/tools.py`: guarded tool functions.
- `epdm_sim/mcp/server.py`: in-process registry and dispatch helper.

## Tool Boundary

Default behavior is `dry_run=True`. Scientific calculations and heavy tasks do not execute unless the request explicitly opts in with `dry_run=False` and, for heavy task IDs, `run_heavy_task=True`.

The interface is designed for:

- external preflight validation;
- reportable metadata and governance snapshots;
- safe dry-run checks before UI or automation calls;
- future MCP/ChatGPT Apps integration.

It is not designed to bypass Streamlit TaskService, UI action registry, release gates, or model audit contracts.

## Current Tools

- `get_model_metadata`
- `validate_simulation_input`
- `run_flowsheet_simulation`
- `run_flash_calculation`
- `run_heat_balance`
- `run_dynamic_reactor`
- `run_residual_aware_optimizer`
- `run_residual_aware_doe`
- `generate_report_snapshot`
- `get_model_governance_certificate`

## Acceptance

The MCP layer is accepted only when:

- unit preflight rejects unsupported units;
- NaN/inf inputs are rejected;
- negative absolute temperature is rejected;
- outside-validity fields are rejected when required;
- heavy tasks cannot run without explicit permission;
- dry-run tool calls do not execute heavy model paths;
- flowsheet execution, when explicitly allowed, returns a bounded ResidualSystem summary.
