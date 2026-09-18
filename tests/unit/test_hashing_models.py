from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from cdrse.errors import ValidationError
from cdrse.hashing import canonical_json_bytes, file_sha256, object_sha256
from cdrse.models import SelectionProblem, ServiceConstraints, VARModel, canonical_subset


def witness_model() -> VARModel:
    return VARModel((np.array([[0.0, 0.5], [0.5, 0.0]]),), np.eye(2), ("x1", "x2"))


def test_canonical_subset_and_bounds() -> None:
    assert canonical_subset([2, 0, 1], 3) == (0, 1, 2)
    with pytest.raises(ValidationError):
        canonical_subset([0, 0], 2)
    with pytest.raises(ValidationError):
        canonical_subset([2], 2)


def test_object_hash_is_order_stable() -> None:
    left = {"b": [2, 1], "a": {"z": 3}}
    right = {"a": {"z": 3}, "b": [2, 1]}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert object_sha256(left) == object_sha256(right)


def test_file_sha256(tmp_path: Path) -> None:
    path = tmp_path / "x.txt"
    path.write_text("abc", encoding="utf-8")
    assert file_sha256(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_var_model_stability_and_roundtrip() -> None:
    model = witness_model()
    assert model.n == 2 and model.p == 1
    assert math.isclose(model.spectral_radius(), 0.5)
    restored = VARModel.from_dict(model.to_dict())
    assert restored.sha256 == model.sha256


def test_var_model_rejects_unstable_and_bad_covariance() -> None:
    with pytest.raises(ValidationError):
        VARModel((np.eye(2),), np.eye(2))
    with pytest.raises(ValidationError):
        VARModel((np.zeros((2, 2)),), np.array([[1.0, 2.0], [0.0, 1.0]]))
    with pytest.raises(ValidationError):
        VARModel((np.zeros((2, 2)),), np.diag([1.0, 0.0]))


def test_service_constraints_endpoint_and_budget_guards() -> None:
    with pytest.raises(ValidationError):
        ServiceConstraints(k_min=0, k_max=1).validate(3, [1, 1, 1])
    with pytest.raises(ValidationError):
        ServiceConstraints(k_min=1, k_max=3).validate(3, [1, 1, 1])
    constraints = ServiceConstraints(exact_k=2, budget=3, mandatory=(0,), coverage_groups=((2, 3),))
    constraints.validate(4, [1, 2, 1, 4])
    assert constraints.is_feasible((0, 2), 4, [1, 2, 1, 4])
    assert not constraints.is_feasible((0, 1), 4, [1, 2, 1, 4])


def test_selection_problem_roundtrip_and_hash() -> None:
    problem = SelectionProblem(
        model=None,
        constraints=ServiceConstraints(exact_k=1, budget=2),
        activation_costs=(1.0, 2.0, 3.0),
        cut_weights=np.array([[0, 1, 0], [2, 0, 1], [0, 0, 0]], dtype=float),
    )
    restored = SelectionProblem.from_dict(problem.to_dict())
    assert restored.sha256 == problem.sha256
    assert restored.n == 3


def test_selection_problem_rejects_invalid_weights() -> None:
    with pytest.raises(ValidationError):
        SelectionProblem(
            None,
            ServiceConstraints(exact_k=1),
            (1.0, 1.0),
            np.array([[1.0, 0.0], [0.0, 0.0]]),
        )
