from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.polymer_props import grade_match, load_target_grades


def test_grade_matching_returns_closest_grade():
    result = run_flowsheet(load_default_config())
    grades = load_target_grades()
    preferred = [grade_id for grade_id in grades if grade_id.startswith("Vistalon_") or grade_id.startswith("Internal_")]
    matches = [grade_match(result.kpis, grade_id) for grade_id in preferred]
    best = max(matches, key=lambda item: item["score"])
    assert best["grade_id"] == result.kpis["best_grade"]
    assert best["score"] >= 0.0
