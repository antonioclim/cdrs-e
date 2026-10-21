from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]


def administrative_module(name):
    spec = importlib.util.spec_from_file_location('rc3_admin_'+name, ROOT/'scripts'/f'{name}.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['../x','/x','C:/x','C:x','a\\b','a//b','a/./b','a/../b','a/CON.txt','a/NUL','a/trailing.','a/trailing '])
def test_rc3_portable_unsafe_paths_are_rejected(name):
    assert administrative_module('verify_distribution').safe_name(name) is False


def test_rc3_duplicate_zip_members_are_rejected():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('x.txt',b'a')
        z.writestr('x.txt',b'b')
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as z:
        with pytest.raises(ValueError, match='duplicate'):
            administrative_module('verify_distribution').validate_zip_members(z)


def test_rc3_case_collisions_are_rejected():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('A.txt',b'a')
        z.writestr('a.txt',b'a')
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as z:
        with pytest.raises(ValueError, match='colliding'):
            administrative_module('verify_distribution').validate_zip_members(z)


def test_rc3_duplicate_record_rows_are_rejected():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('x.txt',b'a')
        z.writestr('dist/RECORD','x.txt,,\nx.txt,,\ndist/RECORD,,\n')
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as z:
        with pytest.raises(ValueError, match='duplicate wheel RECORD'):
            administrative_module('verify_distribution').verify_record(z,'dist/RECORD')


@pytest.mark.parametrize('kind',[tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE])
def test_rc3_tar_links_and_special_members_are_rejected(kind):
    item = tarfile.TarInfo('root/x');item.type=kind
    with pytest.raises(ValueError, match='link or special'):
        administrative_module('verify_distribution').validate_tar_members([item])


def test_rc3_tar_multiple_roots_are_rejected():
    with pytest.raises(ValueError, match='exactly one root'):
        administrative_module('verify_distribution').validate_tar_members([tarfile.TarInfo('one/a'),tarfile.TarInfo('two/b')])


def test_rc3_generated_archive_members_are_excluded_on_roundtrip(tmp_path):
    module = administrative_module('build_source_archive')
    root = tmp_path/'source';root.mkdir()
    (root/'build-recipe.json').write_text(json.dumps({'software_version':'0.1.0rc3','candidate_status':'PREPARED_CANDIDATE_RC3','source_date_epoch':1789689600}))
    (root/'content.txt').write_bytes(b'administrative-packaging-test\n')
    a = tmp_path/'a.zip';module.build_source_archive(a,root=root)
    copy = tmp_path/'copy';copy.mkdir()
    with zipfile.ZipFile(a) as z:
        for info in z.infolist():
            if info.is_dir():continue
            rel=Path(*Path(info.filename).parts[1:]);destination=copy/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(z.read(info.filename))
    b = tmp_path/'b.zip';module.build_source_archive(b,root=copy)
    assert a.read_bytes()==b.read_bytes()
    with zipfile.ZipFile(b) as z:
        names=z.namelist()
        assert len(names)==len(set(names))
        manifest=json.loads(z.read(module.ARCHIVE_ROOT+'/SOURCE_MANIFEST_SHA256.json'))
        assert set(manifest['files'])=={'build-recipe.json','content.txt'}


def test_rc3_archive_preserves_existing_destination(tmp_path):
    module=administrative_module('build_source_archive')
    existing=tmp_path/'existing.zip';existing.write_bytes(b'preserve-partial')
    with pytest.raises(FileExistsError):module.build_source_archive(existing,root=tmp_path)
    assert existing.read_bytes()==b'preserve-partial'


def test_rc3_reserved_case_collision_is_rejected(tmp_path):
    module=administrative_module('build_source_archive')
    (tmp_path/'source_manifest_sha256.json').write_text('{}')
    with pytest.raises(RuntimeError,match='reserved generated-name'):
        module.public_files(tmp_path)


def test_rc3_coverage_report_failure_cannot_pass():
    module=administrative_module('run_reviewer_pipeline')
    good={'returncode':0}
    record={'erase':good,'shards':[good],'combine':good,'json':good,'report':{'returncode':1}}
    assert module.coverage_succeeded(record) is False
    record['report']=good
    assert module.coverage_succeeded(record) is True
    record['erase']={'returncode':1}
    assert module.coverage_succeeded(record) is False


def test_rc3_mutation_entry_point_does_not_execute_or_classify(capsys):
    module=administrative_module('run_scoped_mutation_audit')
    assert module.main()==2
    result=json.loads(capsys.readouterr().out)
    assert result['automatic_kill_classification'] is False
    assert result['status']=='UNRUN_REQUIRES_SEPARATE_MUTATION_PROTOCOL'


def test_rc3_workflow_has_no_automatic_event():
    text=(ROOT/'.github/workflows/ci.yml').read_text()
    assert '  push:' not in text and '  pull_request:' not in text
    assert '  workflow_dispatch:' in text
    assert "inputs.authorisation == 'AUTHORISE_CDRSE_RC3_VALIDATION'" in text
    assert 'timeout-minutes: 30' in text


def test_rc3_release_identifiers_remain_unasserted_until_observed():
    identity=json.loads((ROOT/'release/PUBLICATION_IDENTITY.json').read_text())
    assert identity['version']=='0.1.0rc3' and identity['target_branch']=='main'
    assert identity['successor_commit'] is None and identity['release_date'] is None and identity['version_DOI'] is None
    state=json.loads((ROOT/'release/QUALIFICATION_STATE.json').read_text())
    assert state['software_version']=='0.1.0rc3' and state['build']=='UNRUN'
    assert state['global_scientific_PASS_claimed'] is False
