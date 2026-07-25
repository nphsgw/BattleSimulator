#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 11:20:25 2019

@author: gparkes
"""

from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

# import local package
import battlesim as bsm

ROOT = (Path(__file__).parent / "../").resolve()


@pytest.fixture
def battle() -> bsm.Battle:
    """Generates a battle object."""
    return bsm.Battle(str(ROOT / "datasets/starwars-clonewars.csv"))


def test_battle_attributes(battle: bsm.Battle):
    """Tests basic attributes."""
    # battle object requires input file
    assert battle.M_ is None, "M_ should not be set"
    assert isinstance(battle.db_, pd.DataFrame), "db_ must be a pandas.dataframe"
    assert battle.sim_ is None, "sim_ not set yet"
    assert battle.bounds_ == (0.0, 10.0, 0.0, 10.0)


def test_battle_create_army(battle: bsm.Battle):
    # battle object requires input file
    # try normal
    with pytest.raises(TypeError):
        battle.create_army(cast(Any, "Hello"))
    with pytest.raises(TypeError):
        battle.create_army(cast(Any, pd.DataFrame({"ho": [1, 2], "hi": [2, 3]})))
    with pytest.raises(TypeError):
        battle.create_army(cast(Any, ["Clone"]))
    with pytest.raises(TypeError):
        battle.create_army(cast(Any, ["Clone", 2]))

    with pytest.raises(TypeError):
        battle.create_army(cast(Any, [("Clone", 2)]))
        battle.create_army(cast(Any, [("Droid", 10), ("Clone Trooper", 5)]))

    with pytest.raises(TypeError):
        battle.create_army(cast(Any, [("Clone Trooper", "hello")]))
        battle.create_army(cast(Any, [("B1 battledroid", np.inf)]))

    # created normally.
    comp = [bsm.Composite("B1 battledroid", 10), bsm.Composite("Clone Trooper", 10)]
    battle.create_army(comp)


def test_simulate(battle: bsm.Battle):
    # cannot simulate before creating an army set
    with pytest.raises(AttributeError):
        battle.simulate()

    # create a composite
    comp = [bsm.Composite("B1 battledroid", 100), bsm.Composite("Clone Trooper", 100)]
    # define army
    battle.create_army(comp)

    assert battle.sim_ is None, "no simulation object present"

    # no important parameters apart from those passed to simulate_battle
    # check return type
    F = battle.simulate()
    # check presense of b.sim_
    assert battle.sim_ is not None, "simulation object should be present and isnt"
    assert isinstance(F, np.ndarray), "must be of type np.ndarray for F"


def test_battle_requires_army_before_accessing_composition(battle: bsm.Battle):
    with pytest.raises(AttributeError):
        _ = battle.composition_


def test_create_army_rejects_invalid_composite_values(battle: bsm.Battle):
    with pytest.raises(ValueError, match="at least one"):
        battle.create_army([])
    with pytest.raises(ValueError, match="at least 1"):
        battle.create_army([bsm.Composite("Clone Trooper", 0)])
    with pytest.raises(ValueError, match="not found"):
        battle.create_army([bsm.Composite("Unknown Unit", 1)])
    with pytest.raises(ValueError, match="unsupported decision_ai"):
        battle.create_army([bsm.Composite("Clone Trooper", 1, decision_ai="not-an-ai")])


def test_allegiances_only_contains_participating_teams():
    database = {
        "Name": ["A", "B", "C"],
        "Allegiance": ["Team A", "Team B", "Team C"],
        "HP": [10, 10, 10],
        "Armor": [0, 0, 0],
        "Damage": [1, 1, 1],
        "Accuracy": [0, 0, 0],
        "Miss": [0, 0, 0],
        "Movement Speed": [0.1, 0.1, 0.1],
        "Range": [1, 1, 1],
    }
    battle = bsm.Battle(database, use_tqdm=False)
    battle.create_army([bsm.Composite("B", 1), bsm.Composite("C", 1)])

    assert battle.allegiances_.to_dict() == {1: "Team B", 2: "Team C"}
    assert list(battle.simulate_k(1).columns) == ["Team B", "Team C"]


def test_create_army_invalidates_previous_simulation(battle: bsm.Battle):
    battle.create_army(
        [bsm.Composite("B1 battledroid", 1), bsm.Composite("Clone Trooper", 1)]
    )
    battle.simulate()

    battle.create_army(
        [bsm.Composite("B1 battledroid", 2), bsm.Composite("Clone Trooper", 2)]
    )

    assert battle.M_ is None
    assert battle.sim_ is None
