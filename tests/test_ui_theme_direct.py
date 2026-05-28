from epdm_sim.ui_theme import risk_chip, status_color


def test_ui_theme_status_helpers_return_styled_text():
    assert status_color("normal").startswith("#")
    assert status_color("危险").startswith("#")
    chip = risk_chip("热风险", "danger")
    assert "热风险" in chip
    assert "epdm-chip" in chip
    assert "--dot-color" in chip
