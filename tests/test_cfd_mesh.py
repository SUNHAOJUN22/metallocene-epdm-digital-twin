from epdm_sim.cfd.mesh import CFDGeometryConfig, create_mesh


def test_pipe_mesh_shape_and_mask():
    mesh = create_mesh(CFDGeometryConfig(geometry_type="Pipe 2D", nx=40, ny=20))
    assert mesh.X.shape == (20, 40)
    assert mesh.mask.all()
    assert mesh.dx > 0.0
    assert mesh.dy > 0.0


def test_reactor_mesh_has_inactive_corners():
    mesh = create_mesh(CFDGeometryConfig(geometry_type="Reactor cross-section", nx=40, ny=20))
    assert mesh.X.shape == (20, 40)
    assert mesh.mask.any()
    assert not mesh.mask.all()
