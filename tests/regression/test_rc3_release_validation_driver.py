from __future__ import annotations
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]


def driver_module():
    spec=importlib.util.spec_from_file_location('rc3_finite_release_driver',ROOT/'scripts/run_rc3_release_validation.py')
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name',['../x','/x','C:/x','a\\b','root//x','root/./x','root/NUL.txt'])
def test_rc3_driver_rejects_unsafe_paths(name):
    assert driver_module().safe_path(name) is False


def test_rc3_driver_requires_complete_artefact_inventory(tmp_path):
    with pytest.raises(RuntimeError,match='exactly one'):
        driver_module().inventory(tmp_path)


def test_rc3_driver_installed_subset_is_explicit_and_source_independent():
    module=driver_module()
    assert len(module.INSTALLED_TESTS)==6
    assert 'tests/regression/test_rc3_runtime_boundaries.py' in module.INSTALLED_TESTS
    assert all('identity' not in name and 'release_engineering' not in name for name in module.INSTALLED_TESTS)


def test_rc3_driver_rejects_skipped_installed_tests(tmp_path):
    path=tmp_path/'tests.xml'
    path.write_text('<testsuite><testcase name="x"><skipped/></testcase></testsuite>')
    with pytest.raises(RuntimeError,match='no failures, errors or skips'):
        driver_module().junit_summary(path)


def test_rc3_driver_extracts_only_manifest_bound_members(tmp_path):
    module=driver_module();archive=tmp_path/'source.zip';root=module.ARCHIVE_ROOT
    payload=b'bounded-administrative-test\n'
    manifest={'schema':'CDRSE_RC3_SOURCE_MANIFEST_V1','files':{'content.txt':{'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}}}
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr(root+'/',b'')
        z.writestr(root+'/content.txt',payload)
        z.writestr(root+'/SOURCE_ARCHIVE_README.md',b'Administrative fixture only')
        z.writestr(root+'/SOURCE_MANIFEST_SHA256.json',json.dumps(manifest))
    destination=tmp_path/'new'
    result=module.extract_new_source(archive,destination)
    assert (destination/'content.txt').read_bytes()==payload
    assert result['source_members']==1
    with pytest.raises(FileExistsError):module.extract_new_source(archive,destination)


def test_rc3_driver_rejects_unmanifested_members(tmp_path):
    module=driver_module();archive=tmp_path/'source.zip';root=module.ARCHIVE_ROOT
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr(root+'/SOURCE_ARCHIVE_README.md',b'Administrative fixture only')
        z.writestr(root+'/SOURCE_MANIFEST_SHA256.json',json.dumps({'files':{}}))
        z.writestr(root+'/unlisted.txt',b'not-allowed')
    with pytest.raises(RuntimeError,match='member set mismatch'):
        module.extract_new_source(archive,tmp_path/'new')


@pytest.mark.skipif(os.name != 'posix', reason='prepared release driver requires POSIX')
def test_rc3_driver_failed_administrative_child_records_error(tmp_path):
    module=driver_module()
    driver=module.Driver(tmp_path,'a'*40)
    with pytest.raises(RuntimeError,match='command failed'):
        driver.run([sys.executable,'-I','-B','-c',"import sys;print('control-output');sys.exit(2)"],cwd=tmp_path,label='CONTROL')
    assert driver.finish(RuntimeError('expected-control-failure'))==2
    result=json.loads((tmp_path/'release_validation/RELEASE_VALIDATION.json').read_text())
    assert result['status']=='ERROR' and result['commands'][0]['returncode']==2
    assert result['commands'][0]['stdout_bytes_retained'] <= module.MAX_OUTPUT_BYTES


@pytest.mark.skipif(os.name != 'posix', reason='prepared release driver requires POSIX')
def test_rc3_driver_times_out_administrative_child_without_retry(tmp_path):
    module=driver_module()
    driver=module.Driver(tmp_path,'a'*40)
    with pytest.raises(RuntimeError,match='command failed'):
        driver.run([sys.executable,'-I','-B','-c','import time;time.sleep(60)'],cwd=tmp_path,label='TIMEOUT_CONTROL',timeout=0.1)
    assert len(driver.commands)==1
    row=driver.commands[0]
    assert row['timed_out'] and row['returncode']==124
    assert row.get('process_group_kill_requested') or row.get('process_group_already_absent')


def test_rc3_security_exception_is_bound_to_exact_driver_bytes():
    import ast
    tree=ast.parse((ROOT/'scripts/security_audit.py').read_text())
    values={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='REVIEWED_PROCESS_DRIVER'}
    relative,expected=values['REVIEWED_PROCESS_DRIVER']
    assert relative=='scripts/run_rc3_release_validation.py'
    assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected
