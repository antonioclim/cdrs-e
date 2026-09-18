"""Exact stored-input cut arithmetic and serialisable result enclosures.

The public model stores edge weights as binary64. Fraction(float(x)) preserves
that value, not an intended decimal or an unknown physical parameter.
"""
from __future__ import annotations
from fractions import Fraction
import math
from typing import Any, Iterable, TYPE_CHECKING
import numpy as np
from .errors import ValidationError
if TYPE_CHECKING:
    from .models import SelectionProblem
    from .algorithms.common import Counters, SolverResult


def rational(value: Any) -> Fraction:
    """Embed a finite supported scalar without low-denominator approximation."""
    if isinstance(value, bool):
        raise ValidationError("boolean is not a numerical input")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, (int, np.integer)):
        return Fraction(int(value))
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            raise ValidationError("non-finite rational input")
        return Fraction(float(value))
    raise ValidationError("expected a real integer, binary float or Fraction")


def pack(value: Fraction) -> dict[str, str]:
    value = rational(value)
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def outward(value: Fraction, direction: int) -> float:
    """Convert to a finite binary64 endpoint outwards; reject overflow."""
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValidationError("exact result outside finite display range") from exc
    if not math.isfinite(result):
        raise ValidationError("exact result outside finite display range")
    if direction < 0 and Fraction(result) > value:
        result = math.nextafter(result, -math.inf)
    if direction > 0 and Fraction(result) < value:
        result = math.nextafter(result, math.inf)
    if not math.isfinite(result):
        raise ValidationError("outward endpoint outside finite display range")
    return result


def exact_weights(weights: Any) -> np.ndarray:
    return np.array([[rational(x) for x in row] for row in weights], dtype=object)


def cut_value(weights: Any, subset: Iterable[int]) -> Fraction:
    selected = set(subset)
    return sum((rational(weights[j, i]) for i in selected for j in range(len(weights)) if j not in selected), Fraction(0))


def total_value(problem: SelectionProblem, subset: Iterable[int]) -> Fraction:
    if problem.cut_weights is None:
        raise ValidationError("exact stored cut requires cut_weights")
    selected = tuple(subset)
    return rational(problem.information_weight) * cut_value(problem.cut_weights, selected) + rational(problem.cost_weight) * sum((rational(problem.activation_costs[i]) for i in selected), Fraction(0))


def integral_resources(problem: SelectionProblem) -> tuple[tuple[int, ...], int]:
    values = tuple(rational(c) for c in problem.activation_costs)
    if any(c.denominator != 1 for c in values):
        raise ValidationError("budget DP requires exactly integral activation costs")
    costs = tuple(int(c) for c in values)
    if problem.constraints.budget is None:
        return costs, sum(costs)
    budget = rational(problem.constraints.budget)
    if budget.denominator != 1:
        raise ValidationError("budget DP requires an exactly integral budget")
    return costs, int(budget)


def exact_front(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pareto filtering and supported-point classification without tolerance."""
    unique = {}
    for r in rows:
        key = (r['cost'], r['loss'])
        if key not in unique or r['selected'] < unique[key]['selected']:
            unique[key] = r
    front = []
    best = None
    for key, row in sorted(unique.items()):
        if best is None or row['loss'] < best:
            front.append(row.copy()); best = row['loss']
    result = []
    for row in front:
        lower = Fraction(0); upper = None
        for other in front:
            dc = other['cost'] - row['cost']; df = other['loss'] - row['loss']
            # C + lambda*F(row) <= C + lambda*F(other).
            if df > 0:
                lower = max(lower, -Fraction(dc) / df)
            elif df < 0:
                b = -Fraction(dc) / df
                upper = b if upper is None else min(upper, b)
        r = dict(row)
        r['supported'] = upper is None or lower <= upper
        r['loss_exact'] = pack(row['loss']); r['loss'] = float(row['loss'])
        result.append(r)
    return result


def result_record(problem: SelectionProblem, selected: tuple[int, ...] | None,
                  value: Fraction | None, lower: Fraction | None, counters: Counters,
                  complete: bool, reason: str, exact: bool = True,
                  estimate: float | None = None) -> dict[str, Any]:
    has = selected is not None
    status = ('PROVED_INFEASIBLE' if complete and not has else 'NO_INCUMBENT' if not has
              else 'EXACT_STORED_INPUT' if exact and complete
              else 'VALIDATED_ENCLOSURE' if exact else 'UNCERTIFIED_EVALUATION')
    term = 'PROVED_INFEASIBLE' if complete and not has else 'COMPLETE' if complete else reason
    return {
        'record_kind': 'OBSERVED_SOLVER_RESULT',
        'objective_id': 'weighted_incoming_cut_stored_v1' if exact else 'supplied_callback_unenclosed_v1',
        'arithmetic_contract': 'EXACT_STORED_RATIONAL' if exact else 'FLOAT64_EVALUATION',
        'feasible_family_sha256': problem.sha256,
        'has_incumbent': has, 'selected': list(selected) if has else None,
        'objective_interval': {'lower': pack(value), 'upper': pack(value)} if exact and value is not None else None,
        'global_lower_bound': pack(lower) if exact and lower is not None else None,
        'incumbent_upper_bound': pack(value) if exact and value is not None else None,
        'regret_upper_bound': pack(value - lower) if exact and value is not None and lower is not None else None,
        'proof_status': status,
        'proof_evidence_refs': ['stored-input-exact-recurrence-and-partition-v1'] if exact or status == 'PROVED_INFEASIBLE' else [],
        'oracle_calls': counters.objective_calls, 'expanded_nodes': counters.nodes_expanded,
        'termination_reason': term, 'statistical_event': None,
        'objective_estimate': str(float(value)) if value is not None else str(estimate) if estimate is not None else None,
    }


def make_result(problem: SelectionProblem, selected: tuple[int, ...] | None,
                value: Fraction | None, counters: Counters, *, lower: Fraction | None = None,
                complete: bool = True, reason: str = 'COMPLETE', status: str = 'OPTIMAL',
                metadata: dict[str, Any] | None = None) -> SolverResult:
    from .algorithms.common import SolverResult
    if complete and selected is not None:
        lower = value
    record = result_record(problem, selected, value, lower, counters, complete, reason)
    meta = dict(metadata or {}); meta.update(result_contract=record, certificate_scope='exact stored weighted incoming-cut objective; not DD or physical parameters')
    return SolverResult(status='INFEASIBLE' if complete and selected is None else status,
        selected=selected, objective=float(value) if value is not None else None,
        exact=complete, certified=selected is not None or complete, termination_reason=record['termination_reason'],
        lower_bound=outward(lower, -1) if lower is not None else None,
        upper_bound=outward(value, 1) if value is not None else None,
        counters=counters, metadata=meta)
