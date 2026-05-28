"""3D equipment library page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.digital_twin_3d import equipment_detail_dataframe, equipment_detail_text, figure_for_equipment, selectable_equipment
from epdm_sim.ui_theme import section_title


def render_equipment_library_page(config, result, save_config_callback=None, store=None) -> None:
    """Render individual equipment sketches and metadata."""
    section_title("3D装置库")
    equipment = st.selectbox("选择设备", selectable_equipment())
    c1, c2 = st.columns([1.7, 1.0])
    with c1:
        st.plotly_chart(figure_for_equipment(equipment, result), width="stretch")
    with c2:
        st.dataframe(pd.DataFrame([equipment_detail_text(equipment, result)]), width="stretch", hide_index=True)
        st.dataframe(equipment_detail_dataframe(result), width="stretch", height=360)

