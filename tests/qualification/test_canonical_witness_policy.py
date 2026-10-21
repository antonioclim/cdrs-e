from __future__ import annotations

import numpy as np

from cdrse.algorithms import (
    CANONICAL_WITNESS_POLICY,
    TreeDecomposition,
    solve_branch_bound,
    solve_exhaustive,
    solve_forest_cut,
    solve_treewidth_cut,
)
from cdrse.models import SelectionProblem, ServiceConstraints


def _problem(costs: tuple[float, ...], exact_k: int) -> SelectionProblem:
    n = len(costs)
    return SelectionProblem(
        model=None,
        constraints=ServiceConstraints(exact_k=exact_k),
        activation_costs=costs,
        cut_weights=np.zeros((n, n), dtype=float),
        information_weight=1.0,
        cost_weight=0.0,
    )


def test_equal_objective_witness_is_lexicographically_smallest_across_exact_backends() -> None:
    problem = _problem((1.0, 0.0), 1)
    expected = (0,)
    decomposition = TreeDecomposition(bags=((0,), (1,)), edges=((0, 1),))
    branch, certificate = solve_branch_bound(problem)
    results = [solve_exhaustive(problem), solve_forest_cut(problem), solve_treewidth_cut(problem, decomposition), branch]
    assert {r.selected for r in results} == {expected}
    assert all(r.metadata['tie_break_policy'] == CANONICAL_WITNESS_POLICY for r in results)
    assert certificate is not None and certificate.selected == expected


def test_multi_coordinate_equal_objective_witness_is_canonical() -> None:
    problem = _problem((0.0, 0.0, 0.0), 2)
    expected = (0, 1)
    decomposition = TreeDecomposition(bags=((0, 1, 2),), edges=())
    branch, certificate = solve_branch_bound(problem)
    results = [solve_exhaustive(problem), solve_forest_cut(problem), solve_treewidth_cut(problem, decomposition), branch]
    assert {r.selected for r in results} == {expected}
    assert certificate is not None and certificate.selected == expected
