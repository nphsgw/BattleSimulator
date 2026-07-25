"""Tests for UI-independent visualization data."""

import numpy as np
import pytest

import battlesim as bsm


@pytest.fixture
def fixed_frames() -> np.ndarray:
    dtype = np.dtype(
        [
            ("x", "f4"),
            ("y", "f4"),
            ("ddx", "f4"),
            ("ddy", "f4"),
            ("hp", "f4"),
            ("target", "i4"),
            ("team", "u1"),
            ("utype", "u1"),
            ("z", "f4"),
            ("target_z", "f4"),
            ("move_factor", "f4"),
            ("effective_range", "f4"),
            ("damage_factor", "f4"),
        ]
    )
    frames = np.zeros((2, 2), dtype=dtype)
    frames["x"] = [[1.0, 4.0], [2.0, 3.0]]
    frames["y"] = [[2.0, 5.0], [3.0, 4.0]]
    frames["ddx"] = 1.0
    frames["hp"] = [[10.0, 8.0], [5.0, 0.0]]
    frames["target"] = [[1, 0], [1, 0]]
    frames["team"] = [[0, 1], [0, 1]]
    frames["utype"] = [[2, 3], [2, 3]]
    frames["z"] = 0.25
    frames["target_z"] = 0.5
    frames["move_factor"] = 0.875
    frames["effective_range"] = 6.0
    frames["damage_factor"] = 0.75
    return frames


def test_build_frame_view_extracts_display_values(fixed_frames: np.ndarray):
    view = bsm.build_frame_view(fixed_frames, frame_i=1)

    assert view.frame_index == 1
    assert view.frame_count == 2
    assert view.has_terrain is True
    assert view.units[0].hp_ratio == pytest.approx(0.5)
    assert view.units[0].target_position == pytest.approx((3.0, 4.0))
    assert view.units[0].move_factor == pytest.approx(0.875)
    assert view.units[1].alive is False


def test_build_frame_view_clamps_frame_index(fixed_frames: np.ndarray):
    assert bsm.build_frame_view(fixed_frames, -10).frame_index == 0
    assert bsm.build_frame_view(fixed_frames, 20).frame_index == 1


def test_build_frame_view_rejects_missing_fields():
    frames = np.zeros((1, 1), dtype=[("x", "f4")])

    with pytest.raises(ValueError, match="missing visualization fields"):
        bsm.build_frame_view(frames)
