"""Dynamical-dependence and cut objectives with explicit diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Sequence
import math

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import solve_discrete_lyapunov

from .errors import NumericalConvergenceError, ValidationError
from .models import VARModel, canonical_subset

Array = NDArray[np.float64]


@dataclass(frozen=True)
class NumericalDiagnostics:
    backend: str
    converged: bool
    iterations: int
    residual: float
    spectral_radius: float
    condition_number: float
    jitter: float
    tolerance: float

    def to_dict(self) -> dict[str, float | int | bool | str]:
        return asdict(self)


def orthonormalise(projection: Array) -> Array:
    """Require n-by-k full numerical rank under a relative SVD policy before QR."""
    q = np.asarray(projection, dtype=float)
    if q.ndim != 2 or not 1 <= q.shape[1] <= q.shape[0]:
        raise ValidationError("projection must be n-by-k with 1 <= k <= n")
    if not np.all(np.isfinite(q)):
        raise ValidationError("projection contains non-finite entries")
    scale = float(np.max(np.abs(q)))
    if scale == 0:
        raise ValidationError("projection has zero numerical rank")
    scaled = q / scale
    singular = np.linalg.svd(scaled, compute_uv=False)
    threshold = max(q.shape) * np.finfo(float).eps * singular[0]
    if singular[-1] <= threshold:
        raise ValidationError("projection is rank-deficient or below the numerical conditioning threshold")
    basis, upper = np.linalg.qr(scaled, mode="reduced")
    signs = np.sign(np.diag(upper)); signs[signs == 0] = 1.0
    return basis * signs


def projected_innovation_covariance(
    model: VARModel,
    projection: Array,
    *,
    tolerance: float = 1e-11,
    max_iterations: int = 20_000,
) -> tuple[Array, NumericalDiagnostics]:
    """Return own-past innovation covariance of ``projection.T @ X_t``.

    The recursion is the steady-state, zero-measurement-noise Kalman filter on
    the VAR companion state.  The result is a numerical enclosure candidate,
    not an exact algebraic certificate.
    """
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValidationError("tolerance must be finite and positive")
    q = orthonormalise(projection)
    if q.shape[0] != model.n:
        raise ValidationError("projection row dimension does not match the model")
    transition, injection, _ = model.companion()
    process = injection @ model.innovation_covariance @ injection.T
    observation = np.zeros((q.shape[1], transition.shape[0]), dtype=float)
    observation[:, : model.n] = q.T
    predicted = solve_discrete_lyapunov(transition, process)
    predicted = (predicted + predicted.T) / 2.0
    residual = float("inf")
    jitter_max = 0.0
    condition_max = 1.0
    converged = False
    for iteration in range(1, max_iterations + 1):
        omega = observation @ predicted @ observation.T
        omega = (omega + omega.T) / 2.0
        eig_min = float(np.min(np.linalg.eigvalsh(omega)))
        jitter = max(0.0, 1e-14 - eig_min)
        jitter_max = max(jitter_max, jitter)
        if jitter:
            omega = omega + jitter * np.eye(omega.shape[0])
        condition_max = max(condition_max, float(np.linalg.cond(omega)))
        gain = predicted @ observation.T @ np.linalg.inv(omega)
        filtered = predicted - gain @ observation @ predicted
        filtered = (filtered + filtered.T) / 2.0
        nxt = transition @ filtered @ transition.T + process
        nxt = (nxt + nxt.T) / 2.0
        residual = float(np.linalg.norm(nxt - predicted, ord="fro") / max(1.0, np.linalg.norm(predicted, ord="fro")))
        predicted = nxt
        if residual <= tolerance:
            converged = True
            break
    if not converged:
        raise NumericalConvergenceError(
            f"Riccati iteration did not converge in {max_iterations} iterations; residual={residual:.3e}"
        )
    omega = observation @ predicted @ observation.T
    omega = (omega + omega.T) / 2.0
    diag = NumericalDiagnostics(
        backend="float64-no-measurement-noise-riccati",
        converged=True,
        iterations=iteration,
        residual=residual,
        spectral_radius=model.spectral_radius(),
        condition_number=condition_max,
        jitter=jitter_max,
        tolerance=tolerance,
    )
    return omega, diag


def projected_dd(
    model: VARModel,
    projection: Array,
    *,
    tolerance: float = 1e-11,
    max_iterations: int = 20_000,
) -> tuple[float, NumericalDiagnostics]:
    q = orthonormalise(projection)
    omega, diagnostics = projected_innovation_covariance(
        model, q, tolerance=tolerance, max_iterations=max_iterations
    )
    macro_sigma = q.T @ model.innovation_covariance @ q
    sign1, log1 = np.linalg.slogdet(omega)
    sign0, log0 = np.linalg.slogdet(macro_sigma)
    if sign1 <= 0 or sign0 <= 0:
        raise NumericalConvergenceError("innovation or full-past covariance is not positive definite")
    value = float(log1 - log0)
    if -1e-8 < value < 0:
        value = 0.0
    if value < -1e-8:
        raise NumericalConvergenceError(f"computed negative DD beyond tolerance: {value}")
    return value, diagnostics


def coordinate_projection(n: int, subset: Iterable[int]) -> Array:
    selected = canonical_subset(subset, n)
    if not selected:
        return np.zeros((n, 0), dtype=float)
    return np.eye(n)[:, selected]


def coordinate_dd(
    model: VARModel,
    subset: Iterable[int],
    *,
    tolerance: float = 1e-11,
    max_iterations: int = 20_000,
) -> tuple[float, NumericalDiagnostics]:
    if isinstance(tolerance, (bool, np.bool_)) or not isinstance(tolerance, (int, float, np.integer, np.floating)):
        raise ValidationError("tolerance must be a real scalar")
    if tolerance <= 0 or not math.isfinite(float(tolerance)):
        raise ValidationError("tolerance must be finite and positive")
    selected = canonical_subset(subset, model.n)
    if len(selected) in {0, model.n}:
        diagnostics = NumericalDiagnostics(
            backend="endpoint-identity",
            converged=True,
            iterations=0,
            residual=0.0,
            spectral_radius=model.spectral_radius(),
            condition_number=1.0,
            jitter=0.0,
            tolerance=tolerance,
        )
        return 0.0, diagnostics
    return projected_dd(
        model,
        coordinate_projection(model.n, selected),
        tolerance=tolerance,
        max_iterations=max_iterations,
    )


def cut_weights(model_or_coefficients: VARModel | Sequence[Array]) -> Array:
    coefficients = (
        model_or_coefficients.coefficients
        if isinstance(model_or_coefficients, VARModel)
        else tuple(np.asarray(a, dtype=float) for a in model_or_coefficients)
    )
    n = coefficients[0].shape[0]
    weights = np.zeros((n, n), dtype=float)
    for coefficient in coefficients:
        if coefficient.shape != (n, n):
            raise ValidationError("lag matrices must have a common square shape")
        weights += coefficient.T**2
    np.fill_diagonal(weights, 0.0)
    return weights


def directed_cut(weights: Array, subset: Iterable[int]) -> float:
    matrix = np.asarray(weights, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValidationError("cut weights must be square")
    selected = set(canonical_subset(subset, matrix.shape[0]))
    return float(
        sum(
            matrix[source, target]
            for source in range(matrix.shape[0])
            for target in selected
            if source not in selected
        )
    )


def contractivity(model_or_coefficients: VARModel | Sequence[Array]) -> float:
    coefficients = (
        model_or_coefficients.coefficients
        if isinstance(model_or_coefficients, VARModel)
        else tuple(np.asarray(a, dtype=float) for a in model_or_coefficients)
    )
    return float(sum(np.linalg.norm(a, ord=2) for a in coefficients))


def weak_coupling_bounds(model: VARModel, subset_size: int, cut_value: float) -> dict[str, float]:
    """Return Phase-XXVIII sandwich bounds in the identity-innovation regime."""
    if not np.allclose(model.innovation_covariance, np.eye(model.n), atol=1e-12, rtol=0):
        raise ValidationError("weak-coupling cut sandwich currently requires identity innovations")
    if not 0 <= subset_size <= model.n:
        raise ValidationError("subset_size outside [0,n]")
    a = contractivity(model)
    if a >= 1.0:
        raise ValidationError("sandwich requires a strict contractivity sum below one")
    rank = min(subset_size, model.n - subset_size)
    denominator_lower = (1.0 + a) ** 2 + rank * a * a
    denominator_upper = (1.0 - a) ** 2
    lower = cut_value / denominator_lower
    upper = cut_value / denominator_upper
    return {
        "contractivity": a,
        "rank": float(rank),
        "lower": float(lower),
        "upper": float(upper),
        "multiplicative_ratio": float(denominator_lower / denominator_upper),
    }


def dsrg_swap_witness(parameter: float = 0.5) -> dict[str, float]:
    if not 0 < abs(parameter) < 1:
        raise ValidationError("parameter must satisfy 0 < |parameter| < 1")
    model = VARModel(
        coefficients=(np.array([[0.0, parameter], [parameter, 0.0]]),),
        innovation_covariance=np.eye(2),
        channel_names=("x1", "x2"),
    )
    coordinate_value, _ = coordinate_dd(model, (0,))
    dense = np.array([[1.0], [1.0]]) / math.sqrt(2.0)
    dense_value, _ = projected_dd(model, dense)
    exact = math.log1p(parameter * parameter)
    return {
        "parameter": float(parameter),
        "coordinate_dd": coordinate_value,
        "dense_dd": dense_value,
        "exact_gap": exact,
        "numerical_gap": coordinate_value - dense_value,
    }
