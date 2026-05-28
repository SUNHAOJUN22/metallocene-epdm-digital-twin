from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.plot_validation import plot_validation_dataframe, validate_nonempty_figure, validate_plotly_figure_units
from epdm_sim.plotting import composition_bar, conversion_bar, sankey_material


def test_plot_validation_accepts_core_scientific_figures():
    result = run_flowsheet()
    figures = {
        "sankey_material": sankey_material(result),
        "conversion_bar": conversion_bar(result),
        "composition_bar": composition_bar(result),
    }
    df = plot_validation_dataframe(figures)
    assert not df.empty
    assert not df.query("severity == 'error' and passed == False").any(axis=None)
    assert all(validate_nonempty_figure(fig)[0].passed for fig in figures.values())
    assert any(row.passed for row in validate_plotly_figure_units(composition_bar(result), "composition"))
