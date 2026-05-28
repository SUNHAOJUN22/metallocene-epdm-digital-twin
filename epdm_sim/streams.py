"""Material stream data structures."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 fallback
    ConfigDict = None

from .components import Component, load_components
from .utils import TINY, kg_h_to_mol_h, mol_h_to_kg_h, positive, safe_divide


class Stream(BaseModel):
    """Process stream with component molar and mass flow rates.

    Flow conventions:
    - molar_flows: mol/h
    - mass_flows: kg/h for non-polymer molecular components
    - polymer_mass_kg_h: kg/h of formed polymer
    - segment_masses_kg_h: kg/h contribution from E/P/D incorporated units
    """

    name: str
    temperature_K: float
    pressure_Pa: float
    molar_flows: Dict[str, float] = Field(default_factory=dict)
    mass_flows: Dict[str, float] = Field(default_factory=dict)
    phase: str = "liquid"
    enthalpy_kJ_h: float = 0.0
    polymer_mass_kg_h: float = 0.0
    solids_wt: float = 0.0
    segment_masses_kg_h: Dict[str, float] = Field(default_factory=dict)

    if ConfigDict is not None:
        model_config = ConfigDict(arbitrary_types_allowed=True)
    else:  # pragma: no cover - pydantic v1 fallback
        class Config:
            arbitrary_types_allowed = True

    @classmethod
    def from_mass_flows(
        cls,
        name: str,
        temperature_K: float,
        pressure_Pa: float,
        mass_flows: dict[str, float],
        phase: str = "liquid",
        components: dict[str, Component] | None = None,
    ) -> "Stream":
        """Build a stream from mass flows and component molecular weights."""
        comps = components or load_components()
        clean_mass = {key: positive(value) for key, value in mass_flows.items()}
        molar = {
            key: kg_h_to_mol_h(value, comps[key].MW)
            for key, value in clean_mass.items()
            if key in comps and key != "polymer_pseudo"
        }
        stream = cls(
            name=name,
            temperature_K=temperature_K,
            pressure_Pa=pressure_Pa,
            molar_flows=molar,
            mass_flows=clean_mass,
            phase=phase,
        )
        stream.update_solids()
        return stream

    def copy_stream(self, name: str | None = None) -> "Stream":
        """Return a deep copy, optionally with a new name."""
        clone = deepcopy(self)
        if name:
            clone.name = name
        return clone

    def sync_mass_from_moles(self, components: dict[str, Component] | None = None) -> None:
        """Recompute mass flows from molar flows for molecular components."""
        comps = components or load_components()
        self.mass_flows = {
            key: mol_h_to_kg_h(value, comps[key].MW)
            for key, value in self.molar_flows.items()
            if key in comps and key != "polymer_pseudo"
        }
        self.update_solids()

    def sync_moles_from_mass(self, components: dict[str, Component] | None = None) -> None:
        """Recompute molar flows from mass flows for molecular components."""
        comps = components or load_components()
        self.molar_flows = {
            key: kg_h_to_mol_h(value, comps[key].MW)
            for key, value in self.mass_flows.items()
            if key in comps and key != "polymer_pseudo"
        }
        self.update_solids()

    def total_molar_flow(self) -> float:
        """Return total molecular molar flow in mol/h."""
        return sum(positive(value) for value in self.molar_flows.values())

    def molecular_mass_flow(self) -> float:
        """Return non-polymer molecular mass flow in kg/h."""
        return sum(positive(value) for key, value in self.mass_flows.items() if key != "polymer_pseudo")

    def total_mass_flow(self) -> float:
        """Return total stream mass flow including formed polymer in kg/h."""
        return self.molecular_mass_flow() + positive(self.polymer_mass_kg_h)

    def component_mass(self, name: str) -> float:
        """Return mass flow for a molecular component."""
        if name == "polymer_pseudo":
            return positive(self.polymer_mass_kg_h)
        return positive(self.mass_flows.get(name, 0.0))

    def mole_fractions(self) -> dict[str, float]:
        """Return molecular mole fractions, excluding polymer mass."""
        total = self.total_molar_flow()
        if total <= TINY:
            return {key: 0.0 for key in self.molar_flows}
        return {key: positive(value) / total for key, value in self.molar_flows.items()}

    def mass_fractions(self, include_polymer: bool = True) -> dict[str, float]:
        """Return mass fractions."""
        values = {key: positive(value) for key, value in self.mass_flows.items() if key != "polymer_pseudo"}
        if include_polymer:
            values["polymer_pseudo"] = positive(self.polymer_mass_kg_h)
        total = sum(values.values())
        if total <= TINY:
            return {key: 0.0 for key in values}
        return {key: value / total for key, value in values.items()}

    def update_solids(self) -> None:
        """Update solid polymer wt% for the stream."""
        self.solids_wt = 100.0 * safe_divide(positive(self.polymer_mass_kg_h), self.total_mass_flow(), 0.0)

    def add_polymer(self, segment_masses: dict[str, float]) -> None:
        """Add polymer segment masses to the stream."""
        for key, value in segment_masses.items():
            self.segment_masses_kg_h[key] = positive(self.segment_masses_kg_h.get(key, 0.0)) + positive(value)
        self.polymer_mass_kg_h = sum(self.segment_masses_kg_h.values())
        self.update_solids()


def mix_streams(name: str, streams: list[Stream]) -> Stream:
    """Mix streams by adding molar, mass, polymer and segment flows."""
    if not streams:
        return Stream(name=name, temperature_K=298.15, pressure_Pa=101325.0)
    total_mass = sum(stream.total_mass_flow() for stream in streams)
    temperature = safe_divide(
        sum(stream.temperature_K * stream.total_mass_flow() for stream in streams),
        total_mass,
        streams[0].temperature_K,
    )
    pressure = min(stream.pressure_Pa for stream in streams)
    molar: dict[str, float] = {}
    mass: dict[str, float] = {}
    segments: dict[str, float] = {}
    polymer = 0.0
    for stream in streams:
        for key, value in stream.molar_flows.items():
            molar[key] = positive(molar.get(key, 0.0)) + positive(value)
        for key, value in stream.mass_flows.items():
            mass[key] = positive(mass.get(key, 0.0)) + positive(value)
        for key, value in stream.segment_masses_kg_h.items():
            segments[key] = positive(segments.get(key, 0.0)) + positive(value)
        polymer += positive(stream.polymer_mass_kg_h)
    mixed = Stream(
        name=name,
        temperature_K=temperature,
        pressure_Pa=pressure,
        molar_flows=molar,
        mass_flows=mass,
        phase="mixed",
        polymer_mass_kg_h=polymer,
        segment_masses_kg_h=segments,
    )
    mixed.update_solids()
    return mixed
