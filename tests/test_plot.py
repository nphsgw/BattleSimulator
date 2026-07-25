#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for animation helpers."""

from pathlib import Path
from unittest.mock import patch

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import battlesim as bsm

matplotlib.use("Agg")

ROOT = (Path(__file__).parent / "../").resolve()


def _build_small_battle() -> bsm.Battle:
    battle = bsm.Battle(str(ROOT / "datasets/starwars-clonewars.csv"), use_tqdm=False)
    battle.create_army(
        [bsm.Composite("B1 battledroid", 3), bsm.Composite("Clone Trooper", 3)]
    )
    battle.simulate()
    return battle


def test_quiver_fight_debug_returns_animation():
    battle = _build_small_battle()

    anim = bsm.quiver_fight_debug(battle.sim_)

    assert isinstance(anim, FuncAnimation)


def test_quiver_fight_debug_accepts_terrain_overlay():
    battle = _build_small_battle()

    anim = bsm.quiver_fight_debug(battle.sim_, show_terrain_text=True)

    assert isinstance(anim, FuncAnimation)


def test_quiver_fight_debug_accepts_custom_interval():
    battle = _build_small_battle()

    anim = bsm.quiver_fight_debug(battle.sim_, interval=180)

    assert isinstance(anim, FuncAnimation)
    assert anim.event_source.interval == 180


def test_sim_jupyter_accepts_debug_plotter():
    battle = _build_small_battle()

    anim = battle.sim_jupyter(func=bsm.quiver_fight_debug)

    assert isinstance(anim, FuncAnimation)


def test_sim_jupyter_create_html_returns_javascript_html():
    battle = _build_small_battle()

    html = battle.sim_jupyter(func=bsm.quiver_fight_debug, create_html=True)

    assert "<script" in html
    assert "Animation" in html


def test_sim_export_accepts_debug_plotter():
    battle = _build_small_battle()

    with patch.object(FuncAnimation, "save", autospec=True) as save_mock:
        battle.sim_export("debug_overlay", func=bsm.quiver_fight_debug)

    save_mock.assert_called_once()


def test_simulate_records_terrain_overlay_fields_for_flat_terrain():
    battle = _build_small_battle()
    frame0 = battle.sim_[0]
    matrix = battle.M_

    assert matrix is not None

    assert "z" in frame0.dtype.names
    assert "target_z" in frame0.dtype.names
    assert "move_factor" in frame0.dtype.names
    assert "effective_range" in frame0.dtype.names
    assert "damage_factor" in frame0.dtype.names

    assert (frame0["z"] == 0.0).all()
    assert (frame0["target_z"] == 0.0).all()
    assert (frame0["move_factor"] == 1.0).all()
    assert (frame0["damage_factor"] == 1.0).all()
    assert (frame0["effective_range"] == matrix["range"]).all()


def test_quiver_frame_debug_returns_figure_and_axes():
    battle = _build_small_battle()

    fig, ax = bsm.quiver_frame_debug(battle.sim_, frame_i=0, show_terrain_text=True)

    assert fig is not None
    assert ax is not None
    plt.close(fig)


def test_quiver_frame_debug_can_label_units_by_number():
    battle = _build_small_battle()

    fig, ax = bsm.quiver_frame_debug(
        battle.sim_,
        frame_i=0,
        show_hp=False,
        show_target_lines=False,
        show_unit_numbers=True,
    )

    labels = {text.get_text() for text in ax.texts}
    assert labels == {f"#{unit_i + 1}" for unit_i in range(battle.sim_.shape[1])}
    plt.close(fig)
