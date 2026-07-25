"""Tests for notebook-independent battle scenario configuration."""

from pathlib import Path

import numpy as np
import pytest

import battlesim as bsm


def test_scenario_loads_relative_database():
    scenario_path = Path("scenarios/clone-vs-droid.toml")

    scenario = bsm.BattleScenario.from_toml(scenario_path)

    assert scenario.database == str(Path("datasets/starwars-clonewars.csv").resolve())
    assert scenario.armies[0].name == "B1 battledroid"
    assert scenario.armies[1].position_parameters == (5.0, 0.5)


def test_damage_demo_shows_armor_then_hp_decreasing():
    scenario = bsm.BattleScenario.from_toml("scenarios/damage-demo.toml")

    battle = scenario.run()

    assert battle.sim_ is not None
    assert np.array_equal(
        battle.sim_["armor"],
        np.array(
            [
                [20, 20],
                [10, 10],
                [0, 0],
                [0, 0],
                [0, 0],
                [0, 0],
            ],
            dtype=np.float32,
        ),
    )
    assert np.array_equal(
        battle.sim_["hp"],
        np.array(
            [
                [30, 30],
                [30, 30],
                [30, 30],
                [20, 20],
                [10, 10],
                [0, 0],
            ],
            dtype=np.float32,
        ),
    )
    assert battle.result_ is not None
    assert battle.result_.termination_reason == bsm.TerminationReason.MUTUAL_DESTRUCTION


def test_army_spec_loads_targeting_ai_options():
    army = bsm.ArmySpec.from_mapping(
        {
            "name": "Clone Trooper",
            "count": 1,
            "init_ai": "random",
            "rolling_ai": "close_weak",
        }
    )

    composite = army.to_composite()

    assert composite.init_ai == "random"
    assert composite.rolling_ai == "close_weak"


def test_scenario_requires_two_armies():
    with pytest.raises(ValueError, match="at least two armies"):
        bsm.BattleScenario.from_mapping(
            {"armies": [{"name": "Clone Trooper", "count": 1}]}
        )


def test_army_count_must_be_positive():
    army = bsm.ArmySpec("Clone Trooper", 0)

    with pytest.raises(ValueError, match="at least 1"):
        army.to_composite()


def test_army_spec_preserves_surrogate_doctrine_weights():
    army = bsm.ArmySpec.from_mapping(
        {
            "name": "Clone Trooper",
            "count": 1,
            "rolling_ai": "highest_threat",
            "doctrine_weights": [0.1, 0.2, 0.6, 0.1],
        }
    )

    composite = army.to_composite()

    assert composite.rolling_ai == "highest_threat"
    assert composite.doctrine_weights == (0.1, 0.2, 0.6, 0.1)
