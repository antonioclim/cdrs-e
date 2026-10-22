#!/usr/bin/env python3
"""Verify an explicitly installed wheel from outside the source checkout.

The historical filename is retained. This helper creates no environment,
installs nothing and runs no numerical self-check. Dependency provisioning and
installation need a separate recorded policy. This is installed-wheel origin
verification on one host, not hermetic or independent-host reproduction.
"""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sanitised_environment(working_directory: Path) -> dict[str, str]:
    """Do not inherit caller-controlled Python paths or startup settings."""
    return {
        "PATH": os.defpath,
        "HOME": str(working_directory),
        "TMPDIR": str(working_directory),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }


# Only the explicit child imports the project. -I excludes cwd/PYTHONPATH/user
# site; -B prevents bytecode writes. No numerical self-check is invoked.
_PROBE = r'''
import hashlib, importlib, importlib.metadata, json, pathlib, sys
from email.parser import Parser
from zipfile import ZipFile
wheel = pathlib.Path(sys.argv[1])
source = pathlib.Path(sys.argv[2]).resolve()
prefix = pathlib.Path(sys.prefix).resolve()
if sys.prefix == sys.base_prefix:
    raise RuntimeError("an explicit virtual environment is required")
settings = dict((key.strip(), value.strip().lower()) for key, value in (line.split("=", 1) for line in (prefix / "pyvenv.cfg").read_text().splitlines() if "=" in line))
if settings.get("include-system-site-packages") != "false":
    raise RuntimeError("system-site-packages must be disabled")
if not (sys.flags.isolated and sys.flags.ignore_environment and sys.flags.no_user_site):
    raise RuntimeError("isolated interpreter flags were not applied")
for entry in sys.path:
    path = pathlib.Path(entry).resolve()
    if path == source or source in path.parents:
        raise RuntimeError("source checkout is present on child sys.path")
    if "site-packages" in path.parts and not path.is_relative_to(prefix):
        raise RuntimeError("external site-packages are present on child sys.path")
distribution = importlib.metadata.distribution("cdrs-e")
site = pathlib.Path(distribution.locate_file("")).resolve()
if not site.is_relative_to(prefix):
    raise RuntimeError("distribution metadata is outside selected virtual environment")
direct_url = distribution.read_text("direct_url.json")
if direct_url and json.loads(direct_url).get("dir_info", {}).get("editable"):
    raise RuntimeError("editable installations are not wheel provenance")
with ZipFile(wheel) as archive:
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError("wheel has duplicate entries")
    package_files = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in names if name.startswith("cdrse/") and not name.endswith("/")}
    metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        raise RuntimeError("wheel metadata identity is ambiguous")
    metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
if distribution.metadata["Name"] != metadata["Name"] or distribution.version != metadata["Version"]:
    raise RuntimeError("installed distribution does not match wheel identity")
for name, expected_hash in package_files.items():
    path = site.joinpath(*pathlib.PurePosixPath(name).parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(prefix):
        raise RuntimeError("installed package path is invalid: " + name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise RuntimeError("installed package bytes differ from wheel: " + name)
actual_files = {path.relative_to(site).as_posix() for path in (site / "cdrse").rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}}
if actual_files != set(package_files):
    raise RuntimeError("installed package has an unexpected or missing file")
package = importlib.import_module("cdrse")
cli = importlib.import_module("cdrse.cli")
version = cli.command_version(None)
if version.get("version") != distribution.version or package.__version__ != distribution.version:
    raise RuntimeError("module and installed distribution versions differ")
modules = {}
for name, module in sorted(sys.modules.items()):
    if name != "cdrse" and not name.startswith("cdrse."):
        continue
    filename = getattr(module, "__file__", None)
    if not filename:
        raise RuntimeError("target module has no verifiable origin: " + name)
    path = pathlib.Path(filename).resolve()
    if not path.is_relative_to(site / "cdrse"):
        raise RuntimeError("target module imported outside installed package: " + name)
    member = path.relative_to(site).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if package_files.get(member) != digest:
        raise RuntimeError("target module bytes are not from wheel: " + name)
    modules[name] = {"path": str(path), "member": member, "sha256": digest}
print(json.dumps({"prefix": str(prefix), "base_prefix": sys.base_prefix, "distribution_root": str(site), "version": version, "modules": modules, "package_files": package_files, "isolated": bool(sys.flags.isolated), "ignore_environment": bool(sys.flags.ignore_environment), "no_user_site": bool(sys.flags.no_user_site), "sys_path": sys.path, "system_site_packages": False}))
'''


def validate_provenance(payload: dict, wheel: Path, source_root: Path = ROOT) -> None:
    """Check returned module origins and hashes against literal wheel payloads."""
    prefix = Path(payload["prefix"]).resolve()
    site = Path(payload["distribution_root"]).resolve()
    if not site.is_relative_to(prefix) or prefix == Path(payload["base_prefix"]).resolve():
        raise RuntimeError("probe did not use a distinct virtual environment installation")
    if payload.get("system_site_packages") is not False or not all(payload.get(key) is True for key in ("isolated", "ignore_environment", "no_user_site")):
        raise RuntimeError("probe isolation evidence is incomplete")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("wheel has duplicate entries")
        expected = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in names if name.startswith("cdrse/") and not name.endswith("/")}
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise RuntimeError("wheel metadata identity is ambiguous")
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
    if payload["package_files"] != expected or payload["version"].get("version") != metadata["Version"]:
        raise RuntimeError("probe package hashes or version differ from wheel")
    modules = payload["modules"]
    if not {"cdrse", "cdrse.cli"} <= set(modules):
        raise RuntimeError("probe omitted required module origins")
    source = source_root.resolve()
    for name, row in modules.items():
        if name != "cdrse" and not name.startswith("cdrse."):
            raise RuntimeError("unexpected module name in provenance")
        path = Path(row["path"]).resolve()
        if not path.is_relative_to(site / "cdrse") or path == source or source in path.parents:
            raise RuntimeError("module origin is outside selected installed package")
        if path.relative_to(site).as_posix() != row["member"] or expected.get(row["member"]) != row["sha256"]:
            raise RuntimeError("module provenance does not match wheel bytes")


def probe_installed_wheel(
    python: Path,
    wheel: Path,
    working_directory: Path,
    *,
    source_root: Path = ROOT,
    timeout_seconds: float = 30,
) -> dict:
    """Run one bounded isolated probe; never install, create a venv or build."""
    working = working_directory.resolve()
    source = source_root.resolve()
    if not working.is_dir() or working == source or source in working.parents:
        raise ValueError("probe cwd must exist outside source checkout")
    if not wheel.is_file() or wheel.suffix != ".whl" or not python.is_file():
        raise ValueError("explicit existing Python interpreter and wheel are required")
    if isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 120:
        raise ValueError("probe timeout must be positive and at most 120 seconds")
    completed = subprocess.run(
        [str(python.absolute()), "-I", "-B", "-c", _PROBE, str(wheel.resolve()), str(source)],
        cwd=working,
        env=sanitised_environment(working),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"installed-wheel probe failed ({completed.returncode}): {completed.stderr}")
    payload = json.loads(completed.stdout)
    validate_provenance(payload, wheel, source)
    return {
        "status": "PASS_INSTALLED_WHEEL_PROVENANCE_ONLY",
        "artifact": wheel.name,
        "artifact_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "working_directory": str(working),
        "provenance": payload,
        "scientific_checks_run": False,
        "sdist_installation_checked": False,
        "scope": "literal installed-wheel package bytes and loaded module origins in supplied isolated venv; not dependency hermeticity or independent-host reproduction",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--working-directory", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = probe_installed_wheel(args.python, args.wheel, args.working_directory)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as destination:
            destination.write(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
