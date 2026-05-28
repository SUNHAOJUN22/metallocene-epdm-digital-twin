from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.polymer_props import estimate_mooney, grade_match, load_target_grades


def test_mooney_model_returns_positive_value():
    assert estimate_mooney(360300.0, 3.39, 54.3, 6.8) > 0.0


def test_grade_matching_returns_vistalon_like_fields():
    result = run_flowsheet(load_default_config())
    grades = load_target_grades()
    assert "Vistalon_6602_like" in grades
    match = grade_match(result.kpis, "Vistalon_6602_like")
    assert match["score"] >= 0.0
    assert "product_values" in match
    assert "C2" in match["deviations"]
