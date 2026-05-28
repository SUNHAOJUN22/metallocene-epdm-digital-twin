"""CFD field containers and scalar diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    C_H2: np.ndarray
    solids_wt: np.ndarray
    mu: np.ndarray
    fouling_index: np.ndarray
    r_E: np.ndarray | None = None
    r_P: np.ndarray | None = None
    r_ENB: np.ndarray | None = None
    r_total: np.ndarray | None = None
    wall_shear: np.ndarray | None = None
    dead_zone_mask: np.ndarray | None = None
    high_fouling_mask: np.ndarray | None = None

    def field(self, name: str) -> np.ndarray:
        """Return a named field array."""
        mapping = {
            "velocity": np.sqrt(self.u**2 + self.v**2),
            "pressure": self.p,
            "temperature": self.T,
            "ethylene": self.C_E,
            "propylene": self.C_P,
            "ENB": self.C_ENB,
            "hydrogen": self.C_H2 if self.C_H2 is not None else np.zeros_like(self.C_E),
            "solids": self.solids_wt,
            "viscosity": self.mu,
            "fouling": self.fouling_index,
            "r_E": self.r_E if self.r_E is not None else np.zeros_like(self.C_E),
            "r_P": self.r_P if self.r_P is not None else np.zeros_like(self.C_E),
            "r_ENB": self.r_ENB if self.r_ENB is not None else np.zeros_like(self.C_E),
            "r_total": self.r_total if self.r_total is not None else np.zeros_like(self.C_E),
            "wall_shear": self.wall_shear if self.wall_shear is not None else np.zeros_like(self.C_E),
            "dead_zone_mask": self.dead_zone_mask if self.dead_zone_mask is not None else np.zeros_like(self.C_E),
            "high_fouling_mask": self.high_fouling_mask if self.high_fouling_mask is not None else np.zeros_like(self.C_E),
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
    temperature_uniformity_index: float
    viscosity_nonuniformity_index: float
    heat_removal_effectiveness: float
    kLa_estimate_h: float
    mixing_time_estimate_s: float
    corrected_heat_transfer_U_W_m2K: float
    suggested_agitation_rpm: float
    suggested_max_solids_wt: float
    recommended_cooling_duty_kW: float
    high_fouling_zone_area_fraction: float = 0.0
    low_shear_area_fraction: float = 0.0
    wall_shear_histogram: list[dict[str, float]] | None = None
    recommendations: list[str] = field(default_factory=list)

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
                ("温度均匀性指数", self.temperature_uniformity_index, "-"),
                ("黏度不均匀性指数", self.viscosity_nonuniformity_index, "-"),
                ("移热有效性", self.heat_removal_effectiveness, "-"),
                ("kLa估算", self.kLa_estimate_h, "1/h"),
                ("混合时间估算", self.mixing_time_estimate_s, "s"),
                ("修正传热系数", self.corrected_heat_transfer_U_W_m2K, "W/m2/K"),
                ("建议搅拌转速", self.suggested_agitation_rpm, "rpm"),
                ("建议最高固含", self.suggested_max_solids_wt, "wt%"),
                ("推荐冷却负荷", self.recommended_cooling_duty_kW, "kW"),
                ("高挂胶区域面积占比", self.high_fouling_zone_area_fraction, "-"),
                ("低剪切区域占比", self.low_shear_area_fraction, "-"),
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
