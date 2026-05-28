"""File-path safety and export metadata helpers."""

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Iterable

from .services.cache_keys import hash_payload


SAFE_EXPORT_EXTENSIONS = {".xlsx", ".docx", ".pdf", ".json", ".csv", ".zip", ".txt", ".vtk"}


def validate_safe_filename(name: str) -> str:
    """Return a safe filename or raise ValueError."""
    if not name or not str(name).strip():
        raise ValueError("filename is empty")
    path = Path(str(name))
    if path.name != str(name):
        raise ValueError("filename must not include path components")
    if any(token in str(name) for token in ("..", "/", "\\")):
        raise ValueError("filename contains path traversal tokens")
    if path.suffix.lower() and path.suffix.lower() not in SAFE_EXPORT_EXTENSIONS:
        raise ValueError(f"unsupported file extension: {path.suffix}")
    return path.name


def prevent_path_traversal(path: str | Path, base_dir: str | Path) -> Path:
    """Resolve a path and ensure it stays under base_dir."""
    root = Path(base_dir).resolve()
    candidate = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes base directory: {candidate}") from exc
    return candidate


def validate_upload_extension(filename: str, allowed: Iterable[str]) -> str:
    """Validate an upload extension against an allow-list."""
    suffix = Path(validate_safe_filename(filename)).suffix.lower()
    allowed_clean = {item.lower() if item.startswith(".") else f".{item.lower()}" for item in allowed}
    if suffix not in allowed_clean:
        raise ValueError(f"extension {suffix or '<none>'} not allowed")
    return suffix


def validate_file_size(size_bytes: int, max_bytes: int) -> int:
    """Validate a file size and return it."""
    size = int(size_bytes)
    max_size = int(max_bytes)
    if size < 0:
        raise ValueError("file size must be non-negative")
    if max_size <= 0:
        raise ValueError("max file size must be positive")
    if size > max_size:
        raise ValueError(f"file size {size} exceeds limit {max_size}")
    return size


def export_metadata(
    *,
    version: str,
    config: Any | None = None,
    parameter_set_id: str = "default",
    template_id: str = "EPDM_EPM_metallocene_solution",
    model_registry: Any | None = None,
    equation_registry: Any | None = None,
    warnings: list[str] | None = None,
    missing_heavy_tasks: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata that every export can include without rerunning models."""
    return {
        "software_version": version,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "config_hash": hash_payload(config or {}),
        "parameter_set_id": parameter_set_id,
        "template_id": template_id,
        "model_registry_hash": hash_payload(model_registry or {}),
        "equation_registry_hash": hash_payload(equation_registry or {}),
        "warnings": "; ".join(warnings or []),
        "missing_heavy_tasks": "; ".join(missing_heavy_tasks or []),
    }
