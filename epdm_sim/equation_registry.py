"""Machine-readable equation registry for formulas and model audit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .utils import data_path, load_json


@dataclass(frozen=True)
class EquationSpec:
    """One model equation and its unit metadata."""

    equation_id: str
    module_id: str
    display_name: str
    formula_text: str
    variables: list[str]
    variable_units: dict[str, str]
    output_unit: str
    assumptions: str = ""
    validity_range: str = ""
    dimensional_check: str = ""
    fallback: str = ""
    references_or_origin: str = ""
    implementation_function: str = ""
    input_units: dict[str, str] = field(default_factory=dict)
    dimensional_signature: str = ""
    expected_trends: str = ""
    benchmark_id: str = ""
    fallback_policy: str = ""
    residual_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        row = self.__dict__.copy()
        row["variables"] = ", ".join(self.variables)
        row["variable_units"] = str(self.variable_units)
        row["input_units"] = str(self.input_units or self.variable_units)
        return row


def load_equation_registry(path: str | None = None) -> dict[str, EquationSpec]:
    """Load the equation registry from JSON."""
    payload = load_json(data_path("equation_registry.json") if path is None else path)
    return {item["equation_id"]: EquationSpec(**item) for item in payload.get("equations", [])}


def equation_registry_dataframe(registry: dict[str, EquationSpec] | None = None) -> pd.DataFrame:
    """Return equations as a report table."""
    registry = load_equation_registry() if registry is None else registry
    return pd.DataFrame([spec.as_dict() for spec in registry.values()])


def validate_equation_registry(registry: dict[str, EquationSpec] | None = None) -> list[str]:
    """Return schema-level warnings for incomplete equation records."""
    registry = load_equation_registry() if registry is None else registry
    warnings: list[str] = []
    for equation_id, spec in registry.items():
        if not spec.module_id:
            warnings.append(f"{equation_id} missing module_id")
        if not spec.formula_text:
            warnings.append(f"{equation_id} missing formula")
        if not spec.output_unit:
            warnings.append(f"{equation_id} missing output_unit")
        missing_units = [var for var in spec.variables if var not in spec.variable_units]
        if missing_units:
            warnings.append(f"{equation_id} missing units for {missing_units}")
    return warnings


def equations_by_module() -> dict[str, list[str]]:
    """Return equation ids grouped by module id."""
    grouped: dict[str, list[str]] = {}
    for equation in load_equation_registry().values():
        grouped.setdefault(equation.module_id, []).append(equation.equation_id)
    return grouped
