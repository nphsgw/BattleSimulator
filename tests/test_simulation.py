"""Regression tests for core simulation rules."""

import numpy as np

import battlesim as bsm
from battlesim.simulation import _ai, _damage
from battlesim.simulation._simulator_fast import _terrain_tiles, simulate_battle


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

    assert frames.shape == (1, 2)
