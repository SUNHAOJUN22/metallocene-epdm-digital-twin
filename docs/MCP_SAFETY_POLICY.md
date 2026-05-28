# MCP Safety Policy

Date: 2026-05-28

## Non-Negotiable Rules

The MCP-style interface must not:

- replace the mathematical or physical runtime kernel;
- hide NaN, inf, negative physical values or critical residuals;
- convert a critical residual into a warning to pass a gate;
- run heavy tasks by page navigation, report export, dry run or generic tool calls;
- accept outside-validity optimizer/DOE/posterior candidates.

## Preflight Checks

The following checks run before scientific execution:

1. explicit unit context validation;
2. recursive NaN/inf rejection;
3. negative absolute temperature rejection;
4. validity-envelope rejection for common fields;
5. heavy-task permission checks.

## Residual Safety

When flowsheet execution is explicitly allowed, the result is summarized through the existing `ResidualSystem`. A critical residual or failing residual acceptance returns `rejected`.

## Skill Boundary

Professional skills can own peripheral QA:

- Browser/Playwright: UI navigation checks.
- Spreadsheets: Excel artifact inspection.
- Documents/PDF: report rendering checks.
- GitHub: publication/PR/CI workflow checks.
- ChatGPT Apps/OpenAI Docs: future MCP/widget integration guidance.

They must not replace flash/EOS, ODE/DAE, residual acceptance, benchmark validation or release gates.
