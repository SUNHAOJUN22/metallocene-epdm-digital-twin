import plotly.graph_objects as go

from epdm_sim.equipment_3d import (
    add_box,
    add_cylinder,
    add_label,
    add_pipe,
    equipment_summary,
    feed_area_3d_figure,
    flash_vessel_3d_figure,
    heat_exchanger_3d_figure,
    product_tank_3d_figure,
    reactor_3d_figure,
    risk_color_from_kpis,
)
from epdm_sim.flowsheet import run_flowsheet


def test_equipment_primitives_and_figures_are_nonempty():
    fig = go.Figure()
    add_cylinder(fig, center=(0, 0, 1), radius=0.5, height=1.0, name="vessel")
    add_box(fig, center=(1, 0, 0), size=(0.2, 0.2, 0.2), name="box")
    add_pipe(fig, [(0, 0, 0), (1, 1, 1)], name="pipe", color="#fff")
    add_label(fig, "label", (0, 0, 1))
    assert len(fig.data) >= 4

    result = run_flowsheet()
    figures = [
        reactor_3d_figure(result),
        flash_vessel_3d_figure(result),
        heat_exchanger_3d_figure(result),
        product_tank_3d_figure(result),
        feed_area_3d_figure(),
    ]
    assert all(len(item.data) > 0 for item in figures)
    assert not equipment_summary(result).empty
    assert risk_color_from_kpis({"fouling_index": 4.0}, "黏度/挂胶风险模式").startswith("#")
