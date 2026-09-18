"""Independent finite verification of stored-cut records and public payloads.

The verifier uses its own feasibility and objective loops, without invoking a
solver or the companion's objective routines. A verified mathematical record
is distinct from authenticated execution history. Counters and diagnostic
metadata are reported with their narrower checking scopes.
"""
from __future__ import annotations

from fractions import Fraction
import math
from numbers import Integral
from typing import Any, Mapping

from .errors import ValidationError
from .models import SelectionProblem
from .schemas import validate_json

_CUT = 'weighted_incoming_cut_stored_v1'
_CALLBACK = 'supplied_callback_unenclosed_v1'
_STOPPED = {'CALL_BUDGET', 'TIME_BUDGET', 'NODE_BUDGET', 'NO_FEASIBLE_INCUMBENT'}
_EXACT_STATES = {'OPTIMAL', 'OPTIMAL_CUT_SURROGATE', 'OPTIMAL_GIVEN_VALID_TREE_DECOMPOSITION'}
_PAYLOAD_FIELDS = {
    'status', 'selected', 'objective', 'exact', 'certified', 'termination_reason',
    'lower_bound', 'upper_bound', 'optimality_gap', 'counters', 'metadata'
}
_COUNTER_FIELDS = {
    'objective_calls', 'lower_bound_calls', 'nodes_generated', 'nodes_expanded',
    'nodes_pruned', 'transitions_considered', 'states_stored', 'peak_frontier',
    'iterations', 'line_search_evaluations'
}


def _fraction(value: Mapping[str, str]) -> Fraction:
    n, d = int(value['numerator']), int(value['denominator'])
    if d <= 0:
        raise ValidationError('rational denominator must be positive')
    return Fraction(n, d)


def _stored(value: Any) -> Fraction:
    # Preserve explicitly supported exact costs and the actual binary64 edges.
    if isinstance(value, Fraction):
        return value
    return Fraction(int(value)) if isinstance(value, Integral) else Fraction(float(value))


def _display(value: Fraction | None, direction: int = 0) -> float | None:
    """Independent directed-rounding calculation for the serialised display."""
    if value is None:
        return None
    try:
        shown = float(value)
    except OverflowError as exc:
        raise ValidationError('rational value exceeds the finite display range') from exc
    if not math.isfinite(shown):
        raise ValidationError('rational value exceeds the finite display range')
    if direction < 0 and Fraction(shown) > value:
        shown = math.nextafter(shown, -math.inf)
    elif direction > 0 and Fraction(shown) < value:
        shown = math.nextafter(shown, math.inf)
    if not math.isfinite(shown):
        raise ValidationError('outward endpoint exceeds the finite display range')
    return shown


def _feasible(problem: SelectionProblem, subset: tuple[int, ...]) -> bool:
    """Check this finite subset without ServiceConstraints.is_feasible."""
    n, c = problem.n, problem.constraints
    size = len(subset)
    selected = set(subset)
    if (c.exclude_empty and size == 0) or (c.exclude_full and size == n):
        return False
    if c.exact_k is not None:
        if size != c.exact_k:
            return False
    elif not c.k_min <= size <= (n if c.k_max is None else c.k_max):
        return False
    if not set(c.mandatory) <= selected or set(c.forbidden) & selected:
        return False
    if any(not selected.intersection(g) for g in c.coverage_groups):
        return False
    cost = sum((_stored(problem.activation_costs[i]) for i in subset), Fraction(0))
    return c.budget is None or cost <= _stored(c.budget)


def _family(problem: SelectionProblem) -> list[tuple[int, ...]]:
    out = []
    for mask in range(1 << problem.n):
        selected = tuple(i for i in range(problem.n) if mask >> i & 1)
        if _feasible(problem, selected):
            out.append(selected)
    return out


def _catalogue(problem: SelectionProblem, family: list[tuple[int, ...]]) -> dict[tuple[int, ...], Fraction]:
    weights = [[_stored(x) for x in row] for row in problem.cut_weights]
    costs = tuple(_stored(x) for x in problem.activation_costs)
    alpha, beta = _stored(problem.information_weight), _stored(problem.cost_weight)
    out = {}
    for subset in family:
        selected = set(subset)
        loss = Fraction(0)
        for source in range(problem.n):
            for target in range(problem.n):
                if source not in selected and target in selected:
                    loss += weights[source][target]
        cost = sum((costs[i] for i in subset), Fraction(0))
        out[subset] = alpha * loss + beta * cost
    return out


def _record_preconditions(record: Mapping[str, Any], n: int) -> None:
    """Schema plus strict Python/JSON representation and state invariants."""
    validate_json('result_contract', record)
    for field in ('oracle_calls', 'expanded_nodes'):
        if type(record[field]) is not int or record[field] < 0:
            raise ValidationError(f'{field} must be a nonnegative integer')
    selected = record['selected']
    if record['has_incumbent'] is not (selected is not None):
        raise ValidationError('incumbent availability contradicts the selected field')
    if selected is not None:
        if (not isinstance(selected, list)
                or any(type(i) is not int or not 0 <= i < n for i in selected)
                or selected != sorted(set(selected))):
            raise ValidationError('selected must be a sorted set of integer coordinate indices')
    proof, term = record['proof_status'], record['termination_reason']
    if proof == 'EXACT_STORED_INPUT' and term not in {'COMPLETE', 'BOUND_GAP'}:
        raise ValidationError('exact optimum has an inconsistent termination label')
    if proof == 'NO_INCUMBENT' and term not in _STOPPED:
        raise ValidationError('absence of an incumbent does not establish completion')
    if proof in {'VALIDATED_ENCLOSURE', 'UNCERTIFIED_EVALUATION'} and term not in _STOPPED | {'COMPLETE', 'BOUND_GAP'}:
        raise ValidationError('incumbent result has an inconsistent termination label')


def verify_result(problem: SelectionProblem, record: Mapping[str, Any], *, max_vertices: int = 16) -> dict[str, Any]:
    """Verify finite stored-input claims, or explicitly limit an unenclosed case.

    A callback estimate is never certified by this routine. Callback-free
    infeasibility can be checked from the same finite service family, because it
    makes no numerical objective claim. Execution counters are unauthenticated.
    """
    problem.validate()
    if not isinstance(record, Mapping):
        raise ValidationError('result record must be an object')
    _record_preconditions(record, problem.n)
    if type(max_vertices) is not int or not 1 <= max_vertices <= 20:
        raise ValidationError('max_vertices must be an integer from 1 to 20')
    if problem.n > max_vertices:
        raise ValidationError('finite verifier vertex ceiling exceeded')
    if record['record_kind'] != 'OBSERVED_SOLVER_RESULT':
        raise ValidationError('interface examples cannot establish execution evidence')
    if record['feasible_family_sha256'] != problem.sha256:
        raise ValidationError('problem/family digest mismatch')
    if record['statistical_event'] is not None:
        raise ValidationError('finite stored-input replay establishes no statistical event')
    proof, objective, arithmetic = record['proof_status'], record['objective_id'], record['arithmetic_contract']
    cut_contract = objective == _CUT and arithmetic == 'EXACT_STORED_RATIONAL' and problem.cut_weights is not None
    callback_contract = objective == _CALLBACK and arithmetic in {'FLOAT64_EVALUATION', 'HIGH_PRECISION_EVALUATION'}
    if not (cut_contract or callback_contract):
        raise ValidationError('unsupported objective/arithmetic contract; numerical intervals require their own oracle verifier')
    if callback_contract:
        if proof not in {'UNCERTIFIED_EVALUATION', 'NO_INCUMBENT', 'PROVED_INFEASIBLE'}:
            raise ValidationError('unenclosed callback cannot provide a numerical certificate')
        if record['global_lower_bound'] is not None:
            raise ValidationError('unenclosed callback carries an unsupported global lower bound')
    if proof == 'UNCERTIFIED_EVALUATION':
        if not callback_contract:
            raise ValidationError('uncertified evaluation has an inconsistent objective contract')
        estimate = float(record['objective_estimate'])
        if not math.isfinite(estimate) or estimate < 0:
            raise ValidationError('callback point estimate must be finite and nonnegative')
        if not _feasible(problem, tuple(record['selected'])):
            raise ValidationError('callback incumbent is not feasible in the declared family')
        return {'status': 'ACCEPTED_UNCERTIFIED', 'certificate_verified': False,
                'scope': 'incumbent feasibility checked; callback value and callback optimality not replayed',
                'execution_provenance_verified': False}
    family = _family(problem)
    if proof == 'PROVED_INFEASIBLE':
        if family:
            raise ValidationError('feasible alternatives contradict infeasibility')
        if record['global_lower_bound'] is not None:
            raise ValidationError('infeasible result must not carry an objective lower bound')
        return {'status': 'PASS', 'certificate_verified': True, 'scope': 'finite service-family infeasibility; no objective evaluation',
                'feasible_alternatives': 0, 'execution_provenance_verified': False}
    if callback_contract:
        # Only NO_INCUMBENT remains after the callback cases above.
        return {'status': 'NO_INCUMBENT', 'certificate_verified': False,
                'scope': 'no callback value or incumbent asserted', 'feasible_alternatives': len(family),
                'execution_provenance_verified': False}
    values = _catalogue(problem, family)
    optimum = min(values.values()) if values else None
    lower = _fraction(record['global_lower_bound']) if record['global_lower_bound'] is not None else None
    if optimum is not None and lower is not None and lower > optimum:
        raise ValidationError('global lower bound exceeds the independently computed optimum')
    if proof == 'NO_INCUMBENT':
        return {'status': 'NO_INCUMBENT', 'certificate_verified': False,
                'scope': 'any supplied lower bound replayed; no incumbent asserted',
                'feasible_alternatives': len(values), 'execution_provenance_verified': False}
    selected = tuple(record['selected'])
    if selected not in values:
        raise ValidationError('incumbent is not a canonical feasible selection')
    value = values[selected]
    interval = record['objective_interval']
    lo, hi = _fraction(interval['lower']), _fraction(interval['upper'])
    upper = _fraction(record['incumbent_upper_bound'])
    gap = _fraction(record['regret_upper_bound'])
    if lo > value or hi < value or lo > hi or upper < value:
        raise ValidationError('incumbent interval does not enclose its true stored objective')
    if lower is None or upper < lower or gap < 0 or gap < upper - lower:
        raise ValidationError('inconsistent regret or global bound arithmetic')
    if record['objective_estimate'] is None or float(record['objective_estimate']) != _display(value):
        raise ValidationError('display estimate differs from the stored incumbent objective')
    if proof == 'EXACT_STORED_INPUT' and not (lo == hi == value == optimum == lower == upper and gap == 0):
        raise ValidationError('claimed exact optimum or zero-width interval is false')
    return {'status': 'PASS', 'certificate_verified': True,
            'scope': 'finite stored weighted cut; no DD or population guarantee',
            'feasible_alternatives': len(values),
            'exact_optimum': {'numerator': str(optimum.numerator), 'denominator': str(optimum.denominator)},
            'exact_incumbent': {'numerator': str(value.numerator), 'denominator': str(value.denominator)},
            'execution_provenance_verified': False}


def _check_number(payload: Mapping[str, Any], field: str, expected: float | None) -> None:
    actual = payload[field]
    if expected is None:
        if actual is not None:
            raise ValidationError(f'{field} must be null in the declared result state')
    elif (type(actual) not in (int, float) or not math.isfinite(actual) or actual != expected):
        raise ValidationError(f'{field} differs from its finite authoritative display value')


def verify_solver_payload(problem: SelectionProblem, payload: Mapping[str, Any], *, max_vertices: int = 16) -> dict[str, Any]:
    """Verify the record and every defined assurance field in the public payload.

    Unknown top-level assertions are refused. Extra metadata are explicitly
    outside the assurance verdict. Mirrored counters must agree, but neither
    counter consistency nor a proof-reference string authenticates execution.
    """
    if not isinstance(payload, Mapping):
        raise ValidationError('solver payload must be an object')
    if 'record_kind' in payload:
        return verify_result(problem, payload, max_vertices=max_vertices)
    if set(payload) != _PAYLOAD_FIELDS:
        raise ValidationError('missing or unsupported public payload fields')
    metadata = payload['metadata']
    if not isinstance(metadata, Mapping) or 'result_contract' not in metadata:
        raise ValidationError('payload lacks the adopted result record')
    record = metadata['result_contract']
    verdict = verify_result(problem, record, max_vertices=max_vertices)
    proof = record['proof_status']
    if payload['selected'] != record['selected']:
        raise ValidationError('public selected set differs from the authoritative record')
    if payload['selected'] is not None:
        if not isinstance(payload['selected'], list) or any(type(i) is not int for i in payload['selected']):
            raise ValidationError('public selected indices must be integers')
    expected_exact = proof in {'EXACT_STORED_INPUT', 'PROVED_INFEASIBLE'}
    expected_certified = proof in {'EXACT_STORED_INPUT', 'VALIDATED_ENCLOSURE', 'PROVED_INFEASIBLE'}
    if payload['exact'] is not expected_exact or payload['certified'] is not expected_certified:
        raise ValidationError('public certificate flags contradict the authoritative record')
    if payload['termination_reason'] != record['termination_reason']:
        raise ValidationError('public termination reason contradicts the authoritative record')
    if proof == 'EXACT_STORED_INPUT':
        allowed_status = _EXACT_STATES
    elif proof == 'VALIDATED_ENCLOSURE':
        allowed_status = {'ANYTIME_FEASIBLE_WITH_BOUND'}
    elif proof == 'PROVED_INFEASIBLE':
        allowed_status = {'INFEASIBLE'}
    elif proof == 'NO_INCUMBENT':
        allowed_status = {'NO_INCUMBENT'}
    else:
        allowed_status = {'OPTIMAL'} if record['termination_reason'] == 'COMPLETE' else {'ANYTIME_UNCERTIFIED'}
    if not isinstance(payload['status'], str) or payload['status'] not in allowed_status:
        raise ValidationError('public status contradicts the authoritative proof state')
    estimate = None if record['objective_estimate'] is None else float(record['objective_estimate'])
    _check_number(payload, 'objective', estimate)
    if proof == 'UNCERTIFIED_EVALUATION':
        # The documented legacy displays are diagnostic callback values only.
        _check_number(payload, 'lower_bound', 0.0)
        _check_number(payload, 'upper_bound', estimate)
        _check_number(payload, 'optimality_gap', estimate)
        verdict['diagnostic_only_fields'] = ['lower_bound', 'upper_bound', 'optimality_gap', 'status']
    else:
        for field, key, direction in (
            ('lower_bound', 'global_lower_bound', -1),
            ('upper_bound', 'incumbent_upper_bound', 1),
            ('optimality_gap', 'regret_upper_bound', 1)
        ):
            exact = None if record[key] is None else _fraction(record[key])
            _check_number(payload, field, _display(exact, direction))
    counters = payload['counters']
    if not isinstance(counters, Mapping) or set(counters) != _COUNTER_FIELDS:
        raise ValidationError('missing or unsupported counter fields')
    if any(type(v) is not int or v < 0 for v in counters.values()):
        raise ValidationError('counters must be nonnegative integers')
    if counters['objective_calls'] != record['oracle_calls'] or counters['nodes_expanded'] != record['expanded_nodes']:
        raise ValidationError('mirrored counters contradict the authoritative record')
    verdict.update(
        public_payload_consistent=True,
        gap_display_semantics='upward-rounded record regret; callback display is diagnostic only',
        counter_scope='integer domain and two mirrored equalities; no execution authentication',
        unverified_metadata_fields=sorted(k for k in metadata if k != 'result_contract'),
        proof_reference_authenticity_verified=False,
    )
    return verdict
