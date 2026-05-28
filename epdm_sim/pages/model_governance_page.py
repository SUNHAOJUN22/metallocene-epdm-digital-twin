"""Model governance and confidence-certificate page."""

from __future__ import annotations

import streamlit as st

from epdm_sim.governance_certificate import governance_certificate_dataframe
from epdm_sim.model_confidence_certificate import confidence_certificate_dataframe, validation_data_upgrade_plan
from epdm_sim.evidence_chain import build_evidence_chain
from epdm_sim.evidence_chain_score import evidence_gap_priority_dataframe
from epdm_sim.property_runtime_audit import property_runtime_audit_dataframe
from epdm_sim.residual_system import build_flowsheet_residual_system, residual_system_dataframe
from epdm_sim.ui_theme import section_title


def render_model_governance_page(config, result, save_config_callback=None, store=None) -> None:
    """Render read-only governance diagnostics without triggering heavy tasks."""
    section_title("模型治理与可信度证书")
    residual_system = build_flowsheet_residual_system(result)
    st.subheader("治理证书")
    st.dataframe(governance_certificate_dataframe(result), width="stretch", hide_index=True)
    st.subheader("模型可信度证书")
    st.dataframe(confidence_certificate_dataframe(residual_system=residual_system, model_outputs=result.kpis), width="stretch", hide_index=True)
    st.subheader("方程 / residual / benchmark / data-lineage 证据链")
    st.dataframe(build_evidence_chain(), width="stretch", hide_index=True)
    st.subheader("ResidualSystem 状态")
    st.dataframe(residual_system_dataframe(residual_system), width="stretch", hide_index=True)
    st.subheader("物性模型运行审计")
    st.dataframe(property_runtime_audit_dataframe(result, conditions={"temperature_C": config.temperature_C, "pressure_MPa": config.pressure_MPa, "solids_wt": result.kpis.get("solids_wt", 10.0)}), width="stretch", hide_index=True)
    st.subheader("验证数据缺口优先级")
    st.dataframe(evidence_gap_priority_dataframe(), width="stretch", hide_index=True)
    st.subheader("验证升级计划")
    st.dataframe(validation_data_upgrade_plan(), width="stretch", hide_index=True)

