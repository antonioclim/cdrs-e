"""Canonical serialisation and cryptographic identity helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np


def _normalise(value: Any) -> Any:
    if is_dataclass(value):
        return _normalise(asdict(value))
    if isinstance(value, np.ndarray):
        return _normalise(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical JSON mappings require string keys")
        return {key: _normalise(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if isinstance(value, set | frozenset):
        return sorted(_normalise(v) for v in value)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for supported scientific objects."""
    return json.dumps(
        _normalise(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
