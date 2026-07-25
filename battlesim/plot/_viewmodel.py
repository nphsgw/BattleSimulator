"""UI-independent data model for battle visualizations."""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

_REQUIRED_FIELDS = {
    "x",
    "y",
    "ddx",
    "ddy",
    "hp",
    "target",
    "team",
    "utype",
}
_TERRAIN_FIELDS = {
    "z",
    "target_z",
    "move_factor",
    "effective_range",
    "damage_factor",
}


@dataclass(frozen=True)
class UnitView:
    """Display-ready state for one unit in one frame."""

    index: int
    team: int
    unit_type: int
    x: float
    y: float
    direction_x: float
    direction_y: float
    hp: float
    max_hp: float
    hp_ratio: float
    armor: float | None
    alive: bool
    target_index: int | None
    target_position: tuple[float, float] | None
    z: float | None = None
    target_z: float | None = None
    move_factor: float | None = None
    effective_range: float | None = None
    damage_factor: float | None = None


@dataclass(frozen=True)
class FrameView:
    """Display-ready state for a complete simulation frame."""

    frame_index: int
    frame_count: int
    units: tuple[UnitView, ...]
    has_terrain: bool


@dataclass(frozen=True)
class UnitParameterView:
    """Display-ready parameter values linked to a numbered unit."""

    number: int
    team: str
    unit_type: str
    alive: bool
    hp: float
    max_hp: float
    armor: float | None
    target_number: int | None
    z: float | None
    move_factor: float | None
    effective_range: float | None
    damage_factor: float | None


def advance_playback(frame_i: int, frame_count: int) -> tuple[int, bool]:
    """Advance one frame and report whether playback should continue."""
    if frame_count < 1:
        raise ValueError("frame_count must be at least 1")
    next_frame = min(frame_i + 1, frame_count - 1)
    return next_frame, next_frame < frame_count - 1


def build_unit_parameter_views(
    frame: FrameView,
    *,
    team_labels: Mapping[int, str] | None = None,
    unit_type_labels: Mapping[int, str] | None = None,
) -> tuple[UnitParameterView, ...]:
    """Build the rows shown beside a numbered battle frame."""
    team_labels = team_labels or {}
    unit_type_labels = unit_type_labels or {}
    return tuple(
        UnitParameterView(
            number=unit.index + 1,
            team=team_labels.get(unit.team, str(unit.team)),
            unit_type=unit_type_labels.get(unit.unit_type, str(unit.unit_type)),
            alive=unit.alive,
            hp=unit.hp,
            max_hp=unit.max_hp,
            armor=unit.armor,
            target_number=(
                unit.target_index + 1 if unit.target_index is not None else None
            ),
            z=unit.z,
            move_factor=unit.move_factor,
            effective_range=unit.effective_range,
            damage_factor=unit.damage_factor,
        )
        for unit in frame.units
    )


def build_frame_view(frames: np.ndarray, frame_i: int = 0) -> FrameView:
    """Convert structured simulation frames into immutable display data."""
    if not isinstance(frames, np.ndarray) or frames.ndim != 2:
        raise TypeError("frames must be a two-dimensional NumPy array")
    if frames.shape[0] == 0:
        raise ValueError("frames must contain at least one frame")

    field_names = set(frames.dtype.names or ())
    missing = _REQUIRED_FIELDS - field_names
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"frames are missing visualization fields: {missing_text}")

    frame_index = max(0, min(int(frame_i), frames.shape[0] - 1))
    frame = frames[frame_index]
    max_hp = np.maximum(frames["hp"].max(axis=0), 1.0)
    has_terrain = _TERRAIN_FIELDS.issubset(field_names)
    has_armor = "armor" in field_names
    units = []

    for unit_i in range(frame.shape[0]):
        hp = float(frame["hp"][unit_i])
        unit_max_hp = float(max_hp[unit_i])
        raw_target_i = int(frame["target"][unit_i])
        target_i = raw_target_i if 0 <= raw_target_i < frame.shape[0] else None
        target_position = (
            (
                float(frame["x"][target_i]),
                float(frame["y"][target_i]),
            )
            if target_i is not None
            else None
        )

        terrain_values = (
            {
                "z": float(frame["z"][unit_i]),
                "target_z": float(frame["target_z"][unit_i]),
                "move_factor": float(frame["move_factor"][unit_i]),
                "effective_range": float(frame["effective_range"][unit_i]),
                "damage_factor": float(frame["damage_factor"][unit_i]),
            }
            if has_terrain
            else {}
        )

        units.append(
            UnitView(
                index=unit_i,
                team=int(frame["team"][unit_i]),
                unit_type=int(frame["utype"][unit_i]),
                x=float(frame["x"][unit_i]),
                y=float(frame["y"][unit_i]),
                direction_x=float(frame["ddx"][unit_i]),
                direction_y=float(frame["ddy"][unit_i]),
                hp=hp,
                max_hp=unit_max_hp,
                hp_ratio=float(np.clip(hp / unit_max_hp, 0.0, 1.0)),
                armor=(float(frame["armor"][unit_i]) if has_armor else None),
                alive=hp > 0.0,
                target_index=target_i,
                target_position=target_position,
                **terrain_values,
            )
        )

    return FrameView(
        frame_index=frame_index,
        frame_count=frames.shape[0],
        units=tuple(units),
        has_terrain=has_terrain,
    )
