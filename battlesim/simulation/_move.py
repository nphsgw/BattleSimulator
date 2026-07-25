#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 24 18:07:16 2019

@author: gparkes

This file is concerned with movement functions associated with each army group.

There is the default 'move' and fancier options such as A*.
"""

import numpy as np
from numba import njit
from numpy.typing import NDArray

__all__ = ["to_enemy"]

"""
Parameters
    pos: (np.ndarray, (n, 2), float all) positions of every unit
    speed: (np.ndarray, (n,) float all) base speed of every unit
    dd: (np.ndarray, (n,) float all) directional derivative to target
    distances: (np.ndarray, (n,) float all) unit distance to target
    i : (int) the current unit's index
"""


@njit
def to_enemy(
    M,
    delta_x: NDArray[np.float64],
    delta_y: NDArray[np.float64],
    dist: NDArray[np.float64],
    z_i: float,
    i: int,
    stop_distance: float,
) -> None:
    """
    Updates M[x,y] towards the target.

    Modifies inplace..

    The update speed is calculated as:
        s_i * (dd_i / m_ij) * (1 - (Z_i / 2))
    """
    dist_i = dist[i]
    if dist_i <= stop_distance:
        return
    # cache the terra + speed influences.
    terrain_tick = (1.0 - (z_i / 2.0)) * M["speed"][i]
    step = min(terrain_tick, dist_i - stop_distance)
    # compute normed directional derivative and update.
    M["x"][i] += (delta_x[i] / dist_i) * step
    M["y"][i] += (delta_y[i] / dist_i) * step


@njit
def from_enemy(
    M,
    delta_x: NDArray[np.float64],
    delta_y: NDArray[np.float64],
    dist: NDArray[np.float64],
    z_i: float,
    i: int,
) -> None:
    """
    Updates M[x,y] towards the target.

    Modifies inplace..

    The update speed is calculated as:
        s_i * (dd_i / m_ij) * (1 - (Z_i / 2))
    """
    # modify dist to prevent it being zero
    dist_i = dist[i] + 1e-12
    # cache the terra + speed influences.
    terrain_tick = (1.0 - (z_i / 2.0)) * M["speed"][i]
    # compute normed directional derivative and update.
    M["x"][i] -= (delta_x[i] / dist_i) * terrain_tick
    M["y"][i] -= (delta_y[i] / dist_i) * terrain_tick
