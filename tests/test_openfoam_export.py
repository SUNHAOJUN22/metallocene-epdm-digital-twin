from zipfile import ZipFile
from io import BytesIO

from epdm_sim.cfd.openfoam_export import export_openfoam_case_zip, generate_openfoam_case_files
from epdm_sim.cfd.simple_solver import CFDInput


def test_openfoam_case_contains_required_files():
    files = generate_openfoam_case_files(CFDInput())
    for path in [
        "system/controlDict",
        "system/blockMeshDict",
        "system/fvSchemes",
        "system/fvSolution",
        "constant/transportProperties",
        "constant/thermophysicalProperties",
        "0/U",
        "0/p",
        "0/T",
        "0/C_ENB",
        "README_OpenFOAM.md",
    ]:
        assert path in files


def test_openfoam_zip_is_readable():
    payload = export_openfoam_case_zip(CFDInput())
    with ZipFile(BytesIO(payload), "r") as archive:
        assert "system/controlDict" in archive.namelist()
        assert "system/blockMeshDict" in archive.namelist()
