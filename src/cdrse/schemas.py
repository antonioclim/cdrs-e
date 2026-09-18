from __future__ import annotations

from importlib.resources import files
from typing import Any, Mapping
import json

from jsonschema import Draft202012Validator

from .errors import ValidationError


SCHEMAS = {
    "problem": "problem.schema.json",
    "certificate": "certificate.schema.json",
    "protocol": "protocol.schema.json",
    "result": "result.schema.json",
    "result_contract": "result_contract.schema.json",
}


def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValidationError(f"unknown schema: {name}")
    resource = files("cdrse.schema_files").joinpath(SCHEMAS[name])
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_json(name: str, value: Mapping[str, Any]) -> None:
    validator = Draft202012Validator(load_schema(name))
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        message = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
        )
        raise ValidationError(message)
