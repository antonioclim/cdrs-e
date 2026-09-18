"""Frozen SD3 economic-boundary obligations, synthetic E0 inputs only.

Independent references use finite support intervals and the CVaR variational
formula. Public floating outputs remain approximations, not certificates.
The old 757-case suite is not edited or made part of this file.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
import itertools
import math
import random
import sys

import numpy as np
import pytest

from cdrse.economics import (
    CostComponent, CostLedger, aggregate_scenarios, empirical_cvar, pareto_front,
    present_value, scalarised_decision_value, supported_points,
)
from cdrse.algorithms.robust import solve_scenarios_exhaustive
from cdrse.errors import ValidationError


def q(value):
    if isinstance(value, (int, np.integer)):
        return Fraction(int(value))
    return Fraction.from_float(float(value))


def exact_front(rows):
    return [r for r in rows if not any(
        q(s['cost']) <= q(r['cost']) and q(s['loss']) <= q(r['loss'])
        and (q(s['cost']) < q(r['cost']) or q(s['loss']) < q(r['loss']))
        for s in rows)]


def support_interval(p, rows):
    """Interval of lambda >= 0 supporting p, from pairwise inequalities."""
    lower, upper = Fraction(0), None
    for other in rows:
        a = q(p['cost']) - q(other['cost'])
        b = q(other['loss']) - q(p['loss'])
        if a > 0:
            bound = b / a
            upper = bound if upper is None else min(upper, bound)
        elif a < 0:
            lower = max(lower, b / a)
        elif b < 0:
            return None
    if upper is not None and upper < lower:
        return None
    return lower, upper


def supported_vertex_ids(rows):
    # One deterministic representative per exact coordinate pair. An interval
    # of positive width excludes collinear interior ties, as the API specifies.
    unique = {}
    for r in sorted(rows, key=repr):
        unique.setdefault((q(r['cost']), q(r['loss'])), r)
    candidates = list(unique.values())
    result = set()
    for r in candidates:
        interval = support_interval(r, candidates)
        if interval is not None:
            lo, hi = interval
            if hi is None or hi > max(lo, Fraction(0)):
                result.add(r['id'])
    return result


def variational_cvar(values, alpha):
    vals = [q(v) for v in values]
    a = q(alpha)
    return min(z + sum((max(v-z, Fraction(0)) for v in vals), Fraction(0))
               / (len(vals) * (1-a)) for z in vals)


def finite_float(exact):
    """Correct nearest-binary64 reference; never invoke package arithmetic."""
    result = float(exact)
    assert math.isfinite(result)
    return result


def rows_at_scale(shape, exponent, offset=0.0):
    scale = math.ldexp(1.0, exponent)
    return [{'id':chr(65+i), 'cost':offset+scale*x, 'loss':scale*y}
            for i, (x, y) in enumerate(shape)]


@pytest.mark.parametrize('offset', [0.0, 1e9, 2.0**40, 2.0**50])
def test_supported_endpoint_not_collapsed_by_relative_closeness(offset):
    rows = [{'id':'A','cost':offset,'loss':1.0},
            {'id':'B','cost':offset+0.5,'loss':0.0}]
    assert q(rows[0]['cost']) < q(rows[1]['cost'])
    assert {p['id'] for p in supported_points(pareto_front(rows))} == {'A','B'}


@pytest.mark.parametrize('exponent', [-1000,-600,-80,-25,0,100,550,1000])
@pytest.mark.parametrize('shape,expected', [([(0,4),(1,1),(4,0)], {'A','B','C'}),
                                          ([(0,4),(2,3),(4,0)], {'A','C'})])
def test_supported_vertices_invariant_under_exact_power_of_two_units(exponent, shape, expected):
    rows = rows_at_scale(shape, exponent)
    assert supported_vertex_ids(rows) == expected
    assert {r['id'] for r in supported_points(pareto_front(rows))} == expected


@pytest.mark.parametrize('seed', range(64))
def test_finite_front_and_support_against_independent_weight_intervals(seed):
    rng = random.Random(202609150300 + seed)
    exponent = [-600,-40,0,200,550][seed % 5]
    scale = math.ldexp(1.0, exponent)
    rows = [{'id':f'{i:02d}', 'cost':rng.randrange(0,40)*scale,
             'loss':rng.randrange(0,40)*scale} for i in range(12)]
    oracle = exact_front(rows)
    actual = pareto_front(rows)
    assert {r['id'] for r in actual} == {r['id'] for r in oracle}
    assert {r['id'] for r in supported_points(actual)} == supported_vertex_ids(oracle)


@pytest.mark.parametrize('permutation', list(itertools.permutations(range(4))))
def test_frontier_label_ties_are_deterministic_not_all_supported_labels(permutation):
    rows = [{'id':'A','cost':0,'loss':2}, {'id':'B','cost':1,'loss':1},
            {'id':'C','cost':2,'loss':0}, {'id':'A-copy','cost':0,'loss':2}]
    ordered = [rows[i] for i in permutation]
    assert {r['id'] for r in pareto_front(ordered)} == {'A','A-copy','B','C'}
    assert [r['id'] for r in supported_points(pareto_front(ordered))] == ['A','C']


def test_large_integer_coordinates_do_not_alias_before_dominance():
    rows = [{'id':'A','cost':2**53,'loss':0}, {'id':'B','cost':2**53+1,'loss':0}]
    assert [r['id'] for r in pareto_front(rows)] == ['A']


def test_frontier_custom_keys_preserve_records_and_inputs():
    rows = [{'tag':'a','resource':0.,'risk':4.,'meta':[1]},
            {'tag':'b','resource':1.,'risk':1.,'meta':[2]},
            {'tag':'c','resource':4.,'risk':0.,'meta':[3]}]
    before = repr(rows)
    front = pareto_front(iter(rows), 'resource', 'risk')
    out = supported_points(front, 'resource', 'risk')
    assert [r['tag'] for r in out] == ['a','b','c']
    assert repr(rows) == before and [r['meta'] for r in out] == [[1],[2],[3]]
    assert all(a is not b for a,b in zip(out, rows))


@pytest.mark.parametrize('function', [pareto_front,supported_points])
@pytest.mark.parametrize('field', ['cost','loss'])
@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf, True, '1.0', None, 1+0j])
def test_frontier_rejects_invalid_coordinates(function, field, value):
    row = {'cost':1.,'loss':1.,field:value}
    with pytest.raises(ValidationError):
        function([row])


@pytest.mark.parametrize('function', [pareto_front,supported_points])
@pytest.mark.parametrize('rows', [[{'cost':1.}], [1], ['bad']])
def test_frontier_requires_numeric_coordinate_mappings(function, rows):
    with pytest.raises(ValidationError):
        function(rows)


def test_empty_front_is_valid_empty_output():
    assert pareto_front([]) == [] and supported_points([]) == []


@pytest.mark.parametrize('value', [math.ulp(0.),2.0**-1000,1.,2.0**1000,sys.float_info.max])
@pytest.mark.parametrize('alpha', [0.,.25,.5,.75,math.nextafter(1.,0.)])
def test_cvar_constant_law_without_intermediate_over_or_underflow(value, alpha):
    assert empirical_cvar([value]*4,alpha) == value


@pytest.mark.parametrize('seed', range(80))
def test_cvar_matches_variational_and_decimal_independent_references(seed):
    rng = random.Random(202609150500 + seed)
    scale = math.ldexp(1.,[-800,-50,0,500,1000][seed % 5])
    values = [rng.randrange(-8,9)*scale for _ in range(1+seed%7)]
    alpha = [0.,.125,.5,.75,math.nextafter(1.,0.)][seed%5]
    exact = variational_cvar(values,alpha)
    observed = empirical_cvar(values,alpha)
    assert observed == finite_float(exact)
    # Distinct decimal implementation of the variational expression. Division
    # can be non-terminating: this is a high-precision cross-check, not enclosure.
    with localcontext() as ctx:
        ctx.prec = 2500
        vals = [Decimal.from_float(v) for v in values]
        a = Decimal.from_float(alpha)
        other = min(z + sum((max(v-z,Decimal(0)) for v in vals),Decimal(0))
                    / (Decimal(len(vals))*(1-a)) for z in vals)
        assert observed == float(other)
    assert min(values) <= observed <= max(values)


@pytest.mark.parametrize('mode', ['mean','worst','cvar',' CVAR '])
@pytest.mark.parametrize('value', [math.ulp(0.),1.,1.6e308,sys.float_info.max])
def test_aggregate_finite_constant_and_normalised_mode(mode, value):
    assert aggregate_scenarios([value]*4,mode,alpha=.5) == value


@pytest.mark.parametrize('values', [[1e16,1.,-1e16],[1.6e308,1.6e308],
                                    [-1.6e308,-1.6e308],[2**53+1,-2**53],
                                    [math.ulp(0.),math.ulp(0.)]])
def test_unweighted_mean_uses_stored_operand_expression(values):
    exact = sum(map(q,values),Fraction(0))/len(values)
    assert aggregate_scenarios(values,'mean') == finite_float(exact)


@pytest.mark.parametrize('values,probabilities', [([1.,3.],[.25,.75]),
        ([1e16,1.,-1e16],[.25,.5,.25]),([1.6e308,1.6e308],[.5,.5]),
        ([1.,2.,3.],[.1,.2,.7]),([1.,3.],[0.,1.])])
def test_mean_weights_used_as_declared_without_silent_normalisation(values, probabilities):
    exact = sum((q(x)*q(p) for x,p in zip(values,probabilities)),Fraction(0))
    assert aggregate_scenarios(values,'mean',probabilities) == finite_float(exact)


@pytest.mark.parametrize('mode', ['mean','worst','cvar'])
@pytest.mark.parametrize('values', [[],[math.nan,1.],[math.inf,1.],[-math.inf,1.],
                                   [True,1.],['1.0',1.],[None,1.],[1+0j,1.]])
def test_scenario_values_have_uniform_nonempty_finite_numeric_boundary(mode, values):
    with pytest.raises(ValidationError):
        aggregate_scenarios(values,mode)


@pytest.mark.parametrize('probabilities', [[1.],[-1.,2.],[.2,.2],[math.nan,1.],
                                          [math.inf,0.],[True,False],['.5',.5]])
@pytest.mark.parametrize('mode', ['mean','worst'])
def test_explicit_probability_vector_is_validated_even_when_worst_is_unweighted(probabilities, mode):
    with pytest.raises(ValidationError):
        aggregate_scenarios([1.,2.],mode,probabilities)


@pytest.mark.parametrize('alpha', [True,False,'0.5',None,math.nan,math.inf,-.1,1.])
def test_cvar_alpha_is_finite_real_non_boolean_in_unit_interval(alpha):
    with pytest.raises(ValidationError):
        empirical_cvar([1.,2.],alpha)


def test_cvar_explicit_probabilities_remain_unsupported():
    with pytest.raises(ValidationError):
        aggregate_scenarios([1.,3.],'cvar',[.5,.5])


@pytest.mark.parametrize('mode', ['unknown','',None,False])
def test_aggregation_rejects_unknown_non_string_modes(mode):
    with pytest.raises(ValidationError):
        aggregate_scenarios([1.,2.],mode)


@pytest.mark.parametrize('updates', [dict(name=None),dict(name=' '),dict(unit=1),
    dict(unit=''),dict(value=True),dict(value='1'),dict(value=None),dict(value=math.nan),
    dict(value=math.inf),dict(uncertainty_lower=math.nan,uncertainty_upper=2.),
    dict(uncertainty_lower=0.,uncertainty_upper=math.nan),
    dict(uncertainty_lower=-math.inf,uncertainty_upper=2.),
    dict(uncertainty_lower=0.,uncertainty_upper=math.inf),
    dict(uncertainty_lower=False,uncertainty_upper=2.),
    dict(uncertainty_lower=0.,uncertainty_upper='2'),
    dict(evidence_tier='E2',source=' '),dict(evidence_tier='E3',source=True),
    dict(evidence_tier=[]),dict(uncertainty_lower=2.,uncertainty_upper=3.)])
def test_cost_component_strict_boundary_and_interval(updates):
    item = replace(CostComponent('synthetic',1.,'unit','E0'),**updates)
    with pytest.raises(ValidationError):
        item.validate()
    with pytest.raises(ValidationError):
        CostLedger((item,)).to_dict()


def test_cost_ledger_retains_units_and_does_not_authenticate_provenance():
    ledger = CostLedger((CostComponent('a',2.,'unit','E0',uncertainty_lower=1.,uncertainty_upper=3.),
                         CostComponent('b',3.,'unit','E0')))
    assert ledger.scalar_total() == 5.
    assert ledger.to_dict()['units'] == ['unit']
    assert ledger.to_dict()['components'][0]['evidence_tier'] == 'E0'
    with pytest.raises(ValidationError):
        CostLedger((CostComponent('a',1.,'s','E1'),CostComponent('b',1.,'J','E1'))).scalar_total()


@pytest.mark.parametrize('values', [[1e16,1.,-1e16],[2**53+1,-2**53],[-2.,3.]])
def test_cost_total_evaluates_supplied_operand_sum_once(values):
    ledger = CostLedger(tuple(CostComponent(str(i),v,'unit','E0') for i,v in enumerate(values)))
    assert ledger.scalar_total() == finite_float(sum(map(q,values),Fraction(0)))


@pytest.mark.parametrize('values', [[1.6e308,1.6e308],[-1.6e308,-1.6e308]])
def test_cost_total_overflow_is_refused(values):
    with pytest.raises(ValidationError):
        CostLedger(tuple(CostComponent(str(i),v,'unit','E0') for i,v in enumerate(values))).scalar_total()


@pytest.mark.parametrize('stream,discount', [([1e16,1.,-1e16],1.),([2.,3.],.5),
    ([1.6e308,-1.6e308,1.],1.),([2**53+1,-2**53],1.),([],1.),([1.,2.,3.],.9)])
def test_present_value_exact_stored_polynomial_with_single_conversion(stream, discount):
    expected = sum((q(v)*q(discount)**i for i,v in enumerate(stream)),Fraction(0))
    assert present_value(stream,discount) == finite_float(expected)


@pytest.mark.parametrize('stream,discount', [([1.6e308,1.6e308],1.),([True],.5),
        (['1'],.5),([1.],True),([1.],'0.5'),([math.nan],.5),([1.],0.)])
def test_present_value_rejects_invalid_or_nonfinite_result(stream, discount):
    with pytest.raises(ValidationError):
        present_value(stream,discount)


@pytest.mark.parametrize('args', [(0.,0.,1.6e308,2.),(1e16,2.,.5,1.),
     (-1e16,2.,1e16,1.),(10.,2.,3.,4.),(0.,2.,1.6e308,1.)])
def test_scalarisation_avoids_intermediate_overflow_and_keeps_half_factor(args):
    cost,loss,valuation,predictions = map(q,args)
    expected = cost + loss*valuation*predictions/2
    assert scalarised_decision_value(*args) == finite_float(expected)


@pytest.mark.parametrize('args', [(1.6e308,2.,1.6e308,1.),(0.,True,1.,1.),
                                  (0.,'2',1.,1.),(0.,1.,math.inf,1.)])
def test_scalarisation_refuses_invalid_or_nonfinite_output(args):
    with pytest.raises(ValidationError):
        scalarised_decision_value(*args)


def test_numpy_real_scalars_remain_usable():
    values = [np.float64(1.),np.int64(3)]
    assert empirical_cvar(values,np.float64(.5)) == 3.
    assert aggregate_scenarios(values,'mean') == 2.
    assert CostLedger((CostComponent('a',np.float64(1.),'unit','E0'),)).scalar_total() == 1.


def test_robust_selector_does_not_tie_finite_means_at_infinity():
    objectives = [lambda s:1.6e308 if s==(0,) else 1.2e308]*2
    result = solve_scenarios_exhaustive(2,objectives,exact_k=1,mode='mean')
    assert result['status'] == 'OPTIMAL_BY_ENUMERATION'
    assert result['best']['selected'] == [1]
    assert result['best']['aggregate'] == 1.2e308
    assert all(math.isfinite(r['aggregate']) for r in result['rows'])
    assert result['exact'] is False and result['certified'] is False


def test_robust_order_uses_exact_aggregate_before_display_rounding():
    # Both displayed means are 1.0, but the first exact mean is 1 + 2^-53.
    objectives = [lambda s:1., lambda s:math.nextafter(1.,math.inf) if s==(0,) else 1.]
    result = solve_scenarios_exhaustive(2,objectives,exact_k=1,mode='mean')
    assert result['best']['selected'] == [1]
    assert [r['aggregate'] for r in result['rows']] == [1.,1.]
    assert not result['certified'] and not result['exact']


@pytest.mark.parametrize('mode', ['mean','worst','cvar',' CVAR '])
@pytest.mark.parametrize('value', [math.nan,math.inf,-math.inf,True,'1.0',None,1+0j])
def test_robust_callback_invalidity_cannot_be_reported_as_optimal(mode, value):
    with pytest.raises(ValidationError):
        solve_scenarios_exhaustive(2,[lambda s:value],exact_k=1,mode=mode)


@pytest.mark.parametrize('kwargs', [dict(n=True,exact_k=1,mode='mean'),
    dict(n=2.5,exact_k=1,mode='mean'),dict(n=-1,exact_k=0,mode='mean'),
    dict(n=2,exact_k=True,mode='mean'),dict(n=2,exact_k=1.5,mode='mean'),
    dict(n=2,exact_k=3,mode='mean'),dict(n=2,exact_k=1,mode='unknown'),
    dict(n=2,exact_k=1,mode='cvar',alpha=1.),
    dict(n=2,exact_k=1,mode='mean',probabilities=[.2,.2])])
def test_invalid_enumeration_configuration_is_rejected_before_callbacks_even_if_no_feasible_set(kwargs):
    called = []
    def objective(s):
        called.append(s)
        return 1.
    with pytest.raises(ValidationError):
        solve_scenarios_exhaustive(scenario_objectives=[objective,objective],
                                  feasible=lambda s:False,**kwargs)
    assert called == []


@pytest.mark.parametrize('oracle', [None,1,'f'])
def test_scenario_collection_requires_callable_members(oracle):
    with pytest.raises(ValidationError):
        solve_scenarios_exhaustive(2,[oracle],exact_k=1,mode='mean')


@pytest.mark.parametrize('value', ['false',1,None])
def test_feasibility_predicate_must_return_an_actual_boolean(value):
    with pytest.raises(ValidationError):
        solve_scenarios_exhaustive(2,[lambda s:1.],exact_k=1,mode='mean',feasible=lambda s:value)


def test_robust_callback_exception_is_not_infeasibility():
    def broken(_):
        raise RuntimeError('deliberate callback failure')
    with pytest.raises(RuntimeError,match='deliberate callback failure'):
        solve_scenarios_exhaustive(2,[broken],exact_k=1,mode='mean')


def test_robust_finite_valid_and_empty_domains_retain_scoped_flags():
    normal = solve_scenarios_exhaustive(3,[lambda s:float(s[0]),lambda s:float(2-s[0])],
                                       exact_k=1,mode=' CVAR ',alpha=.5)
    assert normal['best']['selected'] == [1]
    assert normal['mode'] == 'cvar' and normal['alpha'] == .5
    assert normal['submodularity_assumed'] is False
    assert normal['scalability_claimed'] is False
    assert normal['certified'] is False and normal['exact'] is False
    empty = solve_scenarios_exhaustive(2,[lambda s:1.],exact_k=1,mode='mean',feasible=lambda s:False)
    assert empty['status'] == 'INFEASIBLE' and empty['best'] is None
    assert empty['counters']['objective_calls'] == 0 and empty['rows'] == []
    zero = solve_scenarios_exhaustive(0,[lambda s:2.],exact_k=0,mode='mean')
    assert zero['best']['selected'] == [] and zero['best']['aggregate'] == 2.
