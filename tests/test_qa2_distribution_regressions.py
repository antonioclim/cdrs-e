"""Finite administrative regressions for SW-04/SW-05; no numerical models.

Seven controlled wheel fixtures are made once per test session. The real
installed-wheel subprocess checks are performed separately by the phase driver.
"""
from __future__ import annotations

import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import warnings
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
INFO = "cdrs_e-0.1.1.dist-info/"
VARIANTS = ("valid", "changed_license", "changed_notice", "missing_notice", "misplaced_notice", "extra_nested_license", "duplicate_license")


def administrative_module(name):
    spec = importlib.util.spec_from_file_location("qa2_admin_" + name, ROOT / "scripts" / (name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def administrative_fixtures(tmp_path_factory):
    root = tmp_path_factory.mktemp("qa2_admin")
    source = root / "source"
    source.mkdir()
    (source / "LICENSE").write_bytes(b"frozen licence bytes\n")
    (source / "NOTICE").write_bytes(b"frozen notice bytes\n")
    wheels = {}
    for variant in VARIANTS:
        entries = [
            ("cdrse/__init__.py", b"__version__ = '0.1.1'\n"),
            ("cdrse/cli.py", b"# synthetic payload, never imported\n"),
            (INFO + "METADATA", b"Metadata-Version: 2.4\nName: cdrs-e\nVersion: 0.1.1\n\n"),
            (INFO + "licenses/LICENSE", (source / "LICENSE").read_bytes()),
            (INFO + "licenses/NOTICE", (source / "NOTICE").read_bytes()),
        ]
        if variant == "changed_license":
            entries[3] = (entries[3][0], b"altered licence\n")
        elif variant == "changed_notice":
            entries[4] = (entries[4][0], b"altered notice\n")
        elif variant == "missing_notice":
            entries.pop(4)
        elif variant == "misplaced_notice":
            entries[4] = (INFO + "NOTICE", entries[4][1])
        elif variant == "extra_nested_license":
            entries.append((INFO + "licenses/extra/LICENSE", entries[3][1]))
        elif variant == "duplicate_license":
            entries.append(entries[3])
        rows = io.StringIO(newline="")
        writer = csv.writer(rows)
        for name, payload in entries:
            digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
            writer.writerow((name, "sha256=" + digest, str(len(payload))))
        writer.writerow((INFO + "RECORD", "", ""))
        path = root / (variant + ".whl")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "x") as archive:
                for name, payload in entries:
                    archive.writestr(name, payload)
                archive.writestr(INFO + "RECORD", rows.getvalue())
        wheels[variant] = path
    return {"root": root, "source": source, "wheels": wheels}


@pytest.mark.parametrize("variant", VARIANTS)
def test_qa2_literal_wheel_licence_binding(administrative_fixtures, variant):
    module = administrative_module("verify_distribution")
    source = administrative_fixtures["source"]
    with zipfile.ZipFile(administrative_fixtures["wheels"][variant]) as archive:
        if variant == "duplicate_license":
            with pytest.raises(ValueError, match="duplicate"):
                module.validate_zip_members(archive)
            with pytest.raises(ValueError, match="licence paths or multiplicity"):
                module.verify_wheel_licences(archive, INFO, source)
            return
        module.validate_zip_members(archive)
        # The adversarial licence cases have internally correct SHA-256 RECORDs.
        module.verify_record(archive, INFO + "RECORD")
        if variant == "valid":
            module.verify_wheel_licences(archive, INFO, source)
        else:
            with pytest.raises(ValueError, match="wheel licence"):
                module.verify_wheel_licences(archive, INFO, source)


def provenance_payload(fixtures):
    prefix = fixtures["root"] / "venv"
    site = prefix / "lib/python3.11/site-packages"
    with zipfile.ZipFile(fixtures["wheels"]["valid"]) as archive:
        hashes = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith("cdrse/")}
    return {
        "prefix": str(prefix),
        "base_prefix": str(fixtures["root"] / "base"),
        "distribution_root": str(site),
        "isolated": True,
        "ignore_environment": True,
        "no_user_site": True,
        "system_site_packages": False,
        "version": {"version": "0.1.1"},
        "package_files": hashes,
        "modules": {
            "cdrse": {"path": str(site / "cdrse/__init__.py"), "member": "cdrse/__init__.py", "sha256": hashes["cdrse/__init__.py"]},
            "cdrse.cli": {"path": str(site / "cdrse/cli.py"), "member": "cdrse/cli.py", "sha256": hashes["cdrse/cli.py"]},
        },
    }


def test_qa2_provenance_evidence_accepts_bound_origins(administrative_fixtures):
    module = administrative_module("clean_room_verify")
    module.validate_provenance(provenance_payload(administrative_fixtures), administrative_fixtures["wheels"]["valid"], administrative_fixtures["source"])


@pytest.mark.parametrize("defect", ("wrong_hash", "source_origin", "missing_module", "no_isolation", "not_a_venv"))
def test_qa2_provenance_evidence_rejects_defects(administrative_fixtures, defect):
    module = administrative_module("clean_room_verify")
    payload = copy.deepcopy(provenance_payload(administrative_fixtures))
    if defect == "wrong_hash":
        payload["modules"]["cdrse.cli"]["sha256"] = "0" * 64
    elif defect == "source_origin":
        payload["modules"]["cdrse.cli"]["path"] = str(administrative_fixtures["source"] / "src/cdrse/cli.py")
    elif defect == "missing_module":
        del payload["modules"]["cdrse.cli"]
    elif defect == "no_isolation":
        payload["isolated"] = False
    else:
        payload["base_prefix"] = payload["prefix"]
    with pytest.raises(RuntimeError):
        module.validate_provenance(payload, administrative_fixtures["wheels"]["valid"], administrative_fixtures["source"])


def test_qa2_environment_does_not_inherit_python_settings(administrative_fixtures, monkeypatch):
    module = administrative_module("clean_room_verify")
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "LD_PRELOAD"):
        monkeypatch.setenv(name, "/untrusted/checkout")
    environment = module.sanitised_environment(administrative_fixtures["root"])
    assert not {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "LD_PRELOAD"} & set(environment)
    assert environment["PIP_NO_INDEX"] == "1"


def test_qa2_probe_rejects_checkout_cwd_before_subprocess(administrative_fixtures, monkeypatch):
    module = administrative_module("clean_room_verify")
    def forbidden(*args, **kwargs):
        pytest.fail("subprocess must not start from source checkout")
    monkeypatch.setattr(module.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="outside source checkout"):
        module.probe_installed_wheel(Path(sys.executable), administrative_fixtures["wheels"]["valid"], administrative_fixtures["source"], source_root=administrative_fixtures["source"])


def test_qa2_probe_command_is_isolated_and_bounded(administrative_fixtures, monkeypatch):
    module = administrative_module("clean_room_verify")
    observed = {}
    def fake_run(command, **kwargs):
        observed.update(command=command, kwargs=kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps(provenance_payload(administrative_fixtures)), stderr="")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    result = module.probe_installed_wheel(Path(sys.executable), administrative_fixtures["wheels"]["valid"], administrative_fixtures["root"], source_root=administrative_fixtures["source"], timeout_seconds=12)
    assert observed["command"][1:4] == ["-I", "-B", "-c"]
    assert observed["kwargs"]["cwd"] == administrative_fixtures["root"].resolve()
    assert observed["kwargs"]["timeout"] == 12
    assert "PYTHONPATH" not in observed["kwargs"]["env"]
    assert result["scientific_checks_run"] is False
    assert result["sdist_installation_checked"] is False
