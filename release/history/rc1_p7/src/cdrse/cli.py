from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

from . import __version__
from .algorithms import solve_exhaustive, solve_forest_cut
from .algorithms.branch_bound import solve_branch_bound
from .verification import verify_solver_payload
from .backends import ExactRationalBackend, HighPrecisionAuditBackend
from .certificates import DecisionCertificate
from .errors import CDRSError, ValidationError
from .models import SelectionProblem, VARModel
from .objectives import coordinate_dd, directed_cut, dsrg_swap_witness
from .protocols import ExperimentProtocol
from .reporting import write_json_report
from .schemas import load_schema, validate_json


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(payload: dict, output: str | None) -> None:
    if output:
        write_json_report(output, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))


def command_version(_: argparse.Namespace) -> dict:
    return {
        "name": "cdrs-e",
        "version": __version__,
        "release_candidate": True,
        "release_channel": "release-candidate",
        "publication_profile": "publication-durable",
        "canonical_repository": "https://github.com/antonioclim/cdrs-e",
        "licence_selected": True,
        "licence": "Apache-2.0",
    }


def command_validate_problem(args: argparse.Namespace) -> dict:
    payload = _read_json(args.problem)
    validate_json("problem", payload)
    problem = SelectionProblem.from_dict(payload)
    return {"status": "PASS", "problem_sha256": problem.sha256, "n": problem.n}


def command_solve_forest(args: argparse.Namespace) -> dict:
    payload = _read_json(args.problem)
    validate_json("problem", payload)
    problem = SelectionProblem.from_dict(payload)
    result = solve_forest_cut(problem)
    return result.to_dict()


def command_solve_exhaustive(args: argparse.Namespace) -> dict:
    payload = _read_json(args.problem)
    validate_json("problem", payload)
    problem = SelectionProblem.from_dict(payload)
    if args.objective == "cut":
        if problem.cut_weights is None:
            raise ValidationError("cut objective requires cut_weights")
        objective = None
    elif args.objective == "dd":
        if problem.model is None:
            raise ValidationError("DD objective requires model")
        objective = lambda subset: coordinate_dd(problem.model, subset)[0]
    else:
        raise ValidationError("objective must be cut or dd")
    result = solve_exhaustive(problem, objective)
    return result.to_dict()


def command_solve_bnb(args: argparse.Namespace) -> dict:
    payload = _read_json(args.problem)
    validate_json("problem", payload)
    problem = SelectionProblem.from_dict(payload)
    result, _ = solve_branch_bound(problem, max_nodes=args.max_nodes, max_calls=args.max_calls, time_limit=args.time_limit)
    return result.to_dict()


def command_verify_result(args: argparse.Namespace) -> dict:
    payload = _read_json(args.problem)
    validate_json("problem", payload)
    problem = SelectionProblem.from_dict(payload)
    data = _read_json(args.result)
    return verify_solver_payload(problem, data, max_vertices=args.max_vertices)


def command_dd(args: argparse.Namespace) -> dict:
    model_payload = _read_json(args.model)
    model = VARModel.from_dict(model_payload)
    subset = tuple(int(token) for token in args.subset.split(",") if token.strip())
    value, diagnostics = coordinate_dd(model, subset, tolerance=args.tolerance)
    return {"status": "PASS", "subset": list(subset), "dd": value, "diagnostics": diagnostics.to_dict()}


def command_verify_certificate(args: argparse.Namespace) -> dict:
    payload = _read_json(args.certificate)
    validate_json("certificate", payload)
    certificate = DecisionCertificate.from_dict(payload)
    certificate.validate()
    return {
        "status": "PASS",
        "scope": "legacy layer consistency only; no problem or objective replay",
        "certificate_verified": False,
        "regret_upper": certificate.regret_upper,
        "non_vacuous": certificate.non_vacuous,
    }


def command_validate_protocol(args: argparse.Namespace) -> dict:
    payload = _read_json(args.protocol)
    validate_json("protocol", payload)
    protocol = ExperimentProtocol(
        protocol_id=payload["protocol_id"],
        random_seeds=tuple(payload["random_seeds"]),
        metrics=tuple(payload["metrics"]),
        comparators=tuple(payload["comparators"]),
        failure_policy=payload["failure_policy"],
        chronology=payload["chronology"],
        cost_tier=payload["cost_tier"],
        frozen=payload["frozen"],
    )
    protocol.validate()
    return {"status": "PASS", "protocol_sha256": protocol.sha256, "frozen": protocol.frozen}


def command_schema(args: argparse.Namespace) -> dict:
    return load_schema(args.name)


def command_witness(args: argparse.Namespace) -> dict:
    parameter = Fraction(args.parameter)
    exact = ExactRationalBackend.dsrg_swap_witness(parameter)
    numeric = dsrg_swap_witness(float(parameter))
    return {"status": "PASS", "exact_expression": str(exact), "numeric": numeric}


def command_self_check(args: argparse.Namespace) -> dict:
    witness = dsrg_swap_witness(0.5)
    model = VARModel(
        coefficients=(np.array([[0.0, 0.5], [0.5, 0.0]]),),
        innovation_covariance=np.eye(2),
    )
    high_precision, audit = HighPrecisionAuditBackend(decimal_digits=50, tolerance="1e-38").projected_var_dd(
        model, np.array([[1.0], [0.0]])
    )
    exact = ExactRationalBackend.dsrg_swap_witness("1/2")
    difference = abs(float(high_precision) - witness["coordinate_dd"])
    if difference > 1e-9:
        raise ValidationError("float64 and high-precision witness disagree")
    return {
        "status": "PASS",
        "version": __version__,
        "float64_witness": witness,
        "exact_expression": str(exact),
        "high_precision_value": str(high_precision),
        "high_precision_audit": audit,
        "float64_high_precision_difference": difference,
        "release_candidate": True,
        "release_channel": "release-candidate",
        "publication_profile": "publication-durable",
        "canonical_repository": "https://github.com/antonioclim/cdrs-e",
        "licence_selected": True,
        "licence": "Apache-2.0",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cdrse", description="Auditable CDRS-E research software release candidate")
    parser.add_argument("--output", help="write JSON output to this path")
    sub = parser.add_subparsers(dest="command", required=True)
    version = sub.add_parser("version", help="print package version and release status")
    version.set_defaults(handler=command_version)
    validate_problem = sub.add_parser("validate-problem", help="validate a selection-problem JSON document")
    validate_problem.add_argument("problem")
    validate_problem.set_defaults(handler=command_validate_problem)
    forest = sub.add_parser("solve-forest", help="solve an integral-budget forest cut problem")
    forest.add_argument("problem")
    forest.set_defaults(handler=command_solve_forest)
    exhaustive = sub.add_parser("solve-exhaustive", help="solve a small problem by complete enumeration")
    exhaustive.add_argument("problem")
    exhaustive.add_argument("--objective", choices=["cut", "dd"], default="cut")
    exhaustive.set_defaults(handler=command_solve_exhaustive)
    dd = sub.add_parser("dd", help="evaluate coordinate DD for a model and comma-separated subset")
    dd.add_argument("model")
    dd.add_argument("subset")
    dd.add_argument("--tolerance", type=float, default=1e-11)
    dd.set_defaults(handler=command_dd)
    certificate = sub.add_parser("verify-certificate", help="validate a decision certificate")
    certificate.add_argument("certificate")
    certificate.set_defaults(handler=command_verify_certificate)
    protocol = sub.add_parser("validate-protocol", help="validate an experiment protocol")
    protocol.add_argument("protocol")
    protocol.set_defaults(handler=command_validate_protocol)
    schema = sub.add_parser("schema", help="print a packaged JSON schema")
    schema.add_argument("name", choices=["problem", "certificate", "protocol", "result", "result_contract"])
    schema.set_defaults(handler=command_schema)
    witness = sub.add_parser("witness", help="evaluate the exact two-channel DSRG witness")
    witness.add_argument("--parameter", default="1/2")
    witness.set_defaults(handler=command_witness)
    self_check = sub.add_parser("self-check", help="run deterministic cross-backend checks")
    self_check.add_argument("--json", action="store_true", help="retained for explicit machine-readable intent")
    self_check.set_defaults(handler=command_self_check)
    bnb = sub.add_parser("solve-bnb", help="exact stored weighted-cut search with explicit budgets")
    bnb.add_argument("problem")
    bnb.add_argument("--max-nodes", type=int)
    bnb.add_argument("--max-calls", type=int)
    bnb.add_argument("--time-limit", type=float)
    bnb.set_defaults(handler=command_solve_bnb)
    replay = sub.add_parser("verify-result", help="independently enumerate a small stored-cut problem and check its result")
    replay.add_argument("problem")
    replay.add_argument("result")
    replay.add_argument("--max-vertices", type=int, default=16)
    replay.set_defaults(handler=command_verify_result)
    for command in sub.choices.values():
        command.add_argument("--output", default=argparse.SUPPRESS, help="write JSON (also accepted before subcommand)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
        _write(payload, args.output)
        return 0
    except (CDRSError, ValueError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
