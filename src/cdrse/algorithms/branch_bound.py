"""Branch-and-bound with exact stored-cut and unenclosed callback contracts.

A missing callback selects the exact stored-input cut objective. Supplying a
callback never establishes an exact oracle, even when an error parameter is zero.
Call and cooperative time limits include initialisation (C1/C2; F01/F11/F14).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable
import heapq
import math
import time

from ..certificates import AlgorithmicLayer, DecisionCertificate, EconomicLayer, NumericalLayer, StatisticalLayer
from ..errors import ValidationError
from ..exact_cut import rational, exact_weights, total_value, make_result, result_record
from ..models import SelectionProblem
from .common import Counters, SolverResult


@dataclass(order=True)
class _Node:
    lower_bound: Fraction
    serial: int
    included: frozenset[int] = field(compare=False)
    excluded: frozenset[int] = field(compare=False)


def _cardinality(problem: SelectionProblem) -> tuple[int, int]:
    c = problem.constraints
    return (c.exact_k, c.exact_k) if c.exact_k is not None else (c.k_min, problem.n if c.k_max is None else c.k_max)


def solve_branch_bound(
    problem: SelectionProblem,
    objective: Callable[[tuple[int, ...]], float] | None = None,
    *,
    information_lower_bound: Callable[[frozenset[int], frozenset[int]], float] | None = None,
    max_nodes: int | None = None,
    max_calls: int | None = None,
    time_limit: float | None = None,
    numerical_error: float = 0.0,
    statistical_error: float = 0.0,
    cost_error: float = 0.0,
    valuation_error: float = 0.0,
    decision_tolerance: float | None = None,
) -> tuple[SolverResult, DecisionCertificate | None]:
    """Optimise the stored weighted cut, or evaluate an untrusted nonnegative callback.

    Callback mode retains legacy diagnostic bounds but sets certified=False and
    supplies no authoritative enclosure. Bounds supplied as callback arguments are
    not used for pruning: their truth cannot be established from their type.
    time_limit is cooperative and cannot pre-empt an already executing callback.
    """
    start = time.monotonic()
    problem.validate()
    for name, limit in (("max_nodes", max_nodes), ("max_calls", max_calls)):
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
            raise ValidationError(f"{name} must be a nonnegative integer or None")
    if time_limit is not None and (not math.isfinite(time_limit) or time_limit < 0):
        raise ValidationError("time_limit must be finite and nonnegative")
    for error in (numerical_error, statistical_error, cost_error, valuation_error, decision_tolerance):
        if error is not None and (not math.isfinite(error) or error < 0):
            raise ValidationError("error and tolerance values must be finite and nonnegative")
    exact = objective is None
    if exact and problem.cut_weights is None:
        raise ValidationError("omit objective only when cut_weights are supplied")
    n = problem.n
    k_min, k_max = _cardinality(problem)
    c = problem.constraints
    costs = tuple(rational(x) for x in problem.activation_costs)
    alpha, beta = rational(problem.information_weight), rational(problem.cost_weight)
    weights = exact_weights(problem.cut_weights) if exact else None
    budget = None if c.budget is None else rational(c.budget)
    counters = Counters()
    cache: dict[tuple[int, ...], Fraction | float] = {}
    incumbent: tuple[Fraction | float, tuple[int, ...]] | None = None
    reason = 'COMPLETE'

    def stop_reason() -> str | None:
        if time_limit is not None and time.monotonic() - start >= time_limit:
            return 'TIME_BUDGET'
        if max_calls is not None and counters.objective_calls >= max_calls:
            return 'CALL_BUDGET'
        return None

    def evaluate(subset: tuple[int, ...]) -> Fraction | float:
        if subset not in cache:
            counters.objective_calls += 1
            if exact:
                cache[subset] = total_value(problem, subset)
            else:
                assert objective is not None
                information = float(objective(subset))
                if not math.isfinite(information) or information < 0:
                    raise ValidationError('callback must return a finite nonnegative information value')
                value = float(alpha) * information + float(beta) * sum(float(costs[i]) for i in subset)
                if not math.isfinite(value):
                    raise ValidationError('weighted callback value is non-finite')
                cache[subset] = value
        return cache[subset]

    def possible(included: frozenset[int], excluded: frozenset[int]) -> bool:
        available = [i for i in range(n) if i not in included and i not in excluded]
        needed = max(0, k_min - len(included))
        if len(included) > k_max or needed > len(available):
            return False
        least_cost = sum((costs[i] for i in included), Fraction(0)) + sum(sorted(costs[i] for i in available)[:needed], Fraction(0))
        if budget is not None and least_cost > budget:
            return False
        return all(set(group) - excluded for group in c.coverage_groups)

    def bound(included: frozenset[int], excluded: frozenset[int]) -> Fraction:
        counters.lower_bound_calls += 1
        available = [i for i in range(n) if i not in included and i not in excluded]
        needed = max(0, k_min - len(included))
        resource = sum((costs[i] for i in included), Fraction(0)) + sum(sorted(costs[i] for i in available)[:needed], Fraction(0))
        forced = sum((weights[j, i] for j in excluded for i in included), Fraction(0)) if exact else Fraction(0)
        return alpha * forced + beta * resource

    included, excluded = frozenset(c.mandatory), frozenset(c.forbidden)
    if not possible(included, excluded):
        return make_result(problem, None, None, counters, reason='PROVED_INFEASIBLE'), None
    root = _Node(bound(included, excluded), 0, included, excluded)
    heap = [root]
    serial = 1
    counters.nodes_generated = 1
    # One deterministic inexpensive seed, never an exhaustive pre-search scan.
    seed = set(included)
    for group in c.coverage_groups:
        options = set(group) - excluded
        if not seed.intersection(group) and options:
            seed.add(min(options, key=lambda i: (costs[i], i)))
    options = sorted(set(range(n)) - excluded - seed, key=lambda i: (costs[i], i))
    seed.update(options[:max(0, k_min-len(seed))])
    initial = tuple(sorted(seed))
    if stop_reason() is None and c.is_feasible(initial, n, problem.activation_costs):
        incumbent = (evaluate(initial), initial)
    frequency = [sum(i in group for group in c.coverage_groups) for i in range(n)]

    while heap:
        counters.peak_frontier = max(counters.peak_frontier, len(heap))
        stopped = stop_reason()
        if stopped is not None:
            reason = stopped
            break
        if max_nodes is not None and counters.nodes_expanded >= max_nodes:
            reason = 'NODE_BUDGET'
            break
        node = heapq.heappop(heap)
        counters.nodes_expanded += 1
        if exact and incumbent is not None and node.lower_bound >= incumbent[0]:
            counters.nodes_pruned += 1
            continue
        undecided = [i for i in range(n) if i not in node.included and i not in node.excluded]
        if not undecided or len(node.included) == k_max:
            subset = tuple(sorted(node.included))
            if c.is_feasible(subset, n, problem.activation_costs):
                candidate = (evaluate(subset), subset)
                if incumbent is None or candidate < incumbent:
                    incumbent = candidate
            continue
        vertex = max(undecided, key=lambda i: (frequency[i], costs[i], -i))
        for take in (True, False):
            inc = node.included | ({vertex} if take else set())
            exc = node.excluded | ({vertex} if not take else set())
            counters.nodes_generated += 1
            if not possible(inc, exc):
                counters.nodes_pruned += 1
                continue
            lb = bound(inc, exc)
            if exact and incumbent is not None and lb >= incumbent[0]:
                counters.nodes_pruned += 1
                continue
            heapq.heappush(heap, _Node(lb, serial, frozenset(inc), frozenset(exc)))
            serial += 1
    complete = not heap
    reason = 'COMPLETE' if complete else reason
    selected = None if incumbent is None else incumbent[1]
    value = None if incumbent is None else incumbent[0]
    meta = {'frontier_nodes_remaining': len(heap), 'objective_cache_size': len(cache),
            'information_bound_callback_used': False, 'scalability_claimed': False,
            'time_limit_semantics': 'cooperative; no pre-emption of running callbacks',
            'error_parameters': [numerical_error, statistical_error, cost_error, valuation_error]}
    if exact:
        lowers = [node.lower_bound for node in heap]
        if value is not None:
            lowers.append(value)
        lower = min(lowers) if lowers else None
        result = make_result(problem, selected, value, counters, lower=lower, complete=complete,
            reason=reason, status='ANYTIME_FEASIBLE_WITH_BOUND' if selected is not None else 'NO_INCUMBENT', metadata=meta)
        if complete and selected is not None:
            result.status = 'OPTIMAL'
        # This compatibility certificate is conditional on the stored-input model.
        # The exact rational record and semantic replay are the primary evidence.
        certificate = None
        if selected is not None and all(e == 0 for e in (numerical_error, statistical_error, cost_error, valuation_error)):
            certificate = DecisionCertificate(problem.sha256, selected,
                AlgorithmicLayer(True, result.upper_bound, result.lower_bound, reason, True),
                NumericalLayer('exact-stored-rational', True, True, 0.0),
                StatisticalLayer('stored weighted cut; no population coverage asserted', False, 0.0, 'none'),
                EconomicLayer('E0', True, True), tolerance=decision_tolerance,
                notes=('Exactness is conditional on the stored model.', 'Replay the rational result record to check the finite model.'))
            certificate.validate()
        return result, certificate
    record = result_record(problem, selected, None, None, counters, complete, reason, exact=False, estimate=value)
    meta.update(result_contract=record, certificate_scope='none; unenclosed callback evaluation',
                legacy_bounds_semantics='diagnostic evaluated values only; not validated enclosures',
                optimality_scope='enumerated callback evaluations' if complete else 'partial callback evaluations')
    infeasible = record['proof_status'] == 'PROVED_INFEASIBLE'
    result = SolverResult('INFEASIBLE' if infeasible else 'NO_INCUMBENT' if selected is None else 'OPTIMAL' if complete else 'ANYTIME_UNCERTIFIED',
        selected, value, infeasible, infeasible, record['termination_reason'], 0.0 if selected is not None else None,
        value, counters, meta)
    return result, None
