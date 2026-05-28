"""Built-in lightweight 2D CFD-style solver for EPDM process visualization."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from ..fluid_props import RheologyModelParameters, apparent_viscosity, polymer_solution_viscosity
from ..streams import Stream
from ..utils import R_GAS, TINY, clamp, positive, safe_divide
from .fields import CFDDiagnostics, CFDFields, location_of_extreme, masked_stats
from .fem_solver import selected_solver_mode
from .fouling import calculate_fouling_field
from .mesh import CFDGeometryConfig, StructuredMesh, create_mesh
from .transport import normalized_active, smooth_active_field


class CFDInput(BaseModel):
    """Inputs for the lightweight CFD/FEM-style simulation."""

    solver_mode: str = "Simple CFD"
    geometry: CFDGeometryConfig = Field(default_factory=CFDGeometryConfig)
    density_kg_m3: float = 650.0
    viscosity_Pa_s: float = 0.001
    Cp_kJ_kgK: float = 2.1
    thermal_conductivity_W_mK: float = 0.12
    diffusivity_E_m2_s: float = 1.0e-9
    diffusivity_P_m2_s: float = 8.0e-10
    diffusivity_ENB_m2_s: float = 5.0e-10
    heat_generation_W_m3: float = 5000.0
    r_E_mol_m3_s: float = 0.0
    r_P_mol_m3_s: float = 0.0
    r_ENB_mol_m3_s: float = 0.0
    polymer_generation_rate_kg_m3_s: float = 0.0
    inlet_velocity_m_s: float = 0.15
    inlet_temperature_C: float = 100.0
    wall_temperature_C: float = 35.0
    coolant_temperature_C: float = 35.0
    inlet_C_E_mol_m3: float = 1000.0
    inlet_C_P_mol_m3: float = 1000.0
    inlet_C_ENB_mol_m3: float = 100.0
    outlet_pressure_Pa: float = 101325.0
    pressure_Pa: float = 1.0e6
    solids_wt: float = 10.0
    Mw: float = 360300.0
    PDI: float = 3.39
    agitation_rpm: float = 500.0
    impeller_type: str = "Rushton turbine"
    baffles_enabled: bool = True
    feed_position: str = "near impeller"
    section_view: str = "impeller plane"
    dynamic_time_min: float = 30.0
    overall_U_W_m2K: float = 300.0
    cooling_duty_kW: float = 10.0
    residence_time_s: float = 1800.0
    rheology_model: str = "power-law"
    power_law_n: float = 0.72
    carreau_lambda_s: float = 1.2


@dataclass
class SimpleCFDResult:
    """Result from the built-in CFD-style solver."""

    mode: str
    mesh: StructuredMesh
    fields: CFDFields
    diagnostics: CFDDiagnostics
    warnings: list[str]
    input: CFDInput


def run_simple_cfd(config: CFDInput) -> SimpleCFDResult:
    """Run the lightweight CFD-style solver and return fields and diagnostics."""
    actual_mode = selected_solver_mode(config.solver_mode)
    warnings: list[str] = []
    if config.solver_mode == "FEniCSx FEM" and actual_mode != "FEniCSx FEM":
        warnings.append("FEniCSx/dolfinx 不可用，已自动降级为 Simple CFD。")
    mesh = create_mesh(config.geometry)
    u, v = _velocity_field(mesh, config)
    speed = np.sqrt(u**2 + v**2)
    pressure_drop = _pressure_drop(mesh, config, speed)
    p = _pressure_field(mesh, config, pressure_drop, speed)
    T = _temperature_field(mesh, config, speed)
    C_E, C_P, C_ENB, C_H2 = _concentration_fields(mesh, config, speed, T)
    solids = _solids_field(mesh, config, speed, T)
    mu = _viscosity_field(mesh, config, solids, T, speed)
    r_E, r_P, r_ENB, r_total = _rate_fields(mesh, config, C_E, C_P, C_ENB, T)
    wall_shear = _wall_shear_field(mesh, config, speed, mu)
    fouling = calculate_fouling_field(mesh, speed, T, solids, mu, max(config.viscosity_Pa_s, 1.0e-8))
    mean_speed = max(float(np.nanmean(speed[mesh.mask])) if np.any(mesh.mask) else 0.0, 1.0e-9)
    dead_zone_mask = (speed < 0.05 * mean_speed) & mesh.mask
    high_fouling_mask = (fouling > 3.0) & mesh.mask
    fields = CFDFields(
        u=np.where(mesh.mask, u, np.nan),
        v=np.where(mesh.mask, v, np.nan),
        p=np.where(mesh.mask, p, np.nan),
        T=np.where(mesh.mask, T, np.nan),
        C_E=np.where(mesh.mask, C_E, np.nan),
        C_P=np.where(mesh.mask, C_P, np.nan),
        C_ENB=np.where(mesh.mask, C_ENB, np.nan),
        C_H2=np.where(mesh.mask, C_H2, np.nan),
        solids_wt=np.where(mesh.mask, solids, np.nan),
        mu=np.where(mesh.mask, mu, np.nan),
        fouling_index=np.where(mesh.mask, fouling, np.nan),
        r_E=np.where(mesh.mask, r_E, np.nan),
        r_P=np.where(mesh.mask, r_P, np.nan),
        r_ENB=np.where(mesh.mask, r_ENB, np.nan),
        r_total=np.where(mesh.mask, r_total, np.nan),
        wall_shear=np.where(mesh.mask, wall_shear, np.nan),
        dead_zone_mask=np.where(mesh.mask, dead_zone_mask.astype(float), np.nan),
        high_fouling_mask=np.where(mesh.mask, high_fouling_mask.astype(float), np.nan),
    )
    diagnostics = _diagnostics(mesh, config, fields, pressure_drop)
    return SimpleCFDResult(mode=actual_mode, mesh=mesh, fields=fields, diagnostics=diagnostics, warnings=warnings, input=config)


def run_pipe_fvm_solver(config: CFDInput) -> SimpleCFDResult:
    """Run a finite-volume-style pipe calculation with pressure/T/ENB fields.

    This uses the same structured field container as the visual CFD mode, but
    forces pipe geometry and applies axial convection-diffusion trends so the
    output can be exported to VTK/OpenFOAM consistently.
    """
    pipe_cfg = config.model_copy(update={"geometry": config.geometry.model_copy(update={"geometry_type": "Pipe 2D"})}) if hasattr(config, "model_copy") else config.copy(update={"geometry": config.geometry.copy(update={"geometry_type": "Pipe 2D"})})
    return run_simple_cfd(pipe_cfg)


def build_cfd_input_from_flowsheet(result: Any, geometry_type: str = "Reactor cross-section", nx: int = 80, ny: int = 40) -> CFDInput:
    """Create default CFD inputs coupled from a flowsheet result."""
    cfg = result.config
    reactor = result.reactor
    kpis = result.kpis
    volume_m3 = max(cfg.reactor_volume_L / 1000.0, 1.0e-6)
    heat_generation = kpis["heat_duty_kW"] * 1000.0 / volume_m3
    liquid_volume_m3_h = max(reactor.liquid_volume_L_h / 1000.0, 1.0e-9)
    seconds = 3600.0
    return CFDInput(
        geometry=CFDGeometryConfig(
            geometry_type=geometry_type,
            nx=nx,
            ny=ny,
            pipe_length_m=cfg.pipe_length_m,
            pipe_diameter_m=cfg.pipe_diameter_m,
            reactor_diameter_m=max((4.0 * volume_m3 / max(0.20 * math.pi, 1.0e-6)) ** 0.5, 0.10),
            liquid_height_m=0.20,
            impeller_diameter_m=0.08,
        ),
        density_kg_m3=kpis["liquid_density_kg_m3"],
        viscosity_Pa_s=kpis["dynamic_viscosity_Pa_s"],
        Cp_kJ_kgK=kpis["Cp_liq_kJ_kgK"],
        thermal_conductivity_W_mK=kpis["thermal_conductivity_W_mK"],
        heat_generation_W_m3=heat_generation,
        r_E_mol_m3_s=reactor.consumed_mol_h.get("ethylene", 0.0) / liquid_volume_m3_h / seconds,
        r_P_mol_m3_s=reactor.consumed_mol_h.get("propylene", 0.0) / liquid_volume_m3_h / seconds,
        r_ENB_mol_m3_s=reactor.consumed_mol_h.get("ENB", 0.0) / liquid_volume_m3_h / seconds,
        polymer_generation_rate_kg_m3_s=reactor.polymer_kg_h / liquid_volume_m3_h / seconds,
        inlet_velocity_m_s=max(kpis.get("pipe_Reynolds", 0.0) * kpis["dynamic_viscosity_Pa_s"] / max(kpis["liquid_density_kg_m3"] * cfg.pipe_diameter_m, TINY), 0.05),
        inlet_temperature_C=cfg.temperature_C,
        wall_temperature_C=cfg.coolant_outlet_C,
        coolant_temperature_C=cfg.coolant_outlet_C,
        inlet_C_E_mol_m3=positive(result.streams["Preheated feed"].molar_flows.get("ethylene", 0.0)) / liquid_volume_m3_h,
        inlet_C_P_mol_m3=positive(result.streams["Preheated feed"].molar_flows.get("propylene", 0.0)) / liquid_volume_m3_h,
        inlet_C_ENB_mol_m3=positive(result.streams["Preheated feed"].molar_flows.get("ENB", 0.0)) / liquid_volume_m3_h,
        pressure_Pa=cfg.pressure_MPa * 1.0e6,
        solids_wt=kpis["solids_wt"],
        Mw=kpis["Mw"],
        PDI=kpis["PDI"],
        agitation_rpm=getattr(cfg, "agitation_rpm", 500.0),
        impeller_type=getattr(cfg, "impeller_type", "pitched blade turbine"),
        baffles_enabled=getattr(cfg, "baffles", True),
        feed_position=str(getattr(cfg, "feed_nozzle_position", "near impeller")).replace("_", " "),
        dynamic_time_min=cfg.residence_time_min,
        overall_U_W_m2K=cfg.heat_transfer_U_W_m2K,
        cooling_duty_kW=kpis["total_cooling_load_kW"],
        residence_time_s=cfg.residence_time_min * 60.0,
        rheology_model=getattr(cfg, "rheology_model", "power-law"),
        power_law_n=getattr(cfg, "power_law_n", 0.72),
        carreau_lambda_s=getattr(cfg, "carreau_lambda_s", 1.2),
    )


def _velocity_field(mesh: StructuredMesh, config: CFDInput) -> tuple[np.ndarray, np.ndarray]:
    """Generate analytical/semi-analytical velocity fields for supported geometries."""
    X, Y = mesh.X, mesh.Y
    if mesh.geometry_type == "Pipe 2D":
        D = max(config.geometry.pipe_diameter_m, 1.0e-6)
        eta = 2.0 * Y / D - 1.0
        u = 1.5 * config.inlet_velocity_m_s * np.maximum(1.0 - eta**2, 0.0)
        v = np.zeros_like(u)
    elif mesh.geometry_type == "Annulus":
        radius = np.sqrt(X**2 + Y**2)
        theta_u = -Y / np.maximum(radius, 1.0e-9)
        theta_v = X / np.maximum(radius, 1.0e-9)
        gap_speed = max(config.inlet_velocity_m_s, 0.03)
        u = gap_speed * theta_u * np.sin(np.pi * normalized_active(mesh, mesh.wall_distance_m))
        v = gap_speed * theta_v * np.sin(np.pi * normalized_active(mesh, mesh.wall_distance_m))
    else:
        radius = np.sqrt(X**2 + Y**2)
        R = max(config.geometry.reactor_diameter_m / 2.0, 1.0e-6)
        Ri = max(config.geometry.impeller_diameter_m / 2.0, R * 0.15)
        omega = 2.0 * math.pi * positive(config.agitation_rpm) / 60.0
        impeller_velocity = {
            "Rushton turbine": (1.10, 1.25),
            "pitched blade turbine": (0.90, 1.35),
            "anchor impeller": (0.55, 0.80),
            "helical ribbon for high viscosity": (0.70, 1.05),
            "simple disk turbine": (0.95, 1.00),
        }.get(config.impeller_type, (1.0, 1.0))
        baffle_swirl = 0.68 if config.baffles_enabled else 1.45
        baffle_radial = 1.32 if config.baffles_enabled else 0.62
        wall_damping = np.clip(1.0 - (radius / R) ** 2, 0.0, 1.0)
        swirl = 0.25 * impeller_velocity[0] * baffle_swirl * omega * radius * np.exp(-((radius / max(Ri, 1.0e-6)) ** 2)) * wall_damping
        circulation = 0.06 * impeller_velocity[1] * baffle_radial * omega * Ri * np.sin(np.pi * np.clip(radius / R, 0.0, 1.0)) * wall_damping
        u = -swirl * Y / np.maximum(radius, 1.0e-9) + circulation * X / np.maximum(radius, 1.0e-9)
        v = swirl * X / np.maximum(radius, 1.0e-9) - circulation * Y / np.maximum(radius, 1.0e-9)
        u = np.clip(u, -3.0, 3.0)
        v = np.clip(v, -3.0, 3.0)
    return np.where(mesh.mask, u, 0.0), np.where(mesh.mask, v, 0.0)


def _pressure_drop(mesh: StructuredMesh, config: CFDInput, speed: np.ndarray) -> float:
    """Calculate characteristic pressure drop using Darcy-Weisbach style estimates."""
    if mesh.geometry_type == "Pipe 2D":
        D = max(config.geometry.pipe_diameter_m, 1.0e-6)
        L = max(config.geometry.pipe_length_m, D)
        velocity = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    else:
        D = max(config.geometry.impeller_diameter_m, 1.0e-6)
        L = max(config.geometry.reactor_diameter_m, D)
        velocity = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    Re = config.density_kg_m3 * velocity * D / max(config.viscosity_Pa_s, 1.0e-8)
    friction = 64.0 / max(Re, 1.0e-9) if Re < 2100.0 else 0.3164 / max(Re, 1.0e-9) ** 0.25
    return friction * L / D * config.density_kg_m3 * velocity**2 / 2.0


def _pressure_field(mesh: StructuredMesh, config: CFDInput, pressure_drop: float, speed: np.ndarray) -> np.ndarray:
    """Generate pressure field consistent with pipe/reaction section behavior."""
    if mesh.geometry_type == "Pipe 2D":
        x_norm = (mesh.X - np.nanmin(mesh.X)) / max(np.nanmax(mesh.X) - np.nanmin(mesh.X), TINY)
        p = config.outlet_pressure_Pa + pressure_drop * (1.0 - x_norm)
    else:
        dynamic = 0.5 * config.density_kg_m3 * speed**2
        p = config.pressure_Pa + dynamic - np.nanmean(dynamic[mesh.mask])
    return np.where(mesh.mask, p, np.nan)


def _temperature_field(mesh: StructuredMesh, config: CFDInput, speed: np.ndarray) -> np.ndarray:
    """Generate quasi-steady temperature field with heat source and wall cooling."""
    mean_speed = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    residence = min(config.residence_time_s, 3600.0)
    cp_J_kgK = max(config.Cp_kJ_kgK * 1000.0, 1.0)
    heat_rise = _time_progress(config) * config.heat_generation_W_m3 * residence / max(config.density_kg_m3 * cp_J_kgK, 1.0)
    heat_rise = clamp(heat_rise, 0.0, 80.0)
    cooling_strength = clamp(config.overall_U_W_m2K / 500.0, 0.05, 2.0)
    wall_norm = np.exp(-mesh.wall_distance_m / max(0.30 * mesh.length_scale_m, 1.0e-6))
    low_velocity = mean_speed / (speed + 0.15 * mean_speed)
    hotspot = normalized_active(mesh, low_velocity) if mesh.geometry_type != "Pipe 2D" else (mesh.X / max(np.nanmax(mesh.X), TINY))
    T = config.inlet_temperature_C + heat_rise * (0.25 + 0.75 * hotspot) - cooling_strength * wall_norm * (config.inlet_temperature_C - config.wall_temperature_C) * 0.35
    T = smooth_active_field(mesh, np.where(mesh.mask, T, config.wall_temperature_C), iterations=35, relaxation=0.18)
    return np.where(mesh.mask, T, np.nan)


def _concentration_fields(mesh: StructuredMesh, config: CFDInput, speed: np.ndarray, temperature_C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate monomer concentration fields with transport/reaction trends."""
    mean_speed = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    dead_zone = mean_speed / (speed + 0.10 * mean_speed)
    dead_norm = normalized_active(mesh, dead_zone)
    temp_norm = normalized_active(mesh, temperature_C)
    if mesh.geometry_type == "Pipe 2D":
        axial = mesh.X / max(np.nanmax(mesh.X), TINY)
    else:
        axial = normalized_active(mesh, np.sqrt(mesh.X**2 + mesh.Y**2))
    feed_bias = _feed_position_bias(mesh, config)
    reaction_shape = np.clip(_time_progress(config) * (0.15 + 0.55 * axial + 0.30 * dead_norm + 0.20 * temp_norm), 0.0, 1.0)
    C_E = config.inlet_C_E_mol_m3 * np.clip(1.0 - 0.18 * reaction_shape, 0.05, 1.0)
    C_P = config.inlet_C_P_mol_m3 * np.clip(1.0 - 0.12 * reaction_shape, 0.05, 1.0)
    C_ENB = config.inlet_C_ENB_mol_m3 * np.clip(1.0 - 0.30 * reaction_shape - 0.10 * dead_norm + 0.24 * feed_bias, 0.02, 1.35)
    C_H2 = 0.015 * (config.pressure_Pa / 1.0e6) * np.clip(1.0 - 0.08 * reaction_shape + 0.12 * feed_bias, 0.05, 1.25) * 1000.0
    return (
        smooth_active_field(mesh, np.where(mesh.mask, C_E, np.nan), iterations=20, relaxation=0.15),
        smooth_active_field(mesh, np.where(mesh.mask, C_P, np.nan), iterations=20, relaxation=0.15),
        smooth_active_field(mesh, np.where(mesh.mask, C_ENB, np.nan), iterations=20, relaxation=0.15),
        smooth_active_field(mesh, np.where(mesh.mask, C_H2, np.nan), iterations=20, relaxation=0.15),
    )


def _solids_field(mesh: StructuredMesh, config: CFDInput, speed: np.ndarray, temperature_C: np.ndarray) -> np.ndarray:
    """Generate local polymer solids field."""
    mean_speed = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    low_speed = normalized_active(mesh, mean_speed / (speed + 0.10 * mean_speed))
    temp_norm = normalized_active(mesh, temperature_C)
    solids = config.solids_wt * _time_progress(config) * (0.85 + 0.25 * low_speed + 0.12 * temp_norm)
    return smooth_active_field(mesh, np.where(mesh.mask, solids, np.nan), iterations=25, relaxation=0.18)


def _viscosity_field(mesh: StructuredMesh, config: CFDInput, solids_wt: np.ndarray, temperature_C: np.ndarray, speed: np.ndarray) -> np.ndarray:
    """Calculate local polymer solution viscosity field."""
    base_stream = Stream(
        name="CFD pseudo stream",
        temperature_K=config.inlet_temperature_C + 273.15,
        pressure_Pa=config.pressure_Pa,
        molar_flows={"ethylene": 1.0, "propylene": 1.0, "ENB": 0.05},
        mass_flows={"hexane": 1.0},
        polymer_mass_kg_h=0.0,
    )
    mu = np.zeros_like(solids_wt)
    rheology = RheologyModelParameters(
        model=config.rheology_model,
        power_law_n=config.power_law_n,
        carreau_lambda_s=config.carreau_lambda_s,
    )
    shear_distance = np.maximum(mesh.wall_distance_m, max(mesh.dx, mesh.dy))
    shear_rate = np.clip(speed / shear_distance, 1.0e-4, 1.0e5)
    for idx in np.ndindex(solids_wt.shape):
        if not mesh.mask[idx]:
            mu[idx] = np.nan
            continue
        zero_shear_mu = polymer_solution_viscosity(
            base_stream,
            float(temperature_C[idx]) + 273.15,
            config.Mw,
            solids_wt_override=float(solids_wt[idx]),
        )
        mu[idx] = apparent_viscosity(
            zero_shear_mu,
            float(shear_rate[idx]),
            config.rheology_model,
            rheology,
        )
    return np.where(mesh.mask, mu, np.nan)


def _rate_fields(mesh: StructuredMesh, config: CFDInput, C_E: np.ndarray, C_P: np.ndarray, C_ENB: np.ndarray, temperature_C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate local polymerization-rate fields for hotspot diagnostics."""
    temp_factor = np.exp(0.025 * (temperature_C - config.inlet_temperature_C))
    rE = max(config.r_E_mol_m3_s, 0.0) * C_E / max(config.inlet_C_E_mol_m3, TINY) * temp_factor
    rP = max(config.r_P_mol_m3_s, 0.0) * C_P / max(config.inlet_C_P_mol_m3, TINY) * temp_factor
    rD = max(config.r_ENB_mol_m3_s, 0.0) * C_ENB / max(config.inlet_C_ENB_mol_m3, TINY) * temp_factor
    total = rE + rP + rD
    return rE, rP, rD, total


def _wall_shear_field(mesh: StructuredMesh, config: CFDInput, speed: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Estimate wall shear stress field from near-wall velocity gradient."""
    distance = np.maximum(mesh.wall_distance_m, max(mesh.dx, mesh.dy))
    shear = mu * speed / distance
    wall_boost = np.exp(-mesh.wall_distance_m / max(0.08 * mesh.length_scale_m, 1.0e-6))
    return np.where(mesh.mask, shear * wall_boost, np.nan)


def _time_progress(config: CFDInput) -> float:
    """Return quasi-dynamic progress factor for field interpolation."""
    total_min = max(config.residence_time_s / 60.0, 1.0)
    return clamp(config.dynamic_time_min / total_min, 0.03, 1.0)


def _feed_position_bias(mesh: StructuredMesh, config: CFDInput) -> np.ndarray:
    """Return local concentration enrichment around selected feed nozzle position."""
    R = max(mesh.length_scale_m, TINY)
    if config.feed_position == "top":
        x0, y0 = 0.0, 0.75 * R
    elif config.feed_position == "side":
        x0, y0 = 0.72 * R, 0.0
    elif config.feed_position == "bottom":
        x0, y0 = 0.0, -0.75 * R
    else:
        x0, y0 = 0.15 * R, 0.0
    dist2 = (mesh.X - x0) ** 2 + (mesh.Y - y0) ** 2
    return np.exp(-dist2 / max((0.18 * R) ** 2, TINY))


def _diagnostics(mesh: StructuredMesh, config: CFDInput, fields: CFDFields, pressure_drop: float) -> CFDDiagnostics:
    """Calculate engineering diagnostics from CFD fields."""
    speed = fields.field("velocity")
    speed_stats = masked_stats(mesh, speed)
    temp_stats = masked_stats(mesh, fields.T)
    mu_stats = masked_stats(mesh, fields.mu)
    enb_stats = masked_stats(mesh, fields.C_ENB)
    temp_uniformity = safe_divide(temp_stats["std"], max(abs(temp_stats["mean"]), TINY), 0.0)
    viscosity_uniformity = safe_divide(mu_stats["std"], max(abs(mu_stats["mean"]), TINY), 0.0)
    characteristic_D = config.geometry.pipe_diameter_m if mesh.geometry_type == "Pipe 2D" else config.geometry.impeller_diameter_m
    Re = config.density_kg_m3 * speed_stats["mean"] * max(characteristic_D, 1.0e-6) / max(config.viscosity_Pa_s, 1.0e-8)
    q_m3_s = speed_stats["mean"] * max(characteristic_D, 1.0e-6) ** 2
    pump_power = pressure_drop * q_m3_s / 0.65 / 1000.0
    dead_zone = np.mean((speed[mesh.mask] < 0.05 * max(speed_stats["mean"], 1.0e-9)).astype(float))
    mixing_index = safe_divide(enb_stats["std"], max(enb_stats["mean"], TINY), 0.0)
    wall_band = mesh.mask & (mesh.wall_distance_m < 0.12 * mesh.length_scale_m)
    wall_max_fouling = float(np.nanmax(fields.fouling_index[wall_band])) if np.any(wall_band) else float(np.nanmax(fields.fouling_index[mesh.mask]))
    high_fouling_fraction = float(np.nanmean((fields.fouling_index[mesh.mask] > 3.0).astype(float))) if np.any(mesh.mask) else 0.0
    shear_active = fields.wall_shear[mesh.mask] if fields.wall_shear is not None else np.array([], dtype=float)
    shear_active = shear_active[np.isfinite(shear_active)]
    if shear_active.size:
        low_shear_limit = max(float(np.nanmean(shear_active)) * 0.20, 1.0e-12)
        low_shear_fraction = float(np.nanmean((shear_active < low_shear_limit).astype(float)))
        counts, edges = np.histogram(shear_active, bins=8)
        wall_shear_histogram = [
            {"bin_low_Pa": float(edges[i]), "bin_high_Pa": float(edges[i + 1]), "count": float(counts[i])}
            for i in range(len(counts))
        ]
    else:
        low_shear_fraction = 0.0
        wall_shear_histogram = []
    corrected_U = config.overall_U_W_m2K * (1.0 + 0.25 * min(Re / 10000.0, 1.0)) * (1.0 - 0.25 * min(dead_zone, 0.8))
    heat_effectiveness = clamp(corrected_U / max(config.overall_U_W_m2K, TINY) * (1.0 - dead_zone), 0.0, 2.0)
    kLa_estimate = 25.0 * (max(config.agitation_rpm, 1.0) / 500.0) ** 0.7 * (0.001 / max(config.viscosity_Pa_s, 1.0e-6)) ** 0.22
    mixing_time = 5.2 * max(config.geometry.reactor_diameter_m, config.geometry.pipe_diameter_m) / max(speed_stats["mean"], 1.0e-6)
    suggested_rpm = config.agitation_rpm
    suggested_solids = config.solids_wt
    recommendations: list[str] = []
    if dead_zone > 0.20:
        suggested_rpm = config.agitation_rpm * 1.2
        recommendations.append("死区比例偏高：建议提高搅拌转速或调整进料/桨型。")
    if wall_max_fouling > 3.0:
        suggested_solids = max(config.solids_wt * 0.85, 5.0)
        recommendations.append("壁面挂胶风险高：建议降低固含或Mw、提高壁面剪切并优化清洗周期。")
    if high_fouling_fraction > 0.08:
        recommendations.append("高挂胶风险区域面积偏大：建议降低固含、优化桨型并复核壁面清洗策略。")
    if low_shear_fraction > 0.20:
        recommendations.append("低剪切区占比偏高：建议提高近壁循环、加入挡板或采用更适合高黏胶液的桨型。")
    if viscosity_uniformity > 0.35:
        recommendations.append("剪切相关黏度场不均匀：建议使用实测非牛顿流变参数并复核低剪切壁区。")
    if temp_stats["max"] - config.inlet_temperature_C > 15.0:
        recommendations.append("局部热点明显：建议提高换热面积、降低聚合速率或分段进料。")
    if mixing_index > 0.15:
        recommendations.append("ENB浓度梯度较高：建议采用分段ENB进料、进料点靠近搅拌桨或提高混合强度。")
    if not config.baffles_enabled and mesh.geometry_type == "Reactor cross-section":
        recommendations.append("未启用挡板：建议加入四块挡板以削弱中心涡流并提高径向混合。")
    if config.impeller_type in {"anchor impeller", "helical ribbon for high viscosity"} and Re > 10000:
        recommendations.append("当前Re较高：可评估Rushton或斜叶桨以提高气液传质和局部剪切。")
    if config.feed_position in {"top", "side"} and mixing_index > 0.10:
        recommendations.append("当前进料位置导致浓度梯度：建议将ENB/催化剂进料移动到近桨区。")
    if not recommendations:
        recommendations.append("CFD趋势场未显示明显死区/热点，可用更细网格或OpenFOAM进一步验证。")
    return CFDDiagnostics(
        average_velocity_m_s=speed_stats["mean"],
        max_velocity_m_s=speed_stats["max"],
        Reynolds=Re,
        pressure_drop_Pa=pressure_drop,
        pump_power_kW=max(pump_power, 0.0),
        max_temperature_C=temp_stats["max"],
        average_temperature_C=temp_stats["mean"],
        max_temperature_rise_K=max(temp_stats["max"] - config.inlet_temperature_C, 0.0),
        hotspot_location_m=location_of_extreme(mesh, fields.T, "max"),
        min_ENB_location_m=location_of_extreme(mesh, fields.C_ENB, "min"),
        max_viscosity_location_m=location_of_extreme(mesh, fields.mu, "max"),
        wall_max_fouling_risk=wall_max_fouling,
        dead_zone_fraction=float(dead_zone),
        mixing_index=mixing_index,
        temperature_uniformity_index=temp_uniformity,
        viscosity_nonuniformity_index=viscosity_uniformity,
        heat_removal_effectiveness=heat_effectiveness,
        kLa_estimate_h=kLa_estimate,
        mixing_time_estimate_s=mixing_time,
        corrected_heat_transfer_U_W_m2K=corrected_U,
        suggested_agitation_rpm=suggested_rpm,
        suggested_max_solids_wt=suggested_solids,
        recommended_cooling_duty_kW=config.cooling_duty_kW * (1.0 + min(temp_stats["max"] - config.inlet_temperature_C, 40.0) / 100.0),
        high_fouling_zone_area_fraction=high_fouling_fraction,
        low_shear_area_fraction=low_shear_fraction,
        wall_shear_histogram=wall_shear_histogram,
        recommendations=recommendations,
    )
