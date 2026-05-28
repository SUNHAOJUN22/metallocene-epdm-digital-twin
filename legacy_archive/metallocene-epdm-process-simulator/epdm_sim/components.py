"""Component data models and loaders."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 fallback
    ConfigDict = None

from .utils import data_path, load_json


class Component(BaseModel):
    """Pure component data used by simplified process calculations.

    Units:
    - MW: g/mol
    - Tc, Tb: K
    - Pc: Pa
    - Cp_liq, Cp_gas: kJ/kg/K
    - density_liq: kg/m3
    """

    name: str
    formula: str
    MW: float = Field(gt=0)
    Tc: float = Field(gt=0)
    Pc: float = Field(gt=0)
    omega: float
    Tb: float = Field(gt=0)
    Cp_liq: float = Field(gt=0)
    Cp_gas: float = Field(gt=0)
    density_liq: float = Field(gt=0)
    Tc_K: Optional[float] = None
    Pc_Pa: Optional[float] = None
    Cp_liq_kJ_kgK: Optional[float] = None
    Cp_gas_kJ_kgK: Optional[float] = None
    Cp_solid_kJ_kgK: Optional[float] = None
    liquid_density_kg_m3: Optional[float] = None
    density_kg_m3: Optional[float] = None
    viscosity_Pa_s: Optional[float] = None
    thermal_conductivity_W_mK: Optional[float] = None
    property_source: str = "default engineering estimate"
    Antoine_A: Optional[float] = None
    Antoine_B: Optional[float] = None
    Antoine_C: Optional[float] = None
    type: str = "liquid"

    if ConfigDict is not None:
        model_config = ConfigDict(extra="ignore")
    else:  # pragma: no cover - pydantic v1 fallback
        class Config:
            extra = "ignore"

    @property
    def mw_kg_per_mol(self) -> float:
        """Molecular weight in kg/mol."""
        return self.MW / 1000.0


@lru_cache(maxsize=1)
def load_components() -> dict[str, Component]:
    """Load component records from data/components.json."""
    payload = load_json(data_path("components.json"))
    return {name: Component(**record) for name, record in payload.items()}


def get_component(name: str) -> Component:
    """Return a component by name."""
    components = load_components()
    if name not in components:
        raise KeyError(f"Unknown component: {name}")
    return components[name]


def component_dataframe() -> pd.DataFrame:
    """Return component properties as a DataFrame for UI display."""
    rows = []
    for component in load_components().values():
        rows.append(component.model_dump() if hasattr(component, "model_dump") else component.dict())
    return pd.DataFrame(rows)


def solvent_names() -> list[str]:
    """Return available solvent identifiers."""
    return [name for name, comp in load_components().items() if comp.type == "solvent"]
