"""Reusable, interface-independent battle scenario definitions."""

import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from battlesim._battle import Battle
from battlesim._scenario_input import ArmySpecInput, BattleScenarioInput
from battlesim.contracts import BattleRules, CoverZone, ObjectiveZone
from battlesim.distrib import Composite, Sampling

_POSITION_DISTRIBUTIONS = {
    "beta",
    "binomial",
    "chisquare",
    "exponential",
    "laplace",
    "lognormal",
    "normal",
    "uniform",
}
_TARGET_AIS = {
    "nearest",
    "random",
    "close_weak",
    "weakest",
    "highest_threat",
    "focus_fire",
    "objective_priority",
}
_DECISION_AIS = {"aggressive", "hit_and_run"}


@dataclass(frozen=True)
class ArmySpec:
    """Configuration for one unit group."""

    name: str
    count: int
    position_distribution: str = "normal"
    position_parameters: tuple[float, ...] = ()
    init_ai: str = "nearest"
    rolling_ai: str = "nearest"
    decision_ai: str = "aggressive"
    doctrine_weights: tuple[float, float, float, float] = (0.25, 0.15, 0.5, 0.1)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("army name must not be empty")
        if type(self.count) is not int or self.count < 1:
            raise ValueError("army count must be a positive integer")
        if self.position_distribution not in _POSITION_DISTRIBUTIONS:
            raise ValueError("unsupported position_distribution")
        if self.init_ai not in _TARGET_AIS or self.rolling_ai not in _TARGET_AIS:
            raise ValueError("unsupported targeting AI")
        if self.decision_ai not in _DECISION_AIS:
            raise ValueError("unsupported decision AI")
        numeric = (*self.position_parameters, *self.doctrine_weights)
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("army numeric parameters must be finite")
        if any(weight < 0 for weight in self.doctrine_weights):
            raise ValueError("doctrine_weights must be non-negative")
        if sum(self.doctrine_weights) <= 0:
            raise ValueError("doctrine_weights must contain a positive value")

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "ArmySpec":
        validated = ArmySpecInput.model_validate(data)
        weight_values = validated.doctrine_weights
        return cls(
            name=validated.name,
            count=validated.count,
            position_distribution=validated.position_distribution,
            position_parameters=tuple(validated.position_parameters),
            init_ai=validated.init_ai,
            rolling_ai=validated.rolling_ai,
            decision_ai=validated.decision_ai,
            doctrine_weights=(
                weight_values[0],
                weight_values[1],
                weight_values[2],
                weight_values[3],
            ),
        )

    def to_composite(self) -> Composite:
        return Composite(
            self.name,
            self.count,
            pos_dist=Sampling(
                self.position_distribution,
                *self.position_parameters,
            ),
            init_ai=self.init_ai,
            rolling_ai=self.rolling_ai,
            decision_ai=self.decision_ai,
            doctrine_weights=self.doctrine_weights,
        )


@dataclass(frozen=True)
class BattleScenario:
    """Complete input required to construct and run a battle."""

    armies: tuple[ArmySpec, ...]
    database: str | None = None
    bounds: tuple[float, float, float, float] = (0.0, 10.0, 0.0, 10.0)
    terrain: str | None = None
    terrain_resolution: float = 0.1
    seed: int = 0
    family: str = "default"
    rules: BattleRules = field(default_factory=BattleRules)

    def __post_init__(self) -> None:
        if len(self.armies) < 2:
            raise ValueError("scenario must contain at least two armies")
        if len(self.bounds) != 4 or not all(
            math.isfinite(value) for value in self.bounds
        ):
            raise ValueError("scenario bounds must contain four finite values")
        xmin, xmax, ymin, ymax = self.bounds
        if xmin >= xmax or ymin >= ymax:
            raise ValueError("scenario bounds must be ordered and non-degenerate")
        if not math.isfinite(self.terrain_resolution) or self.terrain_resolution <= 0:
            raise ValueError("terrain_resolution must be finite and positive")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if not self.family:
            raise ValueError("scenario family must not be empty")
        if self.terrain not in (None, "grid", "contour"):
            raise ValueError("scenario terrain must be grid, contour, or omitted")

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, object],
        *,
        base_directory: Path | None = None,
    ) -> "BattleScenario":
        validated = BattleScenarioInput.model_validate(data)
        database = validated.database
        if database is not None and base_directory is not None:
            database_path = Path(database)
            if not database_path.is_absolute():
                database = str((base_directory / database_path).resolve())

        objectives = tuple(
            ObjectiveZone(
                x=item.x,
                y=item.y,
                radius=item.radius,
                capture_ticks=item.capture_ticks,
            )
            for item in validated.rules.objectives
        )
        covers = tuple(
            CoverZone(
                x=item.x,
                y=item.y,
                radius=item.radius,
                hit_multiplier=item.hit_multiplier,
            )
            for item in validated.rules.covers
        )
        rules = BattleRules(
            version=validated.rules.version,
            tick_seconds=validated.rules.tick_seconds,
            max_ticks=validated.rules.max_ticks,
            stalemate_ticks=validated.rules.stalemate_ticks,
            simultaneous=validated.rules.simultaneous,
            line_of_sight=validated.rules.line_of_sight,
            collision=validated.rules.collision,
            slope_movement=validated.rules.slope_movement,
            cover_hit_multiplier=validated.rules.cover_hit_multiplier,
            objectives=objectives,
            covers=covers,
        )

        return cls(
            armies=tuple(
                ArmySpec(
                    name=army.name,
                    count=army.count,
                    position_distribution=army.position_distribution,
                    position_parameters=tuple(army.position_parameters),
                    init_ai=army.init_ai,
                    rolling_ai=army.rolling_ai,
                    decision_ai=army.decision_ai,
                    doctrine_weights=(
                        army.doctrine_weights[0],
                        army.doctrine_weights[1],
                        army.doctrine_weights[2],
                        army.doctrine_weights[3],
                    ),
                )
                for army in validated.armies
            ),
            database=database,
            bounds=(
                validated.bounds[0],
                validated.bounds[1],
                validated.bounds[2],
                validated.bounds[3],
            ),
            terrain=validated.terrain,
            terrain_resolution=validated.terrain_resolution,
            seed=validated.seed,
            family=validated.family,
            rules=rules,
        )

    @classmethod
    def from_toml(cls, filename: str | Path) -> "BattleScenario":
        path = Path(filename)
        with path.open("rb") as stream:
            data = tomllib.load(stream)
        return cls.from_mapping(data, base_directory=path.resolve().parent)

    def run(self, *, seed: int | None = None) -> Battle:
        selected_seed = self.seed if seed is None else seed
        battle = (
            Battle(
                self.database,
                bounds=self.bounds,
                use_tqdm=False,
                seed=selected_seed,
                rules=self.rules,
            )
            if self.database is not None
            else Battle(
                bounds=self.bounds,
                use_tqdm=False,
                seed=selected_seed,
                rules=self.rules,
            )
        )
        battle.create_army([army.to_composite() for army in self.armies])
        battle.apply_terrain(self.terrain, res=self.terrain_resolution)
        battle.simulate(seed=selected_seed)
        return battle
