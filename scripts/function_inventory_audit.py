"""Import and public-function inventory audit for the EPDM digital twin.

This script complements pytest and the functional audit.  It does not try to
call arbitrary functions, because many public functions are UI actions, export
writers or heavy simulations that must remain explicitly triggered.  Instead it
checks that every project module imports cleanly and produces a traceable
inventory of public functions/classes plus whether each callable is directly
referenced by tests or audit scripts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import importlib
import inspect
import pkgutil
import sys
import time

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@dataclass
class ModuleImportRecord:
    """One module import audit row."""

    module: str
    imported: bool
    import_time_s: float
    public_functions: int
    public_classes: int
    error: str = ""


@dataclass
class PublicCallableRecord:
    """One public callable inventory row."""

    module: str
    name: str
    kind: str
    directly_referenced_by_tests_or_audits: bool
    has_docstring: bool


@dataclass
class FunctionMatrixRecord:
    """Auditable functional matrix row inferred from a public callable."""

    function_name: str
    file_position: str
    module: str
    call_entry: str
    input_parameters: str
    output_result: str
    dependencies: str
    involves_ui: bool
    involves_api: bool
    involves_database: bool
    involves_file_upload: bool
    involves_file_export: bool
    involves_visualization: bool
    involves_scientific_calculation: bool
    involves_unit_conversion: bool
    involves_numerical_algorithm: bool
    involves_state_management: bool
    has_direct_test_or_audit_reference: bool
    possible_exception_scenarios: str
    risk_level: str


def _project_modules() -> list[str]:
    """Return importable project modules under epdm_sim plus app."""
    package = importlib.import_module("epdm_sim")
    names = ["app", "epdm_sim"]
    names.extend(module.name for module in pkgutil.walk_packages(package.__path__, prefix="epdm_sim."))
    return sorted(set(names))


def _reference_corpus() -> str:
    """Return a lightweight corpus of tests and audit scripts for name lookup."""
    parts: list[str] = []
    for folder in [ROOT / "tests", ROOT / "scripts"]:
        if not folder.exists():
            continue
        for path in folder.rglob("*.py"):
            try:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(parts)


def _safe_signature(obj: object) -> str:
    """Return a compact signature string without failing on C-extension callables."""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(signature unavailable)"


def _annotation_to_text(annotation: object) -> str:
    """Return a readable return annotation."""
    if annotation is inspect.Signature.empty:
        return "unknown"
    text = str(annotation)
    return text.replace("typing.", "")


def _file_position(obj: object) -> str:
    """Return repo-relative source position if available."""
    try:
        source = inspect.getsourcefile(obj) or ""
        _, line = inspect.getsourcelines(obj)
        if source:
            path = Path(source)
            try:
                path_text = str(path.relative_to(ROOT))
            except ValueError:
                path_text = str(path)
            return f"{path_text}:{line}"
    except (OSError, TypeError):
        pass
    return "unknown"


def _module_dependencies(module: object) -> str:
    """Infer direct imported project dependencies from module globals."""
    deps: set[str] = set()
    for value in vars(module).values():
        dep_module = getattr(value, "__module__", "")
        if dep_module.startswith("epdm_sim"):
            deps.add(dep_module)
    return ";".join(sorted(deps))


def _infer_function_tags(module_name: str, name: str) -> dict[str, bool]:
    """Infer functional tags from module and callable names.

    This is intentionally heuristic.  The matrix is an audit index, not a
    behavioral substitute for pytest or auto_functional_audit.
    """
    text = f"{module_name}.{name}".lower()
    return {
        "involves_ui": any(token in text for token in ("page", "ui", "streamlit", "theme", "workflow_wizard", "app.")),
        "involves_api": any(token in text for token in ("api", "request", "response", "http")),
        "involves_database": any(token in text for token in ("db", "sqlite", "database")),
        "involves_file_upload": any(token in text for token in ("upload", "import", "load_", "read_", "parse")),
        "involves_file_export": any(token in text for token in ("export", "report", "package", "write_", "save_")),
        "involves_visualization": any(token in text for token in ("plot", "figure", "3d", "visual", "chart", "sankey", "contour", "streamline")),
        "involves_scientific_calculation": any(
            token in text
            for token in (
                "thermo",
                "eos",
                "flash",
                "reactor",
                "kinetic",
                "heat",
                "fluid",
                "rheology",
                "cfd",
                "polymer",
                "solubility",
                "conservation",
                "equation",
                "dimension",
                "safety",
                "optimizer",
                "pareto",
                "uncertainty",
                "posterior",
                "doe",
                "surrogate",
                "scaleup",
            )
        ),
        "involves_unit_conversion": any(token in text for token in ("unit", "dimension", "convert", "mol", "kg", "pa", "temperature", "pressure")),
        "involves_numerical_algorithm": any(
            token in text
            for token in (
                "solve",
                "ode",
                "optimiz",
                "least",
                "mcmc",
                "posterior",
                "uncertainty",
                "cfd",
                "fvm",
                "surrogate",
                "pareto",
                "simulate",
                "estimate",
                "fit",
            )
        ),
        "involves_state_management": any(token in text for token in ("state", "session", "case", "task", "audit_trail", "workflow")),
    }


def _exception_scenarios(tags: dict[str, bool]) -> str:
    """Return likely exception scenarios for a matrix row."""
    scenarios: list[str] = []
    if tags["involves_scientific_calculation"] or tags["involves_numerical_algorithm"]:
        scenarios.extend(["NaN/inf", "negative physical value", "unit/range mismatch", "non-convergence"])
    if tags["involves_file_upload"] or tags["involves_file_export"]:
        scenarios.extend(["missing file/path", "permission denied", "unsupported format"])
    if tags["involves_database"]:
        scenarios.extend(["sqlite unavailable", "schema mismatch", "duplicate key"])
    if tags["involves_ui"]:
        scenarios.extend(["missing session state", "ambiguous button key", "empty result state"])
    if tags["involves_visualization"]:
        scenarios.extend(["empty figure data", "invalid color scale", "missing units/labels"])
    if not scenarios:
        scenarios.append("invalid input")
    return "; ".join(dict.fromkeys(scenarios))


def _risk_level(tags: dict[str, bool], directly_referenced: bool) -> str:
    """Assign a coarse audit risk from tags and direct coverage."""
    if tags["involves_scientific_calculation"] and tags["involves_numerical_algorithm"] and not directly_referenced:
        return "high"
    if (tags["involves_file_export"] or tags["involves_database"] or tags["involves_ui"]) and not directly_referenced:
        return "medium"
    if tags["involves_scientific_calculation"] and not directly_referenced:
        return "medium"
    return "low"


def run_inventory_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Import all modules and return module/callable inventory tables."""
    module_rows: list[ModuleImportRecord] = []
    callable_rows: list[PublicCallableRecord] = []
    corpus = _reference_corpus()
    for module_name in _project_modules():
        started = time.perf_counter()
        try:
            module = importlib.import_module(module_name)
            import_time = time.perf_counter() - started
            functions = [
                (name, obj)
                for name, obj in inspect.getmembers(module, inspect.isfunction)
                if not name.startswith("_") and getattr(obj, "__module__", "") == module.__name__
            ]
            classes = [
                (name, obj)
                for name, obj in inspect.getmembers(module, inspect.isclass)
                if not name.startswith("_") and getattr(obj, "__module__", "") == module.__name__
            ]
            module_rows.append(ModuleImportRecord(module_name, True, import_time, len(functions), len(classes)))
            for name, obj in functions:
                callable_rows.append(
                    PublicCallableRecord(
                        module=module_name,
                        name=name,
                        kind="function",
                        directly_referenced_by_tests_or_audits=name in corpus,
                        has_docstring=bool(inspect.getdoc(obj)),
                    )
                )
            for name, obj in classes:
                callable_rows.append(
                    PublicCallableRecord(
                        module=module_name,
                        name=name,
                        kind="class",
                        directly_referenced_by_tests_or_audits=name in corpus,
                        has_docstring=bool(inspect.getdoc(obj)),
                    )
                )
        except Exception as exc:
            module_rows.append(ModuleImportRecord(module_name, False, time.perf_counter() - started, 0, 0, repr(exc)))
    return pd.DataFrame([asdict(row) for row in module_rows]), pd.DataFrame([asdict(row) for row in callable_rows])


def build_function_matrix(callables: pd.DataFrame) -> pd.DataFrame:
    """Build a feature/function matrix from the callable inventory."""
    rows: list[FunctionMatrixRecord] = []
    module_cache: dict[str, object] = {}
    for row in callables.to_dict("records"):
        module_name = str(row["module"])
        name = str(row["name"])
        try:
            module = module_cache.setdefault(module_name, importlib.import_module(module_name))
            obj = getattr(module, name)
        except Exception:
            module = None
            obj = None
        tags = _infer_function_tags(module_name, name)
        signature = _safe_signature(obj) if obj is not None else "(unavailable)"
        try:
            return_annotation = inspect.signature(obj).return_annotation if obj is not None else inspect.Signature.empty
        except (TypeError, ValueError):
            return_annotation = inspect.Signature.empty
        directly_referenced = bool(row.get("directly_referenced_by_tests_or_audits", False))
        rows.append(
            FunctionMatrixRecord(
                function_name=name,
                file_position=_file_position(obj) if obj is not None else "unknown",
                module=module_name,
                call_entry=f"{module_name}.{name}",
                input_parameters=signature,
                output_result=_annotation_to_text(return_annotation),
                dependencies=_module_dependencies(module) if module is not None else "",
                has_direct_test_or_audit_reference=directly_referenced,
                possible_exception_scenarios=_exception_scenarios(tags),
                risk_level=_risk_level(tags, directly_referenced),
                **tags,
            )
        )
    return pd.DataFrame([asdict(row) for row in rows])


def main() -> int:
    """Run inventory audit and write CSV artifacts."""
    out_dir = ROOT / "tmp_smoke_outputs"
    out_dir.mkdir(exist_ok=True)
    modules, callables = run_inventory_audit()
    if not callables.empty:
        coverage = (
            callables.groupby("module", as_index=False)
            .agg(
                public_callables=("name", "count"),
                directly_referenced=("directly_referenced_by_tests_or_audits", "sum"),
            )
        )
        coverage["uncovered_callables"] = coverage["public_callables"] - coverage["directly_referenced"]
        coverage = coverage.sort_values(["uncovered_callables", "public_callables", "module"], ascending=[False, False, True])
        top_uncovered = coverage.head(20)
    else:
        coverage = pd.DataFrame(columns=["module", "public_callables", "directly_referenced", "uncovered_callables"])
        top_uncovered = coverage
    modules.to_csv(out_dir / "function_inventory_modules.csv", index=False, encoding="utf-8-sig")
    callables.to_csv(out_dir / "function_inventory_callables.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(out_dir / "function_inventory_module_coverage.csv", index=False, encoding="utf-8-sig")
    top_uncovered.to_csv(out_dir / "function_inventory_uncovered_top20.csv", index=False, encoding="utf-8-sig")
    function_matrix = build_function_matrix(callables)
    function_matrix.to_csv(out_dir / "function_matrix.csv", index=False, encoding="utf-8-sig")
    failed = modules.loc[~modules["imported"]]
    referenced = int(callables["directly_referenced_by_tests_or_audits"].sum()) if not callables.empty else 0
    total_callables = len(callables)
    gate_summary = pd.DataFrame(
        [
            {
                "gate": "module_import",
                "passed": failed.empty,
                "detail": f"{len(modules) - len(failed)}/{len(modules)} modules imported",
            },
            {
                "gate": "callable_direct_reference",
                "passed": referenced > 0 and total_callables > 0,
                "detail": f"{referenced}/{total_callables} public callables directly referenced",
            },
            {
                "gate": "function_matrix",
                "passed": not function_matrix.empty,
                "detail": f"{len(function_matrix)} callable rows with UI/API/DB/file/science risk tags",
            },
        ]
    )
    gate_summary.to_csv(out_dir / "quality_gate_summary.csv", index=False, encoding="utf-8-sig")
    print(f"module import audit: {len(modules) - len(failed)}/{len(modules)} modules imported")
    print(f"public callable inventory: {referenced}/{total_callables} directly referenced by tests or audit scripts")
    print(f"function matrix: {len(function_matrix)} callable rows written to tmp_smoke_outputs/function_matrix.csv")
    if not top_uncovered.empty:
        print("top modules by currently unreferenced public callables:")
        print(top_uncovered.to_string(index=False))
    if not failed.empty:
        print(failed[["module", "error"]].to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
