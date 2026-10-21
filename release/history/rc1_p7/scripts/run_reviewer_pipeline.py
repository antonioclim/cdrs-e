#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
SHARDS=('tests/unit','tests/integration','tests/property','tests/qualification','tests/regression','tests/claims')
def h(p):
 d=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): d.update(b)
 return d.hexdigest()
def run(cmd,cwd,env,timeout):
 t=time.perf_counter(); q=subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout); return {'command':cmd,'returncode':q.returncode,'elapsed_seconds':time.perf_counter()-t,'stdout':q.stdout,'stderr':q.stderr}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,default=Path('reviewer_pipeline_results')); ap.add_argument('--skip-coverage',action='store_true'); a=ap.parse_args(); root=Path(__file__).resolve().parents[1]; out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True); env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'src'),PYTEST_ADDOPTS=''); t=time.perf_counter(); runs=[]
 for i,sh in enumerate(SHARDS,1):
  print(f'RUN TEST SHARD {i}/{len(SHARDS)}: {sh}',flush=True); r=run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',sh],root,env,600); r.update(id=f'TEST-SHARD-{i:02d}',shard=sh); runs.append(r); (out/f'test_shard_{i:02d}.json').write_text(json.dumps(r,indent=2)+'\n'); print(f"DONE TEST SHARD {i}: rc={r['returncode']} elapsed={r['elapsed_seconds']:.3f}s",flush=True); 
  if r['returncode']!=0: break
 print('RUN REVIEWER QUICK START',flush=True); q=run([sys.executable,'scripts/reviewer_quick_start.py','--run-claim-tests','--output',str(out/'reviewer_quick_start_results.json')],root,env,300); q['id']='REVIEWER-QUICK-START'; runs.append(q); (out/'reviewer_quick_start_run.json').write_text(json.dumps(q,indent=2)+'\n'); print(f"DONE REVIEWER QUICK START: rc={q['returncode']} elapsed={q['elapsed_seconds']:.3f}s",flush=True)
 cov=None
 if not a.skip_coverage and all(x['returncode']==0 for x in runs):
  subprocess.run([sys.executable,'-m','coverage','erase'],cwd=root,env=env,capture_output=True)
  cs=[]
  for i,sh in enumerate(SHARDS,1):
   print(f'RUN COVERAGE SHARD {i}/{len(SHARDS)}: {sh}',flush=True); r=run([sys.executable,'-m','coverage','run','--branch','--parallel-mode','-m','pytest','-q','-p','no:cacheprovider',sh],root,env,600); cs.append(r); print(f"DONE COVERAGE SHARD {i}: rc={r['returncode']} elapsed={r['elapsed_seconds']:.3f}s",flush=True)
  combine=run([sys.executable,'-m','coverage','combine'],root,env,120); jr=run([sys.executable,'-m','coverage','json','-o',str(out/'coverage.json')],root,env,120); rr=run([sys.executable,'-m','coverage','report','-m'],root,env,120); cov={'shards':cs,'combine':combine,'json':jr,'report':rr}; (out/'coverage_run.json').write_text(json.dumps(cov,indent=2)+'\n'); (out/'coverage_report.txt').write_text(rr['stdout'])
 files=[]
 for p in sorted(root.rglob('*')):
  if p.is_file() and '.coverage' not in p.name and '__pycache__' not in p.parts: files.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':h(p)})
 status='PASS' if all(x['returncode']==0 for x in runs) else 'FAIL'
 if cov and not all([x['returncode']==0 for x in cov['shards']]+[cov['combine']['returncode']==0,cov['json']['returncode']==0]): status='FAIL'
 m={'schema':'APEX_P7_REVIEWER_PIPELINE_RESULTS_V1','status':status,'public_software_version':'0.1.0rc1','local_patch_set':'APEX-P7.1-NOT-PUBLISHED','elapsed_seconds':time.perf_counter()-t,'runs':runs,'coverage':None if cov is None else {'report_stdout':cov['report']['stdout'],'coverage_json':'coverage.json'},'file_manifest':files}; (out/'pipeline_manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n'); print(status); print(f'OUTPUT_DIR={out}'); print(f"ELAPSED_SECONDS={m['elapsed_seconds']:.6f}"); return 0 if status=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
