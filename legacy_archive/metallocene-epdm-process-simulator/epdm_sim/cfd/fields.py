"""CFD field containers and scalar diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .mesh import StructuredMesh


@dataclass
class CFDFields:
    """Scalar and vector fields on a structured CFD mesh."""

    u: np.ndarray
    v: np.ndarray
    p: np.ndarray
    T: np.ndarray
    C_E: np.ndarray
    C_P: np.ndarray
    C_ENB: np.ndarray
    solids_wt: np.ndarray
    mu: np.ndarray
    fouling_index: np.ndarray

    def field(self, name: str) -> np.ndarray:
        """Return a named field array."""
        mapping = {
            "velocity": np.sqrt(self.u**2 + self.v**2),
            "pressure": self.p,
            "temperature": self.T,
            "ethylene": self.C_E,
            "propylene": self.C_P,
            "ENB": self.C_ENB,
            "solids": self.solids_wt,
            "viscosity": self.mu,
            "fouling": self.fouling_index,
        }
        if name not in mapping:
            raise KeyError(f"Unknown CFD field: {name}")
        return mapping[name]


@dataclass
class CFDDiagnostics:
    """Engineering diagnostics from the CFD-style fields."""

    average_velocity_m_s: float
    max_velocity_m_s: float
    Reynolds: float
    pressure_drop_Pa: float
    pump_power_kW: float
    max_temperature_C: float
    average_temperature_C: float
    max_temperature_rise_K: float
    hotspot_location_m: tuple[float, float]
    min_ENB_location_m: tuple[float, float]
    max_viscosity_location_m: tuple[float, float]
    wall_max_fouling_risk: float
    dead_zone_fraction: float
    mixing_index: float
    corrected_heat_transfer_U_W_m2K: float
    suggested_agitation_rpm: float
    suggested_max_solids_wt: float
    recommended_cooling_duty_kW: float
    recommendations: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        """Return diagnostics as a table."""
        return pd.DataFrame(
            [
                ("平均速度", self.average_velocity_m_s, "m/s"),
                ("最大速度", self.max_velocity_m_s, "m/s"),
                ("Reynolds number", self.Reynolds, "-"),
                ("压降", self.pressure_drop_Pa / 1000.0, "kPa"),
                ("泵功率", self.pump_power_kW, "kW"),
                ("最高温度", self.max_temperature_C, "°C"),
                ("平均温度", self.average_temperature_C, "°C"),
                ("最大温升", self.max_temperature_rise_K, "K"),
                ("壁面最大挂胶风险", self.wall_max_fouling_risk, "-"),
                ("死区比例", self.dead_zone_fraction, "-"),
                ("混合均匀性指数", self.mixing_index, "-"),
                ("修正传热系数", self.corrected_heat_transfer_U_W_m2K, "W/m2/K"),
                ("建议搅拌转速", self.suggested_agitation_rpm, "rpm"),
                ("建议最高固含", self.suggested_max_solids_wt, "wt%"),
                ("推荐冷却负荷", self.recommended_cooling_duty_kW, "kW"),
            ],
            columns=["item", "value", "unit"],
        )


def masked_stats(mesh: StructuredMesh, values: np.ndarray) -> dict[str, float]:
    """Return min, max, mean and std on active mesh cells."""
    active = values[mesh.mask]
    if active.size == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}
    return {
        "min": float(np.nanmin(active)),
        "max": float(np.nanmax(active)),
        "mean": float(np.nanmean(active)),
        "std": float(np.nanstd(active)),
    }


def location_of_extreme(mesh: StructuredMesh, values: np.ndarray, mode: str = "max") -> tuple[float, float]:
    """Return x,y location for a field maximum or minimum inside active cells."""
    masked = np.where(mesh.mask, values, np.nan)
    index = np.nanargmin(masked) if mode == "min" else np.nanargmax(masked)
    iy, ix = np.unravel_index(index, values.shape)
    return float(mesh.X[iy, ix]), float(mesh.Y[iy, ix])
