"""Template-aware process configuration adapters.

The legacy :class:`flowsheet.ProcessConfig` remains the EPDM/Vistalon user
interface contract.  V4.7 adds :class:`TemplateProcessConfig` so the process
kernel can work from a reaction-template feed map instead of hard-coded
ethylene/propylene/ENB fields.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .flowsheet import ProcessConfig, normalize_process_config
from .reaction_templates import template_with_fallback
from .utils import model_dump_compat, positive


class TemplateProcessConfig(BaseModel):
    """Template-driven process configuration with EPDM compatibility fields."""

    template_id: str = "EPDM_EPM_metallocene_solution"
    temperature_C: float = 100.0
    pressure_MPa: float = 1.0
    reactor_volume_L: float = 5.0
    residence_time_min: float = 30.0
    solvent: str = "hexane"
    solvent_mass_kg_h: float = 100.0
    monomer_feeds_kg_h: dict[str, float] = Field(default_factory=dict)
    chain_transfer_feeds: dict[str, float] = Field(default_factory=dict)
    catalyst_umol_h: float = 100.0
    AlTi_ratio: float = 1000.0
    BHT_ratio: float = 0.0
    reactor_mode: str = "Semi-batch Reactor"
    num_cstr: int = 2
    flash1_T_C: float = 80.0
    flash1_P_MPa: float = 0.2
    flash2_T_C: float = 140.0
    flash2_P_MPa: float = 0.02
    purge_fraction: float = 0.05
    thermo_mode: str = "Simple Wilson K"
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

    @classmethod
    def from_process_config(
        cls,
        process_config: ProcessConfig | dict[str, Any] | None,
        template_id: str = "EPDM_EPM_metallocene_solution",
    ) -> "TemplateProcessConfig":
        """Build a template config from the legacy process config."""
        cfg = process_config if isinstance(process_config, ProcessConfig) else ProcessConfig(**normalize_process_config(process_config or {}))
        template, _ = template_with_fallback(template_id)
        monomer_feeds = {}
        epdm_alias = {
            "ethylene": cfg.ethylene_kg_h,
            "propylene": cfg.propylene_kg_h,
            "ENB": cfg.enb_kg_h,
        }
        fallback_values = [cfg.ethylene_kg_h, cfg.propylene_kg_h, cfg.enb_kg_h]
        for idx, monomer in enumerate(template.monomers):
            monomer_feeds[monomer] = positive(epdm_alias.get(monomer, fallback_values[min(idx, len(fallback_values) - 1)]))
        chain_transfer = {}
        for agent in template.chain_transfer_agents:
            if agent.lower() in {"hydrogen", "h2"}:
                chain_transfer[agent] = positive(cfg.hydrogen_g_h)
            else:
                chain_transfer[agent] = 0.0
        return cls(
            template_id=template.template_id,
            temperature_C=cfg.temperature_C,
            pressure_MPa=cfg.pressure_MPa,
            reactor_volume_L=cfg.reactor_volume_L,
            residence_time_min=cfg.residence_time_min,
            solvent=cfg.solvent,
            solvent_mass_kg_h=cfg.solvent_mass_kg_h,
            monomer_feeds_kg_h=monomer_feeds,
            chain_transfer_feeds=chain_transfer,
            catalyst_umol_h=cfg.catalyst_umol_h,
            AlTi_ratio=cfg.AlTi_ratio,
            BHT_ratio=cfg.BHT_ratio,
            reactor_mode=cfg.reactor_mode,
            num_cstr=cfg.num_cstr,
            flash1_T_C=cfg.flash1_T_C,
            flash1_P_MPa=cfg.flash1_P_MPa,
            flash2_T_C=cfg.flash2_T_C,
            flash2_P_MPa=cfg.flash2_P_MPa,
            purge_fraction=cfg.purge_fraction,
            thermo_mode=cfg.thermo_mode,
            heat_transfer_U_W_m2K=cfg.heat_transfer_U_W_m2K,
            heat_transfer_area_m2=cfg.heat_transfer_area_m2,
            coolant_inlet_C=cfg.coolant_inlet_C,
            coolant_outlet_C=cfg.coolant_outlet_C,
            pipe_length_m=cfg.pipe_length_m,
            pipe_diameter_m=cfg.pipe_diameter_m,
            pipe_roughness_m=cfg.pipe_roughness_m,
            pump_efficiency=cfg.pump_efficiency,
            rheology_model=cfg.rheology_model,
            power_law_n=cfg.power_law_n,
            carreau_lambda_s=cfg.carreau_lambda_s,
            agitation_rpm=cfg.agitation_rpm,
            impeller_type=cfg.impeller_type,
            baffles=cfg.baffles,
            feed_nozzle_position=cfg.feed_nozzle_position,
            parameter_set_id=cfg.parameter_set_id,
        )


def process_config_to_template_config(
    process_config: ProcessConfig | dict[str, Any] | None,
    template_id: str = "EPDM_EPM_metallocene_solution",
) -> TemplateProcessConfig:
    """Convert a legacy config to the template-aware representation."""
    return TemplateProcessConfig.from_process_config(process_config, template_id)


def template_config_to_process_config(template_config: TemplateProcessConfig | dict[str, Any]) -> ProcessConfig:
    """Convert a template config back to the EPDM-compatible process config."""
    cfg = template_config if isinstance(template_config, TemplateProcessConfig) else TemplateProcessConfig(**template_config)
    aliases = epdm_feed_aliases(cfg)
    return ProcessConfig(
        temperature_C=cfg.temperature_C,
        pressure_MPa=cfg.pressure_MPa,
        reactor_volume_L=cfg.reactor_volume_L,
        residence_time_min=cfg.residence_time_min,
        solvent=cfg.solvent,
        solvent_mass_kg_h=cfg.solvent_mass_kg_h,
        ethylene_kg_h=aliases.get("ethylene_kg_h", 0.0),
        propylene_kg_h=aliases.get("propylene_kg_h", 0.0),
        enb_kg_h=aliases.get("enb_kg_h", 0.0),
        hydrogen_g_h=aliases.get("hydrogen_g_h", 0.0),
        catalyst_umol_h=cfg.catalyst_umol_h,
        AlTi_ratio=cfg.AlTi_ratio,
        BHT_ratio=cfg.BHT_ratio,
        num_cstr=cfg.num_cstr,
        reactor_mode=cfg.reactor_mode,
        flash1_T_C=cfg.flash1_T_C,
        flash1_P_MPa=cfg.flash1_P_MPa,
        flash2_T_C=cfg.flash2_T_C,
        flash2_P_MPa=cfg.flash2_P_MPa,
        purge_fraction=cfg.purge_fraction,
        thermo_mode=cfg.thermo_mode,
        heat_transfer_U_W_m2K=cfg.heat_transfer_U_W_m2K,
        heat_transfer_area_m2=cfg.heat_transfer_area_m2,
        coolant_inlet_C=cfg.coolant_inlet_C,
        coolant_outlet_C=cfg.coolant_outlet_C,
        pipe_length_m=cfg.pipe_length_m,
        pipe_diameter_m=cfg.pipe_diameter_m,
        pipe_roughness_m=cfg.pipe_roughness_m,
        pump_efficiency=cfg.pump_efficiency,
        rheology_model=cfg.rheology_model,
        power_law_n=cfg.power_law_n,
        carreau_lambda_s=cfg.carreau_lambda_s,
        agitation_rpm=cfg.agitation_rpm,
        impeller_type=cfg.impeller_type,
        baffles=cfg.baffles,
        feed_nozzle_position=cfg.feed_nozzle_position,
        parameter_set_id=cfg.parameter_set_id,
    )


def epdm_feed_aliases(template_config: TemplateProcessConfig | dict[str, Any]) -> dict[str, float]:
    """Return legacy EPDM feed aliases from a template feed map."""
    cfg = template_config if isinstance(template_config, TemplateProcessConfig) else TemplateProcessConfig(**template_config)
    return {
        "ethylene_kg_h": positive(cfg.monomer_feeds_kg_h.get("ethylene", 0.0)),
        "propylene_kg_h": positive(cfg.monomer_feeds_kg_h.get("propylene", 0.0)),
        "enb_kg_h": positive(cfg.monomer_feeds_kg_h.get("ENB", 0.0)),
        "hydrogen_g_h": positive(cfg.chain_transfer_feeds.get("hydrogen", cfg.chain_transfer_feeds.get("H2", 0.0))),
    }


def template_config_dict(template_config: TemplateProcessConfig) -> dict[str, Any]:
    """Return a stable JSON-like dictionary for hashing/reporting."""
    return model_dump_compat(template_config)

