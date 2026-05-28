import pytest

from epdm_sim.dimensioned import (
    DimensionedValue,
    as_dimensioned,
    assert_compatible_units,
    convert_value,
    dimension_for_unit,
    mass_flow_to_molar_flow,
    molar_flow_to_mass_flow,
)


def test_temperature_pressure_and_unit_roundtrips():
    assert DimensionedValue(100.0, "C").to("K").value == pytest.approx(373.15)
    assert DimensionedValue(373.15, "K").to("C").value == pytest.approx(100.0)
    assert DimensionedValue(1.2, "MPa").to("Pa").to("MPa").value == pytest.approx(1.2)
    assert DimensionedValue(2.5, "mol/L").to("mol/m3").to("mol/L").value == pytest.approx(2.5)
    assert DimensionedValue(3600.0, "kJ/h").to("kW").value == pytest.approx(1.0)
    assert DimensionedValue(10.0, "cP").to("Pa.s").value == pytest.approx(0.01)


def test_mass_mole_roundtrip_and_metadata():
    mass = as_dimensioned(1.0, "kg/h", component="propylene")
    mol = mass_flow_to_molar_flow(mass, 42.08)
    back = molar_flow_to_mass_flow(mol, 42.08)
    assert mol.unit == "mol/h"
    assert back.value == pytest.approx(1.0)
    assert back.metadata["component"] == "propylene"


def test_dimensioned_rejects_invalid_or_incompatible_units():
    assert dimension_for_unit("bar") == "pressure"
    assert convert_value(1.0, "bar", "Pa") == pytest.approx(100000.0)
    assert_compatible_units("kPa", "MPa")
    with pytest.raises(ValueError):
        assert_compatible_units("Pa", "K")
    with pytest.raises(ValueError):
        DimensionedValue(-1.0, "K")
    with pytest.raises(ValueError):
        DimensionedValue(1.0, "unknown")
