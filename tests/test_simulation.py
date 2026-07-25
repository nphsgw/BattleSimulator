"""Regression tests for core simulation rules."""

import numpy as np
from numba import typed

import battlesim as bsm
from battlesim.simulation import _ai, _damage, _hit
from battlesim.simulation._simulator_fast import (
    _loop_units,
    _terrain_tiles,
    simulate_battle,
)


def _matrix(n: int) -> np.ndarray:
    matrix = bsm.Battle._generate_M(n)
    matrix["hp"] = 10.0
    matrix["range"] = 2.0
    return matrix


def test_damage_never_leaves_negative_armor():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["dmg"][0] = 8.0
    matrix["armor"][1] = 3.0

    _damage.basic(matrix, 0.0, 0.0, 0)

    assert matrix["armor"][1] == 0.0
    assert matrix["hp"][1] == 5.0


def test_retargeting_ignores_enemies_killed_earlier_in_tick():
    matrix = _matrix(3)
    matrix["target"][0] = 1
    matrix["hp"][1] = 0.0
    matrix["x"] = [0.0, 0.1, 1.0]

    selected = _ai._select_enemy(matrix, np.array([1, 2]), 0)

    assert selected is True
    assert matrix["target"][0] == 2


def test_retargeting_uses_units_rolling_ai():
    matrix = _matrix(5)
    matrix["target"][0] = 1
    matrix["hp"] = [10.0, 0.0, 100.0, 1.0, 100.0]
    matrix["x"] = [0.0, 0.1, 1.0, 2.0, 3.0]
    matrix["target_ai_func_index"][0] = 2

    selected = _ai._select_enemy(matrix, np.array([1, 2, 3, 4]), 0)

    assert selected is True
    assert matrix["target"][0] == 3


def test_retargeting_supports_random_rolling_ai():
    matrix = _matrix(3)
    matrix["target"][0] = 1
    matrix["hp"][1] = 0.0
    matrix["target_ai_func_index"][0] = 1

    selected = _ai._select_enemy(matrix, np.array([1, 2]), 0)

    assert selected is True
    assert matrix["target"][0] == 2


def test_aggressive_refreshes_geometry_after_retargeting():
    matrix = _matrix(3)
    matrix["target"] = [1, 0, 0]
    matrix["hp"][1] = 0.0
    matrix["x"] = [0.0, 10.0, -1.0]
    matrix["speed"][0] = 1.0
    dists = np.array([10.0, 10.0, 1.0])
    delta_x = np.array([10.0, -10.0, 1.0])
    delta_y = np.zeros(3)

    _ai.aggressive(
        matrix,
        np.ones(3),
        np.ones(3),
        dists,
        delta_x,
        delta_y,
        np.zeros(3),
        np.zeros(3),
        np.array([2]),
        np.zeros((1, 1)),
        0,
    )

    assert matrix["target"][0] == 2
    assert dists[0] == 1.0
    assert matrix["x"][0] == 0.0


def test_hit_and_run_uses_the_documented_effective_range_formula():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["x"] = [0.0, 3.0]
    matrix["range"] = [3.0, 2.0]
    matrix["speed"] = [2.0, 1.0]

    _ai.hit_and_run(
        matrix,
        np.ones(2),
        np.ones(2),
        np.array([3.0, 3.0]),
        np.array([3.0, -3.0]),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.array([1]),
        np.ones((1, 1)),
        0,
    )

    assert matrix["x"][0] == 0.0


def test_hit_chance_uses_effective_range_and_keeps_half_at_limit():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["acc"][0] = 0.8
    matrix["dodge"][1] = 0.25

    chance = _hit.basic_chance(matrix, np.array([10.0, 10.0]), 10.0, 0)

    assert np.isclose(chance, 0.3)


def test_hit_chance_is_zero_for_non_positive_effective_range():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["acc"][0] = 1.0

    chance = _hit.basic_chance(matrix, np.zeros(2), 0.0, 0)

    assert chance == 0.0


def test_units_act_in_index_order_and_dead_units_skip_their_turn():
    matrix = _matrix(2)
    matrix["team"] = [0, 1]
    matrix["target"] = [1, 0]
    matrix["hp"] = 1.0
    matrix["dmg"] = 2.0
    matrix["acc"] = 1.0
    matrix["x"] = 0.0
    matrix["y"] = 0.0
    enemy_targets = typed.List([np.array([1]), np.array([0])])

    _loop_units(
        matrix,
        np.full(2, 0.5),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        enemy_targets,
        np.zeros((1, 1)),
        np.array([-1.0, 1.0, -1.0, 1.0]),
    )

    assert matrix["hp"][0] == 1.0
    assert matrix["hp"][1] <= 0.0


def test_terrain_bounds_map_to_valid_endpoint_indexes():
    matrix = _matrix(2)
    matrix["x"] = [0.0, 10.0]
    matrix["y"] = [0.0, 20.0]

    x_tiles, y_tiles = _terrain_tiles(
        matrix,
        np.zeros((10, 20)),
        np.array([0.0, 10.0, 0.0, 20.0]),
    )

    assert np.array_equal(x_tiles, np.array([0.0, 9.0]))
    assert np.array_equal(y_tiles, np.array([0.0, 19.0]))


def test_simulation_supports_non_contiguous_team_ids():
    matrix = _matrix(2)
    matrix["team"] = [1, 3]
    matrix["target"] = [1, 0]
    terrain = bsm.Terrain((0.0, 2.0, 0.0, 2.0), 1.0, None).generate()

    frames = simulate_battle(matrix, terrain, max_step=1)

    assert frames.shape == (2, 2)


def test_aggressive_uses_independent_action_and_hit_randomness():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["acc"][0] = 0.03
    matrix["dmg"][0] = 1.0
    dists = np.zeros(2)

    _ai.aggressive(
        matrix,
        np.full(2, 0.5),
        np.full(2, 0.02),
        dists,
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.array([1]),
        np.zeros((1, 1)),
        0,
    )

    assert matrix["hp"][1] == 9.0


def test_movement_stops_at_effective_range_instead_of_overshooting():
    matrix = _matrix(2)
    matrix["target"] = [1, 0]
    matrix["x"] = [0.0, 5.0]
    matrix["range"][0] = 1.0
    matrix["speed"][0] = 10.0

    _ai.aggressive(
        matrix,
        np.ones(2),
        np.ones(2),
        np.array([5.0, 5.0]),
        np.array([5.0, -5.0]),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        np.array([1]),
        np.zeros((1, 1)),
        0,
    )

    assert matrix["x"][0] == 4.0


def test_max_step_frame_contains_final_updated_state():
    matrix = _matrix(2)
    matrix["team"] = [0, 1]
    matrix["target"] = [1, 0]
    matrix["x"] = [0.0, 2.0]
    matrix["range"] = 0.1
    matrix["speed"] = [1.0, 0.0]
    terrain = bsm.Terrain((-5.0, 5.0, -5.0, 5.0), 1.0, None).generate()

    frames = simulate_battle(matrix, terrain, max_step=1)

    assert frames.shape == (2, 2)
    assert frames["x"][-1, 0] == matrix["x"][0]
    assert frames["x"][-1, 0] > frames["x"][0, 0]
