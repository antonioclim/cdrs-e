#!/usr/bin/env python3
"""Historical helper name: fresh installs with host dependencies, not a clean machine.

Local wheel/sdist only; package indexes disabled. Results do not establish
hermetic dependency resolution or independent-platform reproduction.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import site
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {command}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")
    return completed.stdout


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifact(artifact: Path, label: str, root: Path) -> dict:
    environment = root / label
    run([sys.executable, "-m", "venv", str(environment)])
    python = environment / "bin" / "python"
    pip = environment / "bin" / "pip"
    # The active runtime is itself a virtual environment. PEP 405 does not
    # expose the parent venv through --system-site-packages, so add an explicit
    # read-only dependency path while keeping the candidate distribution isolated.
    target_site = Path(run([str(python), "-c", "import site; print(site.getsitepackages()[0])"]).strip())
    audited_sites = [Path(x) for x in site.getsitepackages() if Path(x).is_dir()]
    (target_site / "cdrse_audited_dependencies.pth").write_text("\n".join(str(x) for x in audited_sites) + "\n", encoding="utf-8")
    command = [str(pip), "install", "--no-index", "--no-deps"]
    if artifact.suffixes[-2:] == [".tar", ".gz"]:
        command.append("--no-build-isolation")
    command.append(str(artifact))
    install_log = run(command)
    version = json.loads(run([str(python), "-m", "cdrse", "version"]))
    self_check = json.loads(run([str(python), "-m", "cdrse", "self-check", "--json"]))
    schema = json.loads(run([str(python), "-m", "cdrse", "schema", "certificate"]))
    if version["version"] != tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] or self_check["status"] != "PASS":
        raise RuntimeError("clean-room semantic check failed")
    return {
        "artifact": artifact.name,
        "artifact_sha256": digest(artifact),
        "version": version,
        "self_check": self_check,
        "certificate_schema_title": schema["title"],
        "install_log_tail": install_log.splitlines()[-5:],
    }


def main() -> int:
    wheel = next(DIST.glob("*.whl"))
    sdist = next(DIST.glob("*.tar.gz"))
    with tempfile.TemporaryDirectory(prefix="cdrse-clean-room-") as directory:
        root = Path(directory)
        result = {
            "status": "PASS",
            "dependency_isolation": "candidate distribution installed into fresh venvs; binary scientific dependencies supplied through an explicit .pth to the audited parent runtime",
            "wheel": verify_artifact(wheel, "wheel_env", root),
            "sdist": verify_artifact(sdist, "sdist_env", root),
        }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "clean_room_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
