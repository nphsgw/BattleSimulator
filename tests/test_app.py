"""Headless tests for the local visualization UI."""

from pathlib import Path

import numpy as np
import pytest

import battlesim as bsm

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


class _Labels:
    def to_dict(self) -> dict[int, str]:
        return {0: "Army 1", 1: "Army 2"}


class _Index:
    def tolist(self) -> list[str]:
        return ["Unit A", "Unit B"]


class _Database:
    index = _Index()


class _FakeBattle:
    def __init__(self) -> None:
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
            ]
        )
        self.sim_ = np.zeros((3, 2), dtype=dtype)
        self.sim_["x"] = [[1, 4], [2, 3], [3, 2]]
        self.sim_["y"] = [[1, 4], [2, 3], [3, 2]]
        self.sim_["ddx"] = 1
        self.sim_["hp"] = 10
        self.sim_["target"] = [[1, 0], [1, 0], [1, 0]]
        self.sim_["team"] = [[0, 1], [0, 1], [0, 1]]
        self.T_ = None
        self.allegiances_ = _Labels()
        self.db_ = _Database()


def test_battle_viewer_loads_display_options():
    app_path = Path("apps/battle_viewer.py")
    app = AppTest.from_file(app_path, default_timeout=10).run()

    assert not app.exception
    assert app.selectbox(key="scenario_preset").value == "Custom battle"
    assert app.button(key="run").label == "Run simulation"
    assert app.toggle(key="show_target_lines").value is False
    assert app.select_slider(key="playback_speed").value == 1.0

    app.toggle(key="show_target_lines").set_value(True).run()

    assert not app.exception
    assert app.toggle(key="show_target_lines").value is True


def test_battle_viewer_runs_damage_demo_preset():
    app = AppTest.from_file(
        Path("apps/battle_viewer.py"),
        default_timeout=10,
    ).run()

    app.selectbox(key="scenario_preset").set_value("Damage demo").run()
    assert not app.exception
    assert any("Armor 20" in info.value for info in app.info)

    app.button(key="run").click().run()

    assert not app.exception
    battle = app.session_state["battle"]
    assert battle.sim_ is not None
    assert battle.sim_["armor"].tolist() == [
        [20.0, 20.0],
        [10.0, 10.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
    ]
    assert battle.sim_["hp"].tolist() == [
        [30.0, 30.0],
        [30.0, 30.0],
        [30.0, 30.0],
        [20.0, 20.0],
        [10.0, 10.0],
        [0.0, 0.0],
    ]


def test_advance_playback_moves_one_frame():
    assert bsm.advance_playback(2, 5) == (3, True)


def test_advance_playback_stops_at_final_frame():
    assert bsm.advance_playback(3, 5) == (4, False)
    assert bsm.advance_playback(4, 5) == (4, False)


def test_battle_viewer_shows_playback_controls_for_frames():
    app = AppTest.from_file(
        Path("apps/battle_viewer.py"),
        default_timeout=10,
    )
    app.session_state["battle"] = _FakeBattle()
    app.session_state["playback_frame"] = 0
    app.session_state["playback_playing"] = False
    app.session_state["playback_skip_advance"] = False

    app.run()

    assert not app.exception
    assert app.button(key="play").label == "Play"
    assert app.button(key="pause").label == "Pause"
    assert app.button(key="replay").label == "Replay"
    assert app.slider(key="playback_frame").max == 2
    assert len(app.dataframe) == 1
    assert app.dataframe[0].value["No."].tolist() == ["#1", "#2"]
