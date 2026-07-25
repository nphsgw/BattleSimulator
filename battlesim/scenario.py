"""Reusable, interface-independent battle scenario definitions."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from battlesim._battle import Battle
from battlesim.contracts import BattleRules, CoverZone, ObjectiveZone
from battlesim.distrib import Composite, Sampling


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

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ArmySpec":
        weight_values = tuple(
            float(value)
            for value in data.get("doctrine_weights", (0.25, 0.15, 0.5, 0.1))
        )
        if len(weight_values) != 4:
            raise ValueError("doctrine_weights must contain four values")
        return cls(
            name=str(data["name"]),
            count=int(data["count"]),
            position_distribution=str(data.get("position_distribution", "normal")),
            position_parameters=tuple(
                float(value) for value in data.get("position_parameters", ())
            ),
            init_ai=str(data.get("init_ai", "nearest")),
            rolling_ai=str(data.get("rolling_ai", "nearest")),
            decision_ai=str(data.get("decision_ai", "aggressive")),
            doctrine_weights=(
                weight_values[0],
                weight_values[1],
                weight_values[2],
                weight_values[3],
            ),
        )

    def to_composite(self) -> Composite:
        if self.count < 1:
            raise ValueError("army count must be at least 1")
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

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        base_directory: Path | None = None,
    ) -> "BattleScenario":
        database = data.get("database")
        if database is not None and base_directory is not None:
            database_path = Path(str(database))
            if not database_path.is_absolute():
                database = str((base_directory / database_path).resolve())

        bounds_data = data.get("bounds", (0.0, 10.0, 0.0, 10.0))
        if len(bounds_data) != 4:
            raise ValueError("scenario bounds must contain four values")

        armies = tuple(ArmySpec.from_mapping(army) for army in data.get("armies", ()))
        if len(armies) < 2:
            raise ValueError("scenario must contain at least two armies")

        terrain = data.get("terrain")
        if terrain not in (None, "grid", "contour"):
            raise ValueError("scenario terrain must be grid, contour, or omitted")

        rules_data = dict(data.get("rules", {}))
        objectives = tuple(
            ObjectiveZone(
                x=float(item["x"]),
                y=float(item["y"]),
                radius=float(item["radius"]),
                capture_ticks=int(item["capture_ticks"]),
            )
            for item in rules_data.pop("objectives", ())
        )
        covers = tuple(
            CoverZone(
                x=float(item["x"]),
                y=float(item["y"]),
                radius=float(item["radius"]),
                hit_multiplier=float(item.get("hit_multiplier", 0.6)),
            )
            for item in rules_data.pop("covers", ())
        )
        rules = BattleRules(
            **rules_data,
            objectives=objectives,
            covers=covers,
        )

        return cls(
            armies=armies,
            database=str(database) if database is not None else None,
            bounds=(
                float(bounds_data[0]),
                float(bounds_data[1]),
                float(bounds_data[2]),
                float(bounds_data[3]),
            ),
            terrain=terrain,
            terrain_resolution=float(data.get("terrain_resolution", 0.1)),
            seed=int(data.get("seed", 0)),
            family=str(data.get("family", "default")),
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
