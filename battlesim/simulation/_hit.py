#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 16:20:15 2019

@author: gparkes

Performs calculations on the 'hit chance' of various attacks.
"""

import numpy as np
from numba import njit
from numpy.typing import NDArray


@njit
def basic_chance(M, dist: NDArray[np.float64], effective_range: float, i: int) -> float:
    """
    Hit chance in the range [0..1]
    0 meaning no chance of hitting, 1 meaning perfect accuracy.

    The distance factor decreases from 1.0 at the shooter's position to 0.5
    at the effective range limit.
    """
    if effective_range <= 0.0:
        return 0.0
    distance_factor = 1.0 - (0.5 * dist[i] / effective_range)
    chance = M["acc"][i] * (1.0 - M["dodge"][M["target"][i]]) * distance_factor
    return min(max(chance, 0.0), 1.0)
