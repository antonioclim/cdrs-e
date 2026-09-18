from __future__ import annotations

import math

import pytest

from cdrse.certificates import (
    AlgorithmicLayer,
    DecisionCertificate,
    EconomicLayer,
    NumericalLayer,
    StatisticalLayer,
)
from cdrse.economics import (
    CostComponent,
    CostLedger,
    aggregate_scenarios,
    empirical_cvar,
    pareto_front,
    present_value,
    scalarised_decision_value,
    supported_points,
)
from cdrse.errors import ValidationError


def test_cost_ledger_units_and_provenance() -> None:
    ledger = CostLedger((CostComponent("energy", 2.0, "kWh", "E1"), CostComponent("compute", 3.0, "kWh", "E1")))
    assert ledger.scalar_total() == 5.0
    mixed = CostLedger((CostComponent("energy", 2.0, "kWh", "E1"), CostComponent("latency", 3.0, "ms", "E1")))
    with pytest.raises(ValidationError):
        mixed.scalar_total()
    with pytest.raises(ValidationError):
        CostComponent("money", 10.0, "EUR", "E2").validate()


def test_present_value_and_scalarised_value() -> None:
    assert math.isclose(present_value([1, 1, 1], 0.5), 1.75)
    assert scalarised_decision_value(10, 2, 3, predictions=4) == 22
    with pytest.raises(ValidationError):
        scalarised_decision_value(1, -1, 2)


def test_cvar_and_scenario_aggregation() -> None:
    assert empirical_cvar([0.0, 2.0], 0.5) == 2.0
    assert aggregate_scenarios([1.0, 3.0], "mean") == 2.0
    assert aggregate_scenarios([1.0, 3.0], "mean", [0.25, 0.75]) == 2.5
    assert aggregate_scenarios([1.0, 3.0], "worst") == 3.0
    with pytest.raises(ValidationError):
        aggregate_scenarios([1.0, 3.0], "cvar", [0.5, 0.5])


def test_pareto_and_supported_points() -> None:
    records = [
        {"name": "a", "cost": 0, "loss": 4},
        {"name": "b", "cost": 2, "loss": 3},
        {"name": "c", "cost": 4, "loss": 0},
        {"name": "d", "cost": 4, "loss": 5},
    ]
    front = pareto_front(records)
    assert {row["name"] for row in front} == {"a", "b", "c"}
    assert {row["name"] for row in supported_points(front)} == {"a", "c"}


def valid_certificate() -> DecisionCertificate:
    return DecisionCertificate(
        problem_sha256="a" * 64,
        selected=(0, 2),
        algorithmic=AlgorithmicLayer(True, 1.25, 1.10, "node_budget", False),
        numerical=NumericalLayer("float64", True, True, 1e-9, 100.0),
        statistical=StatisticalLayer("population objective", False, 1.0, "exploratory"),
        economic=EconomicLayer("E0", True, True),
        numerical_error=0.01,
        statistical_error=0.02,
        tolerance=0.25,
    )


def test_certificate_bound_and_roundtrip() -> None:
    certificate = valid_certificate()
    assert math.isclose(certificate.regret_upper, 0.21)
    assert certificate.non_vacuous
    restored = DecisionCertificate.from_dict(certificate.to_dict())
    assert math.isclose(restored.regret_upper, certificate.regret_upper)


def test_certificate_rejects_historical_failure_modes() -> None:
    with pytest.raises(ValidationError):
        DecisionCertificate(
            problem_sha256="a" * 64,
            selected=None,
            algorithmic=AlgorithmicLayer(True, 1.0, 0.0, "node_budget", False),
            numerical=NumericalLayer("float64", True, True, 1e-9),
            statistical=StatisticalLayer("estimand", False, 1.0),
            economic=EconomicLayer("E0", True, True),
        ).validate()
    with pytest.raises(ValidationError):
        AlgorithmicLayer(True, 1.0, 2.0, "bad", True).validate()
    with pytest.raises(ValidationError):
        NumericalLayer("float64", True, False, 1e-9).validate(False)
    with pytest.raises(ValidationError):
        EconomicLayer("E2", True, True).validate()
