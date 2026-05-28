"""Data structures and types for the EPDM flowsheet solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field

from .streams import Stream
from .reactor import ReactorResult
from .flash import FlashResult
from .heat_balance import HeatBalanceResult
from .fluid_props import FluidPropertyResult, PipeHydraulicsResult
from .recycle_solver import RecycleSolverResult

@dataclass
class FlowsheetResult:
    """Full process simulation result."""

    config: 'ProcessConfig'
    streams: dict[str, Stream]
    unit_results: dict[str, dict[str, Any]]
    reactor: ReactorResult
    flash1: FlashResult
    flash2: FlashResult
    heat_balance: HeatBalanceResult
    fluid_properties: FluidPropertyResult
    pipe_hydraulics: PipeHydraulicsResult
    recycle_solver: RecycleSolverResult | None
    kpis: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def stream_table(self) -> pd.DataFrame:
        """Return stream summary table."""
        rows = []
        for name, stream in self.streams.items():
            row = {
                "stream": name,
                "T_C": stream.temperature_K - 273.15,
                "P_MPa": stream.pressure_Pa / 1.0e6,
                "phase": stream.phase,
                "total_kg_h": stream.total_mass_flow(),
                "polymer_kg_h": stream.polymer_mass_kg_h,
                "solids_wt": stream.solids_wt,
            }
            for comp in ["ethylene", "propylene", "ENB", "hydrogen", self.config.solvent]:
                row[f"{comp}_kg_h"] = stream.mass_flows.get(comp, 0.0)
            rows.append(row)
        return pd.DataFrame(rows)

    def unit_table(self) -> pd.DataFrame:
        """Return unit operation result table."""
        rows = []
        for unit, values in self.unit_results.items():
            row = {"unit": unit}
            row.update(values)
            rows.append(row)
        return pd.DataFrame(rows)

    def heat_balance_table(self) -> pd.DataFrame:
        """Return heat-balance report table."""
        return self.heat_balance.as_dataframe()

    def fluid_property_table(self) -> pd.DataFrame:
        """Return fluid-property report table."""
        return self.fluid_properties.as_dataframe()

    def pipe_hydraulics_table(self) -> pd.DataFrame:
        """Return pressure-drop and pumping report table."""
        return self.pipe_hydraulics.as_dataframe()

    def recycle_table(self) -> pd.DataFrame:
        """Return recycle solver table when available."""
        if self.recycle_solver is None:
            return pd.DataFrame()
        return self.recycle_solver.as_dataframe()

class ProcessConfig(BaseModel):
    """User-facing process configuration."""

    temperature_C: float = 100.0
    pressure_MPa: float = 1.0
    reactor_volume_L: float = 5.0
    residence_time_min: float = 30.0
    solvent: str = "hexane"
    solvent_mass_kg_h: float = 100.0
    ethylene_kg_h: float = 20.0
    propylene_kg_h: float = 30.0
    enb_kg_h: float = 3.0
    hydrogen_g_h: float = 5.0
    catalyst_umol_h: float = 100.0
    AlTi_ratio: float = 1000.0
    BHT_ratio: float = 0.0
    num_cstr: int = 2
    reactor_mode: str = "Semi-batch Reactor"
    flash1_T_C: float = 80.0
    flash1_P_MPa: float = 0.2
    flash2_T_C: float = 140.0
    flash2_P_MPa: float = 0.02
    purge_fraction: float = Field(default=0.05, ge=0.0, le=1.0)
    thermo_mode: str = "Simple Wilson K"
    deltaH_ethylene_kJ_mol: float = -95.0
    deltaH_propylene_kJ_mol: float = -85.0
    deltaH_ENB_kJ_mol: float = -80.0
    heat_transfer_U_W_m2K: float = 300.0
    heat_transfer_area_m2: float = 2.0
    coolant_inlet_C: float = 25.0
    coolant_outlet_C: float = 35.0
    pipe_length_m: float = 10.0
    pipe_diameter_m: float = 0.025
    pipe_roughness_m: float = 0.000045
    pump_efficiency: float = 0.65
    rheology_model: str = "newtonian"
    power_law_n: float = 0.72
    carreau_lambda_s: float = 1.2
    agitation_rpm: float = 500.0
    impeller_type: str = "pitched blade turbine"
    baffles: bool = True
    feed_nozzle_position: str = "near_impeller"
    parameter_set_id: str = "default"
