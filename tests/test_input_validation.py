"""Adversarial tests for values crossing the scenario trust boundary."""

from __future__ import annotations

import math
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

import battlesim as bsm


def valid_scenario() -> dict[str, object]:
    return {
        "armies": [
            {"name": "B1 battledroid", "count": 1},
            {"name": "Clone Trooper", "count": 1},
        ]
    }


@pytest.mark.parametrize("count", [True, 1.9, "1"])
def test_count_rejects_implicit_integer_conversion(count: object) -> None:
    with pytest.raises(ValidationError):
        bsm.ArmySpec.from_mapping({"name": "Clone Trooper", "count": count})


def test_unknown_scenario_key_is_rejected() -> None:
    scenario = valid_scenario()
    scenario["terrain_resoluton"] = 0.1

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        bsm.BattleScenario.from_mapping(scenario)


@pytest.mark.parametrize(
    "bounds",
    [
        [10.0, 0.0, 0.0, 10.0],
        [0.0, 0.0, 0.0, 10.0],
        [0.0, 10.0, 5.0, 5.0],
    ],
)
def test_bounds_must_be_ordered_and_non_degenerate(bounds: list[float]) -> None:
    scenario = valid_scenario()
    scenario["bounds"] = bounds

    with pytest.raises(ValidationError, match="must be less than"):
        bsm.BattleScenario.from_mapping(scenario)


@given(st.sampled_from([math.nan, math.inf, -math.inf]))
def test_non_finite_terrain_resolution_is_rejected(value: float) -> None:
    scenario = valid_scenario()
    scenario["terrain_resolution"] = value

    with pytest.raises(ValidationError):
        bsm.BattleScenario.from_mapping(scenario)


@given(st.sampled_from([math.nan, math.inf, -math.inf]))
def test_non_finite_doctrine_weight_is_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        bsm.ArmySpec.from_mapping(
            {
                "name": "Clone Trooper",
                "count": 1,
                "doctrine_weights": [value, 0.0, 0.0, 0.0],
            }
        )


def test_closed_configuration_values_are_rejected_early() -> None:
    with pytest.raises(ValidationError):
        bsm.ArmySpec.from_mapping(
            {
                "name": "Clone Trooper",
                "count": 1,
                "rolling_ai": "typo",
            }
        )


def test_nested_rule_flags_do_not_accept_integers() -> None:
    scenario = valid_scenario()
    scenario["rules"] = {"line_of_sight": 1}

    with pytest.raises(ValidationError):
        bsm.BattleScenario.from_mapping(scenario)


@pytest.mark.parametrize("seed", [True, 1.9, "1"])
def test_direct_battle_seed_rejects_implicit_conversion(seed: object) -> None:
    with pytest.raises(TypeError):
        bsm.Battle(seed=cast(Any, seed), use_tqdm=False)
    battle = bsm.Battle(use_tqdm=False)
    with pytest.raises(TypeError):
        battle.simulate(seed=cast(Any, seed))


@pytest.mark.parametrize("count", [True, 1.9, "1"])
def test_simulate_k_rejects_non_integer_trial_count(count: object) -> None:
    battle = bsm.Battle(use_tqdm=False)

    with pytest.raises(TypeError):
        battle.simulate_k(cast(Any, count))


def test_direct_domain_construction_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        bsm.ObjectiveZone(0.0, 0.0, math.nan, 1)
    with pytest.raises(ValueError, match="finite"):
        bsm.ArmySpec(
            "Clone Trooper",
            1,
            doctrine_weights=(math.nan, 0.0, 0.0, 0.0),
        )
    with pytest.raises(ValueError, match="finite"):
        bsm.Composite(
            "Clone Trooper",
            1,
            doctrine_weights=(math.nan, 0.0, 0.0, 0.0),
        )
    with pytest.raises(ValueError, match="finite"):
        bsm.Terrain(res=math.nan)


def test_direct_rule_flags_must_be_booleans() -> None:
    with pytest.raises(TypeError, match="booleans"):
        bsm.BattleRules(line_of_sight=cast(Any, 1))
