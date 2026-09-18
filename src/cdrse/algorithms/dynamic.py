from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

import networkx as nx
import numpy as np
from numpy.typing import NDArray

from ..errors import ValidationError
from .common import Counters

Array = NDArray[np.float64]


@dataclass(frozen=True)
class DynamicProblem:
    unary_costs: Array
    spatial_weights: tuple[Array, ...]
    switching_costs: Array
    exact_cardinalities: tuple[int, ...] | None = None
    mandatory_by_time: tuple[tuple[int, ...], ...] = ()
    forbidden_by_time: tuple[tuple[int, ...], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "unary_costs", np.asarray(self.unary_costs, dtype=float))
        object.__setattr__(self, "spatial_weights", tuple(np.asarray(weight, dtype=float) for weight in self.spatial_weights))
        object.__setattr__(self, "switching_costs", np.asarray(self.switching_costs, dtype=float))
        self.validate()

    @property
    def T(self) -> int:
        return self.unary_costs.shape[0]

    @property
    def n(self) -> int:
        return self.unary_costs.shape[1]

    def validate(self) -> None:
        if self.unary_costs.ndim != 2:
            raise ValidationError("unary_costs must be T-by-n")
        if len(self.spatial_weights) != self.T or any(weight.shape != (self.n, self.n) for weight in self.spatial_weights):
            raise ValidationError("one n-by-n spatial matrix is required per period")
        if self.switching_costs.shape != (max(0, self.T - 1), self.n):
            raise ValidationError("switching_costs shape mismatch")
        if np.any(self.switching_costs < 0) or any(np.any(weight < -1e-12) for weight in self.spatial_weights):
            raise ValidationError("switching and spatial weights must be non-negative")
        if self.exact_cardinalities is not None:
            if len(self.exact_cardinalities) != self.T or any(not 0 <= k <= self.n for k in self.exact_cardinalities):
                raise ValidationError("invalid exact cardinality vector")
        if self.mandatory_by_time and len(self.mandatory_by_time) != self.T:
            raise ValidationError("mandatory_by_time length mismatch")
        if self.forbidden_by_time and len(self.forbidden_by_time) != self.T:
            raise ValidationError("forbidden_by_time length mismatch")
        mandatory = self.mandatory_by_time or tuple(() for _ in range(self.T))
        forbidden = self.forbidden_by_time or tuple(() for _ in range(self.T))
        for time in range(self.T):
            if set(mandatory[time]) & set(forbidden[time]):
                raise ValidationError("mandatory and forbidden coordinates overlap at a time point")
            if any(i < 0 or i >= self.n for i in set(mandatory[time]) | set(forbidden[time])):
                raise ValidationError("time-specific constrained coordinate is outside the ground set")


def dynamic_objective(problem: DynamicProblem, schedule: Sequence[Iterable[int]]) -> float:
    if len(schedule) != problem.T:
        raise ValidationError("schedule length mismatch")
    sets = [set(int(i) for i in subset) for subset in schedule]
    value = 0.0
    for time, selected in enumerate(sets):
        value += sum(problem.unary_costs[time, i] for i in selected)
        weight = problem.spatial_weights[time]
        value += sum(weight[source, target] for target in selected for source in range(problem.n) if source not in selected)
    for time in range(1, problem.T):
        value += sum(problem.switching_costs[time - 1, i] for i in sets[time] ^ sets[time - 1])
    return float(value)


def _add_capacity(graph: nx.DiGraph, source, target, capacity: float) -> None:
    if capacity <= 0:
        return
    if graph.has_edge(source, target):
        graph[source][target]["capacity"] += float(capacity)
    else:
        graph.add_edge(source, target, capacity=float(capacity))


def solve_time_expanded_mincut(problem: DynamicProblem) -> dict:
    """Exact min-cut in the uncoupled binary regime."""
    if problem.exact_cardinalities is not None:
        raise ValidationError("cardinality constraints invalidate direct min-cut")
    mandatory = problem.mandatory_by_time or tuple(() for _ in range(problem.T))
    forbidden = problem.forbidden_by_time or tuple(() for _ in range(problem.T))
    total = float(
        np.sum(np.abs(problem.unary_costs))
        + np.sum(problem.switching_costs)
        + sum(np.sum(weight) for weight in problem.spatial_weights)
        + 1.0
    )
    infinity = 1000.0 * total + 1.0
    source = ("source",)
    sink = ("sink",)
    graph = nx.DiGraph()
    graph.add_node(source)
    graph.add_node(sink)
    constant = 0.0
    for time in range(problem.T):
        for coordinate in range(problem.n):
            node = (time, coordinate)
            coefficient = float(problem.unary_costs[time, coordinate])
            if coefficient >= 0:
                _add_capacity(graph, source, node, coefficient)
            else:
                constant += coefficient
                _add_capacity(graph, node, sink, -coefficient)
            if coordinate in mandatory[time]:
                _add_capacity(graph, node, sink, infinity)
            if coordinate in forbidden[time]:
                _add_capacity(graph, source, node, infinity)
        weight = problem.spatial_weights[time]
        for physical_source in range(problem.n):
            for physical_target in range(problem.n):
                if physical_source != physical_target and weight[physical_source, physical_target] > 0:
                    _add_capacity(graph, (time, physical_source), (time, physical_target), weight[physical_source, physical_target])
    for time in range(1, problem.T):
        for coordinate in range(problem.n):
            cost = float(problem.switching_costs[time - 1, coordinate])
            _add_capacity(graph, (time - 1, coordinate), (time, coordinate), cost)
            _add_capacity(graph, (time, coordinate), (time - 1, coordinate), cost)
    cut, (_, sink_side) = nx.minimum_cut(graph, source, sink, capacity="capacity")
    schedule = [tuple(i for i in range(problem.n) if (time, i) in sink_side) for time in range(problem.T)]
    objective = dynamic_objective(problem, schedule)
    if abs(cut + constant - objective) > 1e-8:
        raise AssertionError("time-expanded cut does not reproduce the dynamic objective")
    return {
        "status": "OPTIMAL_TIME_EXPANDED_MINCUT",
        "schedule": [list(subset) for subset in schedule],
        "objective": objective,
        "exact": False, "certified": False, "arithmetic_contract": "FLOAT64_EVALUATION",
        "certificate": None,
        "numerical_diagnostics": {"cut_value": float(cut), "constant_offset": constant, "evaluated_objective": objective},
        "graph_nodes": graph.number_of_nodes(),
        "graph_arcs": graph.number_of_edges(),
        "scope": "no global cardinality, budget or coverage coupling",
    }


def solve_explicit_families(problem: DynamicProblem, feasible_families: Sequence[Sequence[Iterable[int]]]) -> dict:
    if len(feasible_families) != problem.T:
        raise ValidationError("one feasible family per period is required")
    families = [[tuple(sorted(set(int(i) for i in subset))) for subset in family] for family in feasible_families]
    if any(not family for family in families):
        return {"status": "INFEASIBLE", "exact": False, "certified": False, "arithmetic_contract": "FLOAT64_EVALUATION"}
    counters = Counters()

    def stage_cost(time: int, subset: tuple[int, ...]) -> float:
        selected = set(subset)
        return float(
            sum(problem.unary_costs[time, i] for i in selected)
            + sum(
                problem.spatial_weights[time][source, target]
                for target in selected
                for source in range(problem.n)
                if source not in selected
            )
        )

    values = [stage_cost(0, subset) for subset in families[0]]
    back = [[-1] * len(families[0])]
    for time in range(1, problem.T):
        current = [float("inf")] * len(families[time])
        parents = [-1] * len(current)
        for target_index, subset in enumerate(families[time]):
            base = stage_cost(time, subset)
            selected = set(subset)
            for source_index, previous in enumerate(families[time - 1]):
                counters.transitions_considered += 1
                switch = sum(problem.switching_costs[time - 1, i] for i in selected ^ set(previous))
                candidate = values[source_index] + base + switch
                if candidate < current[target_index] - 1e-12:
                    current[target_index] = float(candidate)
                    parents[target_index] = source_index
        values = current
        back.append(parents)
    index = min(range(len(values)), key=lambda i: (values[i], families[-1][i]))
    schedule = []
    for time in reversed(range(problem.T)):
        schedule.append(families[time][index])
        index = back[time][index]
    schedule.reverse()
    objective = dynamic_objective(problem, schedule)
    if abs(objective - min(values)) > 1e-8:
        raise AssertionError("layered shortest path reconstruction mismatch")
    return {
        "status": "OPTIMAL_LAYERED_DAG",
        "schedule": [list(subset) for subset in schedule],
        "objective": objective,
        "exact": False, "certified": False, "arithmetic_contract": "FLOAT64_EVALUATION",
        "state_counts": [len(family) for family in families],
        "counters": counters.to_dict(),
    }


def solve_edgeless_constant_cardinality(problem: DynamicProblem, *, integer_scale: int = 1) -> dict:
    if problem.exact_cardinalities is None or len(set(problem.exact_cardinalities)) != 1:
        raise ValidationError("constant exact cardinality is required")
    if any(np.max(np.abs(weight)) > 1e-12 for weight in problem.spatial_weights):
        raise ValidationError("spatial graph must be edgeless")
    if problem.mandatory_by_time or problem.forbidden_by_time:
        raise ValidationError("reference flow does not encode time-specific forced coordinates")
    k = problem.exact_cardinalities[0]
    graph = nx.DiGraph()
    source = ("source",)
    sink = ("sink",)
    graph.add_node(source, demand=-k)
    graph.add_node(sink, demand=k)

    def weight(value: float) -> int:
        return int(round(integer_scale * value))

    for time in range(problem.T):
        for coordinate in range(problem.n):
            node_in = (time, coordinate, "in")
            node_out = (time, coordinate, "out")
            graph.add_node(node_in, demand=0)
            graph.add_node(node_out, demand=0)
            graph.add_edge(node_in, node_out, capacity=1, weight=weight(problem.unary_costs[time, coordinate]))
            if time == 0:
                graph.add_edge(source, node_in, capacity=1, weight=0)
            if time == problem.T - 1:
                graph.add_edge(node_out, sink, capacity=1, weight=0)
    for time in range(problem.T - 1):
        for previous in range(problem.n):
            for current in range(problem.n):
                cost = 0.0 if previous == current else float(problem.switching_costs[time, previous] + problem.switching_costs[time, current])
                graph.add_edge((time, previous, "out"), (time + 1, current, "in"), capacity=1, weight=weight(cost))
    flow_cost, flow = nx.network_simplex(graph)
    schedule = [
        tuple(i for i in range(problem.n) if flow[(time, i, "in")][(time, i, "out")] > 0)
        for time in range(problem.T)
    ]
    objective = dynamic_objective(problem, schedule)
    scaled = flow_cost / integer_scale
    if abs(objective - scaled) > max(1e-8, 0.5 / integer_scale * (problem.T * problem.n + 1)):
        raise AssertionError("min-cost flow does not reproduce the dynamic objective")
    return {
        "status": "OPTIMAL_EDGELESS_MIN_COST_FLOW",
        "schedule": [list(subset) for subset in schedule],
        "objective": objective,
        "scaled_flow_objective": scaled,
        "exact_for_scaled_integer_costs": True,
        "integer_scale": integer_scale,
        "graph_nodes": graph.number_of_nodes(),
        "graph_arcs": graph.number_of_edges(),
    }


@dataclass(frozen=True)
class _TrajectoryCandidate:
    value: float
    labels: tuple[tuple[int, int], ...]


def solve_forest_trajectory(problem: DynamicProblem) -> dict:
    """Exact fixed-horizon DP when the union spatial support is a forest.

    Each vertex label is its full binary trajectory and there are ``2**T``
    labels. Cardinality counter vectors can grow as (n+1)**T; the displayed
    construction gives a fixed-horizon/XP-type bound, not FPT in T alone.
    Floating-point evaluations do not carry a validated numerical certificate.
    """
    if problem.exact_cardinalities is None:
        raise ValidationError("forest trajectory DP requires exact cardinalities at every period")
    k_vector = tuple(problem.exact_cardinalities)
    adjacency = [set() for _ in range(problem.n)]
    for weight in problem.spatial_weights:
        for u in range(problem.n):
            for v in range(u + 1, problem.n):
                if weight[u, v] > 1e-12 or weight[v, u] > 1e-12:
                    adjacency[u].add(v)
                    adjacency[v].add(u)
    seen: set[int] = set()
    components = []
    for root in range(problem.n):
        if root in seen:
            continue
        parent = {root: -1}
        order = []
        stack = [root]
        seen.add(root)
        while stack:
            vertex = stack.pop()
            order.append(vertex)
            for neighbour in sorted(adjacency[vertex], reverse=True):
                if neighbour == parent[vertex]:
                    continue
                if neighbour in seen:
                    raise ValidationError("union spatial support is not a forest")
                seen.add(neighbour)
                parent[neighbour] = vertex
                stack.append(neighbour)
        components.append((root, parent, order))
    mandatory = problem.mandatory_by_time or tuple(() for _ in range(problem.T))
    forbidden = problem.forbidden_by_time or tuple(() for _ in range(problem.T))
    counters = Counters()

    def bit(mask: int, time: int) -> int:
        return (mask >> time) & 1

    component_tables: list[dict[tuple[int, ...], _TrajectoryCandidate]] = []
    for root, parent, order in components:
        children = {vertex: [] for vertex in order}
        for vertex in order:
            if parent[vertex] != -1:
                children[parent[vertex]].append(vertex)
        dp: dict[int, dict[int, dict[tuple[int, ...], _TrajectoryCandidate]]] = {}
        for vertex in reversed(order):
            by_label: dict[int, dict[tuple[int, ...], _TrajectoryCandidate]] = {}
            for mask in range(1 << problem.T):
                if any(vertex in mandatory[time] and bit(mask, time) == 0 for time in range(problem.T)):
                    continue
                if any(vertex in forbidden[time] and bit(mask, time) == 1 for time in range(problem.T)):
                    continue
                counts = tuple(bit(mask, time) for time in range(problem.T))
                if any(counts[time] > k_vector[time] for time in range(problem.T)):
                    continue
                value = sum(problem.unary_costs[time, vertex] * bit(mask, time) for time in range(problem.T))
                value += sum(
                    problem.switching_costs[time - 1, vertex] * abs(bit(mask, time) - bit(mask, time - 1))
                    for time in range(1, problem.T)
                )
                by_label[mask] = {counts: _TrajectoryCandidate(float(value), ((vertex, mask),))}
            for child in children[vertex]:
                merged = {mask: {} for mask in by_label}
                for parent_mask, parent_table in by_label.items():
                    for counts1, candidate1 in parent_table.items():
                        for child_mask, child_table in dp[child].items():
                            edge = 0.0
                            for time in range(problem.T):
                                parent_label = bit(parent_mask, time)
                                child_label = bit(child_mask, time)
                                weight = problem.spatial_weights[time]
                                if parent_label == 0 and child_label == 1:
                                    edge += weight[vertex, child]
                                elif parent_label == 1 and child_label == 0:
                                    edge += weight[child, vertex]
                            for counts2, candidate2 in child_table.items():
                                counters.transitions_considered += 1
                                counts = tuple(counts1[time] + counts2[time] for time in range(problem.T))
                                if any(counts[time] > k_vector[time] for time in range(problem.T)):
                                    continue
                                candidate = _TrajectoryCandidate(
                                    candidate1.value + candidate2.value + float(edge),
                                    tuple(sorted(candidate1.labels + candidate2.labels)),
                                )
                                old = merged[parent_mask].get(counts)
                                if old is None or candidate.value < old.value - 1e-12 or (
                                    abs(candidate.value - old.value) <= 1e-12 and candidate.labels < old.labels
                                ):
                                    merged[parent_mask][counts] = candidate
                by_label = merged
            dp[vertex] = by_label
            states = sum(len(table) for table in by_label.values())
            counters.states_stored += states
            counters.peak_frontier = max(counters.peak_frontier, states)
        component: dict[tuple[int, ...], _TrajectoryCandidate] = {}
        for table in dp[root].values():
            for counts, candidate in table.items():
                old = component.get(counts)
                if old is None or candidate.value < old.value - 1e-12 or (
                    abs(candidate.value - old.value) <= 1e-12 and candidate.labels < old.labels
                ):
                    component[counts] = candidate
        component_tables.append(component)
    global_table = {(0,) * problem.T: _TrajectoryCandidate(0.0, ())}
    for component in component_tables:
        merged: dict[tuple[int, ...], _TrajectoryCandidate] = {}
        for counts1, candidate1 in global_table.items():
            for counts2, candidate2 in component.items():
                counters.transitions_considered += 1
                counts = tuple(counts1[time] + counts2[time] for time in range(problem.T))
                if any(counts[time] > k_vector[time] for time in range(problem.T)):
                    continue
                candidate = _TrajectoryCandidate(candidate1.value + candidate2.value, tuple(sorted(candidate1.labels + candidate2.labels)))
                old = merged.get(counts)
                if old is None or candidate.value < old.value - 1e-12 or (
                    abs(candidate.value - old.value) <= 1e-12 and candidate.labels < old.labels
                ):
                    merged[counts] = candidate
        global_table = merged
    if k_vector not in global_table:
        return {"status": "INFEASIBLE", "exact": False, "certified": False, "arithmetic_contract": "FLOAT64_EVALUATION", "counters": counters.to_dict()}
    candidate = global_table[k_vector]
    label_map = dict(candidate.labels)
    schedule = [tuple(vertex for vertex in range(problem.n) if bit(label_map[vertex], time)) for time in range(problem.T)]
    objective = dynamic_objective(problem, schedule)
    if abs(objective - candidate.value) > 1e-8:
        raise AssertionError("trajectory DP does not reproduce the dynamic objective")
    return {
        "status": "OPTIMAL_FOREST_TRAJECTORY_DP",
        "schedule": [list(subset) for subset in schedule],
        "objective": objective,
        "exact": False, "certified": False, "arithmetic_contract": "FLOAT64_EVALUATION",
        "counters": counters.to_dict(),
        "label_count_per_vertex": 2**problem.T,
        "complexity_scope": "XP-type in T with explicit cardinality-counter factor; variable-horizon forest boundary remains open",
    }
