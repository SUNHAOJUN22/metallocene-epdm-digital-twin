from epdm_sim.industrial_data_package import (
    estimate_measurement_uncertainty,
    industrial_data_lineage_dataframe,
    industrial_data_package_dataframe,
    load_industrial_data_package,
    validate_industrial_dataset_schema,
)


def test_industrial_package_hash_units_and_source_confidence():
    package = load_industrial_data_package()
    same = load_industrial_data_package(package)
    assert package["data_hash"] == same["data_hash"]
    assert validate_industrial_dataset_schema(package)["passed"]
    assert estimate_measurement_uncertainty(package)["effective_uncertainty"] >= 0.0
    assert not industrial_data_lineage_dataframe(package).empty
    assert not industrial_data_package_dataframe(package).empty

    missing = dict(package)
    missing["source_reference"] = ""
    assert not validate_industrial_dataset_schema(missing)["passed"]
    invalid_unit = dict(package)
    invalid_unit["measurement_unit"] = "bad_unit"
    assert not validate_industrial_dataset_schema(invalid_unit)["passed"]

