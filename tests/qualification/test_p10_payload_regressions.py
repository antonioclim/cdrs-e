"""Expected rejection of contradictory user-visible fields, outside the original suite."""
from copy import deepcopy
import pytest
from cdrse.models import SelectionProblem, ServiceConstraints
from cdrse.algorithms.branch_bound import solve_branch_bound
from cdrse.verification import verify_solver_payload
from cdrse.errors import ValidationError

def fixture_problem():
    return SelectionProblem(model=None, cut_weights=[[0,0],[1,0]], activation_costs=(1,1),
        constraints=ServiceConstraints(exact_k=1), information_weight=1, cost_weight=0)

@pytest.mark.parametrize('changes,limit',[
    ({'optimality_gap':0},'partial'),
    ({'optimality_gap':-1},'partial'),
    ({'status':'OPTIMAL','termination_reason':'COMPLETE'},'partial'),
    ({'upper_bound':-999,'optimality_gap':0},'absent'),
])
def test_contradictory_display_is_rejected(changes,limit):
    p=fixture_problem()
    result,_=solve_branch_bound(p,**({'max_nodes':0} if limit=='partial' else {'max_calls':0}))
    payload=deepcopy(result.to_dict());payload.update(changes)
    with pytest.raises(ValidationError): verify_solver_payload(p,payload)

@pytest.mark.parametrize('limit',['partial','complete','absent'])
def test_unmodified_payload_is_accepted_with_correct_scope(limit):
    p=fixture_problem()
    opts={'max_nodes':0} if limit=='partial' else {'max_calls':0} if limit=='absent' else {}
    r,_=solve_branch_bound(p,**opts)
    verdict=verify_solver_payload(p,r.to_dict())
    assert verdict['certificate_verified']==(limit!='absent')
