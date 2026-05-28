"""Physical parameter constraints for estimation, posterior and uncertainty."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


PARAMETER_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "k_E_ref": {"bounds": (0.0, 5000.0), "unit": "L/mol/h", "prior": "log-uniform", "meaning": "ethylene insertion apparent rate", "validity_range": "local EPDM/EPM calibration"},
    "k_P_ref": {"bounds": (0.0, 5000.0), "unit": "L/mol/h", "prior": "log-uniform", "meaning": "propylene insertion apparent rate", "validity_range": "local EPDM/EPM calibration"},
    "k_ENB_ref": {"bounds": (0.0, 1000.0), "unit": "L/mol/h", "prior": "log-uniform", "meaning": "ENB insertion apparent rate", "validity_range": "local EPDM/EPM calibration"},
    "Ea_E_J_mol": {"bounds": (0.0, 200000.0), "unit": "J/mol", "prior": "bounded-normal", "meaning": "ethylene activation energy", "validity_range": "Arrhenius screening"},
    "Ea_P_J_mol": {"bounds": (0.0, 200000.0), "unit": "J/mol", "prior": "bounded-normal", "meaning": "propylene activation energy", "validity_range": "Arrhenius screening"},
    "Ea_ENB_J_mol": {"bounds": (0.0, 200000.0), "unit": "J/mol", "prior": "bounded-normal", "meaning": "ENB activation energy", "validity_range": "Arrhenius screening"},
    "beta_P": {"bounds": (0.0, 10.0), "unit": "1/MPa", "prior": "bounded-normal", "meaning": "ENB pressure penalty", "validity_range": "0.7-2.0 MPa pressure studies"},
    "beta_E": {"bounds": (0.0, 10.0), "unit": "L/mol", "prior": "bounded-normal", "meaning": "ethylene competition penalty", "validity_range": "local E/ENB gradient studies"},
    "ktr_H2": {"bounds": (0.0, 100.0), "unit": "1/(mol/L)", "prior": "bounded-normal", "meaning": "hydrogen chain-transfer strength", "validity_range": "H2 gradient studies"},
    "Mw0": {"bounds": (10000.0, 2000000.0), "unit": "g/mol", "prior": "bounded-normal", "meaning": "zero-H2 molecular-weight scale", "validity_range": "GPC/Mooney calibrated grades"},
    "kd_h": {"bounds": (0.0, 10.0), "unit": "1/h", "prior": "bounded-normal", "meaning": "catalyst deactivation rate", "validity_range": "time-series or residence-time data"},
}


@dataclass(frozen=True)
class ParameterConstraintResult:
    """One parameter-constraint validation result."""

    parameter: str
    value: float
    unit: str
    lower: float
    upper: float
    passed: bool
    severity: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parameter_constraints_dataframe() -> pd.DataFrame:
    """Return configured parameter constraints."""
    return pd.DataFrame(
        [
            {
                "parameter": name,
                "lower": payload["bounds"][0],
                "upper": payload["bounds"][1],
                "unit": payload["unit"],
                "prior": payload["prior"],
                "physical_meaning": payload["meaning"],
                "validity_range": payload.get("validity_range", "registered physical bounds"),
            }
            for name, payload in PARAMETER_CONSTRAINTS.items()
        ]
    )


def validate_parameter_value(name: str, value: float) -> ParameterConstraintResult:
    """Validate one parameter against physical bounds."""
    payload = PARAMETER_CONSTRAINTS.get(name)
    if payload is None:
        return ParameterConstraintResult(name, float(value), "unknown", float("-inf"), float("inf"), True, "warning", "Unknown parameter; no physical bounds registered.")
    lower, upper = payload["bounds"]
    passed = bool(lower <= float(value) <= upper)
    return ParameterConstraintResult(
        name,
        float(value),
        payload["unit"],
        float(lower),
        float(upper),
        passed,
        "ok" if passed else "error",
        "inside physical bounds" if passed else "outside physical parameter bounds",
    )


def validate_parameter_set(params: dict[str, float]) -> list[ParameterConstraintResult]:
    """Validate a parameter dictionary."""
    return [validate_parameter_value(name, value) for name, value in params.items()]


def parameter_constraint_results_dataframe(params: dict[str, float]) -> pd.DataFrame:
    """Return parameter validation results as a DataFrame."""
    return pd.DataFrame([row.as_dict() for row in validate_parameter_set(params)])
