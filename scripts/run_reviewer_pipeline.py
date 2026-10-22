#!/usr/bin/env python3
"""Explicitly authorised reviewer pipeline; no execution is implied by shipping it."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from cdrse import __version__

SHARDS = ("tests/unit", "tests/integration", "tests/property", "tests/qualification", "tests/regression", "tests/claims")
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}


def h(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, cwd, env, timeout):
    started = time.perf_counter()
    try:
        q = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
        return {"command":cmd, "returncode":q.returncode, "elapsed_seconds":time.perf_counter()-started, "stdout":q.stdout, "stderr":q.stderr, "timed_out":False}
    except subprocess.TimeoutExpired as error:
        def text(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
        return {"command":cmd, "returncode":124, "elapsed_seconds":time.perf_counter()-started, "stdout":text(error.stdout), "stderr":text(error.stderr), "timed_out":True}


def coverage_succeeded(record):
    return all(x["returncode"] == 0 for x in [record["erase"], *record["shards"], record["combine"], record["json"], record["report"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, default=Path("reviewer_pipeline_results"))
    ap.add_argument("--skip-coverage", action="store_true")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite earlier or partial evidence.
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(root/"src"), PYTEST_ADDOPTS="")
    started = time.perf_counter()
    runs = []
    for i, shard in enumerate(SHARDS, 1):
        result = run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider",shard],root,env,600)
        result.update(id=f"TEST-SHARD-{i:02d}",shard=shard)
        runs.append(result)
        (out/f"test_shard_{i:02d}.json").write_text(json.dumps(result,indent=2)+"\n")
        if result["returncode"] != 0:
            break
    if len(runs) == len(SHARDS) and all(r["returncode"] == 0 for r in runs):
        result = run([sys.executable,"scripts/reviewer_quick_start.py","--run-claim-tests","--output",str(out/"reviewer_quick_start_results.json")],root,env,300)
        result["id"] = "REVIEWER-QUICK-START"
        runs.append(result)
        (out/"reviewer_quick_start_run.json").write_text(json.dumps(result,indent=2)+"\n")
    cov = None
    if not args.skip_coverage and len(runs) == len(SHARDS)+1 and all(r["returncode"] == 0 for r in runs):
        erase = run([sys.executable,"-m","coverage","erase"],root,env,120)
        shards = []
        if erase["returncode"] == 0:
            for shard in SHARDS:
                result = run([sys.executable,"-m","coverage","run","--branch","--parallel-mode","-m","pytest","-q","-p","no:cacheprovider",shard],root,env,600)
                shards.append(result)
                if result["returncode"] != 0:
                    break
        skipped = {"returncode":125,"status":"NOT_EXECUTED_AFTER_FAILURE"}
        ready = erase["returncode"] == 0 and len(shards) == len(SHARDS) and all(x["returncode"] == 0 for x in shards)
        combine = run([sys.executable,"-m","coverage","combine"],root,env,120) if ready else dict(skipped)
        jr = run([sys.executable,"-m","coverage","json","-o",str(out/"coverage.json")],root,env,120) if combine["returncode"] == 0 else dict(skipped)
        report = run([sys.executable,"-m","coverage","report","-m","--fail-under=85"],root,env,120) if jr["returncode"] == 0 else dict(skipped)
        cov = {"erase":erase,"shards":shards,"combine":combine,"json":jr,"report":report}
        (out/"coverage_run.json").write_text(json.dumps(cov,indent=2)+"\n")
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_relative_to(out) or set(path.relative_to(root).parts) & EXCLUDED or path.name.startswith(".coverage"):
            continue
        files.append({"path":path.relative_to(root).as_posix(),"bytes":path.stat().st_size,"sha256":h(path)})
    passed = len(runs) == len(SHARDS)+1 and all(r["returncode"] == 0 for r in runs)
    if not args.skip_coverage:
        passed = passed and cov is not None and len(cov["shards"]) == len(SHARDS) and coverage_succeeded(cov)
    record = {"schema":"CDRSE_RC3_REVIEWER_PIPELINE_RESULTS_V1","status":"PASS_SCOPED_REVIEWER_PIPELINE" if passed else "FAIL","software_candidate_version":__version__,"candidate_status":"PREPARED_RELEASE_011","coverage_scope":"SKIPPED_BY_EXPLICIT_OPTION" if args.skip_coverage else "REQUIRED_WITH_THRESHOLD_85","elapsed_seconds":time.perf_counter()-started,"runs":runs,"coverage":cov,"file_manifest":files,"scientific_replay":False,"global_PASS":False,"limits":"Finite software checks only; no raw-data campaign, population theorem verification or mutation classification."}
    (out/"pipeline_manifest.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(record["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
