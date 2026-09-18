"""Validated model and problem objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
import math

import numpy as np
from numpy.typing import NDArray

from .errors import ValidationError
from .exact_cut import rational
from .hashing import object_sha256

Array = NDArray[np.float64]


def _is_real_scalar(value: Any) -> bool:
    return not isinstance(value, (bool, np.bool_)) and isinstance(
        value, (int, float, np.integer, np.floating)
    )


def _require_finite_real(value: Any, label: str, *, nonnegative: bool = False) -> None:
    if not _is_real_scalar(value):
        raise ValidationError(f"{label} must be a real numerical scalar")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValidationError(f"{label} must be finite")
    if nonnegative and numeric < 0:
        raise ValidationError(f"{label} must be non-negative")


def _strict_float_array(value: Any, label: str) -> Array:
    try:
        raw = np.asarray(value, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is not a regular numerical array") from exc
    for item in raw.flat:
        if not _is_real_scalar(item):
            raise ValidationError(f"{label} contains a non-numerical or boolean entry")
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError(f"{label} cannot be represented as binary64") from exc


def canonical_subset(items: Iterable[int], n: int | None = None) -> tuple[int, ...]:
    values = tuple(items)
    if any(isinstance(i, (bool, np.bool_)) or not isinstance(i, (int, np.integer)) for i in values):
        raise ValidationError("subset indices must be integers")
    out = tuple(sorted(int(i) for i in values))
    if len(set(out)) != len(out):
        raise ValidationError("subset contains duplicate indices")
    if n is not None and any(i < 0 or i >= n for i in out):
        raise ValidationError("subset index outside the ground set")
    return out


@dataclass(frozen=True)
class VARModel:
    coefficients: tuple[Array, ...]
    innovation_covariance: Array
    channel_names: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        coefficients = tuple(_strict_float_array(a, "lag matrix") for a in self.coefficients)
        covariance = _strict_float_array(self.innovation_covariance, "innovation covariance")
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "innovation_covariance", covariance)
        self.validate()

    @property
    def n(self) -> int:
        return self.coefficients[0].shape[0]

    @property
    def p(self) -> int:
        return len(self.coefficients)

    def validate(self) -> None:
        if not self.coefficients:
            raise ValidationError("at least one lag matrix is required")
        n = self.coefficients[0].shape[0]
        if n == 0 or any(a.shape != (n, n) for a in self.coefficients):
            raise ValidationError("all lag matrices must be non-empty and n-by-n")
        if not all(np.all(np.isfinite(a)) for a in self.coefficients):
            raise ValidationError("lag matrices contain non-finite values")
        if self.innovation_covariance.shape != (n, n):
            raise ValidationError("innovation covariance has incompatible shape")
        if not np.all(np.isfinite(self.innovation_covariance)):
            raise ValidationError("innovation covariance contains non-finite values")
        if not np.allclose(self.innovation_covariance, self.innovation_covariance.T, atol=1e-12, rtol=0):
            raise ValidationError("innovation covariance must be symmetric")
        if np.min(np.linalg.eigvalsh(self.innovation_covariance)) <= 0:
            raise ValidationError("innovation covariance must be positive definite")
        if self.channel_names and len(self.channel_names) != n:
            raise ValidationError("channel_names length must equal n")
        if self.channel_names and len(set(self.channel_names)) != n:
            raise ValidationError("channel_names must be unique")
        if self.spectral_radius() >= 1.0 - 1e-12:
            raise ValidationError("VAR companion matrix is not stable")

    def companion(self) -> tuple[Array, Array, Array]:
        n, p = self.n, self.p
        top = np.concatenate(self.coefficients, axis=1)
        if p == 1:
            transition = top
        else:
            lower = np.concatenate([np.eye(n * (p - 1)), np.zeros((n * (p - 1), n))], axis=1)
            transition = np.concatenate([top, lower], axis=0)
        injection = np.zeros((n * p, n), dtype=float)
        injection[:n, :] = np.eye(n)
        observation = np.zeros((n, n * p), dtype=float)
        observation[:, :n] = np.eye(n)
        return transition, injection, observation

    def spectral_radius(self) -> float:
        transition, _, _ = self.companion()
        return float(np.max(np.abs(np.linalg.eigvals(transition))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "coefficients": [a.tolist() for a in self.coefficients],
            "innovation_covariance": self.innovation_covariance.tolist(),
            "channel_names": list(self.channel_names),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VARModel":
        return cls(
            coefficients=tuple(value["coefficients"]),
            innovation_covariance=value["innovation_covariance"],
            channel_names=tuple(value.get("channel_names", ())),
            metadata=dict(value.get("metadata", {})),
        )

    @property
    def sha256(self) -> str:
        return object_sha256(self.to_dict())


@dataclass(frozen=True)
class ServiceConstraints:
    exact_k: int | None = None
    k_min: int = 0
    k_max: int | None = None
    budget: float | None = None
    mandatory: tuple[int, ...] = ()
    forbidden: tuple[int, ...] = ()
    coverage_groups: tuple[tuple[int, ...], ...] = ()
    exclude_empty: bool = True
    exclude_full: bool = True

    def validate(self, n: int, activation_costs: Sequence[float] | None = None) -> None:
        for label, v in (("exact_k", self.exact_k), ("k_min", self.k_min), ("k_max", self.k_max)):
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, np.integer))):
                raise ValidationError(f"{label} must be an integer")
        if self.k_min is None:
            raise ValidationError("k_min must be an integer")
        for label, v in (("exact_k", self.exact_k), ("k_min", self.k_min), ("k_max", self.k_max)):
            if v is not None and not 0 <= v <= n:
                raise ValidationError(f"{label} outside [0,n]")
        for label, v in (("exclude_empty", self.exclude_empty), ("exclude_full", self.exclude_full)):
            if type(v) is not bool:
                raise ValidationError(f"{label} must be a boolean")
        mandatory = set(canonical_subset(self.mandatory, n))
        forbidden = set(canonical_subset(self.forbidden, n))
        if mandatory & forbidden:
            raise ValidationError("mandatory and forbidden coordinates overlap")
        if self.exact_k is not None:
            if not 0 <= self.exact_k <= n:
                raise ValidationError("exact_k outside [0,n]")
            k_min = k_max = self.exact_k
        else:
            k_max = n if self.k_max is None else self.k_max
            k_min = self.k_min
            if not 0 <= k_min <= k_max <= n:
                raise ValidationError("invalid cardinality interval")
        if self.exclude_empty and k_min == 0:
            raise ValidationError("empty representation is excluded but k_min permits it")
        if self.exclude_full and k_max == n:
            raise ValidationError("full representation is excluded but k_max permits it")
        if len(mandatory) > k_max or n - len(forbidden) < k_min:
            raise ValidationError("mandatory/forbidden sets make cardinality infeasible")
        for group in self.coverage_groups:
            g = set(canonical_subset(group, n))
            if not g:
                raise ValidationError("coverage groups must be non-empty")
            if g <= forbidden and not (g & mandatory):
                raise ValidationError("coverage group is entirely forbidden")
        if self.budget is not None:
            _require_finite_real(self.budget, "budget", nonnegative=True)
            if activation_costs is None:
                raise ValidationError("activation costs are required when a budget is declared")

    def is_feasible(self, subset: Iterable[int], n: int, activation_costs: Sequence[float] | None = None) -> bool:
        try:
            self.validate(n, activation_costs)
            selected = set(canonical_subset(subset, n))
        except ValidationError:
            return False
        if self.exact_k is not None and len(selected) != self.exact_k:
            return False
        k_max = n if self.k_max is None else self.k_max
        if self.exact_k is None and not self.k_min <= len(selected) <= k_max:
            return False
        if self.exclude_empty and not selected:
            return False
        if self.exclude_full and len(selected) == n:
            return False
        if not set(self.mandatory) <= selected or set(self.forbidden) & selected:
            return False
        if any(not selected.intersection(group) for group in self.coverage_groups):
            return False
        if self.budget is not None:
            assert activation_costs is not None
            if sum((rational(activation_costs[i]) for i in selected), rational(0)) > rational(self.budget):
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "exact_k": self.exact_k,
            "k_min": self.k_min,
            "k_max": self.k_max,
            "budget": self.budget,
            "mandatory": list(self.mandatory),
            "forbidden": list(self.forbidden),
            "coverage_groups": [list(g) for g in self.coverage_groups],
            "exclude_empty": self.exclude_empty,
            "exclude_full": self.exclude_full,
        }


@dataclass(frozen=True)
class SelectionProblem:
    model: VARModel | None
    constraints: ServiceConstraints
    activation_costs: tuple[float, ...]
    cut_weights: Array | None = None
    information_weight: float = 1.0
    cost_weight: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        weights = None if self.cut_weights is None else _strict_float_array(self.cut_weights, "cut_weights")
        object.__setattr__(self, "cut_weights", weights)
        self.validate()

    @property
    def n(self) -> int:
        if self.model is not None:
            return self.model.n
        if self.cut_weights is not None:
            return self.cut_weights.shape[0]
        return len(self.activation_costs)

    def validate(self) -> None:
        if self.cut_weights is not None and self.cut_weights.ndim != 2:
            raise ValidationError("cut_weights must be a matrix")
        n = self.n
        if n <= 0:
            raise ValidationError("problem ground set is empty")
        if len(self.activation_costs) != n:
            raise ValidationError("activation_costs length mismatch")
        for value in self.activation_costs:
            _require_finite_real(value, "activation cost", nonnegative=True)
        if self.cut_weights is not None:
            if self.cut_weights.shape != (n, n):
                raise ValidationError("cut_weights must be n-by-n")
            if np.any(~np.isfinite(self.cut_weights)) or np.any(self.cut_weights < 0):
                raise ValidationError("cut weights must be finite and non-negative")
            if np.any(np.diag(self.cut_weights) != 0):
                raise ValidationError("cut-weight diagonal must be zero")
        _require_finite_real(self.information_weight, "information_weight", nonnegative=True)
        _require_finite_real(self.cost_weight, "cost_weight", nonnegative=True)
        self.constraints.validate(n, self.activation_costs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": None if self.model is None else self.model.to_dict(),
            "constraints": self.constraints.to_dict(),
            "activation_costs": list(self.activation_costs),
            "cut_weights": None if self.cut_weights is None else self.cut_weights.tolist(),
            "information_weight": self.information_weight,
            "cost_weight": self.cost_weight,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SelectionProblem":
        c = value["constraints"]
        constraints = ServiceConstraints(
            exact_k=c.get("exact_k"),
            k_min=c.get("k_min", 0),
            k_max=c.get("k_max"),
            budget=c.get("budget"),
            mandatory=tuple(c.get("mandatory", ())),
            forbidden=tuple(c.get("forbidden", ())),
            coverage_groups=tuple(tuple(g) for g in c.get("coverage_groups", ())),
            exclude_empty=c.get("exclude_empty", True),
            exclude_full=c.get("exclude_full", True),
        )
        return cls(
            model=None if value.get("model") is None else VARModel.from_dict(value["model"]),
            constraints=constraints,
            activation_costs=tuple(value["activation_costs"]),
            cut_weights=value.get("cut_weights"),
            information_weight=value.get("information_weight", 1.0),
            cost_weight=value.get("cost_weight", 0.0),
            metadata=dict(value.get("metadata", {})),
        )

    @property
    def sha256(self) -> str:
        return object_sha256(self.to_dict())
