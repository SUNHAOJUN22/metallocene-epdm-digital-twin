from epdm_sim.cfd.grid_convergence import run_cfd_grid_convergence, scalar_labels_from_template


def test_cfd_scalar_labels_and_grid_convergence_are_finite():
    labels = scalar_labels_from_template("generic_terpolymerization_apparent")
    assert "C_monomer_A" in labels
    result = run_cfd_grid_convergence(template_id="EPDM_EPM_metallocene_solution", grids=[(20, 10), (30, 15)])
    df = result.as_dataframe()
    assert not df.empty
    assert 0.0 <= result.convergence_score <= 100.0
    assert df["high_fouling_zone_area_fraction"].between(0, 1).all()

