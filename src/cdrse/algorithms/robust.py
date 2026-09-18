"""Finite scenario reference enumeration, not objective authentication."""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from numbers import Integral
from typing import Callable, Sequence

from ..economics import _aggregate_exact, _nearest_finite, _real_fraction, _scenario_configuration
from ..errors import ValidationError
from .common import Counters


def solve_scenarios_exhaustive(
    n: int,
    scenario_objectives: Sequence[Callable[[tuple[int, ...]], float]],
    *,
    exact_k: int,
    mode: str,
    probabilities: Sequence[float] | None = None,
    alpha: float = 0.5,
    feasible: Callable[[tuple[int, ...]], bool] | None = None,
) -> dict:
    if isinstance(n, bool) or not isinstance(n, Integral) or n < 0:
        raise ValidationError("n must be a non-negative integer")
    if isinstance(exact_k, bool) or not isinstance(exact_k, Integral) or not 0 <= exact_k <= n:
        raise ValidationError("exact_k must be an integer in [0,n]")
    n, exact_k = int(n), int(exact_k)
    try:
        objectives = tuple(scenario_objectives)
    except TypeError as exc:
        raise ValidationError("scenario objectives must be a non-empty callable sequence") from exc
    if not objectives or any(not callable(objective) for objective in objectives):
        raise ValidationError("scenario objectives must be a non-empty callable sequence")
    if feasible is not None and not callable(feasible):
        raise ValidationError("feasible must be a callable or None")
    configuration = _scenario_configuration(len(objectives), mode, probabilities, alpha)
    normalised_mode = configuration[0]
    counters = Counters()
    rows: list[dict] = []
    best: tuple[Fraction, tuple[int, ...], dict] | None = None
    for subset in combinations(range(n), exact_k):
        if feasible is not None:
            admissible = feasible(subset)
            if type(admissible) is not bool:
                raise ValidationError("feasible must return an actual boolean")
            if not admissible:
                continue
        exact_values = []
        values = []
        for objective in objectives:
            supplied = objective(subset)
            counters.objective_calls += 1
            exact = _real_fraction(supplied, "scenario callback result")
            values.append(_nearest_finite(exact, "scenario callback display"))
            exact_values.append(exact)
        exact_aggregate = _aggregate_exact(tuple(exact_values), configuration)
        aggregate = _nearest_finite(exact_aggregate, "scenario aggregate")
        row = {"selected": list(subset), "scenario_values": values, "aggregate": aggregate}
        rows.append(row)
        # Compare aggregates before display rounding; equal displays need not
        # represent equal supplied-operand objectives. This is not a certificate.
        candidate = (exact_aggregate, tuple(subset), row)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    limits = {
        "exact": False, "certified": False,
        "arithmetic_contract": "FLOAT64_EVALUATION",
        "aggregation_contract": "EXACT_STORED_OPERANDS_NEAREST_BINARY64_DISPLAY",
    }
    if best is None:
        return {"status": "INFEASIBLE", **limits, "best": None, "rows": [], "counters": counters.to_dict()}
    return {
        "status": "OPTIMAL_BY_ENUMERATION", **limits,
        "mode": normalised_mode,
        "alpha": alpha if normalised_mode == "cvar" else None,
        "best": best[2], "rows": rows, "counters": counters.to_dict(),
        "submodularity_assumed": False, "scalability_claimed": False,
    }
