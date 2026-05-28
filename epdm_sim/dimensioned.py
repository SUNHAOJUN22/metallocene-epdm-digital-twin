"""Lightweight dimensioned values for unit-safe scientific checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .utils import kg_h_to_mol_h, mol_h_to_kg_h


UNIT_DEFINITIONS: dict[str, tuple[str, float, float]] = {
    "K": ("temperature", 1.0, 0.0),
    "°C": ("temperature", 1.0, 273.15),
    "C": ("temperature", 1.0, 273.15),
    "Pa": ("pressure", 1.0, 0.0),
    "kPa": ("pressure", 1.0e3, 0.0),
    "MPa": ("pressure", 1.0e6, 0.0),
    "bar": ("pressure", 1.0e5, 0.0),
    "atm": ("pressure", 101325.0, 0.0),
    "kg/h": ("mass_flow", 1.0, 0.0),
    "g/h": ("mass_flow", 1.0e-3, 0.0),
    "mol/h": ("molar_flow", 1.0, 0.0),
    "kmol/h": ("molar_flow", 1.0e3, 0.0),
    "mol/L": ("concentration", 1.0e3, 0.0),
    "mol/m3": ("concentration", 1.0, 0.0),
    "J": ("energy", 1.0, 0.0),
    "kJ": ("energy", 1.0e3, 0.0),
    "W": ("power", 1.0, 0.0),
    "kW": ("power", 1.0e3, 0.0),
    "kJ/h": ("power", 1.0e3 / 3600.0, 0.0),
    "Pa.s": ("viscosity", 1.0, 0.0),
    "Pa·s": ("viscosity", 1.0, 0.0),
    "cP": ("viscosity", 1.0e-3, 0.0),
    "kg/m3": ("density", 1.0, 0.0),
    "m": ("length", 1.0, 0.0),
    "mm": ("length", 1.0e-3, 0.0),
    "s": ("time", 1.0, 0.0),
    "min": ("time", 60.0, 0.0),
    "h": ("time", 3600.0, 0.0),
}

SI_UNITS: dict[str, str] = {
    "temperature": "K",
    "pressure": "Pa",
    "mass_flow": "kg/h",
    "molar_flow": "mol/h",
    "concentration": "mol/m3",
    "energy": "J",
    "power": "W",
    "viscosity": "Pa.s",
    "density": "kg/m3",
    "length": "m",
    "time": "s",
}


@dataclass(frozen=True)
class DimensionedValue:
    """Numeric value carrying a unit, dimension and optional metadata."""

    value: float
    unit: str
    dimension: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        dimension = dimension_for_unit(self.unit)
        if self.dimension is not None and self.dimension != dimension:
            raise ValueError(f"Unit {self.unit!r} has dimension {dimension!r}, not {self.dimension!r}")
        object.__setattr__(self, "dimension", dimension)
        _, scale, offset = UNIT_DEFINITIONS[self.unit]
        base_value = float(self.value) * scale + offset
        if dimension == "temperature" and base_value < 0.0:
            raise ValueError("Absolute temperature cannot be below 0 K")

    def to(self, unit: str) -> "DimensionedValue":
        """Convert to a compatible unit."""
        return DimensionedValue(convert_value(self.value, self.unit, unit), unit, metadata=dict(self.metadata))

    def to_si(self) -> "DimensionedValue":
        """Convert to the project SI/base unit for this dimension."""
        return self.to(SI_UNITS[str(self.dimension)])

    def as_dict(self) -> dict[str, Any]:
        """Return report-friendly metadata."""
        return {"value": self.value, "unit": self.unit, "dimension": self.dimension, **self.metadata}


def dimension_for_unit(unit: str) -> str:
    """Return dimension for a supported unit."""
    if unit not in UNIT_DEFINITIONS:
        raise ValueError(f"Unsupported unit: {unit}")
    return UNIT_DEFINITIONS[unit][0]


def assert_compatible_units(unit_a: str, unit_b: str) -> None:
    """Raise if two units do not share a dimension."""
    dim_a = dimension_for_unit(unit_a)
    dim_b = dimension_for_unit(unit_b)
    if dim_a != dim_b:
        raise ValueError(f"Incompatible units: {unit_a} ({dim_a}) vs {unit_b} ({dim_b})")


def convert_value(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a scalar value between compatible supported units."""
    assert_compatible_units(from_unit, to_unit)
    _, from_scale, from_offset = UNIT_DEFINITIONS[from_unit]
    _, to_scale, to_offset = UNIT_DEFINITIONS[to_unit]
    base = float(value) * from_scale + from_offset
    return (base - to_offset) / to_scale


def as_dimensioned(value: float, unit: str, **metadata: Any) -> DimensionedValue:
    """Create a dimensioned value with metadata."""
    return DimensionedValue(float(value), unit, metadata=metadata)


def _coerce_dimensioned(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], default_unit: str, name: str) -> DimensionedValue:
    """Coerce supported scalar/unit payloads to a DimensionedValue."""
    if isinstance(value, DimensionedValue):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        return DimensionedValue(float(value[0]), str(value[1]), metadata={"name": name})
    if isinstance(value, dict) and "value" in value and "unit" in value:
        return DimensionedValue(float(value["value"]), str(value["unit"]), metadata={k: v for k, v in value.items() if k not in {"value", "unit"}})
    return DimensionedValue(float(value), default_unit, metadata={"name": name, "assumed_unit": default_unit})


def _ensure_unit(
    value: float | DimensionedValue | tuple[float, str] | dict[str, Any],
    *,
    target_unit: str,
    default_unit: str,
    expected_dimension: str,
    name: str,
) -> float:
    """Return a scalar in target_unit after dimension validation."""
    item = _coerce_dimensioned(value, default_unit, name)
    if item.dimension != expected_dimension:
        raise ValueError(f"{name} expects {expected_dimension}, got {item.dimension} ({item.unit})")
    return item.to(target_unit).value


def ensure_temperature_K(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "K") -> float:
    """Return temperature in K and reject negative absolute temperature."""
    return _ensure_unit(value, target_unit="K", default_unit=default_unit, expected_dimension="temperature", name="temperature")


def ensure_pressure_Pa(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "Pa") -> float:
    """Return pressure in Pa and reject non-positive pressure."""
    pressure = _ensure_unit(value, target_unit="Pa", default_unit=default_unit, expected_dimension="pressure", name="pressure")
    if pressure <= 0.0:
        raise ValueError("Pressure must be positive")
    return pressure


def ensure_mass_flow_kg_h(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "kg/h") -> float:
    """Return mass flow in kg/h and reject negative values."""
    flow = _ensure_unit(value, target_unit="kg/h", default_unit=default_unit, expected_dimension="mass_flow", name="mass_flow")
    if flow < 0.0:
        raise ValueError("Mass flow must be nonnegative")
    return flow


def ensure_molar_flow_mol_h(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "mol/h") -> float:
    """Return molar flow in mol/h and reject negative values."""
    flow = _ensure_unit(value, target_unit="mol/h", default_unit=default_unit, expected_dimension="molar_flow", name="molar_flow")
    if flow < 0.0:
        raise ValueError("Molar flow must be nonnegative")
    return flow


def ensure_concentration_mol_L(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "mol/L") -> float:
    """Return concentration in mol/L and reject negative values."""
    concentration = _ensure_unit(value, target_unit="mol/L", default_unit=default_unit, expected_dimension="concentration", name="concentration")
    if concentration < 0.0:
        raise ValueError("Concentration must be nonnegative")
    return concentration


def ensure_power_kW(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "kW") -> float:
    """Return power/heat duty in kW."""
    return _ensure_unit(value, target_unit="kW", default_unit=default_unit, expected_dimension="power", name="power")


def ensure_viscosity_Pa_s(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "Pa.s") -> float:
    """Return viscosity in Pa.s and reject non-positive values."""
    viscosity = _ensure_unit(value, target_unit="Pa.s", default_unit=default_unit, expected_dimension="viscosity", name="viscosity")
    if viscosity <= 0.0:
        raise ValueError("Viscosity must be positive")
    return viscosity


def ensure_density_kg_m3(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "kg/m3") -> float:
    """Return density in kg/m3 and reject non-positive values."""
    density = _ensure_unit(value, target_unit="kg/m3", default_unit=default_unit, expected_dimension="density", name="density")
    if density <= 0.0:
        raise ValueError("Density must be positive")
    return density


def ensure_length_m(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "m", name: str = "length") -> float:
    """Return length in m and reject non-positive values."""
    length = _ensure_unit(value, target_unit="m", default_unit=default_unit, expected_dimension="length", name=name)
    if length <= 0.0:
        raise ValueError(f"{name} must be positive")
    return length


def ensure_time_min(value: float | DimensionedValue | tuple[float, str] | dict[str, Any], *, default_unit: str = "min") -> float:
    """Return time/residence time in min and reject non-positive values."""
    time_min = _ensure_unit(value, target_unit="min", default_unit=default_unit, expected_dimension="time", name="time")
    if time_min <= 0.0:
        raise ValueError("Time must be positive")
    return time_min


def mass_flow_to_molar_flow(value: DimensionedValue, molecular_weight_g_mol: float) -> DimensionedValue:
    """Convert kg/h or g/h to mol/h using molecular weight."""
    kg_h = value.to("kg/h").value
    return DimensionedValue(kg_h_to_mol_h(kg_h, molecular_weight_g_mol), "mol/h", metadata=dict(value.metadata))


def molar_flow_to_mass_flow(value: DimensionedValue, molecular_weight_g_mol: float) -> DimensionedValue:
    """Convert mol/h or kmol/h to kg/h using molecular weight."""
    mol_h = value.to("mol/h").value
    return DimensionedValue(mol_h_to_kg_h(mol_h, molecular_weight_g_mol), "kg/h", metadata=dict(value.metadata))


def unit_conversion_trace_dataframe(records: list[DimensionedValue] | None = None) -> pd.DataFrame:
    """Return a unit-conversion trace used by reports and release gates."""
    records = records or [
        as_dimensioned(100.0, "°C", field="temperature").to("K"),
        as_dimensioned(1.0, "MPa", field="pressure").to("Pa"),
        as_dimensioned(3600.0, "kJ/h", field="heat_duty").to("kW"),
        as_dimensioned(1.0, "cP", field="viscosity").to("Pa.s"),
        as_dimensioned(1.0, "mol/L", field="concentration").to("mol/m3"),
    ]
    rows: list[dict[str, Any]] = []
    for item in records:
        source = item.metadata.get("field", item.metadata.get("name", "value"))
        rows.append(
            {
                "field": source,
                "value": item.value,
                "unit": item.unit,
                "dimension": item.dimension,
                "si_value": item.to_si().value,
                "si_unit": item.to_si().unit,
                "assumed_unit": item.metadata.get("assumed_unit", ""),
                "status": "ok",
            }
        )
    return pd.DataFrame(rows)
