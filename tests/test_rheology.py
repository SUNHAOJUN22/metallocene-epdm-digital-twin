from epdm_sim.fluid_props import calculate_pipe_hydraulics
from epdm_sim.rheology import calculate_rheology


def test_rheology_positive_and_trends():
    low = calculate_rheology(373.15, solids_wt=5.0, Mw=300000, shear_rate_s=10.0)
    high_solids = calculate_rheology(373.15, solids_wt=20.0, Mw=300000, shear_rate_s=10.0)
    high_temp = calculate_rheology(413.15, solids_wt=5.0, Mw=300000, shear_rate_s=10.0)
    high_mw = calculate_rheology(373.15, solids_wt=5.0, Mw=700000, shear_rate_s=10.0)
    assert low.dynamic_viscosity_Pa_s > 0
    assert high_solids.dynamic_viscosity_Pa_s > low.dynamic_viscosity_Pa_s
    assert high_temp.dynamic_viscosity_Pa_s < low.dynamic_viscosity_Pa_s
    assert high_mw.dynamic_viscosity_Pa_s > low.dynamic_viscosity_Pa_s


def test_shear_thinning_not_increasing_with_shear():
    low_shear = calculate_rheology(373.15, 12.0, 350000, 1.0, rheology_params={"model": "carreau-yasuda"})
    high_shear = calculate_rheology(373.15, 12.0, 350000, 100.0, rheology_params={"model": "carreau-yasuda"})
    assert high_shear.apparent_viscosity_Pa_s <= low_shear.apparent_viscosity_Pa_s


def test_pipe_pressure_drop_positive_and_diameter_trend():
    large = calculate_pipe_hydraulics(650.0, 0.01, 1.0, 10.0, 0.05)
    small = calculate_pipe_hydraulics(650.0, 0.01, 1.0, 10.0, 0.025)
    assert large.pressure_drop_kPa > 0
    assert small.pressure_drop_kPa > large.pressure_drop_kPa
