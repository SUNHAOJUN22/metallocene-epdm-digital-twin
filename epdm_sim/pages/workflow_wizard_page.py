"""Streamlit page for the V4.7 R&D workflow wizard."""

from __future__ import annotations

from typing import Any

from ..workflow_wizard import next_recommended_action, workflow_status


def render_page(st: Any, state: dict[str, Any] | None = None) -> None:
    """Render workflow guidance without triggering heavy models."""
    state = state or {}
    st.subheader("研发工作流向导")
    st.caption("该页面只显示步骤状态和建议动作，不会在页面加载时运行ODE、CFD、优化、后验采样或DOE。")
    st.dataframe(workflow_status(state.get("available_results", {})), use_container_width=True)
    st.info(f"下一步建议：{next_recommended_action(state.get('available_results', {}))}")

