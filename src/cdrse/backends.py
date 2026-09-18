"""Explicit arithmetic backends and their semantic limits."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence
import math

import mpmath as mp
import numpy as np
import sympy as sp

from .errors import NumericalConvergenceError, UnsupportedBackendError, ValidationError
from .models import VARModel, canonical_subset


@dataclass(frozen=True)
class BackendInfo:
    name: str
    exact: bool
    precision: str
    scope: str


class ExactRationalBackend:
    """Exact arithmetic for combinatorial costs and symbolic small witnesses.

    This backend deliberately does not claim a general exact Riccati solver.
    """

    info = BackendInfo(
        name="exact-rational",
        exact=True,
        precision="Fraction/SymPy exact expressions",
        scope="directed cuts, modular resources, algebraic witness identities",
    )

    @staticmethod
    def fraction(value: int | str | Fraction) -> Fraction:
        if isinstance(value, (bool, np.bool_)):
            raise ValidationError("boolean is not an exact rational input")
        try:
            if isinstance(value, Fraction):
                return value
            if isinstance(value, (int, np.integer)):
                return Fraction(int(value))
            if isinstance(value, str):
                return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValidationError("invalid exact rational input") from exc
        raise ValidationError("expected an integer, rational string or Fraction")

    @staticmethod
    def directed_cut(weights: Sequence[Sequence[int | str | Fraction]], subset: Iterable[int]) -> Fraction:
        n = len(weights)
        if any(len(row) != n for row in weights):
            raise ValidationError("exact cut matrix must be square")
        selected = set(canonical_subset(subset, n))
        total = Fraction(0)
        for source in range(n):
            for target in range(n):
                if source not in selected and target in selected:
                    total += ExactRationalBackend.fraction(weights[source][target])
        return total

    @staticmethod
    def dsrg_swap_witness(parameter: int | str | Fraction = Fraction(1, 2)) -> sp.Expr:
        value = ExactRationalBackend.fraction(parameter)
        if not 0 < abs(value) < 1:
            raise ValidationError("witness parameter must satisfy 0 < |b| < 1")
        b = sp.Rational(value.numerator, value.denominator)
        return sp.log(1 + b**2)


class Float64Backend:
    info = BackendInfo(
        name="float64",
        exact=False,
        precision="IEEE-754 binary64",
        scope="general stable VAR evaluation with residual and conditioning diagnostics",
    )


class HighPrecisionAuditBackend:
    """Arbitrary-precision audit backend for small projected VAR instances."""

    def __init__(self, decimal_digits: int = 80, tolerance: str = "1e-60", max_iterations: int = 50_000):
        if decimal_digits < 30:
            raise ValidationError("high-precision audit requires at least 30 decimal digits")
        self.decimal_digits = int(decimal_digits)
        self.tolerance = mp.mpf(tolerance)
        self.max_iterations = int(max_iterations)

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="high-precision-audit",
            exact=False,
            precision=f"mpmath {self.decimal_digits} decimal digits",
            scope="small dense projected VAR instances; audit, not scalability",
        )

    @staticmethod
    def _matrix(value: np.ndarray) -> mp.matrix:
        return mp.matrix([[mp.mpf(str(float(x))) for x in row] for row in np.asarray(value)])

    @staticmethod
    def _transpose(value: mp.matrix) -> mp.matrix:
        return value.T

    @staticmethod
    def _frobenius(value: mp.matrix) -> mp.mpf:
        return mp.sqrt(mp.fsum(value[i, j] ** 2 for i in range(value.rows) for j in range(value.cols)))

    def projected_var_dd(self, model: VARModel, projection: np.ndarray) -> tuple[mp.mpf, dict[str, object]]:
        mp.mp.dps = self.decimal_digits
        q = np.asarray(projection, dtype=float)
        if q.ndim != 2 or q.shape[0] != model.n:
            raise ValidationError("projection must be n-by-k")
        from .objectives import orthonormalise
        q = orthonormalise(q)
        transition_np, injection_np, _ = model.companion()
        transition = self._matrix(transition_np)
        injection = self._matrix(injection_np)
        sigma = self._matrix(model.innovation_covariance)
        process = injection * sigma * injection.T
        state_dim = transition.rows
        identity = mp.eye(state_dim)

        # Stationary covariance by fixed-point iteration from zero.
        gamma = mp.zeros(state_dim)
        stat_iterations = 0
        for stat_iterations in range(1, self.max_iterations + 1):
            nxt = transition * gamma * transition.T + process
            rel = self._frobenius(nxt - gamma) / max(mp.mpf(1), self._frobenius(gamma))
            gamma = nxt
            if rel <= self.tolerance:
                break
        else:
            raise NumericalConvergenceError("high-precision stationary covariance iteration failed")

        k = q.shape[1]
        observation_np = np.zeros((k, state_dim), dtype=float)
        observation_np[:, : model.n] = q.T
        observation = self._matrix(observation_np)
        pred = gamma
        riccati_iterations = 0
        riccati_residual = mp.inf
        for riccati_iterations in range(1, self.max_iterations + 1):
            omega = observation * pred * observation.T
            try:
                gain = pred * observation.T * omega ** -1
            except ZeroDivisionError as exc:
                raise NumericalConvergenceError("singular high-precision innovation covariance") from exc
            filtered = pred - gain * observation * pred
            nxt = transition * filtered * transition.T + process
            riccati_residual = self._frobenius(nxt - pred) / max(mp.mpf(1), self._frobenius(pred))
            pred = nxt
            if riccati_residual <= self.tolerance:
                break
        else:
            raise NumericalConvergenceError("high-precision Riccati iteration failed")
        omega = observation * pred * observation.T
        qmp = self._matrix(q)
        macro_sigma = qmp.T * sigma * qmp
        det_omega = mp.det(omega)
        det_sigma = mp.det(macro_sigma)
        if det_omega <= 0 or det_sigma <= 0:
            raise NumericalConvergenceError("high-precision determinant is non-positive")
        value = mp.log(det_omega) - mp.log(det_sigma)
        return value, {
            "backend": self.info.name,
            "decimal_digits": self.decimal_digits,
            "stationary_iterations": stat_iterations,
            "riccati_iterations": riccati_iterations,
            "riccati_residual": mp.nstr(riccati_residual, 20),
            "exact": False,
        }


def backend_by_name(name: str) -> ExactRationalBackend | Float64Backend | HighPrecisionAuditBackend:
    normalised = name.strip().lower()
    if normalised in {"float64", "numpy"}:
        return Float64Backend()
    if normalised in {"exact", "exact-rational", "rational"}:
        return ExactRationalBackend()
    if normalised in {"mp", "high-precision", "high-precision-audit"}:
        return HighPrecisionAuditBackend()
    raise UnsupportedBackendError(f"unknown backend: {name}")
