#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 22 14:27:05 2019

@author: gparkes

A selection of algorithms for deciding which enemy to target next.

We use a rather ugly way of doing this - so we can use jit to speed up
the calculation using C rather than Python - all the numpy arrays are
passed to the functions.


    Parameters
    --------
    pos : np.ndarray (n, 2)
        The positions of all units
    hp : np.ndarray (n, )
        The HP of every unit.
    enemies : np.ndarray
        indices of enemy candidates
    allies : np.ndarray
        indices of ally candidates
    i : int
        Index of chosen unit

    Returns
    -------
    j : Index of new target
        -1 if not valid target chosen.

"""

import numpy as np
from numba import njit
from numpy.typing import NDArray

from battlesim import _mathutils


def get_function_names() -> list[str]:
    """Returns the function names."""
    return [
        "random",
        "nearest",
        "close_weak",
        "weakest",
        "highest_threat",
        "focus_fire",
        "objective_priority",
    ]


def get_global_function_names() -> list[str]:
    """Gets global function names."""
    return ["global_" + n for n in get_function_names()]


__all__ = get_function_names() + get_global_function_names()


############## AI FUNCTIONS ##############################


@njit
def random(M, enemies: NDArray[np.uint], i: int | None = None) -> int:
    """
    Given enemy candidates who are alive, draw an index of one at random.
    """
    # draw a candidate
    if enemies.shape[0] > 0:
        return np.random.choice(enemies)
    else:
        return -1


@njit
def nearest(M, enemies: NDArray[np.uint], i: int) -> int:
    """
    Given enemy candidates who are alive, determine which one is nearest.
    """
    if enemies.shape[0] > 0:
        # compute distances/magnitudes
        distances = _mathutils.sq_euclidean_distance2(M["x"], M["y"], i, enemies)
        return enemies[np.argmin(distances)]
    else:
        return -1


@njit
def close_weak(M, enemies: NDArray[np.uint], i: int, wtc_ratio: float = 0.7) -> int:
    """
    Given enemy alive candidates, globally determine which one is the weakest
    and closest, using appropriate weighting for each option.

    Given enemy alive candidates, globally determine which one is the strongest
    of the enemies and target them.

    Parameters (extra)
    --------
    wtc_ratio : float [0..1]
        weak-to-close ratio to determine weighting of each part. Values closer
        to 1 prefer closer enemies, whereas values closer to 0 prefer weaker enemies
    """
    if enemies.shape[0] > 0:
        distances = _mathutils.sq_euclidean_distance2(M["x"], M["y"], i, enemies)
        durability = np.maximum(M["hp"][enemies], 0.0) + np.maximum(
            M["armor"][enemies], 0.0
        )
        return enemies[
            np.argmin(
                (_mathutils.minmax(durability) * (1.0 - wtc_ratio))
                + (_mathutils.minmax(distances) * wtc_ratio)
            )
        ]
    else:
        return -1


@njit
def weakest(M, enemies: NDArray[np.uint], i: int) -> int:
    """Select the enemy with the least remaining HP plus armor."""
    if enemies.shape[0] == 0:
        return -1
    durability = np.maximum(M["hp"][enemies], 0.0) + np.maximum(
        M["armor"][enemies], 0.0
    )
    return enemies[np.argmin(durability)]


@njit
def highest_threat(M, enemies: NDArray[np.uint], i: int) -> int:
    """Select the largest expected damage per attack interval."""
    if enemies.shape[0] == 0:
        return -1
    threat = (
        M["dmg"][enemies]
        * M["acc"][enemies]
        / np.maximum(M["attack_interval"][enemies], 1.0)
    )
    return enemies[np.argmax(threat)]


@njit
def focus_fire(M, enemies: NDArray[np.uint], i: int) -> int:
    """Prefer an enemy already targeted by the most living allies."""
    if enemies.shape[0] == 0:
        return -1
    allies = np.where((M["hp"] > 0.0) & (M["team"] == M["team"][i]))[0]
    counts = np.empty(enemies.shape[0], dtype=np.int64)
    for candidate_i in range(enemies.shape[0]):
        counts[candidate_i] = np.sum(M["target"][allies] == enemies[candidate_i])
    return enemies[np.argmax(counts)]


@njit
def objective_priority(M, enemies: NDArray[np.uint], i: int) -> int:
    """Legacy fallback when objective geometry is unavailable."""
    return nearest(M, enemies, i)


# ------------------------ GLOBAL TARGET ASSIGNMENTS -----------------------

"""
A selection of algorithms for deciding all enemies to target.

This is the same as above except there is no index parameter passed. Assumes
all units need a new target.


    Parameters
    --------
    pos : np.ndarray (n, 2)
        The positions of all units
    hp : np.ndarray (n, )
        The HP of every unit.
    team : np.ndarray (n, )
        Team number of every unit.
    group : np.ndarray (n, )
        The group number of every unit.
    group_i : int
        The group number selected

    Returns
    -------
    j : np.ndarray(n, )
        Index(es) of new target
"""


@njit
def global_random(M, group_i: int):
    """Computes a random target for every unit within the M matrix."""
    # define
    sel = M["id"] == group_i
    t = M["team"][sel][0]
    # get unit IDs that are not equal to this team for enemies.
    (id_not,) = np.where(M["team"] != t)
    # set the index for these guys
    return np.random.choice(id_not, sel.sum())


@njit
def global_nearest(M, group_i: int):
    """Computes the nearest target for every unit within the M matrix."""
    # define
    selector = M["id"] == group_i
    t = M["team"][selector][0]
    # Calculate deterministically; tie-breaking follows candidate matrix order.
    dist_matrix_sq = _mathutils.sq_distance_matrix(M["x"], M["y"])
    # only calculate for diaginal indices.
    np.fill_diagonal(dist_matrix_sq, np.max(dist_matrix_sq))
    # get unit IDs that are not equal to this team for enemies.
    (id_not,) = np.where(M["team"] != t)
    (id_is,) = np.where(selector)
    # use distance matrix and ids to select sub groups to find argmin
    j = _mathutils.matrix_argmin(dist_matrix_sq[id_is, :][:, id_not])
    return id_not[j]


@njit
def global_close_weak(M, group_i: int, wtc_ratio=0.7):
    """Computes the nearest weakest target for every unit within the M matrix."""
    # define
    selector = M["id"] == group_i
    t = M["team"][selector][0]
    # calculate distance matrix.
    dist_matrix_sq = _mathutils.sq_distance_matrix(M["x"], M["y"])

    # get unit IDs that are not equal to this team for enemies.
    (id_not,) = np.where(M["team"] != t)
    (id_is,) = np.where(selector)
    durability = np.maximum(M["hp"][id_not], 0.0) + np.maximum(M["armor"][id_not], 0.0)
    durability_score = _mathutils.minmax(durability)
    candidate_distances = dist_matrix_sq[id_is, :][:, id_not]
    scores = np.empty_like(candidate_distances)
    for row_i in range(candidate_distances.shape[0]):
        scores[row_i] = _mathutils.minmax(
            candidate_distances[row_i]
        ) * wtc_ratio + durability_score * (1.0 - wtc_ratio)
    j = _mathutils.matrix_argmin(scores)
    return id_not[j]


@njit
def _global_from_local(M, group_i: int, mode: int):
    selector = M["id"] == group_i
    team = M["team"][selector][0]
    enemies = np.where(M["team"] != team)[0]
    actors = np.where(selector)[0]
    result = np.empty(actors.shape[0], dtype=np.int64)
    for result_i in range(actors.shape[0]):
        actor = actors[result_i]
        if mode == 3:
            result[result_i] = weakest(M, enemies, actor)
        elif mode == 4:
            result[result_i] = highest_threat(M, enemies, actor)
        elif mode == 5:
            result[result_i] = focus_fire(M, enemies, actor)
        else:
            result[result_i] = objective_priority(M, enemies, actor)
    return result


@njit
def global_weakest(M, group_i: int):
    return _global_from_local(M, group_i, 3)


@njit
def global_highest_threat(M, group_i: int):
    return _global_from_local(M, group_i, 4)


@njit
def global_focus_fire(M, group_i: int):
    return _global_from_local(M, group_i, 5)


@njit
def global_objective_priority(M, group_i: int):
    return _global_from_local(M, group_i, 6)
