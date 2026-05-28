"""Kettle scale-up and engineering similarity calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .utils import clamp, positive, safe_divide


class ScaleUpCase(BaseModel):
    """Single stirred-kettle scale-up case."""

    name: str
    volume_L: float = 5.0
    rpm: float = 500.0
    impeller_diameter_m: float = 0.08
    tank_diameter_m: float | None = None
    density_kg_m3: float = 700.0
    viscosity_Pa_s: float = 0.003
    U_W_m2K: float = 300.0
    baffles: bool = True
    impeller_type: str = "pitched blade turbine"


@dataclass
class ScaleUpResult:
    """Scale-up metrics for one reactor scale."""

    name: str
    volume_L: float
    rpm: float
    impeller_diameter_m: float
    tank_diameter_m: float
    power_kW: float
    power_per_volume_kW_m3: float
    impeller_Re: float
    tip_speed_m_s: float
    mixing_time_s: float
    kLa_scale_factor: float
    U_scale_factor: float
    wall_shear_proxy_Pa: float
    activity_comparability: str
    Mw_PDI_shift_risk: str
    Mooney_shift_risk: str
    fouling_risk: str
    recommended_rpm: float
    recommended_impeller_diameter_m: float
    recommendation: str


def power_number(impeller_type: str, impeller_Re: float, baffles: bool = True) -> float:
    """Estimate impeller power number from type and Reynolds regime."""
    turbulent_np = {
        "Rushton turbine": 5.0,
        "pitched blade turbine": 1.5,
        "anchor impeller": 0.7,
        "helical ribbon for high viscosity": 1.1,
        "simple disk turbine": 2.0,
    }.get(impeller_type, 1.5)
    if not baffles:
        turbulent_np *= 0.72
    if impeller_Re < 10.0:
        return max(80.0 / max(impeller_Re, 1.0e-6), turbulent_np)
    if impeller_Re < 10000.0:
        transition = (math.log10(max(impeller_Re, 10.0)) - 1.0) / 3.0
        laminar_np = 80.0 / max(impeller_Re, 1.0e-6)
        return laminar_np * (1.0 - transition) + turbulent_np * transition
    return turbulent_np


def default_tank_diameter(volume_L: float) -> float:
    """Estimate a lab-kettle tank diameter from volume assuming H/T about 1.2."""
    volume_m3 = max(volume_L, 0.05) / 1000.0
    return (4.0 * volume_m3 / (1.2 * math.pi)) ** (1.0 / 3.0)


def calculate_scaleup_case(case: ScaleUpCase, reference: ScaleUpResult | None = None) -> ScaleUpResult:
    """Calculate stirred-kettle engineering-similarity metrics."""
    volume_m3 = max(case.volume_L / 1000.0, 1.0e-6)
    tank_d = case.tank_diameter_m or default_tank_diameter(case.volume_L)
    impeller_d = positive(case.impeller_diameter_m, 0.25 * tank_d)
    N = positive(case.rpm) / 60.0
    rho = max(case.density_kg_m3, 1.0)
    mu = max(case.viscosity_Pa_s, 1.0e-8)
    Re = rho * N * impeller_d**2 / mu
    Np = power_number(case.impeller_type, Re, case.baffles)
    power_W = Np * rho * N**3 * impeller_d**5
    pv = power_W / volume_m3 / 1000.0
    tip_speed = math.pi * impeller_d * N
    circulation_velocity = max(0.35 * tip_speed, 1.0e-4)
    mixing_time = 5.2 * tank_d / circulation_velocity
    if reference is None:
        kLa_scale = 1.0
        U_scale = 1.0
    else:
        kLa_scale = (pv / max(reference.power_per_volume_kW_m3, 1.0e-9)) ** 0.45 * (tip_speed / max(reference.tip_speed_m_s, 1.0e-9)) ** 0.20
        U_scale = (Re / max(reference.impeller_Re, 1.0e-9)) ** 0.14 * (reference.wall_shear_proxy_Pa / max(_wall_shear(mu, tip_speed, tank_d), 1.0e-9)) ** 0.05
    wall_shear = _wall_shear(mu, tip_speed, tank_d)
    activity = "highly comparable" if 0.65 <= kLa_scale <= 1.45 and 0.65 <= U_scale <= 1.45 else "needs correction"
    mw_risk = "medium" if case.volume_L >= 5.0 and pv < 0.7 else "low"
    if case.volume_L >= 5.0 and Re < 10000.0:
        mw_risk = "medium-high"
    mooney_risk = "medium" if mw_risk != "low" else "low"
    fouling = "high" if wall_shear < 0.12 and mu > 0.01 else "medium" if wall_shear < 0.2 else "low"
    recommended_rpm = case.rpm
    if reference is not None and pv < 0.75 * reference.power_per_volume_kW_m3:
        recommended_rpm = case.rpm * (reference.power_per_volume_kW_m3 / max(pv, 1.0e-9)) ** (1.0 / 3.0)
    recommended_d = clamp(0.35 * tank_d, 0.02, 0.65 * tank_d)
    recommendation = _recommendation(activity, mw_risk, fouling, case, recommended_rpm, recommended_d)
    return ScaleUpResult(
        name=case.name,
        volume_L=case.volume_L,
        rpm=case.rpm,
        impeller_diameter_m=impeller_d,
        tank_diameter_m=tank_d,
        power_kW=power_W / 1000.0,
        power_per_volume_kW_m3=pv,
        impeller_Re=Re,
        tip_speed_m_s=tip_speed,
        mixing_time_s=mixing_time,
        kLa_scale_factor=kLa_scale,
        U_scale_factor=U_scale,
        wall_shear_proxy_Pa=wall_shear,
        activity_comparability=activity,
        Mw_PDI_shift_risk=mw_risk,
        Mooney_shift_risk=mooney_risk,
        fouling_risk=fouling,
        recommended_rpm=float(recommended_rpm),
        recommended_impeller_diameter_m=float(recommended_d),
        recommendation=recommendation,
    )


def compare_scaleup(
    density_kg_m3: float,
    viscosity_Pa_s: float,
    rpm: float = 500.0,
    impeller_type: str = "pitched blade turbine",
    custom_volume_L: float = 20.0,
    baffles: bool = True,
) -> pd.DataFrame:
    """Compare 2 L, 5 L and a custom kettle scale against the 2 L reference."""
    ref_case = ScaleUpCase(
        name="2L reference",
        volume_L=2.0,
        rpm=rpm,
        impeller_diameter_m=0.055,
        density_kg_m3=density_kg_m3,
        viscosity_Pa_s=viscosity_Pa_s,
        baffles=baffles,
        impeller_type=impeller_type,
    )
    ref = calculate_scaleup_case(ref_case)
    cases = [
        ref,
        calculate_scaleup_case(
            ScaleUpCase(
                name="5L pilot",
                volume_L=5.0,
                rpm=rpm,
                impeller_diameter_m=0.08,
                density_kg_m3=density_kg_m3,
                viscosity_Pa_s=viscosity_Pa_s,
                baffles=baffles,
                impeller_type=impeller_type,
            ),
            reference=ref,
        ),
        calculate_scaleup_case(
            ScaleUpCase(
                name="custom",
                volume_L=custom_volume_L,
                rpm=rpm,
                impeller_diameter_m=max(0.35 * default_tank_diameter(custom_volume_L), 0.03),
                density_kg_m3=density_kg_m3,
                viscosity_Pa_s=viscosity_Pa_s,
                baffles=baffles,
                impeller_type=impeller_type,
            ),
            reference=ref,
        ),
    ]
    return pd.DataFrame([_result_row(item) for item in cases])


def _wall_shear(mu: float, tip_speed: float, tank_d: float) -> float:
    """Return a wall shear proxy from viscosity and tip speed."""
    return mu * tip_speed / max(0.12 * tank_d, 1.0e-6)


def _recommendation(activity: str, mw_risk: str, fouling: str, case: ScaleUpCase, rpm: float, impeller_d: float) -> str:
    """Generate a concise scale-up recommendation."""
    notes: list[str] = []
    if activity != "highly comparable":
        notes.append(f"按P/V和kLa相似建议rpm约 {rpm:.0f}。")
    if mw_risk != "low":
        notes.append("5L及以上可能出现Mw升高、PDI变宽、门尼偏低偏移，需用GPC/门尼复核。")
    if fouling != "low":
        notes.append("壁面剪切偏低，建议挡板、近壁桨或降低固含。")
    if "anchor" in case.impeller_type or "helical" in case.impeller_type:
        notes.append(f"高黏窗口可保留近壁桨，建议桨径约 {impeller_d:.3f} m。")
    if not notes:
        notes.append("当前2L/5L相似性较好，可优先验证ENB和氢调边界。")
    return " ".join(notes)


def _result_row(result: ScaleUpResult) -> dict[str, Any]:
    """Convert result dataclass to table row."""
    return {
        "case": result.name,
        "volume_L": result.volume_L,
        "rpm": result.rpm,
        "impeller_diameter_m": result.impeller_diameter_m,
        "tank_diameter_m": result.tank_diameter_m,
        "power_kW": result.power_kW,
        "P_over_V_kW_m3": result.power_per_volume_kW_m3,
        "impeller_Re": result.impeller_Re,
        "tip_speed_m_s": result.tip_speed_m_s,
        "mixing_time_s": result.mixing_time_s,
        "kLa_scale_factor": result.kLa_scale_factor,
        "U_scale_factor": result.U_scale_factor,
        "wall_shear_proxy_Pa": result.wall_shear_proxy_Pa,
        "activity_comparability": result.activity_comparability,
        "Mw_PDI_shift_risk": result.Mw_PDI_shift_risk,
        "Mooney_shift_risk": result.Mooney_shift_risk,
        "fouling_risk": result.fouling_risk,
        "recommended_rpm": result.recommended_rpm,
        "recommended_impeller_diameter_m": result.recommended_impeller_diameter_m,
        "recommendation": result.recommendation,
    }
