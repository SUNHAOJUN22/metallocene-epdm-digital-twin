from __future__ import annotations

from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.pages.calibration_page import render_parameter_management
from epdm_sim.pages.case_manager_page import render_case_manager_page
from epdm_sim.pages.cfd_page import render_cfd_page
from epdm_sim.pages.dashboard_page import render_dashboard_page
from epdm_sim.pages.dynamic_reactor_page import render_dynamic_reactor_page
from epdm_sim.pages.equipment_library_page import render_equipment_library_page
from epdm_sim.pages.experiment_data_page import render_experiment_data_page
from epdm_sim.pages.heat_fluid_page import render_heat_fluid_page
from epdm_sim.pages.product_page import render_product_page
from epdm_sim.pages.reactor_page import render_reactor_page
from epdm_sim.pages.report_page import render_report_page
from epdm_sim.pages.sensitivity_optimization_page import render_sensitivity_optimization_page
from epdm_sim.pages.separation_page import render_separation_page
from epdm_sim.report import export_pdf_report


def test_streamlit_page_entrypoints_are_importable_callables():
    page_functions = [
        render_parameter_management,
        render_case_manager_page,
        render_cfd_page,
        render_dashboard_page,
        render_dynamic_reactor_page,
        render_equipment_library_page,
        render_experiment_data_page,
        render_heat_fluid_page,
        render_product_page,
        render_reactor_page,
        render_report_page,
        render_sensitivity_optimization_page,
        render_separation_page,
    ]
    assert all(callable(func) for func in page_functions)
    assert len({func.__name__ for func in page_functions}) == len(page_functions)


def test_pdf_export_real_flowsheet_smoke():
    result = run_flowsheet(load_default_config())
    pdf_bytes = export_pdf_report(result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"
