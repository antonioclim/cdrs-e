#!/usr/bin/env python3
"""Prepared finite 0.1.0 release-validation driver; execution is UNRUN.

No project module is imported by this driver. Its future commands deliberately
execute separately authorised finite tests and builds. Historical qualification
and scientific campaigns are not rerun or promoted by this software check.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
ARCHIVE_ROOT = "CDRS_E_0.1.0_SOURCE_AND_TESTS"
SOURCE_ZIP = ARCHIVE_ROOT + ".zip"
EPOCH = "1789689600"
MAX_WALL_SECONDS = 1200
MAX_COMMAND_SECONDS = 300
MAX_COMMANDS = 24
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_CLEANUP_SECONDS = 5
MAX_MEMBERS = 4096
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
INSTALLED_TESTS = (
    "tests/unit/test_hashing_models.py",
    "tests/unit/test_objectives_backends.py",
    "tests/unit/test_economics_certificates.py",
    "tests/unit/test_schemas_protocols.py",
    "tests/claims/test_executable_claims.py",
    "tests/regression/test_rc3_runtime_boundaries.py",
)
EXAMPLE_INPUTS = ("examples/forest_problem.json", "examples/frozen_protocol.json")


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            value.update(block)
    return value.hexdigest()


def inventory(dist):
    paths = [*dist.glob("*.whl"), *dist.glob("*.tar.gz"), *dist.glob("*_SOURCE_AND_TESTS.zip")]
    if len(paths) != 3 or len(list(dist.glob("*.whl"))) != 1 or len(list(dist.glob("*.tar.gz"))) != 1 or len(list(dist.glob("*_SOURCE_AND_TESTS.zip"))) != 1:
        raise RuntimeError("exactly one wheel, sdist and curated source ZIP are required")
    return {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(paths)}


def safe_path(name):
    if not isinstance(name, str) or not name or "\\" in name:
        return False
    if any(ord(c) < 32 or c in ':<>|"?*' for c in name):
        return False
    text = name[:-1] if name.endswith("/") else name
    path = PurePosixPath(text)
    devices = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
    return bool(text) and not path.is_absolute() and not PureWindowsPath(text).drive and path.as_posix() == text and all(p not in {"", ".", ".."} and not p.endswith((" ", ".")) and p.split(".", 1)[0].upper() not in devices for p in text.split("/"))


def extract_new_source(archive, destination):
    """Verify the literal source manifest before writing into a fresh directory."""
    if destination.exists():
        raise FileExistsError("extraction destination must be new")
    with ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        canonical = [n.rstrip("/") for n in names]
        if len(names) > MAX_MEMBERS or len(canonical) != len(set(canonical)) or len(canonical) != len({n.casefold() for n in canonical}):
            raise RuntimeError("source ZIP duplicates, collisions or member bound")
        if any(not safe_path(n) for n in names):
            raise RuntimeError("unsafe source ZIP path")
        if any(i.flag_bits & 1 or stat.S_IFMT(i.external_attr >> 16) not in {0, stat.S_IFDIR, stat.S_IFREG} for i in infos):
            raise RuntimeError("source ZIP encryption or special member")
        if any(i.is_dir() and i.file_size != 0 for i in infos):
            raise RuntimeError("source ZIP directory carries an unmanifested payload")
        if any(i.file_size > MAX_MEMBER_BYTES for i in infos) or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
            raise RuntimeError("source ZIP decompression bound")
        if {PurePosixPath(n).parts[0] for n in canonical} != {ARCHIVE_ROOT}:
            raise RuntimeError("source ZIP root mismatch")
        payloads = {i.filename[len(ARCHIVE_ROOT)+1:]: z.read(i.filename) for i in infos if not i.is_dir()}
        manifest = json.loads(payloads["SOURCE_MANIFEST_SHA256.json"])
        rows = manifest["files"]
        if set(payloads) != set(rows) | {"SOURCE_ARCHIVE_README.md", "SOURCE_MANIFEST_SHA256.json"}:
            raise RuntimeError("source ZIP/manifest member set mismatch")
        for name, row in rows.items():
            if not safe_path(name) or len(payloads[name]) != row["bytes"] or hashlib.sha256(payloads[name]).hexdigest() != row["sha256"]:
                raise RuntimeError("source ZIP manifest byte mismatch: " + name)
        destination.mkdir(parents=True, exist_ok=False)
        for name, payload in sorted(payloads.items()):
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    return {"regular_members": len(payloads), "source_members": len(rows), "archive_sha256": digest(archive)}


def junit_summary(path):
    root = ET.fromstring(path.read_bytes())
    cases = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "testcase"]
    failures = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] in {"failure", "error"}]
    skipped = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "skipped"]
    if not cases or failures or skipped:
        raise RuntimeError("installed subset must collect cases with no failures, errors or skips")
    return {"cases": len(cases), "failures": 0, "errors": 0, "skips": 0, "junit_sha256": digest(path)}


class Driver:
    def __init__(self, qa_dir, commit):
        self.started = time.monotonic()
        self.out = qa_dir / "release_validation"
        self.out.mkdir(parents=True, exist_ok=False)
        self.work = Path(tempfile.mkdtemp(prefix="cdrse-0.1.0-release-validation-"))
        self.env = os.environ.copy()
        for key in ("PYTHONPATH", "PYTHONHOME"):
            self.env.pop(key, None)
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PIP_NO_INDEX="1", PIP_NO_INPUT="1", PIP_DISABLE_PIP_VERSION_CHECK="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", SOURCE_DATE_EPOCH=EPOCH, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        self.commands = []
        self.record = {"schema": "CDRSE_RC3_FINITE_RELEASE_VALIDATION_V1", "status": "RUNNING", "job_commit": commit, "software_version": VERSION, "work_directory": str(self.work), "commands": self.commands, "dependency_policy": "Fresh child venvs with --system-site-packages; host dependencies reused transparently; candidate forcibly installed locally. No independent-host or hermetic dependency claim.", "source_import_from_checkout_permitted": False, "scientific_campaign_or_replay": False, "fresh_full_D2_or_Q33": False, "global_PASS": False, "wall_limit_seconds": MAX_WALL_SECONDS, "command_limit_seconds": MAX_COMMAND_SECONDS, "per_command_output_limit_bytes": MAX_OUTPUT_BYTES, "output_capture_policy": "Each stream buffer retains at most 8 MiB; first observed excess requests process-group kill. Kernel/tool buffers and internal temporary materialisation are not certified.", "process_control": "POSIX new session; process-group SIGKILL on deadline or output excess; bounded 5-second drain/reap allowance, with incomplete cleanup reported. Descendants escaping the process group are not contained.", "cleanup_allowance_seconds": MAX_CLEANUP_SECONDS, "wall_scope": "Deadlines checked by selector loop and between commands; OS calls, final report I/O and hard runner termination are not forcibly preempted. Outer Actions timeout is separate."}

    def run(self, command, *, cwd, label, timeout=MAX_COMMAND_SECONDS):
        if len(self.commands) >= MAX_COMMANDS:
            raise RuntimeError("release-validation command-count bound")
        if os.name != "posix":
            raise RuntimeError("release-validation process control requires POSIX")
        remaining = MAX_WALL_SECONDS - (time.monotonic() - self.started)
        if remaining <= 0:
            raise RuntimeError("release-validation wall bound")
        limit = min(timeout, remaining)
        start = time.monotonic()
        deadline = start + limit
        row = {"id": label, "command": [str(x) for x in command], "cwd": str(cwd), "timeout_seconds": limit, "process_group_isolated": True}
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        observed = {"stdout": 0, "stderr": 0}
        process = None
        selector = selectors.DefaultSelector()
        cleanup_deadline = None
        returncode = 127

        def request_stop(reason):
            nonlocal cleanup_deadline
            if cleanup_deadline is None:
                row["stop_reason"] = reason
                cleanup_deadline = time.monotonic() + MAX_CLEANUP_SECONDS
                if process is not None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        row["process_group_kill_requested"] = True
                    except ProcessLookupError:
                        row["process_group_already_absent"] = True
                    except OSError as error:
                        row["process_group_kill_error"] = type(error).__name__

        try:
            process = subprocess.Popen(row["command"], cwd=cwd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            for kind, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, kind)
            while selector.get_map() or process.poll() is None:
                now = time.monotonic()
                if cleanup_deadline is None and now >= deadline:
                    row["timed_out"] = True
                    request_stop("command_deadline")
                if cleanup_deadline is not None and now >= cleanup_deadline:
                    row["cleanup_incomplete"] = True
                    break
                active_deadline = cleanup_deadline if cleanup_deadline is not None else deadline
                for key, _ in selector.select(max(0, min(0.1, active_deadline - now))):
                    try:
                        block = os.read(key.fileobj.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    kind = key.data
                    observed[kind] += len(block)
                    capacity = MAX_OUTPUT_BYTES - len(buffers[kind])
                    if capacity > 0:
                        buffers[kind].extend(block[:capacity])
                    if observed[kind] > MAX_OUTPUT_BYTES:
                        request_stop(kind + "_capture_limit")
            if process.poll() is None:
                request_stop("child_not_reaped")
                allowance = max(0, cleanup_deadline - time.monotonic())
                try:
                    process.wait(timeout=allowance)
                except subprocess.TimeoutExpired:
                    row["cleanup_incomplete"] = True
            row["child_returncode"] = process.poll()
            returncode = process.returncode if process.returncode is not None else 125
            if row.get("stop_reason"):
                returncode = 124 if row.get("timed_out") else 125
        except OSError as error:
            row["spawn_or_io_error"] = type(error).__name__
            buffers["stderr"].extend(str(error).encode("utf-8")[:MAX_OUTPUT_BYTES-len(buffers["stderr"])])
            request_stop("spawn_or_io_error")
            if process is not None:
                try:
                    process.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    row["cleanup_incomplete"] = True
            returncode = 127
        finally:
            selector.close()
            if process is not None:
                for pipe in (process.stdout, process.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
        row.update(returncode=returncode, elapsed_seconds=time.monotonic()-start)
        for kind, payload in buffers.items():
            destination = self.out / f"{len(self.commands)+1:03d}_{label}_{kind}.txt"
            with destination.open("xb") as stream:
                stream.write(payload)
            row[kind+"_file"] = destination.name
            row[kind+"_bytes_retained"] = len(payload)
            row[kind+"_bytes_observed"] = observed[kind]
            row[kind+"_truncated"] = observed[kind] > MAX_OUTPUT_BYTES
        self.commands.append(row)
        with (self.out/"COMMAND_RECEIPTS.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True)+"\n")
        if returncode != 0 or row.get("cleanup_incomplete") or row["stdout_truncated"] or row["stderr_truncated"]:
            raise RuntimeError("command failed, timed out or exceeded output bound: " + label)
        return buffers["stdout"].decode("utf-8")

    def compare(self, expected, observed, label):
        if expected != observed:
            raise RuntimeError("artefact byte identity mismatch: " + label)
        self.record.setdefault("byte_comparisons", []).append({"id": label, "identical": True, "assets": observed})

    def build_copy(self, source_zip, label):
        destination = self.work/label
        extracted = extract_new_source(source_zip, destination)
        for script in ("build_distributions.py", "build_source_archive.py", "verify_distribution.py"):
            self.run([sys.executable, "scripts/"+script], cwd=destination, label=label+"_"+script[:-3])
        return {"source_copy": str(destination), "extraction": extracted, "assets": inventory(destination/"dist")}

    def provenance(self, python, cwd, label):
        code = "import cdrse,json,sys;from pathlib import Path;from importlib import metadata;p=Path(cdrse.__file__).resolve();root=Path(sys.prefix).resolve();assert p.is_relative_to(root) and 'site-packages' in p.parts,(str(p),str(root));assert cdrse.__version__=='0.1.0';print(json.dumps({'module_file':str(p),'venv_prefix':str(root),'version':cdrse.__version__,'setuptools':metadata.version('setuptools'),'pip':metadata.version('pip')}))"
        observed = json.loads(self.run([python,"-I","-B","-c",code],cwd=cwd,label=label))
        if observed["setuptools"] != "84.0.0":
            raise RuntimeError("installed environment backend is not setuptools 84.0.0")
        return observed

    def installed_form(self, artefact, label):
        venv = self.work/(label+"_venv")
        self.run([sys.executable,"-m","venv","--system-site-packages",str(venv)],cwd=self.work,label=label+"_venv_create")
        python = venv/"bin"/"python"
        self.run([python,"-I","-B","-m","pip","install","--ignore-installed","--no-index","--no-deps","--no-build-isolation",str(artefact)],cwd=self.work,label=label+"_install")
        tests_root = self.work/(label+"_external_tests")
        tests_root.mkdir()
        copied = []
        for name in (*INSTALLED_TESTS, *EXAMPLE_INPUTS, "tests/conftest.py"):
            payload = (ROOT/name).read_bytes()
            target = tests_root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
            copied.append({"path":name,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()})
        guard = r"""
# Administrative installed-package guard; no scientific assertion is altered.
import json as _json
import os as _os

def _installed_origin():
    import cdrse
    prefix = Path(sys.prefix).resolve()
    rows = {name: str(Path(module.__file__).resolve()) for name, module in list(sys.modules.items()) if (name == 'cdrse' or name.startswith('cdrse.')) and getattr(module, '__file__', None)}
    if not rows or not all(Path(path).is_relative_to(prefix) and 'site-packages' in Path(path).parts for path in rows.values()):
        raise RuntimeError('installed tests imported checkout or host candidate code')
    return {'venv_prefix': str(prefix), 'modules': rows, 'version': cdrse.__version__}

def pytest_sessionstart(session):
    _installed_origin()

def pytest_sessionfinish(session, exitstatus):
    record = _installed_origin()
    destination = Path(_os.environ['CDRSE_INSTALLED_PROVENANCE'])
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(_json.dumps(record, indent=2, sort_keys=True) + '\n')
"""
        conftest = tests_root/'tests'/'conftest.py'
        original_conftest = conftest.read_bytes()
        with conftest.open('ab') as stream:
            stream.write(guard.encode('utf-8'))
        copied.append({'path':'tests/conftest.py','role':'generated administrative origin guard appended to literal source conftest','source_sha256':hashlib.sha256(original_conftest).hexdigest(),'harness_sha256':digest(conftest)})
        if (tests_root/"src").exists():
            raise RuntimeError("external installed tests must not contain checkout src")
        before = self.provenance(python,tests_root,label+"_provenance_before")
        junit = self.out/(label+"_installed_tests.junit.xml")
        origin_report = self.out/(label+"_test_process_provenance.json")
        self.env['CDRSE_INSTALLED_PROVENANCE'] = str(origin_report)
        try:
            self.run([python,"-I","-B","-m","pytest","-q","-p","no:cacheprovider","--junitxml="+str(junit),*INSTALLED_TESTS],cwd=tests_root,label=label+"_finite_installed_subset",timeout=300)
        finally:
            self.env.pop('CDRSE_INSTALLED_PROVENANCE', None)
        if not origin_report.is_file():
            raise RuntimeError('installed test process did not retain its package provenance')
        after = self.provenance(python,tests_root,label+"_provenance_after")
        freeze = self.run([python,"-I","-B","-m","pip","freeze","--all"],cwd=tests_root,label=label+"_pip_freeze")
        self.record.setdefault("installed_forms", {})[label] = {"artefact":artefact.name,"sha256":digest(artefact),"provenance_before":before,"provenance_after":after,"copied_test_inputs":copied,"finite_subset":list(INSTALLED_TESTS),"full_installed_suite_claimed":False,"observed_junit":junit_summary(junit),"test_process_provenance_sha256":digest(origin_report),"pip_freeze_sha256":hashlib.sha256(freeze.encode()).hexdigest()}

    def execute(self):
        original = inventory(ROOT/"dist")
        self.record["candidate_assets_before"] = original
        source_zip = ROOT/"dist"/SOURCE_ZIP
        host_freeze = self.run([sys.executable,"-I","-B","-m","pip","freeze","--all"],cwd=self.work,label="host_pip_freeze")
        self.record["host_pip_freeze_sha256"] = hashlib.sha256(host_freeze.encode()).hexdigest()
        a = self.build_copy(source_zip,"clean_build_A")
        b = self.build_copy(source_zip,"clean_build_B")
        self.record["clean_builds"] = [a,b]
        self.compare(original,a["assets"],"initial_vs_clean_A_three_assets")
        self.compare(a["assets"],b["assets"],"clean_A_vs_clean_B_three_assets")
        roundtrip = self.work/"source_roundtrip"
        self.record["roundtrip_extraction"] = extract_new_source(source_zip,roundtrip)
        self.run([sys.executable,"scripts/build_source_archive.py"],cwd=roundtrip,label="source_zip_roundtrip_rebuild")
        rebuilt_source = roundtrip/"dist"/SOURCE_ZIP
        if rebuilt_source.read_bytes() != source_zip.read_bytes():
            raise RuntimeError("source ZIP extraction/rebuild byte mismatch")
        self.record["source_zip_roundtrip"] = {"identical":True,"sha256":digest(rebuilt_source)}
        wheel = next((ROOT/"dist").glob("*.whl"))
        sdist = next((ROOT/"dist").glob("*.tar.gz"))
        wheel_dir = self.work/"wheel_from_sdist"
        wheel_dir.mkdir()
        self.run([sys.executable,"-I","-B","-m","pip","wheel","--no-index","--no-deps","--no-build-isolation","--wheel-dir",str(wheel_dir),str(sdist)],cwd=self.work,label="wheel_from_sdist")
        rebuilt = list(wheel_dir.glob("*.whl"))
        if len(rebuilt) != 1 or rebuilt[0].name != wheel.name or rebuilt[0].read_bytes() != wheel.read_bytes():
            raise RuntimeError("sdist-to-wheel byte mismatch")
        self.record["wheel_from_sdist"] = {"identical":True,"sha256":digest(rebuilt[0])}
        self.installed_form(wheel,"wheel")
        self.installed_form(sdist,"sdist")
        self.compare(original,inventory(ROOT/"dist"),"candidate_assets_unchanged_after_validation")
        self.record["status"] = "SCOPED_RELEASE_VALIDATION_PASS"
        self.record["scope"] = "Two fresh same-host builds, three-asset byte comparisons, sourceZIP roundtrip, sdist-to-wheel identity and explicitly listed finite installed-form tests with local package provenance. No full D2/Q33, independent-host reproduction, raw-data campaign or scientific replay."

    def finish(self, error=None):
        if error is not None:
            self.record.update(status="ERROR",error_type=type(error).__name__,error=str(error))
        self.record["elapsed_seconds"] = time.monotonic()-self.started
        with (self.out/"RELEASE_VALIDATION.json").open("x",encoding="utf-8") as stream:
            stream.write(json.dumps(self.record,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"status":self.record["status"],"report":str(self.out/"RELEASE_VALIDATION.json"),"commands":len(self.commands)},sort_keys=True))
        return 0 if self.record["status"] == "SCOPED_RELEASE_VALIDATION_PASS" else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa-dir",type=Path,required=True)
    ap.add_argument("--commit",required=True)
    args = ap.parse_args()
    if re.fullmatch("[0-9a-f]{40}",args.commit) is None:
        raise SystemExit("exact observed commit required")
    try:
        driver = Driver(args.qa_dir.resolve(),args.commit)
    except Exception as error:
        print(json.dumps({'status':'ERROR','error_type':type(error).__name__,'error':str(error),'report':'No existing evidence was overwritten.'}))
        return 2
    try:
        driver.execute()
    except Exception as error:
        return driver.finish(error)
    return driver.finish()


if __name__ == "__main__":
    raise SystemExit(main())
