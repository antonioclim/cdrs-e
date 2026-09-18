from __future__ import annotations

import json
from pathlib import Path

import pytest

from cdrse.errors import ValidationError
from cdrse.protocols import ExperimentProtocol
from cdrse.schemas import load_schema, validate_json

ROOT = Path(__file__).resolve().parents[2]


def test_all_packaged_schemas_load() -> None:
    for name in ("problem", "certificate", "protocol", "result"):
        schema = load_schema(name)
        assert schema["$schema"].endswith("2020-12/schema")


def test_example_problem_and_protocol_validate() -> None:
    problem = json.loads((ROOT / "examples/forest_problem.json").read_text())
    protocol = json.loads((ROOT / "examples/frozen_protocol.json").read_text())
    validate_json("problem", problem)
    validate_json("protocol", protocol)


def test_invalid_schema_and_payload() -> None:
    with pytest.raises(ValidationError):
        load_schema("missing")
    with pytest.raises(ValidationError):
        validate_json("problem", {"constraints": {}, "activation_costs": []})


def test_protocol_freeze_and_hash() -> None:
    protocol = ExperimentProtocol(
        "x", (1, 2), ("loss",), ("random",), "retain failures", "chronological", "E0"
    )
    frozen = protocol.freeze()
    assert frozen.frozen
    assert len(frozen.sha256) == 64
    with pytest.raises(ValidationError):
        ExperimentProtocol("x", (1, 1), ("loss",), ("r",), "f", "c", "E0").validate()
