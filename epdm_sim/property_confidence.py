"""Property source and confidence metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .utils import data_path, load_json


@dataclass(frozen=True)
class PropertySource:
    """One property value and provenance record."""

    property_id: str
    component: str
    property_name: str
    value: float | str
    unit: str
    source_type: str
    temperature_range: str
    pressure_range: str
    uncertainty_pct: float
    confidence_level: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def load_property_sources(path: str | None = None) -> list[PropertySource]:
    """Load property source metadata."""
    payload = load_json(data_path("property_sources.json") if path is None else path)
    return [PropertySource(**item) for item in payload.get("properties", [])]


def property_confidence_dataframe(sources: list[PropertySource] | None = None) -> pd.DataFrame:
    """Return property sources as a DataFrame."""
    sources = load_property_sources() if sources is None else sources
    return pd.DataFrame([item.as_dict() for item in sources])


def get_property_confidence(component: str, property_name: str) -> dict[str, Any]:
    """Return confidence metadata for one component property."""
    for item in load_property_sources():
        if item.component == component and item.property_name == property_name:
            return item.as_dict()
    return {
        "property_id": f"{component}_{property_name}_missing",
        "component": component,
        "property_name": property_name,
        "source_type": "missing",
        "uncertainty_pct": 100.0,
        "confidence_level": "unknown",
        "notes": "No property source metadata found.",
    }


def _level_score(level: str) -> float:
    return {"high": 0.95, "medium": 0.70, "low": 0.40, "unknown": 0.20}.get(str(level).lower(), 0.30)


def propagate_property_uncertainty_to_model_confidence(component_properties: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Aggregate property-confidence metadata into a model-confidence contribution."""
    component_properties = component_properties or [
        ("ethylene", "MW"),
        ("propylene", "MW"),
        ("ENB", "MW"),
        ("hexane", "viscosity_Pa_s"),
        ("polymer_EPDM", "solution_viscosity_model"),
        ("ethylene", "Henry_hexane"),
    ]
    rows = [get_property_confidence(component, prop) for component, prop in component_properties]
    scores = [_level_score(row.get("confidence_level", "unknown")) * max(0.0, 1.0 - float(row.get("uncertainty_pct", 100.0)) / 200.0) for row in rows]
    return {
        "property_confidence_score": float(sum(scores) / max(len(scores), 1) * 100.0),
        "lowest_confidence": min((row.get("confidence_level", "unknown") for row in rows), default="unknown"),
        "records": rows,
    }
