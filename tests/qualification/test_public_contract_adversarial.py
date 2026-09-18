"""Public-result consistency and non-coercing discrete inputs (P10 rework).

Expected values are computed from the rational record independently of its
producer. These tests exercise complete, interrupted, infeasible and unenclosed
outcomes; no expected objective is embedded into an implementation.
"""
from copy import deepcopy
from fractions import Fraction
import math
import pytest
from cdrse.models import SelectionProblem, ServiceConstraints
from cdrse.algorithms import solve_branch_bound, solve_forest_cut, solve_treewidth_cut, solve_exhaustive, TreeDecomposition
from cdrse.verification import verify_solver_payload, verify_result
from cdrse.errors import ValidationError


def problem(*, budget=None):
    return SelectionProblem(None, ServiceConstraints(exact_k=1, budget=budget), (1, 1), [[0, 0], [1, 0]])


def outcome(kind):
    p = problem(budget=0 if kind == 'infeasible' else None)
    if kind == 'exact': r = solve_branch_bound(p)[0]
    elif kind == 'forest': r = solve_forest_cut(p)
    elif kind == 'treewidth': r = solve_treewidth_cut(p, TreeDecomposition(((0, 1),), ()))
    elif kind == 'partial': r = solve_branch_bound(p, max_nodes=0)[0]
    elif kind == 'no_incumbent': r = solve_branch_bound(p, max_calls=0)[0]
    elif kind == 'infeasible': r = solve_forest_cut(p)
    elif kind == 'callback': r = solve_exhaustive(p, lambda s: float(s[0]))
    elif kind == 'callback_partial': r = solve_branch_bound(p, lambda s: float(s[0]), max_nodes=0)[0]
    elif kind == 'callback_absent': r = solve_branch_bound(p, lambda s: float(s[0]), max_calls=0)[0]
    elif kind == 'callback_infeasible':
        p = problem(budget=0); r = solve_exhaustive(p, lambda s: float(s[0]))
    else: raise AssertionError(kind)
    return p, r

STATES = ('exact', 'forest', 'treewidth', 'partial', 'no_incumbent', 'infeasible', 'callback', 'callback_partial', 'callback_absent', 'callback_infeasible')

@pytest.mark.parametrize('kind', STATES)
def test_all_producer_states_have_consistent_public_contract(kind):
    p, r = outcome(kind)
    v = verify_solver_payload(p, r.to_dict())
    assert v['certificate_verified'] is (kind not in {'no_incumbent','callback','callback_partial','callback_absent'})

@pytest.mark.parametrize('kind', ('exact','partial','no_incumbent','infeasible'))
@pytest.mark.parametrize('field', ('selected','objective','exact','certified','status','termination_reason','lower_bound','upper_bound','optimality_gap','counters'))
def test_required_public_field_cannot_be_omitted(kind, field):
    p, r = outcome(kind); x = deepcopy(r.to_dict()); del x[field]
    with pytest.raises(ValidationError): verify_solver_payload(p, x)

@pytest.mark.parametrize('kind', STATES)
@pytest.mark.parametrize('field', ('lower_bound','upper_bound','optimality_gap','objective'))
def test_public_numerical_field_cannot_be_forged(kind, field):
    p, r = outcome(kind); x = deepcopy(r.to_dict())
    x[field] = -999 if x[field] is None else x[field] + 1
    with pytest.raises(ValidationError): verify_solver_payload(p, x)

@pytest.mark.parametrize('kind', STATES)
@pytest.mark.parametrize('field,bad', (('exact',1),('certified',0),('status','UNSUPPORTED'),('termination_reason','INVALID_INPUT')))
def test_assurance_types_and_state_are_checked(kind, field, bad):
    p, r = outcome(kind); x = deepcopy(r.to_dict()); x[field] = bad
    with pytest.raises(ValidationError): verify_solver_payload(p, x)

@pytest.mark.parametrize('field', ('objective_calls','nodes_expanded'))
@pytest.mark.parametrize('kind', ('exact','partial','no_incumbent','infeasible','callback'))
def test_mirrored_counter_must_match_record(kind, field):
    p, r = outcome(kind); x = deepcopy(r.to_dict()); x['counters'][field] += 1
    with pytest.raises(ValidationError): verify_solver_payload(p, x)

@pytest.mark.parametrize('bad', (True, -1, 1.5, '1'))
def test_other_counter_has_strict_nonnegative_integer_type(bad):
    p,r=outcome('exact');x=deepcopy(r.to_dict());x['counters']['iterations']=bad
    with pytest.raises(ValidationError):verify_solver_payload(p,x)

@pytest.mark.parametrize('field', ('exact_k','k_min','k_max'))
@pytest.mark.parametrize('bad', (1.9, True, '1', 1.0))
def test_cardinality_parser_never_coerces(field, bad):
    d=problem().to_dict();d['constraints'].update(exact_k=None,k_min=0,k_max=2,exclude_empty=False,exclude_full=False);d['constraints'][field]=bad
    with pytest.raises(ValidationError):SelectionProblem.from_dict(d)

@pytest.mark.parametrize('field', ('exclude_empty','exclude_full'))
@pytest.mark.parametrize('bad', (0,1,'false','true',None,[],{}))
def test_endpoint_policy_requires_boolean(field,bad):
    d=problem().to_dict();d['constraints'][field]=bad
    with pytest.raises(ValidationError):SelectionProblem.from_dict(d)

@pytest.mark.parametrize('field', ('exclude_empty','exclude_full'))
@pytest.mark.parametrize('bad', (0,1,'false',None))
def test_direct_constraint_construction_has_same_boolean_contract(field,bad):
    with pytest.raises(ValidationError):
        SelectionProblem(None,ServiceConstraints(exact_k=1,**{field:bad}),(1,1),[[0,0],[1,0]])

@pytest.mark.parametrize('field',('mandatory','forbidden'))
@pytest.mark.parametrize('bad',(True,1.0,'1'))
def test_coordinate_ids_remain_noncoercing(field,bad):
    d=problem().to_dict();d['constraints'][field]=[bad]
    with pytest.raises(ValidationError):SelectionProblem.from_dict(d)


def _unpack(v):return Fraction(int(v['numerator']),int(v['denominator']))

def upward(v):
    f=float(v)
    return math.nextafter(f,math.inf) if Fraction(f)<v else f

@pytest.mark.parametrize('a,b',((0.1,0.3),(0.7,0.9),(1.0,2**-42),(0.3,0.2),(0.9,0.9)))
def test_gap_rounds_from_rational_record_outwards(a,b):
    p=SelectionProblem(None,ServiceConstraints(exact_k=1),(1,1),[[0,0],[a,0]],b,0)
    r=solve_branch_bound(p,max_nodes=0)[0];d=r.to_dict();g=_unpack(d['metadata']['result_contract']['regret_upper_bound'])
    assert d['optimality_gap']==upward(g)
    assert Fraction(d['optimality_gap'])>=g
    assert verify_solver_payload(p,d)['certificate_verified']
    if g>0:
        d['optimality_gap']=math.nextafter(upward(g),-math.inf)
        with pytest.raises(ValidationError):verify_solver_payload(p,d)

@pytest.mark.parametrize('kind',('no_incumbent','infeasible'))
def test_no_selection_means_no_objective_fields(kind):
    p,r=outcome(kind);d=r.to_dict();rec=d['metadata']['result_contract']
    for key in ('selected','objective','upper_bound','optimality_gap'):assert d[key] is None
    for key in ('selected','objective_estimate','incumbent_upper_bound','regret_upper_bound','objective_interval'):assert rec[key] is None
    if kind=='infeasible':assert d['termination_reason']==rec['termination_reason']=='PROVED_INFEASIBLE'
    else:assert d['termination_reason']==rec['termination_reason']=='CALL_BUDGET'
    assert verify_solver_payload(p,d)['certificate_verified'] is (kind=='infeasible')


def test_unknown_public_assertion_is_refused():
    p,r=outcome('partial');d=r.to_dict();d['population_certified']=True
    with pytest.raises(ValidationError):verify_solver_payload(p,d)


def test_status_cannot_upgrade_an_interrupted_result():
    p,r=outcome('partial');d=r.to_dict();d['status']='OPTIMAL';d['termination_reason']='COMPLETE'
    with pytest.raises(ValidationError):verify_solver_payload(p,d)


def test_raw_no_incumbent_cannot_claim_completion():
    p,r=outcome('no_incumbent');d=deepcopy(r.to_record());d['termination_reason']='COMPLETE'
    with pytest.raises(ValidationError):verify_result(p,d)


def test_counter_type_rejected_in_raw_record():
    p,r=outcome('exact');d=deepcopy(r.to_record());d['oracle_calls']=1.0
    with pytest.raises(ValidationError):verify_result(p,d)


def test_raw_callback_needs_a_concrete_canonical_selection():
    p,r=outcome('callback');d=deepcopy(r.to_record());d['selected']=None
    with pytest.raises(ValidationError):verify_result(p,d)

@pytest.mark.parametrize('bad',(True,'0',float('inf'),float('nan')))
def test_public_display_scalar_types_are_strict(bad):
    p,r=outcome('exact');d=deepcopy(r.to_dict());d['optimality_gap']=bad
    with pytest.raises(ValidationError):verify_solver_payload(p,d)
