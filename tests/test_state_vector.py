import numpy as np

from epdm_sim.state_vector import build_state_layout_from_template, default_state_dict, pack_state, unpack_state, validate_state_nonnegative


def test_state_pack_unpack_roundtrip():
    layout = build_state_layout_from_template("EPDM_EPM_metallocene_solution")
    state = default_state_dict(layout)
    state["liquid_moles"]["ethylene"] = 1.2
    state["segment_masses"]["E"] = 0.03
    state["T_K"] = 380.0
    y = pack_state(layout, state)
    out = unpack_state(layout, y)
    assert len(y) == len(layout.labels)
    assert out["liquid_moles"]["ethylene"] == 1.2
    assert out["segment_masses"]["E"] == 0.03
    assert out["T_K"] == 380.0
    assert validate_state_nonnegative(out) == []


def test_generic_state_layout_has_template_monomers():
    layout = build_state_layout_from_template("generic_terpolymerization_apparent")
    assert layout.liquid_moles == ["monomer_A", "monomer_B", "monomer_C"]
    assert np.isfinite(pack_state(layout, default_state_dict(layout))).all()
