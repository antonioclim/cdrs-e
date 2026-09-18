from __future__ import annotations

from fractions import Fraction
from ..exact_cut import rational, exact_weights, cut_value, integral_resources, exact_front, make_result

from collections import deque
from dataclasses import dataclass
from typing import Sequence

import networkx as nx
import numpy as np
from numpy.typing import NDArray

from ..economics import pareto_front, supported_points
from ..errors import ValidationError
from ..models import SelectionProblem
from ..objectives import directed_cut
from .common import Counters, SolverResult

Array = NDArray[np.float64]


@dataclass(frozen=True)
class TreeDecomposition:
    bags: tuple[tuple[int, ...], ...]
    edges: tuple[tuple[int, int], ...]

    @property
    def width(self) -> int:
        return max(len(bag) for bag in self.bags) - 1

    def validate(self, weights: Array, tolerance: float = 1e-12) -> None:
        n = weights.shape[0]
        if not self.bags:
            raise ValidationError("tree decomposition has no bags")
        for bag in self.bags:
            if not bag or len(set(bag)) != len(bag) or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= n for v in bag):
                raise ValidationError("invalid or duplicate bag vertex")
        if any(len(e) != 2 or e[0] == e[1] or any(not isinstance(v, int) or v < 0 or v >= len(self.bags) for v in e) for e in self.edges):
            raise ValidationError("invalid decomposition edge")
        if len({tuple(sorted(e)) for e in self.edges}) != len(self.edges):
            raise ValidationError("duplicate decomposition edge")
        bagsets = [set(bag) for bag in self.bags]
        graph = nx.Graph()
        graph.add_nodes_from(range(len(self.bags)))
        graph.add_edges_from(self.edges)
        if len(self.bags) > 1 and not nx.is_tree(graph):
            raise ValidationError("decomposition edges do not form a tree")
        if len(self.bags) == 1 and self.edges:
            raise ValidationError("single-bag decomposition must have no edges")
        for vertex in range(n):
            containing = [index for index, bag in enumerate(bagsets) if vertex in bag]
            if not containing:
                raise ValidationError(f"vertex {vertex} appears in no bag")
            if len(containing) > 1 and not nx.is_connected(graph.subgraph(containing)):
                raise ValidationError(f"running-intersection property fails for vertex {vertex}")
        for u in range(n):
            for v in range(u + 1, n):
                if weights[u, v] > 0 or weights[v, u] > 0:
                    if not any(u in bag and v in bag for bag in bagsets):
                        raise ValidationError(f"support edge {(u, v)} is uncovered")

    def to_dict(self) -> dict:
        return {"bags": [list(bag) for bag in self.bags], "edges": [list(edge) for edge in self.edges], "width": self.width}


@dataclass(frozen=True)
class _Candidate:
    value: Fraction
    selected: tuple[int, ...]


def approximate_decomposition(weights: Array, tolerance: float = 1e-12) -> TreeDecomposition:
    matrix = np.asarray(weights, dtype=float)
    graph = nx.Graph()
    graph.add_nodes_from(range(matrix.shape[0]))
    for u in range(matrix.shape[0]):
        for v in range(u + 1, matrix.shape[0]):
            if matrix[u, v] > 0 or matrix[v, u] > 0:
                graph.add_edge(u, v)
    _, decomposition = nx.approximation.treewidth_min_fill_in(graph)
    bags = sorted((tuple(sorted(bag)) for bag in decomposition.nodes()), key=lambda bag: (len(bag), bag))
    index = {frozenset(bag): i for i, bag in enumerate(bags)}
    edges = tuple(
        sorted(
            (
                min(index[frozenset(left)], index[frozenset(right)]),
                max(index[frozenset(left)], index[frozenset(right)]),
            )
            for left, right in decomposition.edges()
        )
    )
    return TreeDecomposition(tuple(bags), edges)


def _better(old: _Candidate | None, new: _Candidate, tolerance: float) -> bool:
    return old is None or new.value < old.value or (
        new.value == old.value and new.selected < old.selected
    )


def solve_treewidth_cut(
    problem: SelectionProblem,
    decomposition: TreeDecomposition,
    *,
    tolerance: float = 1e-12,
) -> SolverResult:
    """Exact cut DP conditional on a valid tree decomposition."""
    problem.validate()
    if problem.cut_weights is None:
        raise ValidationError("treewidth DP requires cut_weights")
    weights = exact_weights(problem.cut_weights)
    decomposition.validate(weights, tolerance)
    n = problem.n
    costs, budget = integral_resources(problem)
    constraints = problem.constraints
    if constraints.exact_k is not None:
        k_min = k_max = constraints.exact_k
    else:
        k_min = constraints.k_min
        k_max = n if constraints.k_max is None else constraints.k_max
    bags = [tuple(sorted(bag)) for bag in decomposition.bags]
    bagsets = [set(bag) for bag in bags]
    graph = nx.Graph()
    graph.add_nodes_from(range(len(bags)))
    graph.add_edges_from(decomposition.edges)
    root = min(graph.nodes())
    parent = {root: -1}
    depth = {root: 0}
    order: list[int] = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in sorted(graph.neighbors(node)):
            if neighbour == parent[node]:
                continue
            parent[neighbour] = node
            depth[neighbour] = depth[node] + 1
            queue.append(neighbour)
    children = {node: [] for node in order}
    for node in order:
        if parent[node] != -1:
            children[parent[node]].append(node)
    vertex_owner = {
        vertex: min((index for index, bag in enumerate(bagsets) if vertex in bag), key=lambda index: (depth[index], index))
        for vertex in range(n)
    }
    arc_owner: dict[tuple[int, int], int] = {}
    for source in range(n):
        for target in range(n):
            if source != target and weights[source, target] > 0:
                containing = [index for index, bag in enumerate(bagsets) if source in bag and target in bag]
                arc_owner[(source, target)] = min(containing, key=lambda index: (depth[index], index))
    group_bits = [0] * n
    for group_index, group in enumerate(constraints.coverage_groups):
        for vertex in group:
            group_bits[vertex] |= 1 << group_index
    full_mask = (1 << len(constraints.coverage_groups)) - 1
    mandatory = set(constraints.mandatory)
    forbidden = set(constraints.forbidden)
    counters = Counters()
    tables: dict[int, dict[tuple[int, int, int, int], _Candidate]] = {}

    def assignment(bag: tuple[int, ...], mask: int) -> dict[int, int]:
        return {vertex: (mask >> position) & 1 for position, vertex in enumerate(bag)}

    for node in reversed(order):
        bag = bags[node]
        table: dict[tuple[int, int, int, int], _Candidate] = {}
        for bag_mask in range(1 << len(bag)):
            labels = assignment(bag, bag_mask)
            if any(labels[vertex] != 1 for vertex in mandatory if vertex in labels):
                continue
            if any(labels[vertex] != 0 for vertex in forbidden if vertex in labels):
                continue
            owned = [vertex for vertex in bag if vertex_owner[vertex] == node]
            count = sum(labels[vertex] for vertex in owned)
            spend = sum(costs[vertex] * labels[vertex] for vertex in owned)
            if count > k_max or spend > budget:
                continue
            coverage = 0
            selected = []
            for vertex in owned:
                if labels[vertex]:
                    coverage |= group_bits[vertex]
                    selected.append(vertex)
            value = Fraction(0)
            for (source, target), owner in arc_owner.items():
                if owner == node:
                    value += weights[source, target] * (1 - labels[source]) * labels[target]
            table[(bag_mask, count, spend, coverage)] = _Candidate(value, tuple(sorted(selected)))
        for child in children[node]:
            child_bag = bags[child]
            separator = tuple(sorted(bagsets[node] & bagsets[child]))
            parent_positions = {vertex: bag.index(vertex) for vertex in separator}
            child_positions = {vertex: child_bag.index(vertex) for vertex in separator}
            child_index: dict[tuple[int, ...], list[tuple[tuple[int, int, int, int], _Candidate]]] = {}
            for key, candidate in tables[child].items():
                child_mask = key[0]
                pattern = tuple((child_mask >> child_positions[vertex]) & 1 for vertex in separator)
                child_index.setdefault(pattern, []).append((key, candidate))
            merged: dict[tuple[int, int, int, int], _Candidate] = {}
            for (bag_mask, count1, spend1, coverage1), candidate1 in table.items():
                pattern = tuple((bag_mask >> parent_positions[vertex]) & 1 for vertex in separator)
                for (child_mask, count2, spend2, coverage2), candidate2 in child_index.get(pattern, []):
                    counters.transitions_considered += 1
                    count = count1 + count2
                    spend = spend1 + spend2
                    if count > k_max or spend > budget:
                        continue
                    coverage = coverage1 | coverage2
                    candidate = _Candidate(candidate1.value + candidate2.value, tuple(sorted(candidate1.selected + candidate2.selected)))
                    key = (bag_mask, count, spend, coverage)
                    if _better(merged.get(key), candidate, tolerance):
                        merged[key] = candidate
            table = merged
        tables[node] = table
        counters.states_stored += len(table)
        counters.peak_frontier = max(counters.peak_frontier, len(table))

    feasible: list[dict[str, object]] = []
    for (_, count, spend, coverage), candidate in tables[root].items():
        if not k_min <= count <= k_max:
            continue
        if full_mask and (coverage & full_mask) != full_mask:
            continue
        recomputed = cut_value(weights, candidate.selected)
        if recomputed != candidate.value:
            raise AssertionError("treewidth reconstruction does not reproduce the cut value")
        feasible.append({"selected": list(candidate.selected), "count": count, "cost": spend, "loss": candidate.value})
    if not feasible:
        return make_result(problem, None, None, counters, metadata={'decomposition': decomposition.to_dict(), 'pareto_front': []})
    alpha, beta = rational(problem.information_weight), rational(problem.cost_weight)
    best = min(feasible, key=lambda row: (alpha * row["loss"] + beta * row["cost"], row["cost"], row["loss"], row["selected"]))
    front = exact_front(feasible)
    objective = alpha * best["loss"] + beta * best["cost"]
    meta = {"cut_value": float(best["loss"]), "activation_cost": best["cost"], "pareto_front": front,
            "tolerance_argument_applied": False, "warning": "DD exactness requires a separate transfer certificate"}
    meta["decomposition"] = decomposition.to_dict()
    meta["decomposition_finding_exact"] = False
    return make_result(problem, tuple(best["selected"]), objective, counters, status="OPTIMAL_GIVEN_VALID_TREE_DECOMPOSITION", metadata=meta)
