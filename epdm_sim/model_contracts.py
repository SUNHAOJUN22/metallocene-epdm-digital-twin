"""Generic model contracts for simulation modules.

Contracts are an adapter layer over the data-driven model registry.  They make
model inputs, outputs, parameters, assumptions, units and validation rules
queryable without forcing each legacy model to inherit from a common base class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .model_registry import ModelModule, load_model_registry


@dataclass(frozen=True)
class ModelContract:
    """A normalized, implementation-independent model contract."""

    model_id: str
    inputs: list[str]
    outputs: list[str]
    parameters: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    validity_range: dict[str, str] = field(default_factory=dict)
    required_units: dict[str, str] = field(default_factory=dict)
    fallback_mode: str = ""
    validation_rules: list[str] = field(default_factory=list)
    trigger_mode: str = "auto_cached"

    @classmethod
    def from_registry_module(cls, module: ModelModule) -> "ModelContract":
        """Build a contract from a registered model module."""
        return cls(
            model_id=module.module_id,
            inputs=list(module.inputs),
            outputs=list(module.outputs),
            parameters=list(module.parameters),
            assumptions=[module.engineering_logic],
            validity_range=dict(module.validity_range),
            required_units=dict(module.required_units),
            fallback_mode=module.fallback,
            validation_rules=list(module.mathematical_checks) + list(module.chemical_engineering_checks),
            trigger_mode=module.trigger_mode,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-like row."""
        return {
            "model_id": self.model_id,
            "inputs": ", ".join(self.inputs),
            "outputs": ", ".join(self.outputs),
            "parameters": ", ".join(self.parameters),
            "required_units": "; ".join(f"{k}: {v}" for k, v in self.required_units.items()),
            "trigger_mode": self.trigger_mode,
            "fallback_mode": self.fallback_mode,
            "validation_rules": " | ".join(self.validation_rules),
        }


def load_model_contracts() -> list[ModelContract]:
    """Load all active model contracts from the registry."""
    return [
        ModelContract.from_registry_module(module)
        for module in load_model_registry()
        if module.status == "active"
    ]


def get_model_contract(model_id: str) -> ModelContract:
    """Return one model contract by id."""
    for contract in load_model_contracts():
        if contract.model_id == model_id:
            return contract
    raise KeyError(f"unknown model contract: {model_id}")


def contracts_dataframe() -> pd.DataFrame:
    """Return contracts as a UI/report table."""
    return pd.DataFrame([contract.to_dict() for contract in load_model_contracts()])
