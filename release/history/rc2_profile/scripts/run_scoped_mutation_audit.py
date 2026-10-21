#!/usr/bin/env python3
"""Dependency-free scoped mutation audit for Phase 7.

The scope is selected correctness- and assurance-critical contracts; it is not
whole-package mutation coverage.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from cdrse import __version__
MUTANTS=(
 {'id':'M01_CANONICAL_KEY_REVERSED','file':'src/cdrse/algorithms/common.py','old':'return value, tuple(selected)','new':'return value, tuple(reversed(selected))','tests':['tests/qualification/test_canonical_witness_policy.py::test_multi_coordinate_equal_objective_witness_is_canonical']},
 {'id':'M02_FOREST_TIE_DIRECTION','file':'src/cdrse/algorithms/forest.py','old':'new.value == old.value and new.selected < old.selected','new':'new.value == old.value and new.selected > old.selected','tests':['tests/qualification/test_canonical_witness_policy.py::test_multi_coordinate_equal_objective_witness_is_canonical']},
 {'id':'M03_FOREST_SECONDARY_COST_TIE','file':'src/cdrse/algorithms/forest.py','old':'best = min(feasible, key=lambda row: canonical_objective_key(alpha * row["loss"] + beta * row["cost"], tuple(row["selected"])))','new':'best = min(feasible, key=lambda row: (alpha * row["loss"] + beta * row["cost"], row["cost"], tuple(row["selected"])))','tests':['tests/qualification/test_canonical_witness_policy.py']},
 {'id':'M04_TREEWIDTH_SECONDARY_COST_TIE','file':'src/cdrse/algorithms/treewidth.py','old':'best = min(feasible, key=lambda row: canonical_objective_key(alpha * row["loss"] + beta * row["cost"], tuple(row["selected"])))','new':'best = min(feasible, key=lambda row: (alpha * row["loss"] + beta * row["cost"], row["cost"], tuple(row["selected"])))','tests':['tests/qualification/test_canonical_witness_policy.py']},
 {'id':'M05_BRANCH_EQUAL_BOUND_ALWAYS_PRUNED','file':'src/cdrse/algorithms/branch_bound.py','old':'or (node.lower_bound == incumbent[0] and can_prune_equal_bound(node.included, node.excluded))','new':'or node.lower_bound == incumbent[0]','tests':['tests/qualification/test_canonical_witness_policy.py']},
 {'id':'M06_ALLOW_NEGATIVE_CUT_WEIGHT','file':'src/cdrse/models.py','old':'np.any(~np.isfinite(self.cut_weights)) or np.any(self.cut_weights < 0)','new':'np.any(~np.isfinite(self.cut_weights)) or np.any(self.cut_weights < -1)','tests':['tests/claims/test_executable_claims.py::test_claim_negative_cut_weights_are_rejected']},
 {'id':'M07_BUDGET_EQUALITY_REJECTED','file':'src/cdrse/models.py','old':'> rational(self.budget):','new':'>= rational(self.budget):','tests':['tests/qualification/test_boundary_contracts_p72.py::test_feasibility_matches_service_and_budget']},
 {'id':'M08_DIRECTED_CUT_ORIENTATION','file':'src/cdrse/objectives.py','old':'if source not in selected','new':'if source in selected','tests':['tests/unit/test_objectives_backends.py::test_cut_orientation_and_weights']},
 {'id':'M09_ALLOW_DUPLICATE_SUBSET_INDICES','file':'src/cdrse/models.py','old':'if len(set(out)) != len(out):','new':'if False:','tests':['tests/qualification/test_boundary_contracts_p72.py::test_subset_rejects_ambiguous_labels']},
 {'id':'M10_ALLOW_MANDATORY_FORBIDDEN_OVERLAP','file':'src/cdrse/models.py','old':'if mandatory & forbidden:','new':'if False:','tests':['tests/qualification/test_boundary_contracts_p72.py::test_service_rejections']},
 {'id':'M11_ALLOW_CALLBACK_GLOBAL_LOWER_BOUND','file':'src/cdrse/verification.py','old':"if record['global_lower_bound'] is not None:\n            raise ValidationError('unenclosed callback carries an unsupported global lower bound')",'new':"if False:\n            raise ValidationError('unenclosed callback carries an unsupported global lower bound')",'tests':['tests/claims/test_executable_claims.py::test_claim_unenclosed_callback_global_bound_is_rejected']},
 {'id':'M12_ZERO_PROJECTION_NOT_REJECTED','file':'src/cdrse/objectives.py','old':'if scale == 0:','new':'if scale < 0:','tests':['tests/qualification/test_adverse_regressions_P3.py::test_invalid_subspace_rejected']},
)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=Path('scoped_mutation_audit.json')); a=ap.parse_args(); src=Path(__file__).resolve().parents[1]; env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'; started=time.perf_counter(); results=[]
 with tempfile.TemporaryDirectory(prefix='cdrse-p7-mutants-') as td:
  for m in MUTANTS:
   work=Path(td)/m['id']; shutil.copytree(src,work,ignore=shutil.ignore_patterns('.git','.pytest_cache','__pycache__','.coverage*','htmlcov','reviewer_pipeline_results'))
   p=work/m['file']; text=p.read_text(); count=text.count(m['old'])
   if count!=1: results.append({**m,'status':'NOT_APPLIED','occurrences':count}); continue
   p.write_text(text.replace(m['old'],m['new'],1)); cmd=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',*m['tests']]; e=env.copy(); e['PYTHONPATH']=str(work/'src'); t=time.perf_counter(); q=subprocess.run(cmd,cwd=work,env=e,text=True,capture_output=True,timeout=120); results.append({**m,'status':'KILLED' if q.returncode else 'SURVIVED','returncode':q.returncode,'elapsed_seconds':time.perf_counter()-t,'stdout_tail':q.stdout[-2000:],'stderr_tail':q.stderr[-2000:]})
 applied=[r for r in results if r['status'] in {'KILLED','SURVIVED'}]; killed=sum(r['status']=='KILLED' for r in applied); score=killed/len(applied) if applied else 0.0; payload={'schema':'CDRSE_RC2_SCOPED_MUTATION_AUDIT_V1','software_candidate_version':__version__,'candidate_status':'LOCAL_SOFTWARE_CANDIDATE_RC2','source_baseline_archive_sha256':'97360a18dcd684b4524b915f2c06386f5feb2c4b95afb7fb5ba7847f862ff7a0','historical_schema':'APEX_P7_SCOPED_MUTATION_AUDIT_V1','scope':'selected safety- and correctness-critical contracts; not whole-package mutation coverage','mutants_declared':len(MUTANTS),'mutants_applied':len(applied),'killed':killed,'survived':sum(r['status']=='SURVIVED' for r in applied),'not_applied':sum(r['status']=='NOT_APPLIED' for r in results),'mutation_score':score,'threshold':0.70,'threshold_met':score>=0.70 and len(applied)==len(MUTANTS),'elapsed_seconds':time.perf_counter()-started,'results':results}; payload['status']='PASS' if payload['threshold_met'] else 'FAIL'; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(payload['status']); print(f'MUTATION_SCORE={score:.6f}'); print(f'KILLED={killed}/{len(applied)}'); print(f'OUTPUT={a.output}'); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
