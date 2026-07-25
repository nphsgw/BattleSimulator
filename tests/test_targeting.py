#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for internal targeting helpers."""

import numpy as np

from battlesim._battle import Battle
from battlesim.simulation import _target


def _build_target_matrix() -> np.ndarray:
    matrix = Battle._generate_M(4)
    matrix["id"] = np.array([0, 0, 1, 1], dtype=np.uint32)
    matrix["team"] = np.array([0, 0, 1, 1], dtype=np.uint8)
    matrix["hp"] = np.array([10.0, 10.0, 1.0, 100.0], dtype=np.float32)
    matrix["x"] = np.array([0.0, 0.0, 1.0, 10.0], dtype=np.float32)
    matrix["y"] = np.array([0.0, 2.0, 0.0, 10.0], dtype=np.float32)
    return matrix


def test_global_nearest_returns_absolute_indexes():
    matrix = _build_target_matrix()

    targets = _target.global_nearest(matrix, 0)

    assert np.array_equal(targets, np.array([2, 2], dtype=np.int64))


def test_global_close_weak_returns_absolute_indexes():
    matrix = _build_target_matrix()

    targets = _target.global_close_weak(matrix, 0)

    assert np.array_equal(targets, np.array([2, 2], dtype=np.int64))


def test_close_weak_is_invariant_to_coordinate_scale():
    matrix = Battle._generate_M(3)
    matrix["hp"] = [10.0, 100.0, 1.0]
    matrix["x"] = [0.0, 1.0, 5.0]
    enemies = np.array([1, 2])

    target_at_base_scale = _target.close_weak(matrix, enemies, 0)
    matrix["x"] *= 10.0
    target_at_larger_scale = _target.close_weak(matrix, enemies, 0)

    assert target_at_base_scale == target_at_larger_scale


def test_close_weak_includes_armor_in_remaining_durability():
    matrix = Battle._generate_M(3)
    matrix["hp"] = [10.0, 1.0, 10.0]
    matrix["armor"] = [0.0, 100.0, 0.0]
    matrix["x"] = [0.0, 1.0, 1.0]

    target = _target.close_weak(matrix, np.array([1, 2]), 0)

    assert target == 2


def test_additional_targeting_doctrines_are_explicit():
    matrix = Battle._generate_M(4)
    matrix["team"] = [0, 0, 1, 1]
    matrix["hp"] = [10, 10, 2, 20]
    matrix["armor"] = 0
    matrix["dmg"] = [1, 1, 2, 10]
    matrix["acc"] = 1
    matrix["attack_interval"] = [1, 1, 1, 2]
    matrix["target"] = [2, 2, 0, 0]
    enemies = np.array([2, 3])

    assert _target.weakest(matrix, enemies, 0) == 2
    assert _target.highest_threat(matrix, enemies, 0) == 3
    assert _target.focus_fire(matrix, enemies, 0) == 2
    assert _target.objective_priority(matrix, enemies, 0) in enemies
