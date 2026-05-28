import numpy as np

from epdm_sim.cfd.fouling import calculate_fouling_field, risk_level
from epdm_sim.cfd.mesh import CFDGeometryConfig, create_mesh


def test_fouling_field_higher_near_low_velocity_wall():
    mesh = create_mesh(CFDGeometryConfig(geometry_type="Pipe 2D", nx=40, ny=20))
    speed = np.ones_like(mesh.X) * 0.2
    speed[0, :] = 0.005
    temp = np.ones_like(mesh.X) * 110.0
    solids = np.ones_like(mesh.X) * 12.0
    mu = np.ones_like(mesh.X) * 0.002
    risk = calculate_fouling_field(mesh, speed, temp, solids, mu, base_viscosity_Pa_s=0.001)
    assert np.nanmax(risk[0, :]) > np.nanmean(risk[mesh.mask])
    assert risk_level(float(np.nanmax(risk))) in {"low", "medium", "high"}
