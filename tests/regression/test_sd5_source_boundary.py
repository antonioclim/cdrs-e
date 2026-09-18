"""P10-SD5 source-boundary obligations fixed before the candidate patch."""
from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest
import sympy as sp

from cdrse.backends import ExactRationalBackend
from cdrse.errors import ValidationError
from cdrse.hashing import object_sha256
from cdrse.models import SelectionProblem, ServiceConstraints, VARModel
from cdrse.objectives import coordinate_dd


WEIGHTS = [[0, "1/2"], ["3/4", 0]]


@pytest.mark.parametrize(
    "subset",
    [(0.75,), (-1,), (2,), (1, 1), (True,)],
    ids=["fractional", "negative", "out_of_range", "duplicate", "boolean"],
)
def test_exact_cut_rejects_noncanonical_subset(subset) -> None:
    with pytest.raises(ValidationError):
        ExactRationalBackend.directed_cut(WEIGHTS, subset)


def test_exact_cut_retains_valid_fraction_result() -> None:
    assert ExactRationalBackend.directed_cut(WEIGHTS, (1,)) == Fraction(1, 2)


@pytest.mark.parametrize(
    "parameter",
    [Fraction(1, 2**1075), Fraction(2**60 - 1, 2**60)],
    ids=["positive_underflows_float", "strictly_below_one_rounds_to_one"],
)
def test_exact_witness_domain_is_decided_exactly(parameter: Fraction) -> None:
    observed = ExactRationalBackend.dsrg_swap_witness(parameter)
    expected = sp.log(1 + sp.Rational(parameter.numerator, parameter.denominator) ** 2)
    assert observed == expected


def test_exact_fraction_rejects_boolean() -> None:
    with pytest.raises(ValidationError):
        ExactRationalBackend.fraction(True)


@pytest.mark.parametrize("subset", [(), (0, 1)], ids=["empty", "full"])
@pytest.mark.parametrize("tolerance", [0.0, -1.0, math.nan, math.inf], ids=["zero", "negative", "nan", "infinity"])
def test_coordinate_endpoints_reject_invalid_tolerance(subset, tolerance: float) -> None:
    model = VARModel((np.zeros((2, 2)),), np.eye(2))
    with pytest.raises(ValidationError):
        coordinate_dd(model, subset, tolerance=tolerance)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SelectionProblem(None, ServiceConstraints(exact_k=1), (True, False), np.zeros((2, 2))),
        lambda: SelectionProblem(None, ServiceConstraints(exact_k=1, budget=True), (1.0, 1.0), np.zeros((2, 2))),
        lambda: SelectionProblem(None, ServiceConstraints(exact_k=1), (1.0, 1.0), np.zeros((2, 2)), True, 0.0),
        lambda: SelectionProblem(None, ServiceConstraints(exact_k=1), (1.0, 1.0), np.zeros((2, 2)), 1.0, False),
    ],
    ids=["activation_cost", "budget", "information_weight", "cost_weight"],
)
def test_problem_rejects_boolean_numeric_fields(factory) -> None:
    with pytest.raises(ValidationError):
        factory()


def test_var_model_rejects_textual_numeric_coercion() -> None:
    with pytest.raises(ValidationError):
        VARModel.from_dict(
            {
                "coefficients": [[["0.0", "0.0"], ["0.0", "0.0"]]],
                "innovation_covariance": [["1.0", "0.0"], ["0.0", "1.0"]],
            }
        )


def test_hash_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(TypeError):
        object_sha256({1: "integer-key", "1": "string-key"})
