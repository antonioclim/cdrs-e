"""Regression obligations on the unchanged candidate; failures must remain visible."""
from fractions import Fraction
from itertools import combinations
import numpy as np
import pytest
from cdrse import VARModel,SelectionProblem,ServiceConstraints,projected_dd
from cdrse.algorithms.branch_bound import solve_branch_bound
from cdrse.algorithms.forest import solve_forest_cut
from cdrse.algorithms.treewidth import solve_treewidth_cut,TreeDecomposition
from cdrse.errors import ValidationError

def cut_exact(W,S):
 S=set(S);return sum((Fraction.from_float(float(W[j,i])) for i in S for j in range(len(W)) if j not in S),Fraction(0))

def tiny_problem():
 d=2.**-42;W=np.array([[0,d,d],[d,0,0],[0,0,0]])
 return SelectionProblem(None,ServiceConstraints(k_min=1,k_max=2,budget=3),(1,1,1),W)

def test_branch_bound_tiny_exact_bound():
 p=tiny_problem();r,c=solve_branch_bound(p,lambda S:float(cut_exact(p.cut_weights,S)))
 optimum=min(cut_exact(p.cut_weights,S) for k in [1,2] for S in combinations(range(3),k))
 assert Fraction.from_float(r.lower_bound)<=optimum<=Fraction.from_float(r.upper_bound), 'Exact bound excludes exact optimum'

@pytest.mark.parametrize('solver',['forest','treewidth'])
def test_tiny_incumbent_upper_bound(solver):
 p=tiny_problem();r=solve_forest_cut(p) if solver=='forest' else solve_treewidth_cut(p,TreeDecomposition(((0,1,2),),()))
 assert Fraction.from_float(r.upper_bound)>=cut_exact(p.cut_weights,r.selected), 'Incumbent upper bound below exact selected objective'

@pytest.mark.parametrize('solver',['forest','treewidth'])
def test_weighted_bound_inherited_F01(solver):
 p=SelectionProblem(None,ServiceConstraints(exact_k=1,budget=11),(1,10),np.array([[0.,0.],[1.,0.]]),1,1)
 r=solve_forest_cut(p) if solver=='forest' else solve_treewidth_cut(p,TreeDecomposition(((0,1),),()))
 assert r.lower_bound<=2<=r.upper_bound, 'Weighted optimum is 2'

@pytest.mark.parametrize('q',[np.zeros((2,1)),np.array([[1.,1.],[0.,0.]]),np.ones((2,3))],ids=['zero','dependent','excess_columns'])
def test_invalid_subspace_rejected(q):
 model=VARModel((np.array([[0.,.5],[.5,0.]]),),np.eye(2))
 with pytest.raises(ValidationError):projected_dd(model,q)
