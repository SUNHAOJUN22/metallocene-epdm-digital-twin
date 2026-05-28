"""Template-aware feed stream construction and validation."""

from __future__ import annotations

from dataclasses import dataclass

from .components import load_components
from .reaction_templates import template_with_fallback
from .streams import Stream
from .template_config import TemplateProcessConfig
from .utils import c_to_k, kg_h_to_mol_h, mpa_to_pa, positive


@dataclass(frozen=True)
class FeedValidationResult:
    """One feed-map validation message."""

    passed: bool
    severity: str
    message: str
    field: str = ""
    suggested_fix: str = ""


def validate_template_feed_map(template_config: TemplateProcessConfig | dict) -> list[FeedValidationResult]:
    """Validate template monomer and chain-transfer feed maps before simulation."""
    cfg = template_config if isinstance(template_config, TemplateProcessConfig) else TemplateProcessConfig(**template_config)
    template, warnings = template_with_fallback(cfg.template_id)
    results: list[FeedValidationResult] = [
        FeedValidationResult(True, "info", warning, "template_id") for warning in warnings
    ]
    template_monomers = set(template.monomers)
    for monomer, value in cfg.monomer_feeds_kg_h.items():
        if monomer not in template_monomers:
            results.append(
                FeedValidationResult(
                    False,
                    "error",
                    f"Monomer feed {monomer} is not in template {template.template_id}.",
                    f"monomer_feeds_kg_h.{monomer}",
                    "Remove the feed or choose a reaction template containing this monomer.",
                )
            )
        if value < 0:
            results.append(
                FeedValidationResult(False, "error", f"Negative monomer feed for {monomer}.", f"monomer_feeds_kg_h.{monomer}", "Use non-negative feed rates.")
            )
    for monomer in template.monomers:
        if monomer not in cfg.monomer_feeds_kg_h:
            results.append(FeedValidationResult(False, "warning", f"Template monomer {monomer} has no feed; using zero.", f"monomer_feeds_kg_h.{monomer}", "Add a feed value if this monomer should be present."))
    template_agents = set(template.chain_transfer_agents)
    for agent, value in cfg.chain_transfer_feeds.items():
        if value < 0:
            results.append(FeedValidationResult(False, "error", f"Negative chain-transfer feed for {agent}.", f"chain_transfer_feeds.{agent}", "Use non-negative feed rates."))
        if agent not in template_agents:
            results.append(FeedValidationResult(False, "warning", f"Chain-transfer agent {agent} is not declared by template {template.template_id}.", f"chain_transfer_feeds.{agent}", "Declare it in reaction_templates.json or remove it."))
    if cfg.solvent_mass_kg_h < 0:
        results.append(FeedValidationResult(False, "error", "Negative solvent feed.", "solvent_mass_kg_h", "Use non-negative solvent feed."))
    if not results:
        results.append(FeedValidationResult(True, "info", "Template feed map is valid."))
    return results


def build_template_feed_stream(template_config: TemplateProcessConfig | dict) -> Stream:
    """Build a feed stream from a template feed map.

    Components not present in `components.json` still receive molar flows from
    the reaction template molecular weights so generic templates remain usable.
    """
    cfg = template_config if isinstance(template_config, TemplateProcessConfig) else TemplateProcessConfig(**template_config)
    template, _ = template_with_fallback(cfg.template_id)
    components = load_components()
    solvent = cfg.solvent if cfg.solvent in components else "hexane"
    mass_flows: dict[str, float] = {solvent: positive(cfg.solvent_mass_kg_h)}
    for monomer in template.monomers:
        mass_flows[monomer] = positive(cfg.monomer_feeds_kg_h.get(monomer, 0.0))
    for agent, value in cfg.chain_transfer_feeds.items():
        key = "hydrogen" if agent.lower() in {"h2", "hydrogen"} else agent
        mass_flows[key] = mass_flows.get(key, 0.0) + positive(value) / (1000.0 if key == "hydrogen" else 1.0)
    stream = Stream.from_mass_flows(
        "Template feed",
        temperature_K=c_to_k(25.0),
        pressure_Pa=mpa_to_pa(cfg.pressure_MPa),
        mass_flows=mass_flows,
        phase="mixed",
        components=components,
    )
    for monomer in template.monomers:
        if monomer not in stream.molar_flows:
            stream.molar_flows[monomer] = kg_h_to_mol_h(mass_flows.get(monomer, 0.0), template.molecular_weights.get(monomer, 100.0))
    for agent in cfg.chain_transfer_feeds:
        key = "hydrogen" if agent.lower() in {"h2", "hydrogen"} else agent
        if key not in stream.molar_flows:
            mw = 2.016 if key == "hydrogen" else 100.0
            stream.molar_flows[key] = kg_h_to_mol_h(mass_flows.get(key, 0.0), mw)
    stream.update_solids()
    return stream

