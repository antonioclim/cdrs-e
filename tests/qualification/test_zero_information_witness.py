"""Regression for the reviewed zero-information canonical-witness boundary.

The oracle enumerates the finite family without calling a solver objective,
feasibility predicate or Pareto helper. Non-zero cut weights are intentional:
zero weights would conceal the original state-retention defect.
"""
from fractions import Fraction

import numpy as np
import pytest

from cdrse.algorithms import (
    approximate_decomposition,
    solve_forest_cut,
    solve_treewidth_cut,
)
from cdrse.models import SelectionProblem, ServiceConstraints


def _problem(case: str, beta: float) -> SelectionProblem:
    if case == "minimal":
        weights = np.zeros((3, 3))
        weights[1, 0] = 1.0
        constraints = ServiceConstraints(exact_k=1)
        costs = (1, 1, 1)
    elif case == "resources":
        weights = np.zeros((6, 6))
        weights[1, 0], weights[2, 1] = 2.0, 0.125
        weights[4, 3], weights[5, 4] = 1.0, 0.5
        constraints = ServiceConstraints(
            k_min=2, k_max=3, budget=5, mandatory=(0,), forbidden=(5,),
            coverage_groups=((1, 2), (3, 4)),
        )
        costs = (2, 1, 0, 2, 3, 0)
    else:
        weights = np.zeros((4, 4))
        weights[1, 0], weights[2, 1], weights[3, 2] = 1.0, 0.5, 0.25
        constraints = ServiceConstraints(k_min=1, k_max=3, budget=3)
        costs = (2, 0, 0, 1)
    return SelectionProblem(None, constraints, costs, weights, 0.0, beta)


def _independent_rows(problem: SelectionProblem):
    c = problem.constraints
    rows = []
    for mask in range(1 << problem.n):
        selected = tuple(i for i in range(problem.n) if mask & (1 << i))
        members = set(selected)
        if c.exact_k is not None and len(selected) != c.exact_k:
            continue
        if c.exact_k is None and not c.k_min <= len(selected) <= c.k_max:
            continue
        if c.exclude_empty and not selected or c.exclude_full and len(selected) == problem.n:
            continue
        if not set(c.mandatory) <= members or set(c.forbidden) & members:
            continue
        if any(not members.intersection(group) for group in c.coverage_groups):
            continue
        cost = sum((Fraction(problem.activation_costs[i]) for i in selected), Fraction(0))
        if c.budget is not None and cost > Fraction(c.budget):
            continue
        cut = sum((Fraction(float(problem.cut_weights[j, i]))
                   for i in selected for j in range(problem.n) if j not in members), Fraction(0))
        rows.append((cost, cut, selected))
    return rows


@pytest.mark.parametrize("solver", ["forest", "treewidth"])
@pytest.mark.parametrize("beta", [0.0, 1.0])
@pytest.mark.parametrize("case", ["minimal", "resources", "cardinality_interval"])
def test_zero_information_witness_and_unweighted_pareto_front(solver, beta, case):
    problem = _problem(case, beta)
    rows = _independent_rows(problem)
    expected_cost, expected_cut, expected_selected = min(
        rows, key=lambda row: (Fraction(beta) * row[0], row[2])
    )
    result = (solve_forest_cut(problem) if solver == "forest" else
              solve_treewidth_cut(problem, approximate_decomposition(problem.cut_weights)))

    assert result.selected == expected_selected
    assert result.objective == float(Fraction(beta) * expected_cost)
    assert result.metadata["cut_value"] == float(expected_cut)
    assert result.metadata["activation_cost"] == expected_cost
    contract = result.to_record()
    assert contract["feasible_family_sha256"] == problem.sha256
    assert contract["proof_status"] == "EXACT_STORED_INPUT"

    # A canonical objective witness can be cut-dominated when alpha is zero.
    # The existing two-objective frontier must still contain the original cuts.
    unique = {}
    for cost, cut, selected in rows:
        unique[(cost, cut)] = min(selected, unique.get((cost, cut), selected))
    expected_front = {
        (cost, cut): selected for (cost, cut), selected in unique.items()
        if not any(other_cost <= cost and other_cut <= cut and
                   (other_cost < cost or other_cut < cut)
                   for other_cost, other_cut in unique)
    }
    actual_front = {
        (Fraction(row["cost"]), Fraction(int(row["loss_exact"]["numerator"]),
                                         int(row["loss_exact"]["denominator"]))): tuple(row["selected"])
        for row in result.metadata["pareto_front"]
    }
    assert actual_front == expected_front
