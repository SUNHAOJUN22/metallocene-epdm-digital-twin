import math
from io import BytesIO
from zipfile import ZipFile

from epdm_sim.eos import cubic_eos_details, cubic_z_roots, fugacity_coefficient
from epdm_sim.parameter_estimation import estimate_parameters, save_parameter_set
from epdm_sim.experiment_data import load_internal_experiment_dataset
from epdm_sim.cfd.mesh import CFDGeometryConfig
from epdm_sim.cfd.simple_solver import CFDInput, run_pipe_fvm_solver, run_simple_cfd
from epdm_sim.cfd.visualization import export_legacy_vtk
from epdm_sim.cfd.openfoam_export import export_openfoam_case_zip, generate_openfoam_case_files


def test_eos_details_include_z_phi_and_positive_k():
    details = cubic_eos_details("ethylene", 373.15, 1.0e6, "PR")
    assert details["K"] > 0
    assert details["Z_vapor"] > 0
    assert fugacity_coefficient("ethylene", 373.15, 1.0e6, "vapor") > 0
    assert all(z > 0 for z in cubic_z_roots("ethylene", 373.15, 1.0e6))


def test_real_flowsheet_fit_completes_small_nfev_and_metadata(tmp_path):
    df = load_internal_experiment_dataset().head(3)
    result = estimate_parameters(df, target="ENB_wt", model_mode="flowsheet_real", max_nfev=2, max_seconds=8)
    assert result.model_mode == "flowsheet_real"
    assert result.fitting_runtime_s >= 0
    assert math.isfinite(result.fitted_params["k_E_ref"])
    registry = save_parameter_set(
        "v4_fit",
        result.fitted_params,
        path=tmp_path / "sets.json",
        model_mode=result.model_mode,
        fitting_runtime_s=result.fitting_runtime_s,
        run_failures=result.run_failures,
    )
    saved = registry["sets"]["v4_fit"]
    assert saved["model_mode"] == "flowsheet_real"
    assert "run_failures" in saved


def test_failed_model_run_returns_penalty_not_crash(monkeypatch):
    import epdm_sim.parameter_estimation as pe

    def broken(*_, **__):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(pe, "_predict_flowsheet_row", broken)
    result = estimate_parameters(load_internal_experiment_dataset().head(2), target="ENB_wt", model_mode="flowsheet_real", max_nfev=1)
    assert not result.run_failures.empty


def test_openfoam_and_vtk_v4_outputs():
    config = CFDInput(geometry=CFDGeometryConfig(geometry_type="Pipe 2D", nx=20, ny=10))
    files = generate_openfoam_case_files(config)
    assert "system/controlDict.scalarTransportFoam" in files
    assert "0/C" in files
    assert all(name in files["system/blockMeshDict"] for name in ["inlet", "outlet", "walls", "frontAndBack"])
    with ZipFile(BytesIO(export_openfoam_case_zip(config)), "r") as archive:
        assert "system/controlDict.scalarTransportFoam" in archive.namelist()
    result = run_simple_cfd(config)
    vtk = export_legacy_vtk(result).decode("utf-8")
    assert "dead_zone_mask" in vtk
    assert "high_fouling_mask" in vtk
    fvm = run_pipe_fvm_solver(config)
    assert fvm.diagnostics.pressure_drop_Pa >= 0

