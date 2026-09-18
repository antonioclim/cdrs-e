"""Frozen SD1 obligations on compositional arithmetic and representation.

Synthetic E0 operands only. These checks do not certify an objective, a population,
an economic valuation or execution history. The original tests are not edited.
"""
from __future__ import annotations
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
import copy
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

import pytest

from cdrse.certificates import (
    AlgorithmicLayer, DecisionCertificate, NumericalLayer,
    StatisticalLayer, EconomicLayer,
)
from cdrse.errors import ValidationError


def base() -> DecisionCertificate:
    return DecisionCertificate(
        problem_sha256='a'*64, selected=(0,),
        algorithmic=AlgorithmicLayer(True, 1.0, 0.0, 'COMPLETE', False),
        numerical=NumericalLayer('float64', True, True, 0.0),
        statistical=StatisticalLayer('synthetic SD1 operand', False, 1.0, 'none'),
        economic=EconomicLayer('E0', True, True), tolerance=1.0,
    )


def raw(c: DecisionCertificate | None = None) -> dict:
    d = (base() if c is None else c).to_dict()
    for name in ('discrepancy', 'regret_upper', 'non_vacuous'):
        d.pop(name, None)
    return d


def exact_terms(c: DecisionCertificate) -> tuple[Fraction, Fraction]:
    d = sum((Fraction(v) for v in (c.numerical_error, c.statistical_error,
                                  c.cost_error, c.valuation_error)), Fraction())
    b = Fraction(c.algorithmic.incumbent_upper) - Fraction(c.algorithmic.optimum_lower) + 2*d
    return d, b


def assert_minimal_upper(shown: float, expected: Fraction) -> None:
    assert math.isfinite(shown)
    assert Fraction(shown) >= expected, 'upper endpoint rounds below the exact operand expression'
    previous = math.nextafter(shown, -math.inf)
    if math.isfinite(previous):
        assert Fraction(previous) < expected, 'endpoint is not the least representable upper endpoint'


ERROR_FIELDS = ('numerical_error', 'statistical_error', 'cost_error', 'valuation_error')


@pytest.mark.parametrize('field', ERROR_FIELDS)
@pytest.mark.parametrize('exponent', [-1000, -900, -100, -2, 0, 40, 900, 1022])
def test_half_ulp_threshold_never_false_positive(field: str, exponent: int) -> None:
    u = math.ldexp(1.0, exponent)
    e = math.ldexp(1.0, exponent-54)
    c = replace(base(), algorithmic=replace(base().algorithmic, incumbent_upper=u),
                tolerance=u, **{field:e})
    d, b = exact_terms(c)
    assert b > Fraction(u)
    assert_minimal_upper(c.discrepancy, d)
    assert_minimal_upper(c.regret_upper, b)
    assert c.non_vacuous is False


@pytest.mark.parametrize('exponent', [-1000, -100, 0, 100, 1022])
def test_subtraction_rounddown_is_enclosed(exponent: int) -> None:
    u = math.ldexp(1.0, exponent)
    c = replace(base(), algorithmic=replace(base().algorithmic,
        incumbent_upper=u, optimum_lower=-math.ldexp(1.0, exponent-54)), tolerance=u)
    assert_minimal_upper(c.regret_upper, exact_terms(c)[1])
    assert c.non_vacuous is False


def test_four_component_sum_is_not_sequentially_rounded() -> None:
    c = replace(base(), numerical_error=1.0, statistical_error=2**-53, cost_error=2**-53)
    d, b = exact_terms(c)
    assert_minimal_upper(c.discrepancy, d)
    assert_minimal_upper(c.regret_upper, b)


@pytest.mark.parametrize('index', range(128))
def test_generated_finite_operands_against_fraction_and_decimal(index: int) -> None:
    rng = random.Random(202609150000 + index)
    u = math.ldexp(1.0 + rng.random(), rng.randint(-1000, 950))
    lo = -math.ldexp(1.0 + rng.random(), rng.randint(-1000, 950))
    errors = [math.ldexp(1.0+rng.random(), rng.randint(-1000, 950)) for _ in range(4)]
    c = replace(base(), algorithmic=replace(base().algorithmic, incumbent_upper=u, optimum_lower=lo),
                tolerance=u, **dict(zip(ERROR_FIELDS, errors)))
    d, b = exact_terms(c)
    assert_minimal_upper(c.discrepancy, d)
    assert_minimal_upper(c.regret_upper, b)
    # A second calculation does not call the implementation or use Fraction.
    # 2500 digits exceed the exact decimal length needed for these binary64 inputs.
    with localcontext() as ctx:
        ctx.prec = 2500
        dd = sum((Decimal.from_float(v) for v in errors), Decimal(0))
        db = Decimal.from_float(u) - Decimal.from_float(lo) + 2*dd
        assert Decimal.from_float(c.discrepancy) >= dd
        assert Decimal.from_float(c.regret_upper) >= db
        assert Decimal.from_float(math.nextafter(c.regret_upper, -math.inf)) < db
    assert c.non_vacuous is False


@pytest.mark.parametrize('kwargs', [
    {'numerical_error':1e308},
    {'numerical_error':1e308, 'cost_error':1e308},
    {'algorithmic':AlgorithmicLayer(True, 1e308, -1e308, 'COMPLETE', False)},
])
def test_aggregate_overflow_is_a_validation_error(kwargs: dict) -> None:
    c = replace(base(), **kwargs)
    with pytest.raises(ValidationError):
        c.validate()


def test_smallest_subnormal_and_exact_zero() -> None:
    z = replace(base(), algorithmic=replace(base().algorithmic, incumbent_upper=0.0),
                tolerance=0.0)
    assert z.discrepancy == z.regret_upper == 0.0
    assert z.non_vacuous is True
    c = replace(z, numerical_error=math.ulp(0.0))
    assert c.regret_upper == 2*math.ulp(0.0)
    assert c.non_vacuous is False


def test_large_integer_operands_are_not_first_cast_to_float() -> None:
    c = replace(base(), algorithmic=replace(base().algorithmic,
        incumbent_upper=2**53+1, optimum_lower=2**53))
    assert c.regret_upper == 1.0
    assert c.non_vacuous is True


BOOL_FIELDS = [('algorithmic','feasible'), ('algorithmic','exact_oracle'),
               ('numerical','finite'), ('numerical','enclosed'),
               ('statistical','simultaneous_coverage'), ('economic','units_declared'),
               ('economic','valuation_nonnegative')]


@pytest.mark.parametrize('layer,field', BOOL_FIELDS)
@pytest.mark.parametrize('value', ['false', 0, 1, None])
def test_layer_flags_require_actual_booleans(layer: str, field: str, value) -> None:
    c = base()
    c = replace(c, **{layer:replace(getattr(c, layer), **{field:value})})
    with pytest.raises(ValidationError):
        c.validate()


@pytest.mark.parametrize('indices', [[0.75],[-1],[True],[1.0],['1'],[0,0]])
@pytest.mark.parametrize('route', ['constructor','from_dict'])
def test_selected_coordinates_are_not_coerced(indices, route: str) -> None:
    with pytest.raises(ValidationError):
        if route == 'constructor':
            replace(base(), selected=tuple(indices)).validate()
        else:
            d=raw();d['selected']=indices
            DecisionCertificate.from_dict(d).validate()


NUMBER_FIELDS=[('algorithmic','incumbent_upper'),('algorithmic','optimum_lower'),
 ('numerical','tolerance'),('numerical','condition_number'),('statistical','failure_probability'),
 (None,'numerical_error'),(None,'statistical_error'),(None,'cost_error'),(None,'valuation_error'),(None,'tolerance')]


@pytest.mark.parametrize('layer,field', NUMBER_FIELDS)
@pytest.mark.parametrize('value', [float('nan'),float('inf'),True,'0.0'])
def test_numeric_domain_refusal_is_controlled(layer, field: str, value) -> None:
    c=base()
    if layer:
        c=replace(c,**{layer:replace(getattr(c,layer),**{field:value})})
    else:
        c=replace(c,**{field:value})
    with pytest.raises(ValidationError):
        c.validate()


@pytest.mark.parametrize('field', ERROR_FIELDS+('tolerance',))
def test_negative_error_and_tolerance_refused(field: str) -> None:
    with pytest.raises(ValidationError):
        replace(base(),**{field:-math.ulp(0.0)}).validate()


@pytest.mark.parametrize('field,value', [('discrepancy',0.0),('regret_upper',0.0),('non_vacuous',True)])
def test_supplied_derived_assertions_are_checked(field: str,value) -> None:
    c=replace(base(),numerical_error=0.125,tolerance=0.5)
    d=c.to_dict();d[field]=value
    with pytest.raises(ValidationError):
        DecisionCertificate.from_dict(d).validate()


@pytest.mark.parametrize('kind', ['string_oracle','unknown_status','unknown_field','unknown_version',
                                  'string_notes','false_with_selected','missing_layer'])
def test_serialised_layer_boundary(kind: str) -> None:
    d=raw()
    if kind=='string_oracle':
        d['algorithmic']['exact_oracle']='false';d['numerical']['enclosed']=False
    elif kind=='unknown_status':d['statistical']['status']='proved'
    elif kind=='unknown_field':d['population_guarantee']=True
    elif kind=='unknown_version':d['schema_version']='unrecognised'
    elif kind=='string_notes':d['notes']='not an array'
    elif kind=='false_with_selected':
        d['algorithmic'].update(feasible=False,incumbent_upper=None,optimum_lower=None)
    else:d.pop('economic')
    with pytest.raises(ValidationError):
        DecisionCertificate.from_dict(d).validate()


@pytest.mark.parametrize('mutate', ['none','exact_assertion','no_incumbent','no_tolerance','negative_lower','empty_subset'])
def test_valid_controls_and_roundtrip(mutate: str) -> None:
    c=base()
    if mutate=='exact_assertion':
        c=replace(c,algorithmic=replace(c.algorithmic,exact_oracle=True),numerical=replace(c.numerical,enclosed=False))
    elif mutate=='no_incumbent':
        c=replace(c,selected=None,algorithmic=replace(c.algorithmic,feasible=False,incumbent_upper=None))
    elif mutate=='no_tolerance':c=replace(c,tolerance=None)
    elif mutate=='negative_lower':c=replace(c,algorithmic=replace(c.algorithmic,optimum_lower=-1.0))
    elif mutate=='empty_subset':c=replace(c,selected=())
    c.validate()
    d=c.to_dict()
    assert DecisionCertificate.from_dict(d).to_dict()==d
    json.dumps(d,allow_nan=False)


@pytest.mark.parametrize('kind', ['rounding','stale_rounding_summary','forged_summary',
                                  'no_incumbent_with_selected','valid','no_incumbent','oracle_string','overflow'])
def test_cli_boundary(kind: str,tmp_path: Path) -> None:
    d=raw()
    expected_rc=0
    if kind in {'rounding','stale_rounding_summary'}:
        d['numerical_error']=2**-54
        if kind=='stale_rounding_summary':
            d.update(discrepancy=2**-54,regret_upper=1.0,non_vacuous=True);expected_rc=2
    elif kind=='forged_summary':d.update(regret_upper=0.0);expected_rc=2
    elif kind=='no_incumbent_with_selected':
        d['algorithmic'].update(feasible=False,incumbent_upper=None);expected_rc=2
    elif kind=='no_incumbent':
        d['algorithmic'].update(feasible=False,incumbent_upper=None);d['selected']=None
    elif kind=='oracle_string':
        d['algorithmic']['exact_oracle']='false';expected_rc=2
    elif kind=='overflow':d['numerical_error']=1e308;expected_rc=2
    p=tmp_path/(kind+'.json');p.write_text(json.dumps(d,allow_nan=False),encoding='utf-8')
    q=subprocess.run([sys.executable,'-B','-m','cdrse','verify-certificate',str(p)],
                     text=True,capture_output=True,timeout=15,env=os.environ.copy())
    assert q.returncode==expected_rc,(q.stdout,q.stderr)
    result=json.loads(q.stdout if q.returncode==0 else q.stderr)
    if expected_rc==0:
        assert result['certificate_verified'] is False
        assert result['scope']=='legacy layer consistency only; no problem or objective replay'
        if kind=='rounding':
            assert result['regret_upper']==math.nextafter(1.0,math.inf)
            assert result['non_vacuous'] is False
    else:
        assert result['status']=='FAIL'
        assert 'Traceback' not in q.stderr
