from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.repro_package import export_repro_package, load_repro_manifest_from_zip


def test_repro_package_manifest_roundtrip():
    result = run_flowsheet()
    payload = export_repro_package(result, test_status="pytest smoke")
    manifest = load_repro_manifest_from_zip(payload)
    assert manifest["app_version"].startswith("V6.4")
    assert manifest["config_hash"]
    assert manifest["test_status"] == "pytest smoke"

