"""Economic resources, Pareto frontiers and finite scenario aggregation.

Arithmetic uses the exact values of supplied real operands, then rounds public
scalar displays once to binary64. Such displays are not validated enclosures and
do not authenticate an objective, a source or a monetary valuation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, asdict
from fractions import Fraction
from numbers import Integral, Rational, Real
import math

from .errors import ValidationError


def _real_fraction(value: object, label: str) -> Fraction:
    """Preserve real operands without boolean/string or integer coercion loss."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{label} must be a finite real number, not a boolean")
    if isinstance(value, Integral):
        return Fraction(int(value))
    if isinstance(value, Rational):
        return Fraction(int(value.numerator), int(value.denominator))
    try:
        numerator, denominator = value.as_integer_ratio()
        return Fraction(int(numerator), int(denominator))
    except (AttributeError, OverflowError, ValueError, TypeError) as exc:
        raise ValidationError(f"{label} must be a finite real number") from exc


def _nearest_finite(value: Fraction, label: str) -> float:
    """One nearest conversion, with explicit refusal of a non-finite display."""
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{label} has no finite binary64 result") from exc
    if not math.isfinite(result):
        raise ValidationError(f"{label} has no finite binary64 result")
    return result


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be non-empty text")
    return value


def _real_values(values: Iterable[float], label: str, *, allow_empty: bool = False) -> tuple[Fraction, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValidationError(f"{label} must be an iterable of finite real numbers")
    try:
        entries = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{label} must be an iterable of finite real numbers") from exc
    if not entries and not allow_empty:
        raise ValidationError(f"{label} requires at least one value")
    return tuple(_real_fraction(value, f"{label}[{i}]") for i, value in enumerate(entries))


@dataclass(frozen=True)
class CostComponent:
    name: str
    value: float
    unit: str
    evidence_tier: str
    source: str | None = None
    uncertainty_lower: float | None = None
    uncertainty_upper: float | None = None

    def validate(self) -> None:
        _text(self.name, "cost name")
        _text(self.unit, "cost unit")
        value = _real_fraction(self.value, "cost value")
        if not isinstance(self.evidence_tier, str) or self.evidence_tier not in {"E0", "E1", "E2", "E3"}:
            raise ValidationError("evidence_tier must be one of E0, E1, E2 or E3")
        if self.source is not None:
            _text(self.source, "cost source")
        if self.evidence_tier in {"E2", "E3"} and self.source is None:
            raise ValidationError("monetary or decision-value components require provenance")
        if (self.uncertainty_lower is None) != (self.uncertainty_upper is None):
            raise ValidationError("uncertainty interval requires both endpoints")
        if self.uncertainty_lower is not None:
            lower = _real_fraction(self.uncertainty_lower, "uncertainty lower endpoint")
            upper = _real_fraction(self.uncertainty_upper, "uncertainty upper endpoint")
            if not lower <= value <= upper:
                raise ValidationError("uncertainty interval must contain the stated value")


@dataclass(frozen=True)
class CostLedger:
    components: tuple[CostComponent, ...]

    def validate(self) -> None:
        if not isinstance(self.components, Sequence) or not self.components:
            raise ValidationError("cost ledger requires a non-empty component sequence")
        for component in self.components:
            if not isinstance(component, CostComponent):
                raise ValidationError("cost ledger entries must be CostComponent objects")
            component.validate()

    @property
    def units(self) -> tuple[str, ...]:
        self.validate()
        return tuple(sorted({component.unit for component in self.components}))

    def scalar_total(self) -> float:
        self.validate()
        if len(self.units) != 1:
            raise ValidationError("non-commensurate units cannot be summed without a valuation model")
        exact = sum((_real_fraction(c.value, "cost value") for c in self.components), Fraction(0))
        return _nearest_finite(exact, "cost total")

    def to_dict(self) -> dict:
        self.validate()
        return {"components": [asdict(component) for component in self.components], "units": list(self.units)}


def present_value(stream: Sequence[float], discount_factor: float) -> float:
    discount = _real_fraction(discount_factor, "discount_factor")
    if not 0 < discount <= 1:
        raise ValidationError("discount_factor must lie in (0,1]")
    values = _real_values(stream, "cash/resource stream", allow_empty=True)
    total, power = Fraction(0), Fraction(1)
    for value in values:
        total += power * value
        power *= discount
    return _nearest_finite(total, "present value")


def scalarised_decision_value(cost: float, information_loss: float, currency_per_nat: float, predictions: float = 1.0) -> float:
    c = _real_fraction(cost, "cost")
    loss = _real_fraction(information_loss, "information_loss")
    valuation = _real_fraction(currency_per_nat, "currency_per_nat")
    count = _real_fraction(predictions, "predictions")
    if loss < 0 or valuation < 0 or count < 0:
        raise ValidationError("information loss, valuation and prediction count must be non-negative")
    return _nearest_finite(c + valuation * count * loss / 2, "scalarised decision value")


def _scenario_configuration(count: int, mode: str, probabilities: Sequence[float] | None, alpha: float) -> tuple[str, tuple[Fraction, ...] | None, Fraction | None]:
    """Validate configuration before any scenario callback is evaluated."""
    if count < 1:
        raise ValidationError("scenario aggregation requires at least one scenario")
    normalised = _text(mode, "scenario mode").strip().lower()
    if normalised not in {"mean", "worst", "cvar"}:
        raise ValidationError("scenario mode must be mean, worst or cvar")
    if normalised == "cvar":
        if probabilities is not None:
            raise ValidationError("reference CVaR currently supports equiprobable scenarios only")
        a = _real_fraction(alpha, "alpha")
        if not 0 <= a < 1:
            raise ValidationError("alpha must lie in [0,1)")
        return normalised, None, a
    weights = None
    if probabilities is not None:
        weights = _real_values(probabilities, "scenario probabilities")
        if len(weights) != count:
            raise ValidationError("probability vector length mismatch")
        if any(weight < 0 for weight in weights):
            raise ValidationError("scenario probabilities must be non-negative and sum to one")
        total = _nearest_finite(sum(weights, Fraction(0)), "probability sum")
        # Preserve the previous acceptance tolerance. Accepted weights are used
        # as supplied, not silently renormalised or interpreted as provenance.
        if not math.isclose(total, 1.0, abs_tol=1e-10):
            raise ValidationError("scenario probabilities must be non-negative and sum to one")
    return normalised, weights, None


def _aggregate_exact(values: tuple[Fraction, ...], configuration: tuple[str, tuple[Fraction, ...] | None, Fraction | None]) -> Fraction:
    mode, weights, alpha = configuration
    if mode == "worst":
        return max(values)
    if mode == "mean":
        if weights is None:
            return sum(values, Fraction(0)) / len(values)
        return sum((p * v for p, v in zip(weights, values)), Fraction(0))
    # The caller validated a finite alpha in [0,1), so tail mass is positive.
    tail_mass = (1 - alpha) * len(values)
    remaining, total = tail_mass, Fraction(0)
    for value in sorted(values, reverse=True):
        take = min(Fraction(1), remaining)
        total += take * value
        remaining -= take
        if remaining == 0:
            break
    return total / tail_mass


def empirical_cvar(values: Sequence[float], alpha: float) -> float:
    """Upper-tail equiprobable empirical CVaR, with one final float conversion."""
    exact_values = _real_values(values, "scenario values")
    configuration = _scenario_configuration(len(exact_values), "cvar", None, alpha)
    return _nearest_finite(_aggregate_exact(exact_values, configuration), "CVaR")


def aggregate_scenarios(values: Sequence[float], mode: str, probabilities: Sequence[float] | None = None, alpha: float = 0.5) -> float:
    exact_values = _real_values(values, "scenario values")
    configuration = _scenario_configuration(len(exact_values), mode, probabilities, alpha)
    return _nearest_finite(_aggregate_exact(exact_values, configuration), "scenario aggregate")


def _points(records: Iterable[Mapping[str, object]], cost_key: str, loss_key: str) -> list[tuple[Fraction, Fraction, dict[str, object]]]:
    _text(cost_key, "cost_key")
    _text(loss_key, "loss_key")
    try:
        iterator = iter(records)
    except TypeError as exc:
        raise ValidationError("frontier records must be iterable mappings") from exc
    rows = []
    for record in iterator:
        if not isinstance(record, Mapping) or cost_key not in record or loss_key not in record:
            raise ValidationError("frontier record requires the declared cost and loss fields")
        point = dict(record)
        rows.append((_real_fraction(point[cost_key], cost_key),
                     _real_fraction(point[loss_key], loss_key), point))
    return rows


def pareto_front(records: Iterable[Mapping[str, object]], cost_key: str = "cost", loss_key: str = "loss") -> list[dict[str, object]]:
    """Keep all nondominated labels, comparing the supplied coordinates exactly."""
    points = _points(records, cost_key, loss_key)
    front = [(c, loss, row) for c, loss, row in points if not any(
        oc <= c and ol <= loss and (oc < c or ol < loss) for oc, ol, _ in points)]
    return [row for _, _, row in sorted(front, key=lambda p: (p[0], p[1], repr(p[2])))]


def supported_points(front: Sequence[Mapping[str, object]], cost_key: str = "cost", loss_key: str = "loss") -> list[dict[str, object]]:
    """Return extreme lower-hull representatives of a nondominated front.

Exact duplicates use deterministic repr-based label selection. Collinear
interior ties are not listed: this is a vertex routine, not all supported labels.
No tolerance merges distinct finite coordinates or changes an orientation sign.
"""
    ordered = sorted(_points(front, cost_key, loss_key), key=lambda p: (p[0], p[1], repr(p[2])))
    unique = []
    for point in ordered:
        if unique and point[0] == unique[-1][0]:
            # Losses are sorted ascending, so the first exact-cost entry is best.
            continue
        unique.append(point)
    hull = []
    for point in unique:
        while len(hull) >= 2:
            x1, y1, _ = hull[-2]
            x2, y2, _ = hull[-1]
            x3, y3, _ = point
            cross = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
            if cross <= 0:
                hull.pop()
            else:
                break
        hull.append(point)
    return [row for _, _, row in hull]
