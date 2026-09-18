"""Deterministic JSON reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import json

from .hashing import object_sha256


def write_json_report(path: str | Path, payload: Mapping[str, Any]) -> dict[str, str | int]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    destination.write_text(text, encoding="utf-8")
    return {"path": destination.as_posix(), "sha256": object_sha256(payload), "bytes": len(text.encode("utf-8"))}
