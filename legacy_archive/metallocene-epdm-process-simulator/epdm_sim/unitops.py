"""Unit operation abstractions for the EPDM process flowsheet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 fallback
    ConfigDict = None

from .flash import Flash
from .flowsheet import calculate_preheat, quench_reactor
from .kinetics import KineticParameters
from .reactor import simulate_reactor
from .streams import Stream, mix_streams
from .utils import c_to_k, mpa_to_pa, positive


class UnitOperation(BaseModel, ABC):
    """Base class for process unit operation blocks."""

    name: str
    inlet_streams: list[Stream] = Field(default_factory=list)
    outlet_streams: list[Stream] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)

    if ConfigDict is not None:
        model_config = ConfigDict(arbitrary_types_allowed=True)
    else:  # pragma: no cover - pydantic v1 fallback
        class Config:
            arbitrary_types_allowed = True

    @abstractmethod
    def calculate(self, *args: Any, **kwargs: Any) -> Any:
        """Run the unit operation calculation and update outlet streams."""


class Mixer(UnitOperation):
    """Mixer block that combines material streams."""

    def calculate(self, *args: Any, **kwargs: Any) -> Stream:
        """Mix inlet streams."""
        outlet = mix_streams(f"{self.name} outlet", self.inlet_streams)
        self.outlet_streams = [outlet]
        self.results = {"total_kg_h": outlet.total_mass_flow(), "solids_wt": outlet.solids_wt}
        return outlet


class Heater(UnitOperation):
    """Preheater block with constant-Cp heat-duty estimate."""

    target_temperature_K: float

    def calculate(self, *args: Any, **kwargs: Any) -> tuple[Stream, dict[str, float]]:
        """Heat one inlet stream to target temperature."""
        outlet, duty, cp_mix = calculate_preheat(self.inlet_streams[0], self.target_temperature_K)
        outlet.name = f"{self.name} outlet"
        self.outlet_streams = [outlet]
        self.results = {"Q_preheat_kJ_h": duty, "Cp_mix_kJ_kg_K": cp_mix}
        return outlet, self.results


class Reactor(UnitOperation):
    """Polymerization reactor block wrapper."""

    temperature_C: float
    pressure_MPa: float
    residence_time_min: float
    reactor_volume_L: float
    catalyst_umol_h: float
    AlTi_ratio: float
    BHT_ratio: float = 0.0
    mode: str = "CSTR series"
    num_cstr: int = 2

    def calculate(self, *args: Any, **kwargs: Any):
        """Run polymerization reactor model."""
        result = simulate_reactor(
            self.inlet_streams[0],
            temperature_K=c_to_k(self.temperature_C),
            pressure_MPa=self.pressure_MPa,
            residence_time_min=self.residence_time_min,
            reactor_volume_L=self.reactor_volume_L,
            catalyst_umol_h=self.catalyst_umol_h,
            AlTi_ratio=self.AlTi_ratio,
            BHT_ratio=self.BHT_ratio,
            mode=self.mode,
            num_cstr=self.num_cstr,
            params=KineticParameters(),
        )
        self.outlet_streams = [result.outlet]
        self.results = {
            "Q_rxn_kJ_h": result.heat_duty_kJ_h,
            "polymer_kg_h": result.polymer_kg_h,
            "Cstar_mol_L": result.Cstar_mol_L,
        }
        return result


class Quench(UnitOperation):
    """Catalyst deactivation/quench block."""

    catalyst_umol_h: float = 0.0

    def calculate(self, *args: Any, **kwargs: Any) -> tuple[Stream, dict[str, Any]]:
        """Deactivate catalyst using the shared quench estimate."""
        config_like = type("ConfigLike", (), {"catalyst_umol_h": self.catalyst_umol_h})()
        outlet, results = quench_reactor(self.inlet_streams[0], config_like)
        outlet.name = f"{self.name} outlet"
        self.outlet_streams = [outlet]
        self.results = results
        return outlet, results


class FlashUnit(UnitOperation):
    """Flash block wrapper."""

    temperature_C: float
    pressure_MPa: float
    thermo_mode: str = "Simple Wilson K"

    def calculate(self, *args: Any, **kwargs: Any):
        """Run isothermal flash calculation."""
        result = Flash(self.name, self.thermo_mode).calculate(
            self.inlet_streams[0],
            c_to_k(self.temperature_C),
            mpa_to_pa(self.pressure_MPa),
        )
        self.outlet_streams = [result.vapor, result.liquid]
        self.results = {"vapor_fraction": result.vapor_fraction, "duty_kJ_h": result.duty_kJ_h}
        return result


class Splitter(UnitOperation):
    """Simple fraction splitter, useful for purge/recycle blocks."""

    split_fraction: float = 0.05

    def calculate(self, *args: Any, **kwargs: Any) -> tuple[Stream, Stream]:
        """Split inlet stream into purge and recycle streams."""
        feed = self.inlet_streams[0]
        purge = feed.copy_stream(f"{self.name} purge")
        recycle = feed.copy_stream(f"{self.name} recycle")
        fraction = min(max(self.split_fraction, 0.0), 1.0)
        for stream, factor in [(purge, fraction), (recycle, 1.0 - fraction)]:
            stream.molar_flows = {key: positive(value) * factor for key, value in feed.molar_flows.items()}
            stream.mass_flows = {key: positive(value) * factor for key, value in feed.mass_flows.items()}
            stream.polymer_mass_kg_h = positive(feed.polymer_mass_kg_h) * factor
            stream.segment_masses_kg_h = {
                key: positive(value) * factor for key, value in feed.segment_masses_kg_h.items()
            }
            stream.update_solids()
        self.outlet_streams = [purge, recycle]
        self.results = {
            "purge_kg_h": purge.total_mass_flow(),
            "recycle_kg_h": recycle.total_mass_flow(),
            "split_fraction": fraction,
        }
        return purge, recycle


class RecycleBlock(UnitOperation):
    """Simplified recycle accounting block without rigorous tear-stream iteration."""

    purge_fraction: float = 0.05

    def calculate(self, *args: Any, **kwargs: Any) -> dict[str, float]:
        """Calculate total purge and recycle material from inlet streams."""
        total = sum(stream.total_mass_flow() for stream in self.inlet_streams)
        purge = total * min(max(self.purge_fraction, 0.0), 1.0)
        recycle = total - purge
        self.outlet_streams = []
        self.results = {"total_recoverable_kg_h": total, "purge_kg_h": purge, "recycle_kg_h": recycle}
        return self.results
