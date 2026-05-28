import numpy as np

from epdm_sim.cfd.fields import CFDFields, CFDDiagnostics, location_of_extreme, masked_stats
from epdm_sim.cfd.mesh import CFDGeometryConfig, create_mesh


def test_cfd_fields_public_methods_return_finite_values():
    mesh = create_mesh(CFDGeometryConfig(nx=20, ny=10))
    shape = mesh.shape
    ones = np.ones(shape)
    gradient = mesh.X + mesh.Y
    fields = CFDFields(
        u=ones,
        v=ones * 0.5,
        p=ones * 101325.0,
        T=ones * 373.15,
        C_E=ones * 0.1,
        C_P=ones * 0.2,
        C_ENB=ones * 0.03,
        C_H2=ones * 0.001,
        solids_wt=ones * 15.0,
        mu=ones * 0.02,
        fouling_index=gradient,
        wall_shear=ones * 3.0,
        dead_zone_mask=np.zeros(shape),
        high_fouling_mask=(gradient > np.nanmean(gradient)).astype(float),
    )
    assert np.isfinite(fields.field("velocity")).all()
    assert np.isfinite(fields.field("wall_shear")).all()
    stats = masked_stats(mesh, fields.field("fouling"))
    assert stats["max"] >= stats["mean"] >= stats["min"]
    x, y = location_of_extreme(mesh, fields.field("fouling"), "max")
    assert np.isfinite([x, y]).all()


def test_cfd_diagnostics_dataframe_has_units_and_bounded_fractions():
    diagnostics = CFDDiagnostics(
        average_velocity_m_s=0.2,
        max_velocity_m_s=0.6,
        Reynolds=1200.0,
        pressure_drop_Pa=5000.0,
        pump_power_kW=0.02,
        max_temperature_C=105.0,
        average_temperature_C=100.0,
        max_temperature_rise_K=5.0,
        hotspot_location_m=(0.0, 0.0),
        min_ENB_location_m=(0.01, 0.0),
        max_viscosity_location_m=(0.02, 0.0),
        wall_max_fouling_risk=2.0,
        dead_zone_fraction=0.1,
        mixing_index=0.2,
        temperature_uniformity_index=0.05,
        viscosity_nonuniformity_index=0.1,
        heat_removal_effectiveness=0.8,
        kLa_estimate_h=12.0,
        mixing_time_estimate_s=20.0,
        corrected_heat_transfer_U_W_m2K=250.0,
        suggested_agitation_rpm=550.0,
        suggested_max_solids_wt=18.0,
        recommended_cooling_duty_kW=3.0,
        high_fouling_zone_area_fraction=0.2,
        low_shear_area_fraction=0.3,
    )
    df = diagnostics.as_dataframe()
    assert not df.empty
    assert df["unit"].astype(str).str.len().gt(0).all()
    assert 0.0 <= diagnostics.dead_zone_fraction <= 1.0
    assert 0.0 <= diagnostics.high_fouling_zone_area_fraction <= 1.0

