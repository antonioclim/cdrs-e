"""Finite QA2 regressions for CLI contracts, selected-run labels and backend inputs.

The Grassmann witnesses use two coordinates, one retained direction and zero
optimisation steps. They exercise actual gradient/convergence reporting rather
than assuming that a multistart return constitutes stationarity.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from cdrse import cli
from cdrse.algorithms.grassmann import optimise_multistart
from cdrse.backends import HighPrecisionAuditBackend
from cdrse.errors import ValidationError


@pytest.mark.parametrize(
    "kind",
    ["unknown_argument", "missing_command", "missing_operand", "missing_key",
     "non_object", "non_array", "bad_channel_names", "non_numeric"],
)
def test_cli_expected_errors_are_json(kind, tmp_path, capsys):
    model = tmp_path / "model.json"
    output = tmp_path / "result.json"
    payload = {"coefficients": [[[0.0]]], "innovation_covariance": [[1.0]]}
    args = ["--output", str(output), "dd", str(model), "0"]
    if kind == "unknown_argument":
        args = ["--unknown-qa2-argument"]
    elif kind == "missing_command":
        args = []
    elif kind == "missing_operand":
        args = ["dd"]
    elif kind == "missing_key":
        payload = {}
    elif kind == "non_object":
        payload = []
    elif kind == "non_array":
        payload["coefficients"] = None
    elif kind == "bad_channel_names":
        payload["channel_names"] = [[]]
    elif kind == "non_numeric":
        payload["coefficients"] = [[["not-a-number"]]]
    model.write_text(json.dumps(payload), encoding="utf-8")
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    error = json.loads(captured.err)
    assert error["status"] == "FAIL" and error["error"]
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_cli_help_is_distinct(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out and captured.err == ""


def test_cli_version_success_is_json(capsys):
    assert cli.main(["version"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["name"] == "cdrs-e"
    assert captured.err == ""


def test_cli_zero_denominator_witness_is_json(tmp_path, capsys):
    output = tmp_path / "result.json"
    assert cli.main(["--output", str(output), "witness", "--parameter", "1/0"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["status"] == "FAIL"
    assert "non-zero denominator" in payload["error"]
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_cli_unexpected_internal_failure_is_not_hidden(monkeypatch):
    def broken_handler(args):
        raise RuntimeError("QA2 synthetic internal defect")
    monkeypatch.setattr(cli, "command_version", broken_handler)
    with pytest.raises(RuntimeError, match="synthetic internal defect"):
        cli.main(["version"])


@pytest.mark.parametrize("kind", ["all_nonconvergent", "selected_nonconvergent", "selected_convergent"])
def test_grassmann_status_follows_selected_run(kind):
    starts = []
    if kind == "all_nonconvergent":
        def objective(q):
            return float(q[0, 0] * q[1, 0])
        def value_gradient(q):
            return objective(q), np.array([[q[1, 0]], [q[0, 0]]])
    elif kind == "selected_nonconvergent":
        starts = [np.array([[1.0], [1.0]]) / np.sqrt(2.0)]
        def objective(q):
            return float(q[0, 0] ** 2)
        def value_gradient(q):
            return objective(q), np.array([[2.0 * q[0, 0]], [0.0]])
    else:
        def objective(q):
            return float(q[1, 0] ** 2)
        def value_gradient(q):
            return objective(q), np.array([[0.0], [2.0 * q[1, 0]]])
    result = optimise_multistart(
        2, 1, objective, value_gradient=value_gradient, starts=starts,
        random_starts=0, max_iterations=0, seed=0,
    )
    assert result["global_certified"] is False
    selected = result["best"]
    assert selected == result["runs"][selected["start_index"]]
    if kind == "selected_convergent":
        assert selected["converged"] is True
        assert result["status"] == "NUMERICALLY_STATIONARY_MULTISTART_BASELINE"
        assert result["certificate_scope"] == "first_order_stationarity_only"
    else:
        assert selected["converged"] is False
        assert result["status"] == "MULTISTART_CANDIDATE_NOT_CONVERGED"
        assert result["certificate_scope"] == "none"
        if kind == "all_nonconvergent":
            assert not any(run["converged"] for run in result["runs"])
        else:
            assert any(run["converged"] for run in result["runs"])


@pytest.mark.parametrize("tolerance", [float("nan"), float("inf"), -float("inf"), "nan", "inf", "0", "-1", "invalid", True, np.bool_(True)])
def test_backend_rejects_invalid_tolerance(tolerance):
    with pytest.raises(ValidationError):
        HighPrecisionAuditBackend(30, tolerance, max_iterations=1)


@pytest.mark.parametrize("digits", [True, 30.5, "30", 29])
def test_backend_rejects_invalid_precision(digits):
    with pytest.raises(ValidationError):
        HighPrecisionAuditBackend(digits, "1e-20", max_iterations=1)


@pytest.mark.parametrize("iterations", [True, 1.5, "2", 0, -1])
def test_backend_rejects_invalid_iteration_limit(iterations):
    with pytest.raises(ValidationError):
        HighPrecisionAuditBackend(30, "1e-20", max_iterations=iterations)


@pytest.mark.parametrize("digits,iterations,tolerance", [(30, 1, "1e-20"), (np.int64(30), np.int64(2), 0.5)])
def test_backend_accepts_documented_boundaries(digits, iterations, tolerance):
    backend = HighPrecisionAuditBackend(digits, tolerance, max_iterations=iterations)
    assert backend.decimal_digits == 30
    assert backend.max_iterations == int(iterations)
    assert backend.tolerance > 0
