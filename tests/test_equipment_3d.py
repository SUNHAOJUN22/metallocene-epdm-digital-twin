import plotly.graph_objects as go

from epdm_sim.digital_twin_3d import build_digital_twin_figure, figure_for_equipment
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_3d_equipment_primitives_can_be_generated():
    result = run_flowsheet(load_default_config())
    overview = build_digital_twin_figure(result, mode="物料流模式", selected_equipment="总览")
    reactor = figure_for_equipment("Reactor", result, mode="黏度/挂胶风险模式")
    flash = figure_for_equipment("Flash1", result)
    product = figure_for_equipment("Product", result)
    assert isinstance(overview, go.Figure)
    assert isinstance(reactor, go.Figure)
    assert isinstance(flash, go.Figure)
    assert isinstance(product, go.Figure)
    assert len(overview.data) > 10
    assert len(reactor.data) > 5
