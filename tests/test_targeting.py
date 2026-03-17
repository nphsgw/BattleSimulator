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
