"""Compositional layer checks with finite, outward-rounded display semantics.

The arithmetic concerns the supplied integer/binary64 operands. Neither an
``exact_oracle`` flag nor successful layer validation authenticates an oracle,
a statistical event, an economic valuation or the selected set's feasibility in
an external problem. The legacy CLI retains ``certificate_verified=False``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from typing import Any, Mapping

from .errors import ValidationError
from .schemas import validate_json


def _boolean(value: Any, label: str) -> None:
    if type(value) is not bool:
        raise ValidationError(f"{label} must be a boolean")


def _text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be non-empty text")


def _number(value: Any, label: str, *, nonnegative: bool = False) -> None:
    # Do not silently accept bool, numeric strings or a lossy coercion. Keep
    # integer operands exact; a preceding float() would lose large integers.
    if type(value) not in (int, float):
        raise ValidationError(f"{label} must be an integer or binary64 number")
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is outside the finite numeric domain") from exc
    if not finite or (nonnegative and value < 0):
        raise ValidationError(f"{label} must be finite" + (" and non-negative" if nonnegative else ""))


def _upper_display(value: Fraction, label: str) -> float:
    """Least finite binary64 value at or above the exact supplied expression."""
    try:
        shown = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{label} exceeds the finite display range") from exc
    if not math.isfinite(shown):
        raise ValidationError(f"{label} exceeds the finite display range")
    if Fraction(shown) < value:
        shown = math.nextafter(shown, math.inf)
    if not math.isfinite(shown):
        raise ValidationError(f"{label} has no finite outward display endpoint")
    return shown


@dataclass(frozen=True)
class AlgorithmicLayer:
    feasible: bool
    incumbent_upper: float | None
    optimum_lower: float | None
    termination: str
    exact_oracle: bool = False

    def validate(self) -> None:
        _boolean(self.feasible, "algorithmic.feasible")
        _boolean(self.exact_oracle, "algorithmic.exact_oracle")
        _text(self.termination, "algorithmic.termination")
        if self.optimum_lower is not None:
            _number(self.optimum_lower, "algorithmic.optimum_lower")
        if not self.feasible:
            if self.incumbent_upper is not None:
                raise ValidationError("a result without an incumbent cannot carry its objective")
            # This flag is a layer assertion, not a proof of infeasibility.
            return
        if self.incumbent_upper is None or self.optimum_lower is None:
            raise ValidationError("feasible certificate requires lower and upper bounds")
        _number(self.incumbent_upper, "algorithmic.incumbent_upper")
        if self.optimum_lower > self.incumbent_upper:
            raise ValidationError("algorithmic lower bound exceeds incumbent upper bound")


@dataclass(frozen=True)
class NumericalLayer:
    backend: str
    finite: bool
    enclosed: bool
    tolerance: float
    condition_number: float | None = None

    def validate(self, exact_oracle: bool) -> None:
        _boolean(exact_oracle, "exact_oracle")
        _boolean(self.finite, "numerical.finite")
        _boolean(self.enclosed, "numerical.enclosed")
        _text(self.backend, "numerical.backend")
        if not self.finite:
            raise ValidationError("numeric layer reports non-finite values")
        _number(self.tolerance, "numerical.tolerance", nonnegative=True)
        if not exact_oracle and not self.enclosed:
            raise ValidationError("non-exact backend requires a validated enclosure")
        if self.condition_number is not None:
            _number(self.condition_number, "numerical.condition_number")
            if self.condition_number <= 0:
                raise ValidationError("condition number must be finite and positive")


@dataclass(frozen=True)
class StatisticalLayer:
    estimand: str
    simultaneous_coverage: bool
    failure_probability: float
    status: str = "none"

    def validate(self) -> None:
        _text(self.estimand, "statistical.estimand")
        _boolean(self.simultaneous_coverage, "statistical.simultaneous_coverage")
        _number(self.failure_probability, "statistical.failure_probability")
        if not 0 <= self.failure_probability <= 1:
            raise ValidationError("failure_probability must lie in [0,1]")
        if not isinstance(self.status, str) or self.status not in {"none", "exploratory", "confirmatory"}:
            raise ValidationError("unsupported statistical status")
        if self.status == "confirmatory" and not self.simultaneous_coverage:
            raise ValidationError("confirmatory certificate requires simultaneous coverage")


@dataclass(frozen=True)
class EconomicLayer:
    tier: str
    units_declared: bool
    valuation_nonnegative: bool
    currency: str | None = None
    base_date: str | None = None

    def validate(self) -> None:
        if not isinstance(self.tier, str) or self.tier not in {"E0", "E1", "E2", "E3"}:
            raise ValidationError("economic tier must be E0, E1, E2 or E3")
        _boolean(self.units_declared, "economic.units_declared")
        _boolean(self.valuation_nonnegative, "economic.valuation_nonnegative")
        if not self.units_declared or not self.valuation_nonnegative:
            raise ValidationError("economic units and valuation sign must be declared")
        for label, value in (("currency", self.currency), ("base_date", self.base_date)):
            if value is not None:
                _text(value, "economic." + label)
        if self.tier in {"E2", "E3"} and (not self.currency or not self.base_date):
            raise ValidationError("E2/E3 certificate requires currency and base date")


@dataclass(frozen=True)
class DecisionCertificate:
    problem_sha256: str
    selected: tuple[int, ...] | None
    algorithmic: AlgorithmicLayer
    numerical: NumericalLayer
    statistical: StatisticalLayer
    economic: EconomicLayer
    numerical_error: float = 0.0
    statistical_error: float = 0.0
    cost_error: float = 0.0
    valuation_error: float = 0.0
    tolerance: float | None = None
    notes: tuple[str, ...] = ()

    def _exact_discrepancy(self) -> Fraction:
        return sum((Fraction(v) for v in (
            self.numerical_error, self.statistical_error,
            self.cost_error, self.valuation_error)), Fraction(0))

    def _exact_regret(self) -> Fraction | None:
        if not self.algorithmic.feasible:
            return None
        assert self.algorithmic.incumbent_upper is not None
        assert self.algorithmic.optimum_lower is not None
        return (Fraction(self.algorithmic.incumbent_upper)
                - Fraction(self.algorithmic.optimum_lower)
                + 2 * self._exact_discrepancy())

    def validate(self) -> None:
        if (not isinstance(self.problem_sha256, str) or len(self.problem_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in self.problem_sha256)):
            raise ValidationError("problem_sha256 must be a lowercase hexadecimal SHA-256")
        for label, layer, cls in (
            ("algorithmic", self.algorithmic, AlgorithmicLayer),
            ("numerical", self.numerical, NumericalLayer),
            ("statistical", self.statistical, StatisticalLayer),
            ("economic", self.economic, EconomicLayer),
        ):
            if not isinstance(layer, cls):
                raise ValidationError(f"{label} must be a {cls.__name__} instance")
        self.algorithmic.validate()
        if self.algorithmic.feasible is not (self.selected is not None):
            raise ValidationError("incumbent availability contradicts the selected subset")
        if self.selected is not None:
            if (not isinstance(self.selected, (tuple, list))
                    or any(type(i) is not int or i < 0 for i in self.selected)):
                raise ValidationError("selected must contain non-negative integer coordinate indices")
            if len(set(self.selected)) != len(self.selected):
                raise ValidationError("selected subset contains duplicates")
        self.numerical.validate(self.algorithmic.exact_oracle)
        self.statistical.validate()
        self.economic.validate()
        for label in ("numerical_error", "statistical_error", "cost_error", "valuation_error"):
            _number(getattr(self, label), label, nonnegative=True)
        if self.tolerance is not None:
            _number(self.tolerance, "decision tolerance", nonnegative=True)
        if (not isinstance(self.notes, (tuple, list))
                or any(not isinstance(note, str) for note in self.notes)):
            raise ValidationError("notes must be a sequence of text values")
        # Finite operands alone do not imply a finite aggregate. Refuse rather
        # than serialise infinity or let a later threshold check conceal it.
        _upper_display(self._exact_discrepancy(), "discrepancy")
        bound = self._exact_regret()
        if bound is not None:
            _upper_display(bound, "regret upper bound")

    @property
    def discrepancy(self) -> float:
        self.validate()
        return _upper_display(self._exact_discrepancy(), "discrepancy")

    @property
    def regret_upper(self) -> float | None:
        self.validate()
        bound = self._exact_regret()
        return None if bound is None else _upper_display(bound, "regret upper bound")

    @property
    def non_vacuous(self) -> bool | None:
        self.validate()
        if self.tolerance is None:
            return None
        bound = self.regret_upper
        # A conservative display decision. For a very large integer tolerance
        # this may decline a mathematically admissible boundary case; it cannot
        # make a below-expression float into a positive threshold certificate.
        return bound is not None and bound <= self.tolerance

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        value = asdict(self)
        value["selected"] = None if self.selected is None else list(self.selected)
        value["notes"] = list(self.notes)
        value["discrepancy"] = self.discrepancy
        value["regret_upper"] = self.regret_upper
        value["non_vacuous"] = self.non_vacuous
        value["schema_version"] = "0.1.0"
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionCertificate":
        """Validate a serialised layer object without lossy input coercion.

        Complete structured inputs follow the packaged certificate schema. Any
        supplied derived display is an assertion and must match the calculation;
        it is not silently discarded. This is not external evidence validation.
        """
        if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
            raise ValidationError("certificate must be an object with text keys")
        validate_json("certificate", value)
        if "schema_version" in value and value["schema_version"] != "0.1.0":
            raise ValidationError("unsupported certificate schema version")
        obj = cls(
            problem_sha256=value["problem_sha256"],
            selected=None if value["selected"] is None else tuple(value["selected"]),
            algorithmic=AlgorithmicLayer(**value["algorithmic"]),
            numerical=NumericalLayer(**value["numerical"]),
            statistical=StatisticalLayer(**value["statistical"]),
            economic=EconomicLayer(**value["economic"]),
            numerical_error=value["numerical_error"],
            statistical_error=value["statistical_error"],
            cost_error=value["cost_error"],
            valuation_error=value["valuation_error"],
            tolerance=value.get("tolerance"),
            notes=tuple(value.get("notes", ())),
        )
        obj.validate()
        for name, expected in (("discrepancy", obj.discrepancy),
                               ("regret_upper", obj.regret_upper),
                               ("non_vacuous", obj.non_vacuous)):
            if name not in value:
                continue
            actual = value[name]
            if expected is None or type(expected) is bool:
                agrees = actual is expected
            else:
                _number(actual, name, nonnegative=True)
                agrees = actual == expected
            if not agrees:
                raise ValidationError(f"{name} contradicts the derived layer display")
        return obj
