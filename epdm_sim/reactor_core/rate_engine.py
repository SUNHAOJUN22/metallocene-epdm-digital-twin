"""Template rate-engine wrapper."""

from __future__ import annotations

from typing import Any

from ..kinetics import calculate_template_rates


def template_rate_engine(template_id: str, concentrations: dict[str, float], catalyst_state: dict[str, float], conditions: dict[str, float], parameters: Any) -> dict[str, float]:
    """Return nonnegative template rates in mol/L/h."""
    result = calculate_template_rates(template_id, concentrations, catalyst_state, conditions, parameters)
    return {key: max(float(value), 0.0) for key, value in result.rates_mol_L_h.items()}

