import numpy as np

from epdm_sim.flowsheet import load_default_config
from epdm_sim.ode_scaling import bdf_readiness_check, estimate_state_scales, scale_state_vector, unscale_state_vector


def test_ode_scaling_roundtrip_and_bdf_readiness():
    scales = estimate_state_scales("EPDM_EPM_metallocene_solution", load_default_config())
    assert scales
    assert all(value > 0 and np.isfinite(value) for value in scales.values())
    y = np.arange(1, len(scales) + 1, dtype=float)
    scale_array = np.asarray(list(scales.values()), dtype=float)
    assert np.allclose(unscale_state_vector(scale_state_vector(y, scale_array), scale_array), y)
    readiness = bdf_readiness_check(load_default_config())
    assert readiness.min_scale > 0
    assert readiness.max_scale >= readiness.min_scale
    assert readiness.reason
