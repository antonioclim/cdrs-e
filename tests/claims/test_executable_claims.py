from __future__ import annotations

from copy import deepcopy
import numpy as np
import pytest

from cdrse.algorithms import (
    CANONICAL_WITNESS_POLICY,
    TreeDecomposition,
    approximate_decomposition,
    solve_branch_bound,
    solve_exhaustive,
    solve_forest_cut,
    solve_treewidth_cut,
)
from cdrse.errors import ValidationError
from cdrse.models import SelectionProblem, ServiceConstraints
from cdrse.verification import verify_result

SEED = 20261010


def _problem(weights: np.ndarray, *, exact_k: int, costs: tuple[int, ...], cost_weight: float = 0.0) -> SelectionProblem:
    return SelectionProblem(None, ServiceConstraints(exact_k=exact_k), costs, weights, 1.0, cost_weight)


@pytest.mark.claim
@pytest.mark.parametrize("n", range(2, 8))
def test_claim_exact_forest_and_treewidth_backends_match_exhaustive(n: int) -> None:
    rng = np.random.default_rng(SEED + n)
    weights = np.zeros((n, n), dtype=float)
    for child in range(1, n):
        parent = int(rng.integers(0, child))
        weights[parent, child] = int(rng.integers(0, 5))
        weights[child, parent] = int(rng.integers(0, 5))
    costs = tuple(int(x) for x in rng.integers(0, 4, size=n))
    problem = _problem(weights, exact_k=max(1, n // 2), costs=costs, cost_weight=0.25)
    exhaustive = solve_exhaustive(problem)
    forest = solve_forest_cut(problem)
    treewidth = solve_treewidth_cut(problem, approximate_decomposition(weights))
    assert forest.objective == exhaustive.objective
    assert treewidth.objective == exhaustive.objective
    assert forest.selected == exhaustive.selected
    assert treewidth.selected == exhaustive.selected
    assert forest.metadata["tie_break_policy"] == CANONICAL_WITNESS_POLICY
    assert treewidth.metadata["tie_break_policy"] == CANONICAL_WITNESS_POLICY


@pytest.mark.claim
def test_claim_all_exact_static_backends_use_canonical_equal_objective_witness() -> None:
    for costs, k, expected, decomposition in [
        ((1, 0), 1, (0,), TreeDecomposition(((0,), (1,)), ((0, 1),))),
        ((0, 0, 0), 2, (0, 1), TreeDecomposition(((0, 1, 2),), ())),
    ]:
        problem = _problem(np.zeros((len(costs), len(costs))), exact_k=k, costs=costs)
        branch, certificate = solve_branch_bound(problem)
        results = [solve_exhaustive(problem), solve_forest_cut(problem), solve_treewidth_cut(problem, decomposition), branch]
        assert {result.selected for result in results} == {expected}
        assert all(result.metadata["tie_break_policy"] == CANONICAL_WITNESS_POLICY for result in results)
        assert certificate is not None and certificate.selected == expected


@pytest.mark.claim
def test_claim_exact_branch_bound_agrees_with_exhaustive_on_generated_instances() -> None:
    rng = np.random.default_rng(SEED)
    checks = 0
    for n in range(3, 8):
        for _ in range(5):
            weights = rng.integers(0, 4, size=(n, n)).astype(float)
            np.fill_diagonal(weights, 0.0)
            costs = tuple(int(x) for x in rng.integers(0, 5, size=n))
            problem = _problem(weights, exact_k=max(1, n // 2), costs=costs, cost_weight=0.2)
            expected = solve_exhaustive(problem)
            actual, certificate = solve_branch_bound(problem)
            assert actual.objective == expected.objective
            assert actual.selected == expected.selected
            assert certificate is not None
            checks += 1
    assert checks == 25


@pytest.mark.claim
def test_claim_callback_evaluation_never_self_certifies() -> None:
    problem = SelectionProblem(None, ServiceConstraints(exact_k=1), (0.0, 0.0))
    result, certificate = solve_branch_bound(problem, lambda subset: float(sum(subset)))
    assert certificate is None and not result.certified and not result.exact
    assert result.metadata["certificate_scope"] == "none; unenclosed callback evaluation"


@pytest.mark.claim
def test_claim_unenclosed_callback_global_bound_is_rejected() -> None:
    problem = SelectionProblem(None, ServiceConstraints(exact_k=1), (0.0, 0.0))
    result, _ = solve_branch_bound(problem, lambda subset: float(sum(subset)))
    forged = deepcopy(result.metadata["result_contract"])
    forged["global_lower_bound"] = {"numerator": "0", "denominator": "1"}
    with pytest.raises(ValidationError, match="unsupported global lower bound"):
        verify_result(problem, forged)


@pytest.mark.claim
def test_claim_cut_scaling_is_metamorphic_and_preserves_canonical_selection() -> None:
    weights = np.array([[0, 2, 0, 1], [3, 0, 4, 0], [0, 1, 0, 2], [2, 0, 5, 0]], dtype=float)
    costs = (1, 1, 1, 1)
    base = _problem(weights, exact_k=2, costs=costs)
    scaled = _problem(7 * weights, exact_k=2, costs=costs)
    base_result, scaled_result = solve_exhaustive(base), solve_exhaustive(scaled)
    assert scaled_result.selected == base_result.selected
    assert scaled_result.objective == pytest.approx(7 * base_result.objective)


@pytest.mark.claim
def test_claim_invalid_forest_support_fails_loudly() -> None:
    weights = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
    with pytest.raises(ValidationError, match="not a forest"):
        solve_forest_cut(_problem(weights, exact_k=1, costs=(0, 0, 0)))


@pytest.mark.claim
def test_claim_negative_cut_weights_are_rejected() -> None:
    weights = np.array([[0.0, -0.5], [0.0, 0.0]])
    with pytest.raises(ValidationError, match="non-negative"):
        _problem(weights, exact_k=1, costs=(0, 0))
