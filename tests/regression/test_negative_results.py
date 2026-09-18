from __future__ import annotations

import itertools
import math

import numpy as np
import pytest

from cdrse.algorithms import DynamicProblem, solve_time_expanded_mincut
from cdrse.algorithms.common import SolverResult
from cdrse.algorithms.robust import solve_scenarios_exhaustive
from cdrse.certificates import AlgorithmicLayer, DecisionCertificate, EconomicLayer, NumericalLayer, StatisticalLayer
from cdrse.errors import ValidationError
from cdrse.economics import empirical_cvar


def test_worst_case_and_cvar_counterexample_regression() -> None:
    c = math.log(5 / 4)

    def scenario1(subset):
        selected = set(subset)
        return c if 1 in selected and 0 not in selected else 0.0

    def scenario2(subset):
        selected = set(subset)
        return c if 3 in selected and 2 not in selected else 0.0

    result = solve_scenarios_exhaustive(4, [scenario1, scenario2], exact_k=2, mode="worst")
    assert result["submodularity_assumed"] is False
    assert empirical_cvar([0.0, c], 0.5) == pytest.approx(c)
    A = (0, 1)
    B = (1, 3)
    H = lambda S: max(scenario1(S), scenario2(S))
    slack = H(A) + H(B) - H(tuple(set(A) & set(B))) - H(tuple(set(A) | set(B)))
    assert slack == pytest.approx(-c)


def test_historical_null_incumbent_is_rejected() -> None:
    certificate = DecisionCertificate(
        problem_sha256="a" * 64,
        selected=None,
        algorithmic=AlgorithmicLayer(True, 0.0, -1.0, "node_budget", False),
        numerical=NumericalLayer("float64", True, True, 1e-9),
        statistical=StatisticalLayer("estimand", False, 1.0),
        economic=EconomicLayer("E0", True, True),
    )
    with pytest.raises(ValidationError):
        certificate.validate()


def test_nonfinite_solver_result_is_rejected() -> None:
    result = SolverResult("BAD", (0,), float("-inf"), False, False, "bad")
    with pytest.raises(ValidationError):
        result.validate()


def test_mincut_rejects_global_cardinality() -> None:
    problem = DynamicProblem(
        np.zeros((2, 3)),
        (np.zeros((3, 3)), np.zeros((3, 3))),
        np.zeros((1, 3)),
        (1, 1),
    )
    with pytest.raises(ValidationError):
        solve_time_expanded_mincut(problem)
