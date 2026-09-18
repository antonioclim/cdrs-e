from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest
import sympy as sp

from cdrse.backends import ExactRationalBackend, HighPrecisionAuditBackend, backend_by_name
from cdrse.errors import UnsupportedBackendError, ValidationError
from cdrse.models import VARModel
from cdrse.objectives import (
    contractivity,
    coordinate_dd,
    cut_weights,
    directed_cut,
    dsrg_swap_witness,
    projected_dd,
    weak_coupling_bounds,
)


def model() -> VARModel:
    return VARModel((np.array([[0.0, 0.5], [0.5, 0.0]]),), np.eye(2))


def test_exact_rational_cut_and_witness() -> None:
    weights = [[0, "1/2"], ["3/4", 0]]
    assert ExactRationalBackend.directed_cut(weights, (1,)) == Fraction(1, 2)
    assert ExactRationalBackend.dsrg_swap_witness(Fraction(1, 2)) == sp.log(sp.Rational(5, 4))


def test_float64_witness_values() -> None:
    result = dsrg_swap_witness(0.5)
    assert math.isclose(result["coordinate_dd"], math.log(5 / 4), abs_tol=1e-10)
    assert abs(result["dense_dd"]) < 1e-10
    assert math.isclose(result["numerical_gap"], result["exact_gap"], abs_tol=1e-10)


def test_coordinate_endpoints_are_zero() -> None:
    m = model()
    assert coordinate_dd(m, ())[0] == 0.0
    assert coordinate_dd(m, (0, 1))[0] == 0.0


def test_projected_dd_is_basis_invariant() -> None:
    m = model()
    q = np.array([[1.0], [1.0]]) / math.sqrt(2)
    left = projected_dd(m, q)[0]
    right = projected_dd(m, -3.0 * q)[0]
    assert abs(left - right) < 1e-10


def test_cut_orientation_and_weights() -> None:
    coefficients = (np.array([[0.0, 2.0], [3.0, 0.0]]),)
    weights = cut_weights(coefficients)
    assert weights[0, 1] == 9.0  # source 0 -> target 1 uses A[target,source]^2
    assert weights[1, 0] == 4.0
    assert directed_cut(weights, (1,)) == 9.0


def test_contractivity_and_weak_coupling_bounds() -> None:
    m = VARModel((np.array([[0.0, 0.1], [0.1, 0.0]]),), np.eye(2))
    assert math.isclose(contractivity(m), 0.1)
    bounds = weak_coupling_bounds(m, 1, 0.01)
    assert 0 < bounds["lower"] <= 0.01 <= bounds["upper"]
    dense = VARModel((np.array([[0.0, 0.1], [0.1, 0.0]]),), np.array([[1.0, 0.2], [0.2, 1.0]]))
    with pytest.raises(ValidationError):
        weak_coupling_bounds(dense, 1, 0.01)


def test_high_precision_matches_float64() -> None:
    m = model()
    value, audit = HighPrecisionAuditBackend(50, "1e-38").projected_var_dd(m, np.array([[1.0], [0.0]]))
    assert abs(float(value) - math.log(5 / 4)) < 1e-20
    assert audit["riccati_iterations"] >= 1


def test_backend_dispatch_and_errors() -> None:
    assert backend_by_name("rational").info.exact
    assert backend_by_name("numpy").info.name == "float64"
    assert backend_by_name("mp").info.name == "high-precision-audit"
    with pytest.raises(UnsupportedBackendError):
        backend_by_name("imaginary")
    with pytest.raises(ValidationError):
        ExactRationalBackend.dsrg_swap_witness(Fraction(2, 1))
