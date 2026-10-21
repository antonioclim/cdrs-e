"""Prepared rc3 runtime-boundary regressions. Execution remains UNRUN."""
from __future__ import annotations

from itertools import combinations as original_combinations

import numpy as np
import pytest

from cdrse.algorithms import grassmann
from cdrse.algorithms.dynamic import DynamicProblem, solve_edgeless_constant_cardinality
from cdrse.errors import ValidationError
from cdrse.models import VARModel


def _dynamic_problem(**updates):
    values = {
        "unary_costs": np.zeros((2, 2)),
        "spatial_weights": (np.zeros((2, 2)), np.zeros((2, 2))),
        "switching_costs": np.zeros((1, 2)),
        "exact_cardinalities": (1, 1),
    }
    values.update(updates)
    return DynamicProblem(**values)


def test_rc3_grassmann_consumes_only_the_coordinate_prefix(monkeypatch):
    """Abort before objective evaluation; reject eager iterator exhaustion."""
    yielded = []

    def guarded_combinations(items, k):
        iterator = original_combinations(items, k)
        for _ in range(2):
            item = next(iterator)
            yielded.append(item)
            yield item
        raise AssertionError("coordinate family was eagerly consumed")

    class ReachedEvaluation(Exception):
        pass

    def stop_before_evaluation(_basis):
        raise ReachedEvaluation

    monkeypatch.setattr(grassmann, "combinations", guarded_combinations)
    with pytest.raises(ReachedEvaluation):
        grassmann.optimise_multistart(
            4, 2, stop_before_evaluation,
            value_gradient=stop_before_evaluation,
            random_starts=4, max_iterations=0,
        )
    assert yielded == [(0, 1), (0, 2)]


@pytest.mark.parametrize("coefficient", [0.2, np.array(0.2), np.array([0.2])])
def test_rc3_var_lag_rank_rejected_as_validation_error(coefficient):
    with pytest.raises(ValidationError):
        VARModel(coefficients=(coefficient,), innovation_covariance=np.eye(1))


@pytest.mark.parametrize("field", ["unary_costs", "spatial_weights", "switching_costs"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_rc3_dynamic_nonfinite_costs_are_rejected(field, bad):
    if field == "unary_costs":
        value = np.array([[bad, 0.0], [0.0, 0.0]])
    elif field == "spatial_weights":
        value = (np.array([[0.0, bad], [0.0, 0.0]]), np.zeros((2, 2)))
    else:
        value = np.array([[bad, 0.0]])
    with pytest.raises(ValidationError):
        _dynamic_problem(**{field: value})


@pytest.mark.parametrize("bad", [True, np.bool_(True), 1.0, 1.5, "1", -1, 3])
def test_rc3_dynamic_cardinalities_reject_wrong_types_and_domain(bad):
    with pytest.raises(ValidationError):
        _dynamic_problem(exact_cardinalities=(bad, 1))


def test_rc3_dynamic_cardinalities_accept_python_and_numpy_integers():
    problem = _dynamic_problem(exact_cardinalities=(1, np.int64(1)))
    assert tuple(problem.exact_cardinalities) == (1, 1)


@pytest.mark.parametrize("bad", [0, -1, True, False, np.bool_(True), 1.0, 1.5, "1"])
def test_rc3_flow_scale_rejected_before_flow_execution(monkeypatch, bad):
    def forbidden_flow(*_args, **_kwargs):
        raise AssertionError("flow must not execute for an invalid scale")

    monkeypatch.setattr("cdrse.algorithms.dynamic.nx.network_simplex", forbidden_flow)
    with pytest.raises(ValidationError):
        solve_edgeless_constant_cardinality(_dynamic_problem(), integer_scale=bad)


@pytest.mark.parametrize("scale", [1, np.int64(2)])
def test_rc3_flow_positive_integer_scale_passes_scale_validation(monkeypatch, scale):
    class ReachedFlow(Exception):
        pass

    def stop_before_flow(*_args, **_kwargs):
        raise ReachedFlow

    monkeypatch.setattr("cdrse.algorithms.dynamic.nx.network_simplex", stop_before_flow)
    with pytest.raises(ReachedFlow):
        solve_edgeless_constant_cardinality(_dynamic_problem(), integer_scale=scale)
