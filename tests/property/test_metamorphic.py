from __future__ import annotations

import math

import numpy as np
import pytest

from cdrse.algorithms.grassmann import leakage_value_gradient
from cdrse.economics import pareto_front
from cdrse.models import VARModel
from cdrse.objectives import coordinate_dd, directed_cut, projected_dd

rng = np.random.default_rng(9917)


@pytest.mark.metamorphic
def test_grassmann_quotient_invariance() -> None:
    for n in range(3, 7):
        for k in range(1, n):
            for _ in range(5):
                coefficients = [rng.normal(size=(n, n)) * 0.1 for _ in range(2)]
                q = np.linalg.qr(rng.normal(size=(n, k)))[0]
                rotation = np.linalg.qr(rng.normal(size=(k, k)))[0]
                left, _ = leakage_value_gradient(coefficients, q)
                right, _ = leakage_value_gradient(coefficients, q @ rotation)
                assert math.isclose(left, right, abs_tol=1e-10)


@pytest.mark.metamorphic
def test_coordinate_rescaling_invariance() -> None:
    base = VARModel((np.array([[0.1, 0.2], [0.3, -0.1]]),), np.diag([1.0, 2.0]))
    scale = np.diag([2.0, 0.5])
    inverse = np.diag([0.5, 2.0])
    transformed = VARModel((scale @ base.coefficients[0] @ inverse,), scale @ base.innovation_covariance @ scale)
    for subset in ((0,), (1,)):
        left = coordinate_dd(base, subset)[0]
        right = coordinate_dd(transformed, subset)[0]
        assert math.isclose(left, right, abs_tol=1e-8)


@pytest.mark.metamorphic
def test_cut_scaling_and_permutation() -> None:
    weights = np.array([[0, 2, 0], [1, 0, 3], [4, 0, 0]], dtype=float)
    selected = (0, 2)
    value = directed_cut(weights, selected)
    assert directed_cut(7.0 * weights, selected) == pytest.approx(7.0 * value)
    permutation = np.array([2, 0, 1])
    permuted = weights[np.ix_(permutation, permutation)]
    inverse_position = {original: new for new, original in enumerate(permutation)}
    permuted_subset = tuple(inverse_position[i] for i in selected)
    assert directed_cut(permuted, permuted_subset) == pytest.approx(value)


@pytest.mark.metamorphic
def test_pareto_positive_affine_scaling() -> None:
    rows = [
        {"id": "a", "cost": 0.0, "loss": 4.0},
        {"id": "b", "cost": 2.0, "loss": 3.0},
        {"id": "c", "cost": 4.0, "loss": 0.0},
        {"id": "d", "cost": 3.0, "loss": 5.0},
    ]
    original = {row["id"] for row in pareto_front(rows)}
    transformed = [
        {"id": row["id"], "cost": 5.0 + 3.0 * row["cost"], "loss": -2.0 + 7.0 * row["loss"]}
        for row in rows
    ]
    assert {row["id"] for row in pareto_front(transformed)} == original
