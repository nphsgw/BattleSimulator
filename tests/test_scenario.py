"""Tests for notebook-independent battle scenario configuration."""

from pathlib import Path

import pytest

import battlesim as bsm


def test_scenario_loads_relative_database():
    scenario_path = Path("scenarios/clone-vs-droid.toml")

    scenario = bsm.BattleScenario.from_toml(scenario_path)

    assert scenario.database == str(Path("datasets/starwars-clonewars.csv").resolve())
    assert scenario.armies[0].name == "B1 battledroid"
    assert scenario.armies[1].position_parameters == (5.0, 0.5)


def test_scenario_requires_two_armies():
    with pytest.raises(ValueError, match="at least two armies"):
        bsm.BattleScenario.from_mapping(
            {"armies": [{"name": "Clone Trooper", "count": 1}]}
        )


def test_army_count_must_be_positive():
    army = bsm.ArmySpec("Clone Trooper", 0)

    with pytest.raises(ValueError, match="at least 1"):
        army.to_composite()
