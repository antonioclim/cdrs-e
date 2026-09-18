from __future__ import annotations

from fractions import Fraction
from ..exact_cut import rational, exact_weights, cut_value, integral_resources, exact_front, make_result

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from numpy.typing import NDArray

from ..economics import pareto_front, supported_points
from ..errors import ValidationError
from ..models import SelectionProblem
from ..objectives import directed_cut
from .common import Counters, SolverResult

Array = NDArray[np.float64]


@dataclass(frozen=True)
class _Candidate:
    value: Fraction
    selected: tuple[int, ...]


def _forest_adjacency(weights: Array, tolerance: float) -> list[set[int]]:
    n = weights.shape[0]
    adjacency = [set() for _ in range(n)]
    for u in range(n):
        for v in range(u + 1, n):
            if weights[u, v] > 0 or weights[v, u] > 0:
                adjacency[u].add(v)
                adjacency[v].add(u)
    seen: set[int] = set()
    for root in range(n):
        if root in seen:
            continue
        stack = [(root, -1)]
        while stack:
            vertex, parent = stack.pop()
            if vertex in seen:
                raise ValidationError("undirected cut support is not a forest")
            seen.add(vertex)
            for neighbour in adjacency[vertex]:
                if neighbour != parent:
                    stack.append((neighbour, vertex))
    return adjacency


def _better(old: _Candidate | None, new: _Candidate, tolerance: float) -> bool:
    return old is None or new.value < old.value or (
        new.value == old.value and new.selected < old.selected
    )


def _prune(
    table: dict[tuple[int, int, int], _Candidate], tolerance: float
) -> dict[tuple[int, int, int], _Candidate]:
    """Budget dominance for fixed count and coverage mask."""
    grouped: dict[tuple[int, int], list[tuple[int, _Candidate]]] = {}
    for (count, spend, mask), candidate in table.items():
        grouped.setdefault((count, mask), []).append((spend, candidate))
    result: dict[tuple[int, int, int], _Candidate] = {}
    for (count, mask), rows in grouped.items():
        best_value = float("inf")
        for spend, candidate in sorted(rows, key=lambda item: (item[0], item[1].value, item[1].selected)):
            if candidate.value < best_value:
                result[(count, spend, mask)] = candidate
                best_value = candidate.value
    return result


def solve_forest_cut(problem: SelectionProblem, *, tolerance: float = 1e-12) -> SolverResult:
    """Exact pseudo-polynomial DP for the directed-cut surrogate on a forest."""
    problem.validate()
    if problem.cut_weights is None:
        raise ValidationError("forest DP requires cut_weights")
    weights = exact_weights(problem.cut_weights)
    adjacency = _forest_adjacency(weights, tolerance)
    n = problem.n
    constraints = problem.constraints
    costs, budget = integral_resources(problem)
    if constraints.exact_k is not None:
        k_min = k_max = constraints.exact_k
    else:
        k_min = constraints.k_min
        k_max = n if constraints.k_max is None else constraints.k_max
    mandatory = set(constraints.mandatory)
    forbidden = set(constraints.forbidden)
    group_bits = [0] * n
    for index, group in enumerate(constraints.coverage_groups):
        for vertex in group:
            group_bits[vertex] |= 1 << index
    full_mask = (1 << len(constraints.coverage_groups)) - 1
    counters = Counters()
    seen: set[int] = set()
    components: list[dict[tuple[int, int, int], _Candidate]] = []

    for root in range(n):
        if root in seen:
            continue
        parent = {root: -1}
        order: list[int] = []
        stack = [root]
        seen.add(root)
        while stack:
            vertex = stack.pop()
            order.append(vertex)
            for neighbour in sorted(adjacency[vertex], reverse=True):
                if neighbour == parent[vertex]:
                    continue
                if neighbour in seen:
                    raise ValidationError("cycle detected while rooting forest")
                parent[neighbour] = vertex
                seen.add(neighbour)
                stack.append(neighbour)
        children = {vertex: [] for vertex in order}
        for vertex in order:
            if parent[vertex] != -1:
                children[parent[vertex]].append(vertex)
        dp: dict[int, dict[int, dict[tuple[int, int, int], _Candidate]]] = {}
        for vertex in reversed(order):
            by_label: dict[int, dict[tuple[int, int, int], _Candidate]] = {0: {}, 1: {}}
            for label in (0, 1):
                if label == 0 and vertex in mandatory:
                    continue
                if label == 1 and vertex in forbidden:
                    continue
                count = label
                spend = costs[vertex] if label else 0
                if count > k_max or spend > budget:
                    continue
                mask = group_bits[vertex] if label else 0
                selected = (vertex,) if label else ()
                by_label[label][(count, spend, mask)] = _Candidate(Fraction(0), selected)
            for child in children[vertex]:
                merged: dict[int, dict[tuple[int, int, int], _Candidate]] = {0: {}, 1: {}}
                for label in (0, 1):
                    for (count1, spend1, mask1), candidate1 in by_label[label].items():
                        for child_label in (0, 1):
                            edge = (
                                weights[vertex, child]
                                if label == 0 and child_label == 1
                                else weights[child, vertex]
                                if label == 1 and child_label == 0
                                else Fraction(0)
                            )
                            for (count2, spend2, mask2), candidate2 in dp[child][child_label].items():
                                counters.transitions_considered += 1
                                count = count1 + count2
                                spend = spend1 + spend2
                                if count > k_max or spend > budget:
                                    continue
                                mask = mask1 | mask2
                                selected = tuple(sorted(candidate1.selected + candidate2.selected))
                                candidate = _Candidate(candidate1.value + candidate2.value + edge, selected)
                                key = (count, spend, mask)
                                if _better(merged[label].get(key), candidate, tolerance):
                                    merged[label][key] = candidate
                by_label = {label: _prune(table, tolerance) for label, table in merged.items()}
            dp[vertex] = by_label
            current_states = sum(len(table) for table in by_label.values())
            counters.states_stored += current_states
            counters.peak_frontier = max(counters.peak_frontier, current_states)
        component: dict[tuple[int, int, int], _Candidate] = {}
        for label in (0, 1):
            for key, candidate in dp[root][label].items():
                if _better(component.get(key), candidate, tolerance):
                    component[key] = candidate
        components.append(component)

    global_table: dict[tuple[int, int, int], _Candidate] = {(0, 0, 0): _Candidate(Fraction(0), ())}
    for component in components:
        merged: dict[tuple[int, int, int], _Candidate] = {}
        for (count1, spend1, mask1), candidate1 in global_table.items():
            for (count2, spend2, mask2), candidate2 in component.items():
                counters.transitions_considered += 1
                count = count1 + count2
                spend = spend1 + spend2
                if count > k_max or spend > budget:
                    continue
                mask = mask1 | mask2
                selected = tuple(sorted(candidate1.selected + candidate2.selected))
                candidate = _Candidate(candidate1.value + candidate2.value, selected)
                key = (count, spend, mask)
                if _better(merged.get(key), candidate, tolerance):
                    merged[key] = candidate
        global_table = _prune(merged, tolerance)
        counters.states_stored += len(global_table)
        counters.peak_frontier = max(counters.peak_frontier, len(global_table))

    feasible: list[dict[str, object]] = []
    for (count, spend, mask), candidate in global_table.items():
        if not k_min <= count <= k_max:
            continue
        if full_mask and (mask & full_mask) != full_mask:
            continue
        recomputed = cut_value(weights, candidate.selected)
        if recomputed != candidate.value:
            raise AssertionError("forest reconstruction does not reproduce the cut value")
        feasible.append(
            {
                "selected": list(candidate.selected),
                "count": count,
                "cost": spend,
                "loss": candidate.value,
                "coverage_mask": mask,
            }
        )
    if not feasible:
        return make_result(problem, None, None, counters, metadata={'pareto_front': [], 'arithmetic': 'exact-stored-rational'})
    alpha, beta = rational(problem.information_weight), rational(problem.cost_weight)
    best = min(feasible, key=lambda row: (alpha * row["loss"] + beta * row["cost"], row["cost"], row["loss"], row["selected"]))
    front = exact_front(feasible)
    objective = alpha * best["loss"] + beta * best["cost"]
    meta = {"cut_value": float(best["loss"]), "activation_cost": best["cost"], "pareto_front": front,
            "tolerance_argument_applied": False, "warning": "DD exactness requires a separate transfer certificate"}
    return make_result(problem, tuple(best["selected"]), objective, counters, status="OPTIMAL_CUT_SURROGATE", metadata=meta)
