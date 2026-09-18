"""Post-audit contract tests. The protected P3 regressions remain unchanged."""
from copy import deepcopy
from fractions import Fraction
import json
import math
import numpy as np
import pytest
from cdrse.algorithms import solve_forest_cut, solve_treewidth_cut, solve_branch_bound, TreeDecomposition
from cdrse.algorithms.exhaustive import solve_exhaustive
from cdrse.algorithms.robust import solve_scenarios_exhaustive
from cdrse.algorithms.dynamic import DynamicProblem, solve_time_expanded_mincut
from cdrse.errors import ValidationError
from cdrse.models import SelectionProblem, ServiceConstraints
from cdrse.objectives import orthonormalise
from cdrse.exact_cut import rational, outward
from cdrse.verification import verify_result
from cdrse import cli


def problem(**kw):
    base = dict(model=None, constraints=ServiceConstraints(exact_k=1, budget=11),
                activation_costs=(1, 10), cut_weights=np.array([[0.,0.],[1.,0.]]), information_weight=1, cost_weight=1)
    base.update(kw)
    return SelectionProblem(**base)


def run(kind, p):
    if kind == 'forest': return solve_forest_cut(p)
    if kind == 'treewidth': return solve_treewidth_cut(p, TreeDecomposition((tuple(range(p.n)),), ()))
    if kind == 'bnb': return solve_branch_bound(p)[0]
    return solve_exhaustive(p)


@pytest.mark.parametrize('kind',['forest','treewidth','bnb','exhaustive'])
@pytest.mark.parametrize('alpha,beta', [(1,1),(1,0),(0,1),(0,0)])
def test_exact_positive_scalar_controls(kind, alpha, beta):
    p=problem(information_weight=alpha,cost_weight=beta)
    r=run(kind,p)
    assert r.certified and r.exact
    v=verify_result(p,r.to_record())
    assert v['certificate_verified']
    expected=min(alpha+beta,10*beta)
    assert r.objective==expected
    assert r.to_record()['regret_upper_bound']=={'numerator':'0','denominator':'1'}


@pytest.mark.parametrize('kind',['forest','treewidth','bnb','exhaustive'])
@pytest.mark.parametrize('scale',[2.**-60,2.**-42,1.,2.**20])
def test_small_arcs_with_exact_replay(kind,scale):
    p=problem(constraints=ServiceConstraints(k_min=1,k_max=2,budget=3),activation_costs=(1,1,1),
      cut_weights=np.array([[0,scale,scale],[scale,0,0],[0,0,0]]),cost_weight=0)
    r=run(kind,p)
    assert r.objective==0 and r.exact
    assert verify_result(p,r.to_record())['certificate_verified']


@pytest.mark.parametrize('mode',['max_calls','max_nodes'])
@pytest.mark.parametrize('budget',[0,1,10])
def test_interruptions_keep_truthful_bounds(mode,budget):
    p=problem(constraints=ServiceConstraints(exact_k=2,budget=6),activation_costs=(1,2,3,1),
      cut_weights=np.array([[0,2,0,1],[1,0,3,0],[2,0,0,1],[0,4,0,0]]))
    r,c=solve_branch_bound(p,**{mode:budget})
    count=r.counters.objective_calls if mode=='max_calls' else r.counters.nodes_expanded
    assert count<=budget
    observed=verify_result(p,r.to_record())
    assert observed['status'] in {'PASS','NO_INCUMBENT'}
    if mode=='max_calls' and budget==0:
        assert r.selected is None and r.upper_bound is None and c is None


def test_cooperative_time_zero_and_bad_budgets():
    p=problem()
    r,_=solve_branch_bound(p,time_limit=0)
    assert r.selected is None and r.counters.objective_calls==0
    for kwargs in ({'max_calls':-1},{'max_nodes':1.5},{'time_limit':-1},{'numerical_error':float('nan')}):
        with pytest.raises(ValidationError):solve_branch_bound(p,**kwargs)


def test_initialisation_no_longer_scans_combinations():
    p=SelectionProblem(None,ServiceConstraints(exact_k=6,budget=12),tuple([1]*12),np.zeros((12,12)))
    calls=[]
    r,c=solve_branch_bound(p,lambda s:calls.append(s) or 1.,max_nodes=0)
    assert len(calls)==r.counters.objective_calls==1
    assert c is None and not r.certified


def test_callback_cannot_self_certify_even_with_zero_declared_error():
    p=problem()
    for r,c in (solve_branch_bound(p,lambda s:1.),(solve_exhaustive(p,lambda s:1.),None)):
        assert not r.exact and not r.certified and c is None
        record=r.to_record()
        assert record['proof_status']=='UNCERTIFIED_EVALUATION'
        assert record['incumbent_upper_bound'] is None and record['global_lower_bound'] is None
        assert not verify_result(p,record)['certificate_verified']
    # Untrusted lower-bound callback cannot prune the real optimum.
    exact,_=solve_branch_bound(p,information_lower_bound=lambda *_:10**6)
    assert exact.objective==2


@pytest.mark.parametrize('case',['lower','upper','regret','hash','selected','arithmetic','display','example','statistical','exact'])
def test_semantic_forgery_rejected(case):
    p=problem(); rec=solve_forest_cut(p).to_record(); bad=deepcopy(rec)
    updates={
      'lower':('global_lower_bound',{'numerator':'100','denominator':'1'}),
      'upper':('incumbent_upper_bound',{'numerator':'0','denominator':'1'}),
      'regret':('regret_upper_bound',{'numerator':'-1','denominator':'1'}),
      'hash':('feasible_family_sha256','0'*64), 'selected':('selected',[0,1]),
      'arithmetic':('arithmetic_contract','VALIDATED_NUMERICAL_INTERVAL'),
      'display':('objective_estimate','10'), 'example':('record_kind','INTERFACE_EXAMPLE_NOT_OBSERVED_RUN'),
      'statistical':('statistical_event',{'description':'unsupported','failure_probability':0,'simultaneous_scope':'all'}),
      'exact':('global_lower_bound',{'numerator':'1','denominator':'1'})}
    k,v=updates[case];bad[k]=v
    with pytest.raises(ValidationError):verify_result(p,bad)


@pytest.mark.parametrize('kind',['forest','treewidth','bnb','exhaustive'])
def test_feasibility_no_budget_and_zero_budget(kind):
    p=problem(constraints=ServiceConstraints(exact_k=1,budget=0))
    r=run(kind,p)
    assert r.status=='INFEASIBLE' and r.selected is None
    assert verify_result(p,r.to_record())['status']=='PASS'
    p=problem(constraints=ServiceConstraints(exact_k=1,budget=None))
    assert run(kind,p).objective==2


@pytest.mark.parametrize('shape',[np.zeros((2,1)),np.ones((2,3)),np.ones((2,2)),np.array([[np.inf],[1.]])])
def test_invalid_projection_rejected(shape):
    with pytest.raises(ValidationError):orthonormalise(shape)


def test_projection_scale_and_near_rank_threshold():
    q=np.array([[1.,0.],[0.,1.],[1.,1.]])
    base=orthonormalise(q)
    for scale in [1e-100,1e100]:
        scaled=orthonormalise(q*scale)
        assert np.allclose(scaled@scaled.T,base@base.T,atol=1e-13)
    with pytest.raises(ValidationError):orthonormalise(np.array([[1.,1.],[0.,1e-18]]))


def test_strict_domains_and_dyadic_outward_bounds():
    for kw in ({'cut_weights':np.array([[0.,-2.**-60],[0.,0.]])}, {'information_weight':float('nan')},
               {'cut_weights':np.array([1,2])}):
        with pytest.raises(ValidationError):problem(**kw)
    for r in [Fraction(1,10),Fraction(1,3),Fraction(1,2**1075),Fraction(-1,3)]:
        assert Fraction(outward(r,-1))<=r<=Fraction(outward(r,1))
    assert rational(0.1)!=Fraction('0.1')
    with pytest.raises(ValidationError):rational(float('nan'))
    for k in [0.5,True]:
        with pytest.raises(ValidationError):problem(constraints=ServiceConstraints(exact_k=k))


def test_nonintegral_resource_rejected_and_tiny_cycle_retained():
    for f in (solve_forest_cut,lambda p:solve_treewidth_cut(p,TreeDecomposition(((0,1),),()))):
        with pytest.raises(ValidationError):f(problem(activation_costs=(1.+2.**-42,10)))
    p=problem(constraints=ServiceConstraints(exact_k=1,budget=3),activation_costs=(1,1,1),
              cut_weights=np.array([[0,1,0],[0,0,1],[2.**-60,0,0]]))
    with pytest.raises(ValidationError):solve_forest_cut(p)
    with pytest.raises(ValidationError):solve_treewidth_cut(p,TreeDecomposition(((0,1),(1,2)),((0,1),)))


def test_cli_output_both_placements_and_semantic_verification(tmp_path,capsys):
    p=problem(); src=tmp_path/'problem.json'; dst=tmp_path/'result.json'
    src.write_text(json.dumps(p.to_dict()))
    assert cli.main(['solve-forest',str(src),'--output',str(dst)])==0
    assert cli.main(['verify-result',str(src),str(dst)])==0
    assert json.loads(capsys.readouterr().out)['certificate_verified']
    assert cli.main(['--output',str(dst),'solve-bnb',str(src)])==0
    data=json.loads(dst.read_text());data['metadata']['result_contract']['objective_estimate']='123'
    dst.write_text(json.dumps(data))
    assert cli.main(['verify-result',str(src),str(dst)])==2


def test_unqualified_numeric_search_not_labelled_exact():
    r=solve_scenarios_exhaustive(3,[lambda s:.1*len(s)],exact_k=1,mode='mean')
    assert r['exact'] is False and r['certified'] is False
    d=DynamicProblem(np.zeros((1,2)),(np.zeros((2,2)),),np.zeros((0,2)))
    r=solve_time_expanded_mincut(d)
    assert r['exact'] is False and r['certified'] is False


def test_cli_rejects_forged_legacy_display_fields(tmp_path,capsys):
    p=problem();src=tmp_path/'problem.json';dst=tmp_path/'result.json';src.write_text(json.dumps(p.to_dict()))
    r=solve_forest_cut(p).to_dict();dst.write_text(json.dumps(r))
    assert cli.main(['verify-result',str(src),str(dst)])==0
    capsys.readouterr()
    r['objective']=1000;dst.write_text(json.dumps(r))
    assert cli.main(['verify-result',str(src),str(dst)])==2
    r=solve_forest_cut(p).to_dict();r['exact']=False;dst.write_text(json.dumps(r))
    assert cli.main(['verify-result',str(src),str(dst)])==2
