from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from cdrse import cli
from cdrse.algorithms.common import Counters, SolverResult
from cdrse.algorithms.grassmann import leakage_value_gradient, optimise_multistart
from cdrse.certificates import AlgorithmicLayer, DecisionCertificate, EconomicLayer, NumericalLayer, StatisticalLayer
from cdrse.economics import CostComponent, CostLedger, aggregate_scenarios, empirical_cvar, present_value
from cdrse.errors import ValidationError
from cdrse.hashing import canonical_json_bytes
from cdrse.models import SelectionProblem, ServiceConstraints, VARModel
from cdrse.protocols import ExperimentProtocol
from cdrse.reporting import write_json_report

ROOT = Path(__file__).resolve().parents[2]


def test_direct_cli_commands_and_failure(capsys, tmp_path: Path) -> None:
    assert cli.main(["version"]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == "0.1.0rc1"
    assert cli.main(["schema", "result"]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "CDRS-E solver result"
    assert cli.main(["validate-problem", str(ROOT / "examples/forest_problem.json")]) == 0
    capsys.readouterr()
    assert cli.main(["solve-forest", str(ROOT / "examples/forest_problem.json")]) == 0
    capsys.readouterr()
    assert cli.main(["solve-exhaustive", str(ROOT / "examples/forest_problem.json"), "--objective", "cut"]) == 0
    capsys.readouterr()
    assert cli.main(["dd", str(ROOT / "examples/dsrg_witness_model.json"), "0"]) == 0
    capsys.readouterr()
    assert cli.main(["verify-certificate", str(ROOT / "examples/valid_certificate.json")]) == 0
    capsys.readouterr()
    assert cli.main(["validate-protocol", str(ROOT / "examples/frozen_protocol.json")]) == 0
    capsys.readouterr()
    assert cli.main(["witness", "--parameter", "1/2"]) == 0
    capsys.readouterr()
    output = tmp_path / "version.json"
    assert cli.main(["--output", str(output), "version"]) == 0
    assert output.exists()
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert cli.main(["validate-problem", str(bad)]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "FAIL"


def test_direct_cli_self_check(capsys) -> None:
    assert cli.main(["self-check", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"


def test_reporting_and_canonical_extra_types(tmp_path: Path) -> None:
    payload = {"path": tmp_path, "array": np.array([1, 2]), "set": {3, 1}, "scalar": np.int64(4)}
    data = canonical_json_bytes(payload)
    assert b'"set":[1,3]' in data
    report = write_json_report(tmp_path / "report.json", {"b": 2, "a": 1})
    assert report["bytes"] > 0 and len(report["sha256"]) == 64


def test_grassmann_multistart_and_finite_difference_branch() -> None:
    coefficient = np.array([[0.0, 0.5], [0.5, 0.0]])
    objective = lambda q: leakage_value_gradient((coefficient,), q)[0]
    analytic = optimise_multistart(
        2, 1, objective, value_gradient=lambda q: leakage_value_gradient((coefficient,), q), random_starts=4, seed=3, max_iterations=50
    )
    assert analytic["best"]["objective"] < 1e-12
    assert analytic["global_certified"] is False
    numeric = optimise_multistart(2, 1, objective, random_starts=2, seed=4, max_iterations=20)
    assert numeric["best"]["objective"] >= -1e-12
    with pytest.raises(ValidationError):
        optimise_multistart(2, 2, objective)


def test_common_result_validation_paths() -> None:
    counters = Counters(objective_calls=2)
    result = SolverResult("OK", (0,), 1.0, True, True, "done", 1.0, 1.0, counters)
    assert result.optimality_gap == 0.0
    assert result.to_dict()["counters"]["objective_calls"] == 2
    with pytest.raises(ValidationError):
        SolverResult("bad", None, 1.0, False, False, "bad").validate()
    with pytest.raises(ValidationError):
        SolverResult("bad", (0,), 1.0, False, True, "bad", 2.0, 1.0).validate()
    with pytest.raises(ValidationError):
        SolverResult("bad", (0,), 1.0, True, False, "bad").validate()


def test_more_certificate_validation_paths() -> None:
    base = dict(
        problem_sha256="b" * 64,
        selected=(0,),
        algorithmic=AlgorithmicLayer(True, 1.0, 0.0, "done", False),
        numerical=NumericalLayer("float64", True, True, 1e-9, 2.0),
        statistical=StatisticalLayer("estimand", True, 0.05, "confirmatory"),
        economic=EconomicLayer("E2", True, True, "EUR", "2026-09-12"),
    )
    assert DecisionCertificate(**base).regret_upper == 1.0
    with pytest.raises(ValidationError):
        DecisionCertificate(**{**base, "problem_sha256": "bad"}).validate()
    with pytest.raises(ValidationError):
        DecisionCertificate(**{**base, "selected": (0, 0)}).validate()
    with pytest.raises(ValidationError):
        NumericalLayer("", True, True, 0).validate(False)
    with pytest.raises(ValidationError):
        NumericalLayer("float64", False, True, 0).validate(False)
    with pytest.raises(ValidationError):
        NumericalLayer("float64", True, True, -1).validate(False)
    with pytest.raises(ValidationError):
        StatisticalLayer("", False, 0.1).validate()
    with pytest.raises(ValidationError):
        StatisticalLayer("e", True, 1.1).validate()
    with pytest.raises(ValidationError):
        StatisticalLayer("e", False, 0.05, "confirmatory").validate()


def test_more_economic_and_protocol_errors() -> None:
    with pytest.raises(ValidationError):
        present_value([1], 0)
    with pytest.raises(ValidationError):
        empirical_cvar([], 0.5)
    with pytest.raises(ValidationError):
        empirical_cvar([1], 1.0)
    with pytest.raises(ValidationError):
        aggregate_scenarios([1, 2], "mean", [0.2, 0.2])
    with pytest.raises(ValidationError):
        aggregate_scenarios([1, 2], "unknown")
    with pytest.raises(ValidationError):
        CostLedger(()).validate()
    with pytest.raises(ValidationError):
        CostComponent("", 1, "EUR", "E2", "source").validate()
    with pytest.raises(ValidationError):
        CostComponent("x", float("nan"), "u", "E0").validate()
    with pytest.raises(ValidationError):
        ExperimentProtocol("", (1,), ("m",), ("c",), "f", "c", "E0").validate()
    with pytest.raises(ValidationError):
        ExperimentProtocol("x", (1,), (), ("c",), "f", "c", "E0").validate()
    with pytest.raises(ValidationError):
        ExperimentProtocol("x", (1,), ("m",), ("c",), "f", "c", "BAD").validate()


def test_more_model_validation_paths() -> None:
    with pytest.raises(ValidationError):
        VARModel((), np.eye(1))
    with pytest.raises(ValidationError):
        VARModel((np.zeros((2, 3)),), np.eye(2))
    with pytest.raises(ValidationError):
        VARModel((np.array([[0.0, np.nan], [0.0, 0.0]]),), np.eye(2))
    with pytest.raises(ValidationError):
        VARModel((np.zeros((2, 2)),), np.eye(2), ("x",))
    with pytest.raises(ValidationError):
        VARModel((np.zeros((2, 2)),), np.eye(2), ("x", "x"))
    with pytest.raises(ValidationError):
        ServiceConstraints(exact_k=3).validate(2, [1, 1])
    with pytest.raises(ValidationError):
        ServiceConstraints(exact_k=1, mandatory=(0,), forbidden=(0,)).validate(2, [1, 1])
    with pytest.raises(ValidationError):
        ServiceConstraints(exact_k=1, budget=1).validate(2, None)
    with pytest.raises(ValidationError):
        SelectionProblem(None, ServiceConstraints(exact_k=1), (1, 1), information_weight=-1)
