from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Callable, Sequence
import math

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import null_space

from ..errors import ValidationError
from ..objectives import orthonormalise
from .common import Counters

Array = NDArray[np.float64]


def leakage_value_gradient(coefficients: Sequence[Array], basis: Array) -> tuple[float, Array]:
    q = orthonormalise(basis)
    n, _ = q.shape
    projector_perp = np.eye(n) - q @ q.T
    value = 0.0
    ambient = np.zeros_like(q)
    for coefficient in coefficients:
        b = np.asarray(coefficient, dtype=float)
        if b.shape != (n, n):
            raise ValidationError("coefficient shape mismatch")
        reduced = q.T @ b @ q
        cross = q.T @ b @ projector_perp
        value += float(np.sum(cross * cross))
        ambient += 2.0 * (b @ b.T @ q - b @ q @ reduced.T - b.T @ q @ reduced)
    gradient = ambient - q @ (q.T @ ambient)
    return value, gradient


def _retract(q: Array, tangent: Array, step: float) -> Array:
    return orthonormalise(q + step * tangent)


@dataclass
class GrassmannRun:
    start_index: int
    objective: float
    stationarity_norm: float
    iterations: int
    converged: bool
    reason: str
    basis: list[list[float]]
    trace: list[dict[str, float]]

    def to_dict(self) -> dict:
        return asdict(self)


def optimise_multistart(
    n: int,
    k: int,
    objective: Callable[[Array], float],
    *,
    value_gradient: Callable[[Array], tuple[float, Array]] | None = None,
    starts: Sequence[Array] = (),
    random_starts: int = 8,
    seed: int = 0,
    max_iterations: int = 500,
    stationarity_tolerance: float = 1e-8,
    finite_difference_step: float = 1e-6,
    initial_step: float = 0.5,
) -> dict:
    if not 0 < k < n:
        raise ValidationError("Grassmann optimisation requires 0 < k < n")
    rng = np.random.default_rng(seed)
    start_list = [orthonormalise(start) for start in starts]
    coordinate_count = min(math.comb(n, k), max(1, random_starts // 2))
    for indices in list(combinations(range(n), k))[:coordinate_count]:
        start_list.append(np.eye(n)[:, indices])
    for _ in range(random_starts):
        start_list.append(orthonormalise(rng.normal(size=(n, k))))
    counters = Counters()
    runs: list[GrassmannRun] = []

    def finite_difference(q: Array) -> Array:
        complement = null_space(q.T)
        gradient = np.zeros_like(q)
        for a in range(complement.shape[1]):
            for b in range(k):
                direction = np.zeros_like(q)
                direction[:, b] = complement[:, a]
                plus = objective(_retract(q, direction, finite_difference_step))
                minus = objective(_retract(q, direction, -finite_difference_step))
                counters.objective_calls += 2
                gradient += ((plus - minus) / (2.0 * finite_difference_step)) * direction
        return gradient

    for start_index, start in enumerate(start_list):
        q = orthonormalise(start)
        trace = []
        converged = False
        reason = "maximum_iterations"
        for iteration in range(max_iterations + 1):
            counters.iterations += 1
            if value_gradient is None:
                value = float(objective(q)); counters.objective_calls += 1
                gradient = finite_difference(q)
            else:
                value, gradient = value_gradient(q); counters.objective_calls += 1
                value = float(value)
                gradient = gradient - q @ (q.T @ gradient)
            norm = float(np.linalg.norm(gradient, ord="fro"))
            trace.append({"iteration": float(iteration), "objective": value, "stationarity": norm})
            if norm <= stationarity_tolerance:
                converged = True
                reason = "stationarity_tolerance"
                break
            if iteration == max_iterations:
                break
            step = initial_step
            accepted = False
            while step >= 1e-12:
                candidate = _retract(q, -gradient, step)
                candidate_value = float(objective(candidate)); counters.objective_calls += 1
                counters.line_search_evaluations += 1
                if candidate_value <= value - 1e-4 * step * norm * norm:
                    q = candidate
                    accepted = True
                    break
                step *= 0.5
            if not accepted:
                reason = "line_search_stalled"
                break
        if value_gradient is None:
            value = float(objective(q)); counters.objective_calls += 1
            gradient = finite_difference(q)
        else:
            value, gradient = value_gradient(q); counters.objective_calls += 1
            gradient = gradient - q @ (q.T @ gradient)
        runs.append(
            GrassmannRun(
                start_index=start_index,
                objective=float(value),
                stationarity_norm=float(np.linalg.norm(gradient, ord="fro")),
                iterations=len(trace) - 1,
                converged=converged,
                reason=reason,
                basis=q.tolist(),
                trace=trace,
            )
        )
    best = min(runs, key=lambda run: (run.objective, run.stationarity_norm, run.start_index))
    return {
        "status": "NUMERICALLY_STATIONARY_MULTISTART_BASELINE",
        "best": best.to_dict(),
        "runs": [run.to_dict() for run in runs],
        "global_certified": False,
        "certificate_scope": "first_order_stationarity_only",
        "seed": seed,
        "counters": counters.to_dict(),
        "warnings": [
            "Multiple starts do not certify a global optimum.",
            "Stationarity is conditional on the numerical backend and tolerance.",
        ],
    }
