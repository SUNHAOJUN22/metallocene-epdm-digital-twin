import json
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from epdm_sim import APP_VERSION
from epdm_sim.case_manager import compare_cases, duplicate_case, export_case_package, import_case_package_zip, list_cases, load_case, save_case
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_case_save_load_duplicate_and_compare(tmp_path):
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    a = save_case("base", cfg, result=result, case_dir=tmp_path)
    cfg.temperature_C += 5
    b = save_case("hotter", cfg, result=run_flowsheet(cfg), case_dir=tmp_path)
    loaded = load_case(a.case_id, case_dir=tmp_path)
    assert loaded.case_name == "base"
    dup = duplicate_case(b.case_id, "hotter_copy", case_dir=tmp_path)
    assert dup.case_id == "hotter_copy"
    listing = list_cases(case_dir=tmp_path)
    assert len(listing) == 3
    comparison = compare_cases(a, b)
    assert "temperature_C" in comparison["field"].tolist()


def test_case_package_zip_roundtrip(tmp_path):
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    record = save_case("package_case", cfg, result=result, case_dir=tmp_path)
    payload = export_case_package(
        record,
        dynamic_profile=pd.DataFrame({"t_min": [0, 1], "T_C": [100, 101]}),
        cfd_metrics={"dead_zone_fraction": 0.1},
        report_metadata={"author": "pytest"},
    )
    with ZipFile(BytesIO(payload), "r") as archive:
        assert "case.json" in archive.namelist()
        assert "manifest.json" in archive.namelist()
        assert "dynamic_profile.csv" in archive.namelist()
        assert "cfd_metrics.json" in archive.namelist()
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["app_version"] == APP_VERSION
    imported = import_case_package_zip(payload, case_dir=tmp_path / "imported")
    assert imported.case_id == record.case_id


def test_case_comparison_includes_kpi_deltas(tmp_path):
    cfg = load_default_config()
    a = save_case("kpi_base", cfg, result=run_flowsheet(cfg), case_dir=tmp_path)
    cfg.enb_kg_h += 1.0
    b = save_case("kpi_enb", cfg, result=run_flowsheet(cfg), case_dir=tmp_path)
    comparison = compare_cases(a, b)
    assert "ENB_wt" in comparison["field"].tolist()
