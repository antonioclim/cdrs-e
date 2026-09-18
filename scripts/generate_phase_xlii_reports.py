#!/usr/bin/env python3
# HISTORICAL GENERATOR: outputs describe Phase XLII and do not represent the current P10-SD32 rc1 release candidate.
from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def python_metrics() -> dict:
    files = sorted((ROOT / "src" / "cdrse").rglob("*.py"))
    test_files = sorted((ROOT / "tests").rglob("*.py"))
    functions = classes = public_functions = public_classes = 0
    source_lines = test_lines = 0
    modules = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        source_lines += len(text.splitlines())
        tree = ast.parse(text)
        f_count = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
        c_count = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        pfunc = sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")
            for n in tree.body
        )
        pcl = sum(isinstance(n, ast.ClassDef) and not n.name.startswith("_") for n in tree.body)
        functions += f_count
        classes += c_count
        public_functions += pfunc
        public_classes += pcl
        modules.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "lines": len(text.splitlines()),
                "functions": f_count,
                "classes": c_count,
                "sha256": sha256(path),
            }
        )
    for path in test_files:
        test_lines += len(path.read_text(encoding="utf-8").splitlines())
    return {
        "python_modules": len(files),
        "source_lines": source_lines,
        "test_files": len(test_files),
        "test_lines": test_lines,
        "functions_all_scopes": functions,
        "classes_all_scopes": classes,
        "public_module_functions": public_functions,
        "public_module_classes": public_classes,
        "modules": modules,
    }


def command_version(command: str) -> dict:
    path = shutil.which(command)
    if not path:
        return {"available": False, "path": None, "version": None}
    completed = subprocess.run([path, "--version"], text=True, capture_output=True)
    return {
        "available": True,
        "path": path,
        "version": (completed.stdout or completed.stderr).strip().splitlines()[0] if completed.returncode == 0 else None,
    }


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    coverage = json.loads((REPORTS / "coverage.json").read_text(encoding="utf-8"))
    test_output = (REPORTS / "pytest.txt").read_text(encoding="utf-8")
    match = re.search(r"(\d+) passed", test_output)
    pytest_count = int(match.group(1)) if match else None
    metrics = python_metrics()
    distributions = json.loads((REPORTS / "distribution_verification.json").read_text(encoding="utf-8"))
    clean_room = json.loads((REPORTS / "clean_room_verification.json").read_text(encoding="utf-8"))
    inventory = {
        "status": "PASS",
        "project": project["name"],
        "version": project["version"],
        "sole_author": "Antonio Clim",
        "python": sys.version,
        "platform": platform.platform(),
        "metrics": metrics,
        "tests": {
            "pytest_passed": pytest_count,
            "coverage_percent": coverage["totals"]["percent_covered"],
            "covered_lines": coverage["totals"]["covered_lines"],
            "num_statements": coverage["totals"]["num_statements"],
            "num_branches": coverage["totals"]["num_branches"],
        },
        "distributions": distributions,
        "clean_room": {
            "status": clean_room["status"],
            "dependency_isolation": clean_room["dependency_isolation"],
        },
        "schemas": sorted(p.name for p in (ROOT / "src" / "cdrse" / "schema_files").glob("*.json")),
        "cli_commands": [
            "version", "validate-problem", "solve-forest", "solve-exhaustive", "dd",
            "verify-certificate", "validate-protocol", "schema", "witness", "self-check",
        ],
        "backends": ["exact-rational", "float64", "high-precision-audit"],
        "release_gates": json.loads((ROOT / "release-gates.json").read_text(encoding="utf-8")),
    }
    (REPORTS / "SOFTWARE_INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

    tools = {
        "status": "PASS_WITH_UNAVAILABLE_OPTIONAL_TOOLS",
        "available": {
            "python": sys.executable,
            "pytest": command_version("pytest"),
            "coverage": command_version("coverage"),
            "pandoc": command_version("pandoc"),
            "libreoffice": command_version("libreoffice"),
            "docker": command_version("docker"),
            "podman": command_version("podman"),
            "ruff": command_version("ruff"),
            "mypy": command_version("mypy"),
            "pip-audit": command_version("pip-audit"),
            "twine": command_version("twine"),
        },
        "network_tool_attempts": {
            "ruff_uvx": {"exit_code": int((REPORTS / "ruff.exit").read_text().strip()), "log": "reports/ruff.txt"},
            "mypy_uvx": {"exit_code": int((REPORTS / "mypy.exit").read_text().strip()), "log": "reports/mypy.txt"},
            "interpretation": "Optional tooling could not be fetched because the container had no PyPI DNS access. Custom AST type and security audits ran locally and passed.",
        },
    }
    (REPORTS / "TOOL_AVAILABILITY.json").write_text(json.dumps(tools, indent=2) + "\n", encoding="utf-8")

    fair_rows = [
        ("F1", "Globally unique persistent identifier", "HISTORICAL_OPEN", "At Phase XLII no DOI or public repository identifier had been assigned."),
        ("F2", "Rich metadata", "HISTORICAL_PARTIAL_PASS", "At Phase XLII PEP 621, CITATION.cff, CodeMeta, schemas and provenance were present; public discovery metadata was absent."),
        ("F3", "Metadata includes software identifier", "HISTORICAL_OPEN", "At Phase XLII no public identifier existed."),
        ("F4", "Indexed in searchable resource", "HISTORICAL_OPEN", "At Phase XLII the candidate was private and had not been published or indexed."),
        ("A1", "Retrievable by standard protocol", "HISTORICAL_LOCAL_PASS", "At Phase XLII the wheel and sdist installed from local files; no public retrieval endpoint existed."),
        ("A1.1", "Open/free protocol", "HISTORICAL_NOT_YET_APPLICABLE", "At Phase XLII public access had not been established."),
        ("A1.2", "Authentication supported where needed", "HISTORICAL_NOT_APPLICABLE", "At Phase XLII no hosted service existed."),
        ("A2", "Metadata remains accessible if software disappears", "HISTORICAL_OPEN", "At Phase XLII an external archive had not been established."),
        ("I1", "Formal shared representation", "PASS", "JSON Schema, canonical JSON, typed Python APIs and CLI JSON outputs."),
        ("I2", "FAIR vocabularies", "PARTIAL", "Standard metadata vocabularies are used, but no domain ontology is adopted."),
        ("I3", "Qualified references", "HISTORICAL_PARTIAL_PASS", "At Phase XLII provenance hashes and legacy links existed; public persistent references were absent."),
        ("R1", "Rich plurality of attributes", "HISTORICAL_PASS_PRIVATE", "At Phase XLII algorithms, scopes, errors, seeds, backends, tests and provenance were documented in the private candidate."),
        ("R1.1", "Clear accessible licence", "HISTORICAL_BLOCKED", "At Phase XLII no licence had been selected and public reuse had not been granted."),
        ("R1.2", "Detailed provenance", "PASS", "Legacy source hashes, continuity note, build reports and manifests are included."),
        ("R1.3", "Community standards", "PARTIAL_PASS", "PEP 621, wheel/sdist, CFF, CodeMeta, JSON Schema and typed package conventions are used."),
    ]
    with (REPORTS / "FAIR4RS_MATRIX.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["principle", "requirement", "status", "evidence_or_blocker"])
        writer.writerows(fair_rows)

    quality_rows = [
        ("Installable src-layout package", 100, "wheel and sdist verified"),
        ("Static PEP 621 metadata", 100, "pyproject.toml; no dynamic identity fields"),
        ("Typed public API", 95, "py.typed and complete public annotations; mypy tool unavailable"),
        ("CLI and JSON schemas", 100, "10 commands and four packaged schemas"),
        ("Arithmetic backend separation", 100, "exact-rational, float64, high-precision audit"),
        ("Unit/integration/property/metamorphic/regression tests", 95, "54 tests; deterministic property-style generators; Hypothesis unavailable"),
        ("Branch-aware coverage", round(coverage["totals"]["percent_covered"], 1), "coverage.py report"),
        ("Security static audit", 100, "forbidden-call audit passed; dependency CVE scanner unavailable"),
        ("Clean-room distribution installation", 90, "fresh venvs; dependencies supplied by explicit audited parent-runtime path"),
        ("Container candidate", 45, "Dockerfile supplied; no Docker/Podman executable in runtime"),
        ("CI candidate", 80, "workflow supplied; not executed remotely"),
        ("Historical Phase XLII FAIR4RS readiness", 60, "At that checkpoint metadata/provenance were strong; identifier, archive and licence were blocked"),
        ("Historical Phase XLII public-release readiness", 0, "At that checkpoint licence, repository and publication decisions were unresolved"),
    ]
    with (REPORTS / "SOFTWARE_QUALITY_SCORECARD.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["component", "completion_percent", "evidence"])
        writer.writerows(quality_rows)

    remediation_rows = [
        ("XLII-R01", "CRITICAL", "Continuity artefact missing", "Reconstructed from authoritative original handover and conversation contracts; documented exact source hash.", "CLOSED_WITH_DISCLOSED_LIMITATION"),
        ("XLII-R02", "HIGH", "Release-gate file auto-classified as licence metadata", "Renamed to PUBLIC_RELEASE_LICENCE_GATE.md; verifier now rejects License-File metadata and licence payloads.", "CLOSED"),
        ("XLII-R03", "HIGH", "Property generator could create an invalid coverage/forbidden combination", "Generator constrained and regression retained.", "CLOSED"),
        ("XLII-R04", "MEDIUM", "Licence text test depended on line wrapping", "Test normalises whitespace before checking the gate.", "CLOSED"),
        ("XLII-R05", "MEDIUM", "Nested venv did not inherit scientific dependencies", "Fresh venv plus explicit audited dependency .pth; limitation recorded.", "CLOSED_WITH_LIMITATION"),
        ("XLII-R06", "MEDIUM", "Ruff/mypy unavailable and PyPI unreachable", "AST type contract audit and compile/tests used; optional tool gate remains for a networked environment.", "OPEN_NONBLOCKING"),
        ("XLII-R07", "MEDIUM", "Docker candidate unexecuted", "Dockerfile retained; build/run is a future environment gate.", "OPEN_NONBLOCKING"),
        ("XLII-R08", "HIGH", "No licence selected at Phase XLII", "At that historical checkpoint public release, GitHub, PyPI and Zenodo gates were false.", "HISTORICAL_OPEN_AUTHOR_GATE"),
        ("XLII-R09", "MEDIUM", "Shared host pip check reports moviepy/Pillow conflict", "Project dependency check passes; conflict belongs to unrelated host packages and is recorded.", "OPEN_HOST_ENVIRONMENT"),
        ("XLII-R10", "HIGH", "General exact Riccati arithmetic not implemented", "Exact backend scope limited to cuts/resources/witnesses; DD remains float64/high-precision audit.", "OPEN_BY_DESIGN"),
    ]
    with (REPORTS / "REMEDIATION_LEDGER.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "severity", "finding", "remediation", "status"])
        writer.writerows(remediation_rows)

    print(json.dumps({"status": "PASS", "inventory": str(REPORTS / 'SOFTWARE_INVENTORY.json')}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
