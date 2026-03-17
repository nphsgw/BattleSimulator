#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 16:17:14 2019

@author: gparkes
"""

from typing import Any, cast

import pytest

# import local
import battlesim as bsm


def test_define_terrain():
    """Define Terrain properties."""
    _ = bsm.Terrain()
    # test with bad settings.
    with pytest.raises(TypeError):
        bsm.Terrain(cast(Any, "hello"))
    with pytest.raises(TypeError):
        bsm.Terrain(cast(Any, 42))
    with pytest.raises(TypeError):
        bsm.Terrain((0, 10, 0, 10), cast(Any, "hello"), "contour")
    with pytest.raises(AttributeError):
        bsm.Terrain((0, 10, 0, 10), 0.1, cast(Any, 42))
    with pytest.raises(AttributeError):
        bsm.Terrain(cast(Any, (0, 10, 0)), 0.1, "contour")
    with pytest.raises(TypeError):
        bsm.Terrain((0, 10, 0, 10), -1, "contour")
    with pytest.raises(AttributeError):
        bsm.Terrain((0, -1, 0, 10), 0.1, "contour")
    with pytest.raises(AttributeError):
        bsm.Terrain((0, 10, 0, -1), 0.1, "contour")
    with pytest.raises(TypeError):
        bsm.Terrain(cast(Any, (0, [0, 1], "hi", 10)), 0.1, "contour")
    with pytest.raises(AttributeError):
        bsm.Terrain((0, 10, 0, 10), 0.1, cast(Any, "hello contour boy"))

    bsm.Terrain((0, 10, 0, 10), 0.1, None)


def test_terrain_attributes():
    """Testing attributes."""
    T = bsm.Terrain()

    assert T.Z_ is None, "Z_ should be undefined at this stage"
    assert isinstance(T.bounds_, tuple), "dim_ should be a tuple"
    assert len(T.bounds_) == 4, "dim_ should be of length 4"
    assert isinstance(T.res_, float), "resolution must be float"
    assert isinstance(T.form_, str), "form_ must be of type str"
    assert T.form_ in [None, "grid", "contour"], "form_ must be None, grid or contour"


def test_generate():
    """Testing the terrain generation."""
    T = bsm.Terrain()
    # good
    T.generate()
    assert T.Z_ is not None

    flat = bsm.Terrain(form=None)
    flat.generate()
    assert flat.Z_ is not None
    assert (flat.Z_ == 0).all(), "form=None should produce a flat terrain"

    with pytest.raises(TypeError):
        T.generate(cast(Any, "hello"))
    with pytest.raises(TypeError):
        T.generate(cast(Any, 42))
    # generate with function that does not have 2 parameters

    # generate with function that does not pass 2 numpy arrays
