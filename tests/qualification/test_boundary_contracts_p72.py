"""P7.2 public-contract boundaries; original tests remain unmodified.

These checks exercise rejection, boundary feasibility and independently computed
outputs. Synthetic costs are test inputs and have no monetary provenance claim.
"""
from __future__ import annotations
from dataclasses import replace
from fractions import Fraction
import itertools
import math
import numpy as np
import pytest
from cdrse.errors import ValidationError, NumericalConvergenceError
from cdrse.models import VARModel, SelectionProblem, ServiceConstraints, canonical_subset
from cdrse.economics import (CostComponent, CostLedger, present_value, scalarised_decision_value,
                             empirical_cvar, aggregate_scenarios, pareto_front, supported_points)
from cdrse.certificates import AlgorithmicLayer, NumericalLayer, StatisticalLayer, EconomicLayer
from cdrse.protocols import ExperimentProtocol
from cdrse.objectives import projected_innovation_covariance, cut_weights, directed_cut, weak_coupling_bounds, dsrg_swap_witness
from cdrse.backends import ExactRationalBackend
from cdrse.algorithms.treewidth import TreeDecomposition, solve_treewidth_cut, approximate_decomposition
from cdrse.algorithms.forest import solve_forest_cut
from cdrse.algorithms.branch_bound import solve_branch_bound
from cdrse.algorithms.exhaustive import solve_exhaustive
from cdrse.algorithms.robust import solve_scenarios_exhaustive
from cdrse.algorithms.dynamic import DynamicProblem, dynamic_objective
from cdrse.exact_cut import rational, outward


def problem(**kw):
    d=dict(model=None, constraints=ServiceConstraints(exact_k=1),activation_costs=(1,2,3),
           cut_weights=np.array([[0,2,0],[1,0,3],[0,1,0]],dtype=float))
    d.update(kw)
    return SelectionProblem(**d)

@pytest.mark.parametrize('items',[(True,), (np.bool_(False),),(.5,), (0,0),(-1,),(3,)])
def test_subset_rejects_ambiguous_labels(items):
    with pytest.raises(ValidationError): canonical_subset(items,3)

@pytest.mark.parametrize('kw',[dict(exact_k=True),dict(exact_k=-1),dict(exact_k=4),dict(k_min=2,k_max=1),
    dict(k_min=0,k_max=2),dict(k_min=1,k_max=3),dict(exact_k=1,mandatory=(0,1)),
    dict(exact_k=2,forbidden=(0,1)),dict(exact_k=1,coverage_groups=((),)),
    dict(exact_k=1,coverage_groups=((0,),),forbidden=(0,)),dict(exact_k=1,budget=-1),
    dict(exact_k=1,budget=math.nan),dict(exact_k=1,mandatory=(0,),forbidden=(0,))])
def test_service_rejections(kw):
    c=ServiceConstraints(**kw)
    with pytest.raises(ValidationError): c.validate(3,(1,2,3))
    assert not c.is_feasible((1,),3,(1,2,3))

@pytest.mark.parametrize('subset,expected',[((0,),False),((1,),True),((2,),False),((0,1),True),((1,2),False), ((),False)])
def test_feasibility_matches_service_and_budget(subset,expected):
    c=ServiceConstraints(k_min=1,k_max=2,mandatory=(1,),forbidden=(2,),coverage_groups=((0,1),),budget=3)
    assert c.is_feasible(subset,3,(1,2,3)) is expected

@pytest.mark.parametrize('kw',[dict(activation_costs=(1,)),dict(activation_costs=(1,2,-1)),
    dict(activation_costs=(1,math.inf,1)),dict(cut_weights=np.zeros((3,2))),dict(cut_weights=np.eye(3)),
    dict(cut_weights=np.array([[0,math.nan,0],[0,0,0],[0,0,0]])),dict(cost_weight=-1),dict(information_weight=math.inf)])
def test_problem_rejects_invalid_units_and_shapes(kw):
    with pytest.raises(ValidationError): problem(**kw)

@pytest.mark.parametrize('coefs,cov,names',[
    ((),np.eye(2),()),((np.empty((0,0)),),np.empty((0,0)),()),
    ((np.ones((2,3)),),np.eye(2),()),((np.full((2,2),math.nan),),np.eye(2),()),
    ((np.zeros((2,2)),),np.eye(3),()),((np.zeros((2,2)),),np.full((2,2),math.inf),()),
    ((np.zeros((2,2)),),np.array([[1,1],[0,1]]),()),((np.zeros((2,2)),),np.diag([1,0]),()),
    ((np.zeros((2,2)),),np.eye(2),('one',)),((np.zeros((2,2)),),np.eye(2),('same','same')),
    ((np.eye(2),),np.eye(2),())])
def test_var_validation(coefs,cov,names):
    with pytest.raises(ValidationError): VARModel(coefs,cov,names)


def test_multilag_companion_reconstructs_recursion():
    a=np.array([[.1,.2],[0,.1]]);b=np.diag([.2,.2])
    model=VARModel((a,b),np.eye(2))
    t,g,h=model.companion()
    x=np.array([2.,3.,5.,7.]);e=np.array([.3,.4])
    np.testing.assert_allclose((t@x+g@e)[:2],a@x[:2]+b@x[2:]+e)
    np.testing.assert_allclose((t@x)[2:],x[:2]);np.testing.assert_equal(h@x,x[:2])
    assert model.p==2 and model.n==2

@pytest.mark.parametrize('kw',[dict(time_limit=-1),dict(time_limit=math.inf),dict(max_calls=True),
    dict(max_nodes=.5),dict(numerical_error=-1),dict(statistical_error=math.nan),dict(cost_error=-1),
    dict(valuation_error=math.inf),dict(decision_tolerance=-1)])
def test_search_limits_reject_invalid_contracts(kw):
    with pytest.raises(ValidationError): solve_branch_bound(problem(),**kw)

@pytest.mark.parametrize('value',[-1.,math.nan,math.inf])
def test_callback_rejects_invalid_loss(value):
    with pytest.raises(ValidationError): solve_branch_bound(problem(),lambda _:value)


def test_missing_cut_is_not_an_exact_oracle():
    p=problem(cut_weights=None)
    for call in (lambda:solve_branch_bound(p),lambda:solve_exhaustive(p),
                 lambda:solve_forest_cut(p),lambda:solve_treewidth_cut(p,TreeDecomposition(((0,1,2),),()))):
        with pytest.raises(ValidationError): call()

@pytest.mark.parametrize('bags,edges',[((),()),(((0,0),),()),(((True,1,2),),()),(((0,1,3),),()),
    (((0,1),(1,2)),((0,0),)),(((0,1),(1,2)),((0,1),(1,0))),(((0,1),(1,2)),()),
    (((0,1),),()),(((0,),(1,),(2,)),((0,1),(1,2))),
    (((0,1),(1,2),(0,2)),((0,1),(1,2)))])
def test_decomposition_rejects_missing_scope(bags,edges):
    with pytest.raises(ValidationError): TreeDecomposition(bags,edges).validate(problem().cut_weights)


def test_coverage_states_match_independent_enumeration():
    p=problem(constraints=ServiceConstraints(k_min=1,k_max=2,budget=3,coverage_groups=((0,2),(1,2))))
    vals={s:sum(Fraction(float(p.cut_weights[i,j])) for i in range(3) for j in s if i not in s)
          for k in [1,2] for s in itertools.combinations(range(3),k)
          if sum(p.activation_costs[i] for i in s)<=3 and set(s)&{0,2} and set(s)&{1,2}}
    for result in (solve_forest_cut(p),solve_treewidth_cut(p,approximate_decomposition(p.cut_weights)),solve_branch_bound(p)[0],solve_exhaustive(p)):
        assert result.selected in vals and Fraction(result.objective)==min(vals.values())

@pytest.mark.parametrize('kw',[dict(name=' '),dict(unit=''),dict(value=math.inf),dict(evidence_tier='unknown'),
    dict(uncertainty_lower=0),dict(uncertainty_upper=2),dict(uncertainty_lower=2,uncertainty_upper=3),
    dict(uncertainty_lower=0,uncertainty_upper=.5)])
def test_cost_component_requires_declared_interval_and_units(kw):
    obj=replace(CostComponent('synthetic resource',1.,'unit','E0'),**kw)
    with pytest.raises(ValidationError):obj.validate()

@pytest.mark.parametrize('factor',[0,-1,1.01,math.nan])
def test_discount_domain(factor):
    with pytest.raises(ValidationError):present_value([1.,2.],factor)


def test_discount_and_log_score_units():
    assert present_value([2.,3.],1)==5.
    with pytest.raises(ValidationError):present_value([math.inf],1)
    with pytest.raises(ValidationError):CostLedger(()).scalar_total()
    assert scalarised_decision_value(3,4,2,5)==23
    for vals in [(3,4,-1,5),(3,4,2,-1),(math.nan,4,2,5)]:
        with pytest.raises(ValidationError):scalarised_decision_value(*vals)

@pytest.mark.parametrize('values,alpha',[([],0),([1.],-1),([1.],1),([math.inf],.5)])
def test_cvar_rejects_invalid_distribution(values,alpha):
    with pytest.raises(ValidationError):empirical_cvar(values,alpha)


def test_risk_fractional_tail_and_probability_contracts():
    assert empirical_cvar([1,2,6],.5)==pytest.approx(14/3)
    assert empirical_cvar([1,2,6],0)==3
    for args in [([1,2],'mean',[1]),([1,2],'mean',[-1,2]),([1,2],'mean',[.2,.2]),([1,2],'unknown',None)]:
        with pytest.raises(ValidationError):aggregate_scenarios(*args)
    result=solve_scenarios_exhaustive(3,[lambda s:float(s[0]),lambda s:float(2-s[0])],exact_k=1,mode='worst',feasible=lambda s:s!=(0,))
    assert result['best']['selected']==[1] and result['best']['aggregate']==1
    assert not result['certified']
    empty=solve_scenarios_exhaustive(3,[lambda s:1.],exact_k=1,mode='mean',feasible=lambda s:False)
    assert empty['status']=='INFEASIBLE' and empty['best'] is None
    with pytest.raises(ValidationError):solve_scenarios_exhaustive(3,[],exact_k=1,mode='mean')
    with pytest.raises(ValidationError):solve_scenarios_exhaustive(3,[lambda s:1.],exact_k=4,mode='mean')

@pytest.mark.parametrize('obj',[AlgorithmicLayer(False,1,None,'bad'),AlgorithmicLayer(True,None,0,'bad'),
    AlgorithmicLayer(True,1,None,'bad'),AlgorithmicLayer(True,math.inf,0,'bad'),AlgorithmicLayer(True,0,1,'bad'),
    StatisticalLayer('',False,0),StatisticalLayer('x',False,-1),StatisticalLayer('x',False,1.1),
    StatisticalLayer('x',False,.05,'confirmatory'),EconomicLayer('bad',True,True),
    EconomicLayer('E0',False,True),EconomicLayer('E0',True,False)])
def test_layer_preconditions(obj):
    with pytest.raises(ValidationError):obj.validate()

@pytest.mark.parametrize('obj',[NumericalLayer('',True,True,0),NumericalLayer('x',False,True,0),
    NumericalLayer('x',True,True,-1),NumericalLayer('x',True,True,math.inf),
    NumericalLayer('x',True,True,0,0),NumericalLayer('x',True,True,0,math.inf)])
def test_numeric_layer_preconditions(obj):
    with pytest.raises(ValidationError):obj.validate(True)

@pytest.mark.parametrize('kw',[dict(protocol_id=''),dict(random_seeds=()),dict(metrics=()),dict(comparators=()),
    dict(failure_policy=''),dict(chronology=''),dict(cost_tier='unknown')])
def test_protocol_preconditions(kw):
    p=ExperimentProtocol('p',(1,),('loss',),('reference',),'keep','ordered','E0')
    with pytest.raises(ValidationError):replace(p,**kw).validate()

@pytest.mark.parametrize('tol',[0,-1,math.nan])
def test_riccati_tolerance_domain(tol):
    m=VARModel((np.zeros((2,2)),),np.eye(2))
    with pytest.raises(ValidationError):projected_innovation_covariance(m,np.array([[1.],[0.]]),tolerance=tol)


def test_riccati_dimension_and_nonconvergence():
    m=VARModel((np.array([[0.,.5],[.5,0.]]),),np.eye(2))
    with pytest.raises(ValidationError):projected_innovation_covariance(m,np.ones((3,1)))
    with pytest.raises(NumericalConvergenceError):projected_innovation_covariance(m,np.ones((2,1)),max_iterations=0)
    with pytest.raises(ValidationError):cut_weights([np.zeros((2,2)),np.zeros((3,3))])
    with pytest.raises(ValidationError):directed_cut(np.zeros((2,3)),[0])
    with pytest.raises(ValidationError):weak_coupling_bounds(m,3,1)
    dense=VARModel((np.zeros((2,2)),),np.array([[1.,.1],[.1,1.]]))
    with pytest.raises(ValidationError):weak_coupling_bounds(dense,1,1)

@pytest.mark.parametrize('a',[0,1,-1,2,math.nan])
def test_swap_domain(a):
    with pytest.raises(ValidationError):dsrg_swap_witness(a)

@pytest.mark.parametrize('value',[True,'1/2',math.inf,math.nan])
def test_stored_numeric_parser_is_explicit(value):
    with pytest.raises(ValidationError):rational(value)


def test_exact_numeric_boundaries():
    q=Fraction(1,2**1075)
    assert rational(Fraction(1,3))==Fraction(1,3)
    assert rational(np.int64(2))==2
    assert Fraction(outward(q,False))<=q<=Fraction(outward(q,True))
    with pytest.raises(ValidationError):outward(Fraction(10**400),True)
    with pytest.raises(ValidationError):ExactRationalBackend.directed_cut([[1,2],[3]],(0,))

@pytest.mark.parametrize('kw',[dict(unary_costs=np.zeros(3)),dict(spatial_weights=()),
    dict(switching_costs=np.zeros((1,3))),dict(switching_costs=np.full((1,2),-1)),
    dict(spatial_weights=(np.full((2,2),-1),np.zeros((2,2)))),dict(exact_cardinalities=(1,)),
    dict(exact_cardinalities=(1,3)),dict(mandatory_by_time=((0,),)),dict(forbidden_by_time=((0,),)),
    dict(mandatory_by_time=((0,),()),forbidden_by_time=((0,),())),dict(mandatory_by_time=((2,),()))])
def test_dynamic_shape_and_service_boundaries(kw):
    d=dict(unary_costs=np.zeros((2,2)),spatial_weights=(np.zeros((2,2)),)*2,switching_costs=np.ones((1,2)))
    d.update(kw)
    with pytest.raises(ValidationError):DynamicProblem(**d)


def test_dynamic_objective_counts_each_transition_once():
    p=DynamicProblem(np.array([[1.,2.],[3.,4.]]),(np.array([[0.,5.],[6.,0.]]),np.zeros((2,2))),np.array([[7.,8.]]))
    assert dynamic_objective(p,[(0,),(1,)])==1+6+4+7+8
    with pytest.raises(ValidationError):dynamic_objective(p,[(0,)])
