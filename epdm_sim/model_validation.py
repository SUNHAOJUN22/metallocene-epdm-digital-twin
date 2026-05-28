"""Validation utilities for model contracts and registry entries."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .model_contracts import ModelContract, load_model_contracts
from .model_registry import load_model_registry, validate_model_registry


@dataclass(frozen=True)
class ModelValidationIssue:
    """One model-contract validation issue."""

    model_id: str
    severity: str
    message: str
    suggested_fix: str

    def as_dict(self) -> dict[str, str]:
        """Return a table row."""
        return {
            "model_id": self.model_id,
            "severity": self.severity,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


def validate_model_contract(contract: ModelContract) -> list[ModelValidationIssue]:
    """Validate one model contract for completeness and UI safety."""
    issues: list[ModelValidationIssue] = []
    if not contract.inputs:
        issues.append(ModelValidationIssue(contract.model_id, "error", "inputs are missing", "Add registry inputs."))
    if not contract.outputs:
        issues.append(ModelValidationIssue(contract.model_id, "error", "outputs are missing", "Add registry outputs."))
    if not contract.required_units:
        issues.append(ModelValidationIssue(contract.model_id, "error", "required_units are missing", "Declare input/output units."))
    if not contract.validation_rules:
        issues.append(ModelValidationIssue(contract.model_id, "error", "validation rules are missing", "Add mathematical and engineering checks."))
    if contract.trigger_mode == "button_manual" and "cache" not in " ".join(contract.validation_rules).lower():
        issues.append(
            ModelValidationIssue(
                contract.model_id,
                "warning",
                "manual task does not explicitly mention cache/hash validation",
                "Record input hash and task status for long-running modules.",
            )
        )
    if contract.trigger_mode == "auto_cached" and "hash" not in " ".join(contract.validation_rules).lower():
        issues.append(
            ModelValidationIssue(
                contract.model_id,
                "warning",
                "auto-cached model does not explicitly mention input hash",
                "Add input-hash/cache validation in registry checks.",
            )
        )
    return issues


def validate_all_model_contracts() -> list[ModelValidationIssue]:
    """Validate registry and all active model contracts."""
    issues = [
        ModelValidationIssue("model_registry", "error", error, "Fix data/model_registry.json.")
        for error in validate_model_registry(load_model_registry())
    ]
    for contract in load_model_contracts():
        issues.extend(validate_model_contract(contract))
    return issues


def validation_dataframe() -> pd.DataFrame:
    """Return all model-validation issues as a DataFrame."""
    rows = [issue.as_dict() for issue in validate_all_model_contracts()]
    return pd.DataFrame(rows, columns=["model_id", "severity", "message", "suggested_fix"])
