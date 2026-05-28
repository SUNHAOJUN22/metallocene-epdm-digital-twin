from pathlib import Path

import pytest

from epdm_sim.file_security import (
    export_metadata,
    prevent_path_traversal,
    validate_file_size,
    validate_safe_filename,
    validate_upload_extension,
)


def test_file_security_rejects_path_traversal_and_bad_extensions(tmp_path):
    assert validate_safe_filename("report.xlsx") == "report.xlsx"
    assert validate_upload_extension("data.csv", {".csv", ".xlsx"}) == ".csv"
    assert prevent_path_traversal("nested/report.json", tmp_path) == (tmp_path / "nested" / "report.json").resolve()
    assert validate_file_size(1024, 2048) == 1024
    with pytest.raises(ValueError):
        validate_safe_filename("../secret.xlsx")
    with pytest.raises(ValueError):
        prevent_path_traversal(Path("..") / "secret.txt", tmp_path)
    with pytest.raises(ValueError):
        validate_upload_extension("payload.exe", {".csv"})
    with pytest.raises(ValueError):
        validate_file_size(4096, 1024)


def test_export_metadata_contains_release_fields():
    meta = export_metadata(version="V5.3 / 0.6.3", config={"a": 1}, parameter_set_id="p1", template_id="t1")
    for key in [
        "software_version",
        "created_at",
        "config_hash",
        "parameter_set_id",
        "template_id",
        "model_registry_hash",
        "equation_registry_hash",
        "warnings",
        "missing_heavy_tasks",
    ]:
        assert key in meta
