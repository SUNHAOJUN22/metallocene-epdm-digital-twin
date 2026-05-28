from epdm_sim.flash import Flash
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.fluid_props import calculate_pipe_hydraulics, polymer_solution_viscosity
from epdm_sim.heat_balance import calculate_reaction_heat
from epdm_sim.streams import Stream
from epdm_sim.units import assert_weight_percent_sum
from epdm_sim.utils import c_to_k, mpa_to_pa


def _cfg(**updates):
    cfg = load_default_config()
    for key, value in updates.items():
        setattr(cfg, key, value)
    return cfg


def test_hydrogen_increase_decreases_mw_and_mooney():
    low = run_flowsheet(_cfg(hydrogen_g_h=0.1))
    high = run_flowsheet(_cfg(hydrogen_g_h=50.0))

    assert high.kpis["Mw"] <= low.kpis["Mw"]
    assert high.kpis["Mooney"] <= low.kpis["Mooney"]


def test_viscosity_trends_with_solids_temperature_and_mw():
    stream = Stream.from_mass_flows(
        "solution",
        temperature_K=c_to_k(100),
        pressure_Pa=mpa_to_pa(1.0),
        mass_flows={"hexane": 100.0},
        phase="liquid",
    )
    low_solids = polymer_solution_viscosity(stream, c_to_k(100), 300000.0, solids_wt_override=5.0)
    high_solids = polymer_solution_viscosity(stream, c_to_k(100), 300000.0, solids_wt_override=20.0)
    hot = polymer_solution_viscosity(stream, c_to_k(130), 300000.0, solids_wt_override=20.0)
    high_mw = polymer_solution_viscosity(stream, c_to_k(100), 600000.0, solids_wt_override=20.0)

    assert high_solids > low_solids
    assert hot < high_solids
    assert high_mw > high_solids


def test_pressure_above_enb_optimum_does_not_raise_enb_incorporation():
    low_pressure = run_flowsheet(_cfg(pressure_MPa=0.7))
    high_pressure = run_flowsheet(_cfg(pressure_MPa=2.0))

    assert high_pressure.kpis["ENB_wt"] <= low_pressure.kpis["ENB_wt"] + 1.0e-9


def test_enb_feed_increase_raises_product_enb_wt():
    low = run_flowsheet(_cfg(enb_kg_h=1.0))
    high = run_flowsheet(_cfg(enb_kg_h=8.0))

    assert high.kpis["ENB_wt"] > low.kpis["ENB_wt"]


def test_heat_release_scales_with_conversion_basis():
    low = calculate_reaction_heat({"ethylene": 10.0, "propylene": 5.0, "ENB": 1.0})
    high = calculate_reaction_heat({"ethylene": 20.0, "propylene": 10.0, "ENB": 2.0})

    assert high > low > 0.0


def test_pipe_pressure_drop_increases_with_smaller_diameter_and_velocity():
    base = calculate_pipe_hydraulics(700.0, 0.01, 1.0, 10.0, 0.05)
    narrow = calculate_pipe_hydraulics(700.0, 0.01, 1.0, 10.0, 0.025)
    high_flow = calculate_pipe_hydraulics(700.0, 0.01, 2.0, 10.0, 0.05)

    assert narrow.pressure_drop_kPa > base.pressure_drop_kPa
    assert high_flow.pressure_drop_kPa > base.pressure_drop_kPa


def test_flash_pressure_drop_increases_vapor_fraction_and_polymer_stays_liquid():
    result = run_flowsheet(_cfg())
    inlet = result.streams["Quenched solution"]
    high_p = Flash("test-high").calculate(inlet, c_to_k(100), mpa_to_pa(0.5))
    low_p = Flash("test-low").calculate(inlet, c_to_k(100), mpa_to_pa(0.05))

    assert low_p.vapor_fraction >= high_p.vapor_fraction
    assert high_p.vapor.polymer_mass_kg_h == 0.0
    assert low_p.vapor.polymer_mass_kg_h == 0.0


def test_product_composition_sums_to_100_wt():
    result = run_flowsheet(_cfg())
    comp = {
        "C2": result.kpis["C2_wt"],
        "C3": result.kpis["C3_wt"],
        "ENB": result.kpis["ENB_wt"],
    }
    assert_weight_percent_sum(comp, tolerance=1.0e-6)
