# MCP Tool Contract

Date: 2026-05-28

## Required Request Fields

Every simulation request uses a guarded envelope:

- `payload`: model input values.
- `units`: explicit unit context.
- `dry_run`: defaults to `true`.
- `run_heavy_task`: defaults to `false`.
- `require_validity`: defaults to `true`.
- `source`: caller label for lineage.

## Unit Context

Supported units are intentionally narrow:

- pressure: `Pa`, `kPa`, `MPa`
- temperature: `K`, `C`, `degC`, `°C`
- concentration: `mol/L`, `mol/m3`
- power: `kJ/h`, `kW`
- viscosity: `cP`, `Pa.s`, `Pa·s`
- mass flow: `kg/h`
- molar flow: `mol/h`, `kmol/h`

Unsupported units are rejected before model execution.

## Response Contract

Tool responses include:

- `tool_name`
- `status`
- `message`
- `data`
- `residual_summary` when available
- `validity` when preflight applies
- `lineage`
- `heavy_task_executed`
- `warnings`

## Status Values

- `ok`: accepted and completed.
- `not_run`: dry run or intentionally non-executing endpoint.
- `warning`: reportable non-critical concern.
- `rejected`: failed preflight, invalid tool, or residual acceptance failure.

## Heavy-Task Policy

The MCP interface does not automatically execute ODE, CFD, optimizer, posterior, DOE, uncertainty, report export or repro export heavy paths. Those remain explicit TaskService/UI-action workstreams.
