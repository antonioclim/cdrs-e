"""Protocol objects that prevent outcome-driven changes."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence

from .errors import ValidationError
from .hashing import object_sha256


@dataclass(frozen=True)
class ExperimentProtocol:
    protocol_id: str
    random_seeds: tuple[int, ...]
    metrics: tuple[str, ...]
    comparators: tuple[str, ...]
    failure_policy: str
    chronology: str
    cost_tier: str
    frozen: bool = False

    def validate(self) -> None:
        if not self.protocol_id.strip():
            raise ValidationError("protocol_id is missing")
        if not self.random_seeds or len(set(self.random_seeds)) != len(self.random_seeds):
            raise ValidationError("protocol requires unique deterministic seeds")
        if not self.metrics or not self.comparators:
            raise ValidationError("protocol requires metrics and comparators")
        if not self.failure_policy.strip() or not self.chronology.strip():
            raise ValidationError("failure policy and chronology are mandatory")
        if self.cost_tier not in {"E0", "E1", "E2", "E3"}:
            raise ValidationError("invalid cost tier")

    @property
    def sha256(self) -> str:
        self.validate()
        return object_sha256(asdict(self))

    def freeze(self) -> "ExperimentProtocol":
        self.validate()
        return ExperimentProtocol(**{**asdict(self), "frozen": True})
