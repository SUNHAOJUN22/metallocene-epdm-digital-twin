"""Residual-aware objective helpers for calibration."""

from __future__ import annotations

from typing import Any

from ..residual_objective import residual_penalty_for_optimizer


def residual_aware_parameter_objective(data_error: float, result_or_system: Any, *, residual_weight: float = 0.05) -> float:
    """Combine data residual and physical residual penalty."""
    return max(float(data_error), 0.0) + max(float(residual_weight), 0.0) * residual_penalty_for_optimizer(result_or_system)

