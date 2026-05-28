import numpy as np

from epdm_sim.cfd.mesh import CFDGeometryConfig, create_mesh
from epdm_sim.cfd.simple_solver import CFDInput, run_simple_cfd
from epdm_sim.cfd.transport import smooth_active_field


def test_smooth_active_field_preserves_shape():
    mesh = create_mesh(CFDGeometryConfig(geometry_type="Pipe 2D", nx=30, ny=12))
    field = np.ones_like(mesh.X)
    smoothed = smooth_active_field(mesh, field, iterations=2)
    assert smoothed.shape == field.shape
    assert np.isfinite(smoothed[mesh.mask]).all()


def test_simple_cfd_outputs_required_fields():
    result = run_simple_cfd(CFDInput(geometry=CFDGeometryConfig(geometry_type="Pipe 2D", nx=30, ny=12)))
    assert result.fields.u.shape == result.mesh.X.shape
    assert result.diagnostics.average_velocity_m_s > 0.0
    assert result.diagnostics.max_temperature_C > 0.0
    assert result.diagnostics.mixing_index >= 0.0


def test_cfd_extended_diagnostics_finite():
    result = run_simple_cfd(CFDInput(geometry=CFDGeometryConfig(geometry_type="Reactor cross-section", nx=30, ny=16)))
    assert np.isfinite(result.diagnostics.high_fouling_zone_area_fraction)
    assert np.isfinite(result.diagnostics.low_shear_area_fraction)
    assert isinstance(result.diagnostics.wall_shear_histogram, list)
