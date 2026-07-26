"""Versioned contracts shared by simulation, datasets, and surrogate tooling."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

RULES_VERSION = "1.0"
RESULT_SCHEMA_VERSION = "1.0"
DATASET_SCHEMA_VERSION = "1.0"


class TerminationReason(StrEnum):
    """Why a tactical simulation stopped."""

    ELIMINATION = "elimination"
    MUTUAL_DESTRUCTION = "mutual_destruction"
    TIMEOUT = "timeout"
    STALEMATE = "stalemate"
    OBJECTIVE = "objective"


@dataclass(frozen=True)
class ObjectiveZone:
    """Circular zone captured by uncontested occupation."""

    x: float
    y: float
    radius: float
    capture_ticks: int

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x, self.y, self.radius)):
            raise ValueError("objective coordinates and radius must be finite")
        if self.radius <= 0:
            raise ValueError("objective radius must be positive")
        if type(self.capture_ticks) is not int or self.capture_ticks < 1:
            raise ValueError("objective capture_ticks must be a positive integer")


@dataclass(frozen=True)
class CoverZone:
    """Circular area that reduces incoming hit chance."""

    x: float
    y: float
    radius: float
    hit_multiplier: float = 0.6

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.x, self.y, self.radius, self.hit_multiplier)
        ):
            raise ValueError("cover values must be finite")
        if self.radius <= 0:
            raise ValueError("cover radius must be positive")
        if not 0 <= self.hit_multiplier <= 1:
            raise ValueError("cover hit_multiplier must be in [0, 1]")


@dataclass(frozen=True)
class BattleRules:
    """Rules that affect outcomes and therefore participate in versioning."""

    version: str = RULES_VERSION
    tick_seconds: float = 1.0
    max_ticks: int = 100
    stalemate_ticks: int = 20
    simultaneous: bool = True
    line_of_sight: bool = True
    collision: bool = True
    slope_movement: bool = True
    cover_hit_multiplier: float = 0.6
    covers: tuple[CoverZone, ...] = ()
    objectives: tuple[ObjectiveZone, ...] = ()

    def __post_init__(self) -> None:
        numeric = (self.tick_seconds, self.cover_hit_multiplier)
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("battle rule numeric values must be finite")
        if self.tick_seconds <= 0:
            raise ValueError("tick_seconds must be positive")
        if type(self.max_ticks) is not int or self.max_ticks < 1:
            raise ValueError("max_ticks must be a positive integer")
        if type(self.stalemate_ticks) is not int or self.stalemate_ticks < 1:
            raise ValueError("stalemate_ticks must be a positive integer")
        if not 0 <= self.cover_hit_multiplier <= 1:
            raise ValueError("cover_hit_multiplier must be in [0, 1]")


@dataclass(frozen=True)
class BattleEvent:
    """One auditable state transition."""

    tick: int
    kind: str
    actor_id: int
    target_id: int | None = None
    value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamResult:
    """Terminal aggregate for one team."""

    team_id: int
    initial_units: int
    remaining_units: int
    remaining_hp: float
    remaining_armor: float
    team_label: str | None = None
    damage_dealt: float = 0.0
    damage_received: float = 0.0
    shots: int = 0
    hits: int = 0
    kills: int = 0
    movement: float = 0.0
    high_ground_ticks: int = 0
    cover_ticks: int = 0
    objective_ticks: int = 0
    spatial_dispersion: float = 0.0
    force_exchange_ratio: float | None = None


@dataclass(frozen=True)
class BattleResult:
    """Versioned, serialization-friendly simulation result."""

    scenario_id: str
    trial_id: str
    seed: int
    simulator_version: str
    rules_version: str
    schema_version: str
    ticks: int
    termination_reason: TerminationReason
    winner_team_ids: tuple[int, ...]
    first_contact_tick: int | None
    teams: tuple[TeamResult, ...]
    scenario_features: dict[str, Any] = field(default_factory=dict)
    randomized_subsystems: tuple[str, ...] = ()
    events: tuple[BattleEvent, ...] = ()

    @property
    def decided(self) -> bool:
        return bool(self.winner_team_ids)

    def to_dict(self, *, include_events: bool = True) -> dict[str, Any]:
        record = asdict(self)
        record["termination_reason"] = self.termination_reason.value
        if not include_events:
            record.pop("events")
        return record
