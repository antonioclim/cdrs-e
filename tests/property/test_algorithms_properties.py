from __future__ import annotations

import itertools
import math

import networkx as nx
import numpy as np
import pytest

from cdrse.algorithms import (
    DynamicProblem,
    TreeDecomposition,
    approximate_decomposition,
    dynamic_objective,
    leakage_value_gradient,
    optimise_multistart,
    solve_branch_bound,
    solve_edgeless_constant_cardinality,
    solve_explicit_families,
    solve_forest_cut,
    solve_forest_trajectory,
    solve_time_expanded_mincut,
    solve_treewidth_cut,
)
from cdrse.algorithms.exhaustive import solve_exhaustive
from cdrse.errors import ValidationError
from cdrse.models import SelectionProblem, ServiceConstraints
from cdrse.objectives import directed_cut

SEED = 20260912
rng = np.random.default_rng(SEED)


def random_forest_weights(n: int) -> np.ndarray:
    weights = np.zeros((n, n), dtype=float)
    for vertex in range(1, n):
        if rng.random() < 0.85:
            parent = int(rng.integers(0, vertex))
            weights[parent, vertex] = int(rng.integers(0, 7))
            weights[vertex, parent] = int(rng.integers(0, 7))
            if weights[parent, vertex] == 0 and weights[vertex, parent] == 0:
                weights[parent, vertex] = 1
    return weights


def brute_problem(problem: SelectionProblem):
    rows = []
    constraints = problem.constraints
    if constraints.exact_k is not None:
        sizes = (constraints.exact_k,)
    else:
        sizes = range(constraints.k_min, (problem.n if constraints.k_max is None else constraints.k_max) + 1)
    for size in sizes:
        for subset in itertools.combinations(range(problem.n), size):
            if constraints.is_feasible(subset, problem.n, problem.activation_costs):
                loss = directed_cut(problem.cut_weights, subset)
                objective = problem.information_weight * loss + problem.cost_weight * sum(problem.activation_costs[i] for i in subset)
                rows.append((objective, loss, sum(problem.activation_costs[i] for i in subset), subset))
    return sorted(rows)


@pytest.mark.property
def test_random_forest_dp_matches_enumeration() -> None:
    checks = 0
    for n in range(2, 9):
        for _ in range(18):
            weights = random_forest_weights(n)
            costs = tuple(int(x) for x in rng.integers(0, 5, size=n))
            k = int(rng.integers(1, n))
            budget = int(rng.integers(0, max(1, sum(costs) + 1)))
            mandatory = () if rng.random() < 0.7 else (int(rng.integers(0, n)),)
            forbidden = ()
            if rng.random() < 0.3:
                candidate = int(rng.integers(0, n))
                forbidden = () if candidate in mandatory else (candidate,)
            groups = ()
            if rng.random() < 0.6:
                group = tuple(sorted(set(rng.choice(n, size=int(rng.integers(1, n + 1)), replace=False).tolist())))
                groups = () if set(group).issubset(forbidden) else (group,)
            problem = SelectionProblem(
                None,
                ServiceConstraints(exact_k=k, budget=budget, mandatory=mandatory, forbidden=forbidden, coverage_groups=groups),
                costs,
                weights,
            )
            result = solve_forest_cut(problem)
            brute = brute_problem(problem)
            if not brute:
                assert result.status == "INFEASIBLE"
            else:
                assert math.isclose(result.objective, brute[0][0], abs_tol=1e-9)
                assert math.isclose(result.metadata["cut_value"], brute[0][1], abs_tol=1e-9)
                assert result.selected in {row[3] for row in brute if math.isclose(row[0], brute[0][0], abs_tol=1e-9)}
            checks += 1
    assert checks == 126


@pytest.mark.property
def test_random_treewidth_dp_matches_enumeration() -> None:
    checks = 0
    for n in range(3, 8):
        for _ in range(12):
            weights = np.zeros((n, n), dtype=float)
            for u in range(n):
                for v in range(u + 1, n):
                    if rng.random() < 0.25:
                        weights[u, v] = int(rng.integers(0, 5))
                        weights[v, u] = int(rng.integers(0, 5))
                        if weights[u, v] == 0 and weights[v, u] == 0:
                            weights[u, v] = 1
            costs = tuple(int(x) for x in rng.integers(0, 5, size=n))
            k = int(rng.integers(1, n))
            budget = int(rng.integers(0, max(1, sum(costs) + 1)))
            problem = SelectionProblem(None, ServiceConstraints(exact_k=k, budget=budget), costs, weights)
            decomposition = approximate_decomposition(weights)
            result = solve_treewidth_cut(problem, decomposition)
            brute = brute_problem(problem)
            if not brute:
                assert result.status == "INFEASIBLE"
            else:
                assert math.isclose(result.objective, brute[0][0], abs_tol=1e-9)
            checks += 1
    assert checks == 60


@pytest.mark.property
def test_branch_bound_exact_and_anytime_sandwich() -> None:
    checks = 0
    for n in range(5, 9):
        for _ in range(16):
            unary = rng.uniform(0, 1, size=n)
            pair = np.triu(rng.uniform(0, 0.15, size=(n, n)), 1)

            def objective(subset, unary=unary, pair=pair):
                return float(sum(unary[i] for i in subset) + sum(pair[i, j] for i, j in itertools.combinations(subset, 2)))

            costs = tuple(float(x) for x in rng.integers(1, 5, size=n))
            k = int(rng.integers(1, n))
            budget = float(rng.integers(k, max(k + 1, int(sum(costs)) + 1)))
            problem = SelectionProblem(None, ServiceConstraints(exact_k=k, budget=budget), costs)
            exact, certificate = solve_branch_bound(problem, objective)
            brute = solve_exhaustive(problem, objective)
            assert exact.status in {"OPTIMAL", "INFEASIBLE"}
            assert math.isclose(exact.objective, brute.objective, abs_tol=1e-9) if brute.objective is not None else exact.objective is None
            if brute.objective is not None:
                assert certificate is None and not exact.certified and not exact.exact
                anytime, anytime_certificate = solve_branch_bound(problem, objective, max_nodes=2, numerical_error=0.01)
                assert anytime.selected is not None
                assert anytime.lower_bound <= brute.objective + 1e-9
                assert anytime.objective >= brute.objective - 1e-9
                assert anytime_certificate is None and not anytime.certified and not anytime.exact
            checks += 1
    assert checks == 64


def brute_dynamic(problem: DynamicProblem):
    families = []
    for time in range(problem.T):
        if problem.exact_cardinalities is None:
            families.append([tuple(i for i in range(problem.n) if mask >> i & 1) for mask in range(1 << problem.n)])
        else:
            families.append(list(itertools.combinations(range(problem.n), problem.exact_cardinalities[time])))
    best = None
    mandatory = problem.mandatory_by_time or tuple(() for _ in range(problem.T))
    forbidden = problem.forbidden_by_time or tuple(() for _ in range(problem.T))
    for schedule in itertools.product(*families):
        if any(not set(mandatory[t]).issubset(schedule[t]) or set(forbidden[t]).intersection(schedule[t]) for t in range(problem.T)):
            continue
        candidate = (dynamic_objective(problem, schedule), tuple(tuple(x) for x in schedule))
        if best is None or candidate < best:
            best = candidate
    return best


@pytest.mark.property
def test_dynamic_algorithms_match_bruteforce() -> None:
    mincut_checks = 0
    for _ in range(40):
        n = int(rng.integers(2, 5))
        T = int(rng.integers(2, 4))
        unary = rng.integers(-2, 4, size=(T, n)).astype(float)
        switching = rng.integers(0, 3, size=(T - 1, n)).astype(float)
        spatial = []
        for _time in range(T):
            weight = np.zeros((n, n), dtype=float)
            for source in range(n):
                for target in range(n):
                    if source != target and rng.random() < 0.2:
                        weight[source, target] = int(rng.integers(1, 4))
            spatial.append(weight)
        mandatory = tuple(((0,) if t == 0 and rng.random() < 0.5 else ()) for t in range(T))
        forbidden = tuple(((n - 1,) if t == T - 1 and n - 1 not in mandatory[t] and rng.random() < 0.5 else ()) for t in range(T))
        problem = DynamicProblem(unary, tuple(spatial), switching, mandatory_by_time=mandatory, forbidden_by_time=forbidden)
        result = solve_time_expanded_mincut(problem)
        brute = brute_dynamic(problem)
        assert brute is not None
        assert math.isclose(result["objective"], brute[0], abs_tol=1e-8)
        mincut_checks += 1
    flow_checks = 0
    trajectory_checks = 0
    for _ in range(30):
        n = int(rng.integers(3, 6))
        T = int(rng.integers(2, 4))
        k = int(rng.integers(1, n))
        unary = rng.integers(0, 5, size=(T, n)).astype(float)
        switching = rng.integers(0, 3, size=(T - 1, n)).astype(float)
        zeros = tuple(np.zeros((n, n)) for _ in range(T))
        edgeless = DynamicProblem(unary, zeros, switching, tuple(k for _ in range(T)))
        flow = solve_edgeless_constant_cardinality(edgeless)
        brute = brute_dynamic(edgeless)
        assert brute is not None and math.isclose(flow["objective"], brute[0], abs_tol=1e-8)
        flow_checks += 1
        spatial = []
        for time in range(T):
            weight = np.zeros((n, n))
            for i in range(n - 1):
                weight[i, i + 1] = 1 + time
                weight[i + 1, i] = 2
            spatial.append(weight)
        forest_problem = DynamicProblem(unary, tuple(spatial), switching, tuple(k for _ in range(T)))
        trajectory = solve_forest_trajectory(forest_problem)
        families = [list(itertools.combinations(range(n), k)) for _ in range(T)]
        explicit = solve_explicit_families(forest_problem, families)
        assert math.isclose(trajectory["objective"], explicit["objective"], abs_tol=1e-8)
        trajectory_checks += 1
    assert (mincut_checks, flow_checks, trajectory_checks) == (40, 30, 30)


@pytest.mark.property
def test_invalid_domains_are_rejected() -> None:
    cycle = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
    problem = SelectionProblem(None, ServiceConstraints(exact_k=1, budget=2), (1, 1, 1), cycle)
    with pytest.raises(ValidationError):
        solve_forest_cut(problem)
    dynamic = DynamicProblem(np.zeros((2, 3)), (np.zeros((3, 3)), np.zeros((3, 3))), np.zeros((1, 3)), (1, 1))
    with pytest.raises(ValidationError):
        solve_time_expanded_mincut(dynamic)
