import plotly.graph_objects as go

from epdm_sim.digital_twin_3d import build_digital_twin_figure, figure_for_equipment
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_3d_equipment_primitives_can_be_generated_from_required_filename():
    result = run_flowsheet(load_default_config())
    overview = build_digital_twin_figure(result, mode="物料流模式", selected_equipment="总览")
    reactor = figure_for_equipment("Reactor", result, mode="CFD剖面模式")
    devol = figure_for_equipment("Flash2", result)
    product = figure_for_equipment("Product", result)
    assert isinstance(overview, go.Figure)
    assert isinstance(reactor, go.Figure)
    assert isinstance(devol, go.Figure)
    assert isinstance(product, go.Figure)
    assert len(overview.data) > 10
