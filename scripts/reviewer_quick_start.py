#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, subprocess, sys, time
from pathlib import Path
import numpy as np
from cdrse import __version__
from cdrse.algorithms import CANONICAL_WITNESS_POLICY, TreeDecomposition, solve_branch_bound, solve_exhaustive, solve_forest_cut, solve_treewidth_cut
from cdrse.errors import ValidationError
from cdrse.models import SelectionProblem, ServiceConstraints

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=Path('reviewer_quick_start_results.json')); ap.add_argument('--run-claim-tests',action='store_true'); a=ap.parse_args(); t=time.perf_counter(); checks=[]
    p=SelectionProblem(None,ServiceConstraints(exact_k=1),(1.0,0.0),np.zeros((2,2)),1.0,0.0); d=TreeDecomposition(((0,),(1,)),((0,1),)); b,c=solve_branch_bound(p)
    rs={'exhaustive':solve_exhaustive(p),'forest':solve_forest_cut(p),'treewidth':solve_treewidth_cut(p,d),'branch_bound':b}
    ok=all(x.selected==(0,) for x in rs.values()); checks.append({'id':'DEMO-CANONICAL-WITNESS','status':'PASS' if ok else 'FAIL','observed':{k:list(v.selected or ()) for k,v in rs.items()},'policy':CANONICAL_WITNESS_POLICY})
    checks.append({'id':'DEMO-EXACT-CERTIFICATE','status':'PASS' if c is not None and c.selected==(0,) else 'FAIL','scope':'exact stored weighted incoming-cut objective only'})
    cp=SelectionProblem(None,ServiceConstraints(exact_k=1),(0.0,0.0)); cr,cc=solve_branch_bound(cp,lambda s:float(sum(s))); checks.append({'id':'DEMO-CALLBACK-NONCERTIFICATION','status':'PASS' if cc is None and not cr.exact and not cr.certified else 'FAIL'})
    bad=SelectionProblem(None,ServiceConstraints(exact_k=1),(0,0,0),np.array([[0,1,0],[0,0,1],[1,0,0]],float)); rejected=False; msg=None
    try: solve_forest_cut(bad)
    except ValidationError as e: rejected=True; msg=str(e)
    checks.append({'id':'DEMO-INVALID-FOREST-REJECTION','status':'PASS' if rejected else 'FAIL','message':msg})
    claim=None
    if a.run_claim_tests:
        env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; cmd=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','tests/claims']; q=subprocess.run(cmd,text=True,capture_output=True,env=env); claim={'command':cmd,'returncode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}; checks.append({'id':'DEMO-CLAIMS-AS-TESTS','status':'PASS' if q.returncode==0 else 'FAIL'})
    out={'schema':'CDRSE_RC2_REVIEWER_QUICK_START_RESULTS_V1','software_candidate_version':__version__,'candidate_status':'LOCAL_SOFTWARE_CANDIDATE_RC2','source_baseline_archive_sha256':'97360a18dcd684b4524b915f2c06386f5feb2c4b95afb7fb5ba7847f862ff7a0','historical_local_patch_set':'APEX-P7.1-NOT-PUBLISHED','python':sys.version,'platform':platform.platform(),'elapsed_seconds':time.perf_counter()-t,'checks':checks,'claim_test':claim,'demonstrates':['agreement of four exact static backends on equal-objective witnesses','canonical lexicographic witness contract','scoped exact stored-input certificate','refusal to certify arbitrary callback evaluations','rejection of cyclic support by forest-only backend'],'does_not_demonstrate':['population DD theorems','historical VAR fitting or bootstrap generation','raw-data-to-result reproduction','generic DD numerical enclosures','empirical transfer beyond archived panels']}; out['status']='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL'; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(out['status']); print(f'OUTPUT={a.output}'); print(f"ELAPSED_SECONDS={out['elapsed_seconds']:.6f}"); return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
