from epdm_sim.audit_trail import audit_trail_dataframe, compare_repro_package_manifest, create_audit_record
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.repro_package import export_repro_package, load_repro_manifest_from_zip


def test_audit_record_and_repro_package_contains_trail():
    record = create_audit_record("run_fast_flowsheet", "flowsheet_fast", {"a": 1}, {"b": 2})
    df = audit_trail_dataframe([record])
    assert df.loc[0, "input_hash"]
    result = run_flowsheet(load_default_config())
    package = export_repro_package(result, audit_records=[record])
    manifest = load_repro_manifest_from_zip(package)
    assert manifest["app_version"].startswith("V6.4")
    same = compare_repro_package_manifest(manifest, manifest)
    assert same["same"].all()

