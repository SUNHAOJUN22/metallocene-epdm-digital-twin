from epdm_sim.io_schema import get_io_schema, io_schema_dataframe, load_io_schemas
from epdm_sim.model_registry import load_model_registry


def test_active_registry_modules_have_io_schema():
    schemas = load_io_schemas()
    active = [module.module_id for module in load_model_registry() if module.status == "active"]
    missing = [module_id for module_id in active if module_id not in schemas]
    assert missing == []


def test_schema_inputs_have_units_outputs_have_bounds():
    for schema in load_io_schemas().values():
        assert schema.inputs
        assert schema.outputs
        assert all(item.unit for item in schema.inputs)
        assert all(item.unit for item in schema.outputs)
        assert all(hasattr(item, "physical_bounds") for item in schema.outputs)


def test_io_schema_dataframe_and_lookup():
    df = io_schema_dataframe()
    assert not df.empty
    assert get_io_schema("flowsheet").model_id == "flowsheet"
