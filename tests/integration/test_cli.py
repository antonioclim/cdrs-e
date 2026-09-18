from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def run(*args: str):
    return subprocess.run([sys.executable, "-m", "cdrse", *args], cwd=ROOT, env=ENV, text=True, capture_output=True)


def test_cli_version_and_schema() -> None:
    result = run("version")
    assert result.returncode == 0
    assert json.loads(result.stdout)["version"] == "0.1.0rc1"
    schema = run("schema", "problem")
    assert schema.returncode == 0 and json.loads(schema.stdout)["title"] == "CDRS-E selection problem"


def test_cli_problem_solvers() -> None:
    problem = str(ROOT / "examples/forest_problem.json")
    validated = run("validate-problem", problem)
    assert validated.returncode == 0
    forest = run("solve-forest", problem)
    payload = json.loads(forest.stdout)
    assert forest.returncode == 0 and payload["selected"] == [0, 2]
    exhaustive = run("solve-exhaustive", problem, "--objective", "cut")
    assert exhaustive.returncode == 0 and json.loads(exhaustive.stdout)["objective"] == payload["objective"]


def test_cli_certificate_protocol_and_witness() -> None:
    valid = run("verify-certificate", str(ROOT / "examples/valid_certificate.json"))
    assert valid.returncode == 0 and json.loads(valid.stdout)["status"] == "PASS"
    invalid = run("verify-certificate", str(ROOT / "examples/invalid_certificate.json"))
    assert invalid.returncode == 2 and json.loads(invalid.stderr)["status"] == "FAIL"
    protocol = run("validate-protocol", str(ROOT / "examples/frozen_protocol.json"))
    assert protocol.returncode == 0 and json.loads(protocol.stdout)["frozen"]
    witness = run("witness", "--parameter", "1/2")
    assert witness.returncode == 0 and json.loads(witness.stdout)["exact_expression"] == "log(5/4)"


def test_cli_dd_self_check_and_output_file(tmp_path: Path) -> None:
    model = str(ROOT / "examples/dsrg_witness_model.json")
    dd = run("dd", model, "0")
    assert dd.returncode == 0
    assert abs(json.loads(dd.stdout)["dd"] - 0.22314355131420976) < 1e-10
    check = run("self-check", "--json")
    assert check.returncode == 0 and json.loads(check.stdout)["licence_selected"] is True
    output = tmp_path / "version.json"
    saved = run("--output", str(output), "version")
    assert saved.returncode == 0 and output.exists()
