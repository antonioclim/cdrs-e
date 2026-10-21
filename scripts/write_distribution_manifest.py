#!/usr/bin/env python3
"""Write external job evidence after successful explicitly authorised validation.

No project module is imported. This command is UNRUN in source preparation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):value.update(block)
    return value.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--commit',required=True)
    ap.add_argument('--qa-dir',required=True,type=Path)
    args=ap.parse_args()
    if re.fullmatch('[0-9a-f]{40}',args.commit) is None:
        raise SystemExit('exact observed Git commit required')
    version=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    dist=ROOT/'dist'
    files=sorted([*dist.glob('*.whl'),*dist.glob('*.tar.gz'),*dist.glob('*_SOURCE_AND_TESTS.zip')])
    if len(list(dist.glob('*.whl')))!=1 or len(list(dist.glob('*.tar.gz')))!=1 or len(list(dist.glob('*_SOURCE_AND_TESTS.zip')))!=1:
        raise SystemExit('one wheel, sdist and curated source ZIP required')
    verification=ROOT/'build'/'verification'/'distribution_verification.json'
    verified=json.loads(verification.read_text(encoding='utf-8'))
    if verified.get('status')!='PASS_ADMINISTRATIVE_DISTRIBUTION_CHECK':
        raise SystemExit('administrative distribution verification required')
    for key in ('wheel','sdist'):
        row=verified[key];actual=dist/row['file']
        if actual not in files or actual.stat().st_size!=row['bytes'] or digest(actual)!=row['sha256']:
            raise SystemExit('verified artefact identity changed')
    qa_files=[args.qa_dir/'tests.junit.xml',args.qa_dir/'coverage.json',args.qa_dir/'self_check.json',verification]
    if any(not p.is_file() for p in qa_files):raise SystemExit('complete bounded job evidence is required')
    tests=ET.fromstring((args.qa_dir/'tests.junit.xml').read_bytes())
    cases=[node for node in tests.iter() if node.tag.rsplit('}',1)[-1]=='testcase']
    adverse=[node for node in tests.iter() if node.tag.rsplit('}',1)[-1] in {'failure','error'}]
    if not cases or adverse:raise SystemExit('JUnit must report collected cases without failures or errors')
    coverage=json.loads((args.qa_dir/'coverage.json').read_text(encoding='utf-8'))
    if coverage['totals']['percent_covered'] < 85:raise SystemExit('coverage threshold not met')
    self_check=json.loads((args.qa_dir/'self_check.json').read_text(encoding='utf-8'))
    if self_check.get('status')!='PASS' or self_check.get('version')!=version:raise SystemExit('matching self-check record required')
    release_validation = None
    if sys.version_info[:2] == (3,12):
        validation_path = args.qa_dir/'release_validation'/'RELEASE_VALIDATION.json'
        release_validation = json.loads(validation_path.read_text(encoding='utf-8'))
        if release_validation.get('status')!='SCOPED_RELEASE_VALIDATION_PASS' or release_validation.get('job_commit')!=args.commit or release_validation.get('software_version')!=version:
            raise SystemExit('complete matching authoritative release validation is required')
        current = {p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}
        if release_validation.get('candidate_assets_before') != current or set(release_validation.get('installed_forms',{})) != {'wheel','sdist'}:
            raise SystemExit('release validation does not bind the final assets or installed forms')
        qa_files.append(validation_path)
    # These fields are evidence bindings, not independent authentication of logs.
    record={'schema':'CDRSE_RC3_JOB_ARTEFACT_MANIFEST_V1','version':version,'recorded_test_cases':len(cases),'qualification_scope':'Finite source suite, repeated same-host builds and declared installed subsets for the authoritative 3.12 job; no full D2/Q33, independent host or scientific replay.' if release_validation is not None else 'Diagnostic matrix source-suite and single-build evidence only; not the authoritative release-validation route.','job_commit':args.commit,'python':platform.python_version(),'platform':platform.platform(),'build_role':'AUTHORITATIVE_CANDIDATE' if sys.version_info[:2]==(3,12) else 'DIAGNOSTIC_MATRIX_ONLY','cross_python_byte_identity_claimed':False,'scientific_replay':False,'global_PASS':False,'assets':[{'file':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in files],'evidence':[{'file':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in qa_files]}
    destination=dist/'ARTIFACT_MANIFEST.json'
    with destination.open('x',encoding='utf-8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
    rows=[*files,destination]
    with (dist/'SHA256SUMS.txt').open('x',encoding='utf-8') as f:
        for path in rows:f.write(digest(path)+'  '+path.name+'\n')
    print(json.dumps({'manifest':destination.name,'build_role':record['build_role'],'assets':len(files)}))
    return 0


if __name__=='__main__':raise SystemExit(main())
