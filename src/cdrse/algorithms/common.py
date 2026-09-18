from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import math

from ..errors import ValidationError


@dataclass
class Counters:
    objective_calls: int = 0
    lower_bound_calls: int = 0
    nodes_generated: int = 0
    nodes_expanded: int = 0
    nodes_pruned: int = 0
    transitions_considered: int = 0
    states_stored: int = 0
    peak_frontier: int = 0
    iterations: int = 0
    line_search_evaluations: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class SolverResult:
    status: str
    selected: tuple[int, ...] | None
    objective: float | None
    exact: bool
    certified: bool
    termination_reason: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    counters: Counters = field(default_factory=Counters)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.selected is None and self.objective is not None:
            raise ValidationError("objective cannot exist without a concrete feasible selection")
        for name, value in (("objective", self.objective), ("lower_bound", self.lower_bound), ("upper_bound", self.upper_bound)):
            if value is not None and not math.isfinite(value):
                raise ValidationError(f"{name} must be finite")
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValidationError("lower bound exceeds upper bound")
        if self.exact and not self.certified:
            raise ValidationError("an exact result must be certified")

    def to_record(self) -> dict[str, Any]:
        """Return the adopted authoritative contract, distinct from legacy display."""
        from copy import deepcopy
        if 'result_contract' not in self.metadata:
            raise ValidationError('this algorithm has no adopted result record')
        return deepcopy(self.metadata['result_contract'])

    @property
    def optimality_gap(self) -> float | None:
        self.validate()
        record = self.metadata.get("result_contract")
        if record is not None and record["arithmetic_contract"] == "EXACT_STORED_RATIONAL":
            # Do not obtain a regret enclosure by subtracting rounded displays.
            from fractions import Fraction
            from ..exact_cut import outward
            value = record["regret_upper_bound"]
            if value is None:
                return None
            return outward(Fraction(int(value["numerator"]), int(value["denominator"])), 1)
        if self.lower_bound is None or self.upper_bound is None:
            return None
        return max(0.0, self.upper_bound - self.lower_bound)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "status": self.status,
            "selected": None if self.selected is None else list(self.selected),
            "objective": self.objective,
            "exact": self.exact,
            "certified": self.certified,
            "termination_reason": self.termination_reason,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "optimality_gap": self.optimality_gap,
            "counters": self.counters.to_dict(),
            "metadata": self.metadata,
        }
