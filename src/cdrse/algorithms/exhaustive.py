"""Finite enumeration with distinct stored-cut and callback semantics."""
from __future__ import annotations
from itertools import combinations
from typing import Callable
import math
from ..models import SelectionProblem
from ..errors import ValidationError
from ..exact_cut import total_value, make_result, result_record
from .common import Counters, SolverResult


def solve_exhaustive(problem: SelectionProblem, objective: Callable[[tuple[int, ...]], float] | None = None) -> SolverResult:
    """Enumerate the feasible family. Omit objective for exact stored-cut results."""
    problem.validate()
    exact = objective is None
    if exact and problem.cut_weights is None:
        raise ValidationError('exact enumeration requires cut_weights')
    n, c = problem.n, problem.constraints
    sizes = (c.exact_k,) if c.exact_k is not None else range(c.k_min, (n if c.k_max is None else c.k_max) + 1)
    counters = Counters(); best = None; feasible_count = 0
    for size in sizes:
        for subset in combinations(range(n), size):
            if not c.is_feasible(subset, n, problem.activation_costs):
                continue
            feasible_count += 1; counters.objective_calls += 1
            if exact:
                value = total_value(problem, subset)
            else:
                information = float(objective(subset))
                if not math.isfinite(information) or information < 0:
                    raise ValidationError('callback must return finite nonnegative information')
                value = problem.information_weight * information + problem.cost_weight * sum(problem.activation_costs[i] for i in subset)
                if not math.isfinite(value):
                    raise ValidationError('weighted callback value is non-finite')
            candidate = (value, subset)
            if best is None or candidate < best:
                best = candidate
    selected, value = (None, None) if best is None else (best[1], best[0])
    if exact:
        return make_result(problem, selected, value, counters, reason='COMPLETE' if best else 'PROVED_INFEASIBLE', metadata={'feasible_subsets': feasible_count})
    record = result_record(problem, selected, None, None, counters, True, 'COMPLETE', exact=False, estimate=value)
    infeasible = record['proof_status'] == 'PROVED_INFEASIBLE'
    return SolverResult('INFEASIBLE' if infeasible else 'OPTIMAL', selected, value, infeasible, infeasible, record['termination_reason'],
        0.0 if best else None, value, counters,
        {'feasible_subsets': feasible_count, 'result_contract': record,
         'optimality_scope': 'enumerated callback evaluations',
         'legacy_bounds_semantics': 'diagnostic only; no validated numerical enclosure'})
