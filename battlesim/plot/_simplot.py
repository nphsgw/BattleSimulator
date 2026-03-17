#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 22 14:30:45 2019

@author: gparkes
"""

import itertools as it
from collections.abc import Mapping, Sequence
from functools import reduce

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation, colors
from matplotlib.lines import Line2D

from battlesim._utils import slice_loop
from battlesim.terra._terrain import Terrain

# all functions to import
__all__ = ["quiver_fight", "quiver_fight_debug", "quiver_frame_debug"]


def _resolve_allegiance_metadata(
    frames: np.ndarray,
    allegiance_label: Mapping[object, str] | None,
    allegiance_color: Mapping[object, str] | Sequence[str] | None,
) -> tuple[np.ndarray, dict[object, str], dict[object, str]]:
    allegiances = np.unique(frames["team"])
    n_allegiances = allegiances.shape[0]

    if allegiance_label is None or len(allegiance_label) != n_allegiances:
        allegiance_label = dict(
            zip(
                allegiances.tolist(),
                [f"team{i}" for i in it.islice(it.count(1), 0, n_allegiances)],
            )
        )
    else:
        allegiance_label = dict(allegiance_label)

    if allegiance_color is None or len(allegiance_color) != n_allegiances:
        allegiance_color = dict(
            zip(
                allegiances.tolist(),
                slice_loop(colors.BASE_COLORS.keys(), n_allegiances),
            )
        )
    elif isinstance(allegiance_color, Mapping):
        allegiance_color = dict(allegiance_color)
    else:
        allegiance_color = dict(zip(allegiances.tolist(), allegiance_color))

    return allegiances, allegiance_label, allegiance_color


def _get_plot_bounds(
    frames: np.ndarray, terrain: Terrain | None
) -> tuple[float, float, float, float]:
    if terrain is not None:
        xmin, xmax, ymin, ymax = terrain.bounds_
    else:
        xmin = float(frames["x"].min())
        xmax = float(frames["x"].max())
        ymin = float(frames["y"].min())
        ymax = float(frames["y"].max())
    return xmin, xmax, ymin, ymax


def _setup_axes(
    frames: np.ndarray,
    terrain: Terrain | None,
    allegiance_label: Mapping[object, str] | None,
    allegiance_color: Mapping[object, str] | Sequence[str] | None,
) -> tuple[
    plt.Figure,
    plt.Axes,
    np.ndarray,
    dict[object, str],
    dict[object, str],
    list[tuple[object, object]],
]:
    plt.rcParams["animation.html"] = "jshtml"

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)

    if terrain is not None:
        terrain.plot(ax, alpha=0.2)

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    allegiances, resolved_labels, resolved_colors = _resolve_allegiance_metadata(
        frames, allegiance_label, allegiance_color
    )
    unique_units = np.unique(frames["utype"])
    combs = list(it.product(allegiances, unique_units))

    xmin, xmax, ymin, ymax = _get_plot_bounds(frames, terrain)
    ax.set_xlim(xmin - 0.5, xmax + 0.5)
    ax.set_ylim(ymin - 0.5, ymax + 0.5)

    custom_lines = [
        Line2D([0], [0], color=resolved_colors[a], lw=4) for a in allegiances
    ]
    ax.legend(
        custom_lines, [resolved_labels[a] for a in allegiances], loc="upper right"
    )

    return fig, ax, allegiances, resolved_labels, resolved_colors, combs


def _frame_unit_subset(frame: np.ndarray, team: object, unit_type: object) -> np.ndarray:
    return frame[
        reduce(
            np.logical_and,
            [
                frame["hp"] > 0.0,
                frame["utype"] == unit_type,
                frame["team"] == team,
            ],
        )
    ]


def _hp_color(hp_ratio: float) -> str:
    if hp_ratio > 0.66:
        return "tab:green"
    if hp_ratio > 0.33:
        return "goldenrod"
    return "tab:red"


def _has_terrain_overlay_fields(frames: np.ndarray) -> bool:
    names = frames.dtype.names
    if names is None:
        return False
    required = {"z", "target_z", "move_factor", "effective_range", "damage_factor"}
    return required.issubset(names)


def quiver_fight(
    frames: np.ndarray,
    terrain: Terrain | None = None,
    allegiance_label: Mapping[object, str] | None = None,
    allegiance_color: Mapping[object, str] | Sequence[str] | None = None,
    interval: int = 100,
):
    """
    Generates an animated quiver plot with units moving around the arena
    and attacking each other. Requires the Frames object as output from a 'battle.simulate()'
    call.

    Units that are alive appear as directional quivers, units that are dead
    appear as crosses 'x'.

    We recommend you use this in conjunction with Jupyter notebook:
        HTML(bsm.quiver_fight(Frames).tojshtml())

    Parameters
    -------
    frames : pd.DataFrame
        The dataframe with each frame step to animate
        Columns included must be: 'x', 'y', 'dir_x', 'dir_y', 'allegiance', 'frame' and 'alive'
    terrain : bsm.Terrain object, optional
        A terra object to generate and draw from.
    allegiance_label : dict
        maps allegiance in Frames["allegiance"] (k) to a label str (v)
    allegiance_color : dict
        maps allegiance in Frames["allegiance"] (k) to a color str (v)

    Returns
    ------
    anim : matplotlib.pyplot.animation
        object to animate then from.
    """
    n_frames = frames.shape[0]
    fig, ax, allegiances, allegiance_label, allegiance_color, combs = _setup_axes(
        frames, terrain, allegiance_label, allegiance_color
    )

    """
    Create two groups for each allegiance:
        1. The units that are alive, are arrows.
        2. The units that are dead, are crosses 'x'
    """

    qalive = []
    dead = []

    for a, un in combs:
        f1 = _frame_unit_subset(frames[0], a, un)
        team_alive = ax.quiver(
            f1["x"],
            f1["y"],
            f1["ddx"],
            f1["ddy"],
            color=allegiance_color[a],
            alpha=0.5,
            scale=30,
            width=0.015,
            pivot="mid",
        )
        qalive.append(team_alive)

        (team_dead,) = ax.plot(
            [], [], "x", color=allegiance_color[a], alpha=0.2, markersize=5.0
        )
        dead.append(team_dead)

    fig.tight_layout()
    plt.close(fig)

    # an initialisation function = to plot at the beginning.
    def _init():
        for j, (_a, _un) in enumerate(combs):
            # replaced query with loc as it's way faster.
            new_alive = _frame_unit_subset(frames[0], _a, _un)
            if new_alive.shape[0] > 0:
                qalive[j].set_UVC(new_alive["ddx"], new_alive["ddy"])

        return (*qalive, *dead)

    # animating the graph with step i
    def _animate(i):
        # i is the frame, aligns with frames.
        for j, (_a, _un) in enumerate(combs):
            alive_i = frames[i]["hp"] > 0.0
            team_type_i = np.logical_and(
                frames[i]["team"] == _a, frames[i]["utype"] == _un
            )

            new_alive = frames[i][np.logical_and(team_type_i, alive_i)]
            new_dead = frames[i][np.logical_and(team_type_i, ~alive_i)]
            if len(new_alive) > 0:
                qalive[j].set_offsets(np.vstack((new_alive["x"], new_alive["y"])).T)
                # force N to be number of alive samples to prevent error
                qalive[j].N = new_alive.shape[0]
                qalive[j].set_UVC(new_alive["ddx"], new_alive["ddy"])
            if len(new_dead) > 0:
                dead[j].set_data(new_dead["x"], new_dead["y"])

        return (*qalive, *dead)

    return animation.FuncAnimation(
        fig, _animate, init_func=_init, interval=interval, frames=n_frames, blit=True
    )


def quiver_fight_debug(
    frames: np.ndarray,
    terrain: Terrain | None = None,
    allegiance_label: Mapping[object, str] | None = None,
    allegiance_color: Mapping[object, str] | Sequence[str] | None = None,
    show_hp: bool = True,
    show_target_lines: bool = True,
    show_terrain_text: bool = False,
    interval: int = 100,
):
    """
    Generates a debug-friendly animated quiver plot.

    In addition to the normal unit arrows and dead markers, this view can
    show compact HP bars, dashed lines to current targets, and terrain-derived
    debug values for each unit.
    """
    n_frames = frames.shape[0]
    fig, ax, _allegiances, _labels, allegiance_color, combs = _setup_axes(
        frames, terrain, allegiance_label, allegiance_color
    )

    qalive = []
    dead = []

    for team, unit_type in combs:
        frame0_subset = _frame_unit_subset(frames[0], team, unit_type)
        qalive.append(
            ax.quiver(
                frame0_subset["x"],
                frame0_subset["y"],
                frame0_subset["ddx"],
                frame0_subset["ddy"],
                color=allegiance_color[team],
                alpha=0.6,
                scale=30,
                width=0.015,
                pivot="mid",
                zorder=4,
            )
        )
        (team_dead,) = ax.plot(
            [], [], "x", color=allegiance_color[team], alpha=0.25, markersize=5.0, zorder=5
        )
        dead.append(team_dead)

    xmin, xmax, ymin, ymax = _get_plot_bounds(frames, terrain)
    plot_span = max(xmax - xmin, ymax - ymin, 1.0)
    hp_bar_width = plot_span * 0.04
    hp_bar_offset = plot_span * 0.015
    max_hp = np.maximum(frames["hp"].max(axis=0), 1.0)
    unit_colors = [allegiance_color[team] for team in frames[0]["team"]]
    has_terrain_fields = _has_terrain_overlay_fields(frames)

    target_lines = []
    hp_bars = []
    terrain_text = []
    for color in unit_colors:
        (target_line,) = ax.plot(
            [], [],
            linestyle="--",
            linewidth=0.8,
            color=color,
            alpha=0.25,
            zorder=2,
        )
        target_lines.append(target_line)
        (hp_bar,) = ax.plot(
            [], [],
            linewidth=2.2,
            solid_capstyle="round",
            color="tab:green",
            zorder=6,
        )
        hp_bars.append(hp_bar)
        terrain_text.append(
            ax.text(
                0.0,
                0.0,
                "",
                fontsize=6,
                ha="center",
                va="bottom",
                zorder=7,
                bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "alpha": 0.45, "edgecolor": "none"},
            )
        )

    fig.tight_layout()
    plt.close(fig)

    def _update_debug_overlays(frame_i: int):
        frame = frames[frame_i]
        n_units = frame.shape[0]

        for unit_i in range(n_units):
            alive = frame["hp"][unit_i] > 0.0

            if show_target_lines and alive:
                target_i = int(frame["target"][unit_i])
                if 0 <= target_i < n_units:
                    target_lines[unit_i].set_data(
                        [frame["x"][unit_i], frame["x"][target_i]],
                        [frame["y"][unit_i], frame["y"][target_i]],
                    )
                else:
                    target_lines[unit_i].set_data([], [])
            else:
                target_lines[unit_i].set_data([], [])

            if show_hp and alive:
                hp_ratio = float(np.clip(frame["hp"][unit_i] / max_hp[unit_i], 0.0, 1.0))
                x0 = float(frame["x"][unit_i] - (hp_bar_width / 2.0))
                y0 = float(frame["y"][unit_i] + hp_bar_offset)
                hp_bars[unit_i].set_data(
                    [x0, x0 + (hp_bar_width * hp_ratio)],
                    [y0, y0],
                )
                hp_bars[unit_i].set_color(_hp_color(hp_ratio))
            else:
                hp_bars[unit_i].set_data([], [])

            if show_terrain_text and has_terrain_fields and alive:
                text_x = float(frame["x"][unit_i])
                text_y = float(frame["y"][unit_i] + (hp_bar_offset * 2.2))
                terrain_text[unit_i].set_position((text_x, text_y))
                terrain_text[unit_i].set_text(
                    "\n".join(
                        [
                            f"z {frame['z'][unit_i]:.2f}",
                            f"mv {frame['move_factor'][unit_i]:.2f}  rg {frame['effective_range'][unit_i]:.2f}",
                            f"dmg {frame['damage_factor'][unit_i]:.2f}",
                        ]
                    )
                )
            else:
                terrain_text[unit_i].set_text("")

    def _init():
        for j, (team, unit_type) in enumerate(combs):
            new_alive = _frame_unit_subset(frames[0], team, unit_type)
            if new_alive.shape[0] > 0:
                qalive[j].set_UVC(new_alive["ddx"], new_alive["ddy"])

        _update_debug_overlays(0)
        return (*qalive, *dead, *target_lines, *hp_bars, *terrain_text)

    def _animate(frame_i: int):
        frame = frames[frame_i]
        for j, (team, unit_type) in enumerate(combs):
            alive_i = frame["hp"] > 0.0
            team_type_i = np.logical_and(
                frame["team"] == team, frame["utype"] == unit_type
            )
            new_alive = frame[np.logical_and(team_type_i, alive_i)]
            new_dead = frame[np.logical_and(team_type_i, ~alive_i)]

            if len(new_alive) > 0:
                qalive[j].set_offsets(np.vstack((new_alive["x"], new_alive["y"])).T)
                qalive[j].N = new_alive.shape[0]
                qalive[j].set_UVC(new_alive["ddx"], new_alive["ddy"])
            if len(new_dead) > 0:
                dead[j].set_data(new_dead["x"], new_dead["y"])

        _update_debug_overlays(frame_i)
        return (*qalive, *dead, *target_lines, *hp_bars, *terrain_text)

    return animation.FuncAnimation(
        fig, _animate, init_func=_init, interval=interval, frames=n_frames, blit=True
    )


def quiver_frame_debug(
    frames: np.ndarray,
    frame_i: int = 0,
    terrain: Terrain | None = None,
    allegiance_label: Mapping[object, str] | None = None,
    allegiance_color: Mapping[object, str] | Sequence[str] | None = None,
    show_hp: bool = True,
    show_target_lines: bool = True,
    show_terrain_text: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Draws a single debug frame for notebook inspection.
    """
    frame_index = max(0, min(frame_i, frames.shape[0] - 1))
    frame = frames[frame_index]
    fig, ax, _allegiances, _labels, allegiance_color, combs = _setup_axes(
        frames, terrain, allegiance_label, allegiance_color
    )

    xmin, xmax, ymin, ymax = _get_plot_bounds(frames, terrain)
    plot_span = max(xmax - xmin, ymax - ymin, 1.0)
    hp_bar_width = plot_span * 0.04
    hp_bar_offset = plot_span * 0.015
    max_hp = np.maximum(frames["hp"].max(axis=0), 1.0)
    has_terrain_fields = _has_terrain_overlay_fields(frames)

    for team, unit_type in combs:
        team_type_i = np.logical_and(frame["team"] == team, frame["utype"] == unit_type)
        alive = frame["hp"] > 0.0
        new_alive = frame[np.logical_and(team_type_i, alive)]
        new_dead = frame[np.logical_and(team_type_i, ~alive)]

        if len(new_alive) > 0:
            ax.quiver(
                new_alive["x"],
                new_alive["y"],
                new_alive["ddx"],
                new_alive["ddy"],
                color=allegiance_color[team],
                alpha=0.6,
                scale=30,
                width=0.015,
                pivot="mid",
                zorder=4,
            )
        if len(new_dead) > 0:
            ax.plot(
                new_dead["x"],
                new_dead["y"],
                "x",
                color=allegiance_color[team],
                alpha=0.25,
                markersize=5.0,
                zorder=5,
            )

    for unit_i in range(frame.shape[0]):
        alive = frame["hp"][unit_i] > 0.0
        if not alive:
            continue

        unit_color = allegiance_color[frame["team"][unit_i]]
        x_i = float(frame["x"][unit_i])
        y_i = float(frame["y"][unit_i])

        if show_target_lines:
            target_i = int(frame["target"][unit_i])
            if 0 <= target_i < frame.shape[0]:
                ax.plot(
                    [x_i, frame["x"][target_i]],
                    [y_i, frame["y"][target_i]],
                    linestyle="--",
                    linewidth=0.8,
                    color=unit_color,
                    alpha=0.25,
                    zorder=2,
                )

        if show_hp:
            hp_ratio = float(np.clip(frame["hp"][unit_i] / max_hp[unit_i], 0.0, 1.0))
            x0 = x_i - (hp_bar_width / 2.0)
            y0 = y_i + hp_bar_offset
            ax.plot(
                [x0, x0 + (hp_bar_width * hp_ratio)],
                [y0, y0],
                linewidth=2.2,
                solid_capstyle="round",
                color=_hp_color(hp_ratio),
                zorder=6,
            )

        if show_terrain_text and has_terrain_fields:
            ax.text(
                x_i,
                y_i + (hp_bar_offset * 2.2),
                "\n".join(
                    [
                        f"z {frame['z'][unit_i]:.2f}",
                        f"mv {frame['move_factor'][unit_i]:.2f}  rg {frame['effective_range'][unit_i]:.2f}",
                        f"dmg {frame['damage_factor'][unit_i]:.2f}",
                    ]
                ),
                fontsize=6,
                ha="center",
                va="bottom",
                zorder=7,
                bbox={
                    "boxstyle": "round,pad=0.15",
                    "facecolor": "white",
                    "alpha": 0.45,
                    "edgecolor": "none",
                },
            )

    ax.set_title(f"Frame {frame_index}")
    fig.tight_layout()
    return fig, ax
