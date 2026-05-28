import pytest
import numpy as np
from epdm_sim.flowsheet import run_flowsheet, load_default_config
from epdm_sim.utils import TINY

def test_extreme_temperature_stability():
    """Verify system stability at near-unphysical temperatures."""
    cfg = load_default_config()
    
    # Near Absolute Zero (should be clamped to safe minimum)
    cfg.temperature_C = -273.0 
    result = run_flowsheet(cfg)
    assert result.kpis['polymer_kg_h'] >= 0
    assert np.isfinite(result.kpis['heat_duty_kW'])
    
    # Supercritical / Extreme Heat (should be handled by alarm/clamping)
    cfg.temperature_C = 800.0
    result = run_flowsheet(cfg)
    assert result.kpis['polymer_kg_h'] >= 0
    # At 800C, the heat removal margin should definitely be negative or warnings present
    assert len(result.warnings) > 0 or result.kpis['cooling_margin_kW'] < 0

def test_vacuum_and_high_pressure():
    """Verify flowsheet convergence at pressure extremes."""
    cfg = load_default_config()
    
    # Near Vacuum
    cfg.pressure_MPa = 1.0e-6
    result = run_flowsheet(cfg)
    assert result.kpis['flash1_vapor_fraction'] >= 0.0
    
    # Extreme Pressure (100 MPa)
    cfg.pressure_MPa = 100.0
    result = run_flowsheet(cfg)
    assert result.kpis['polymer_kg_h'] >= 0
    assert np.isfinite(result.kpis['dynamic_viscosity_Pa_s'])

def test_zero_feed_robustness():
    """Verify that zeroing monomer feeds doesn't cause division by zero."""
    cfg = load_default_config()
    cfg.ethylene_kg_h = 0.0
    cfg.propylene_kg_h = 0.0
    cfg.enb_kg_h = 0.0
    
    result = run_flowsheet(cfg)
    assert result.kpis['polymer_kg_h'] == 0.0
    assert result.kpis['C2_conversion_pct'] == 0.0
    assert result.kpis['Mw'] >= 0

def test_flash_zero_flow_robustness():
    """Verify that flash unit handles zero input gracefully."""
    from epdm_sim.flash import Flash
    from epdm_sim.streams import Stream
    
    flash = Flash("TestFlash")
    inlet = Stream(name="Empty", temperature_K=300.0, pressure_Pa=101325.0, molar_flows={})
    result = flash.calculate(inlet, 300.0, 101325.0)
    
    assert result.vapor_fraction == 0.0
    assert result.duty_kJ_h == 0.0
    assert result.vapor.total_mass_flow() == 0.0

if __name__ == "__main__":
    pytest.main([__file__])
