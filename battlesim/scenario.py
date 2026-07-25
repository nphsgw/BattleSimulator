"""Reusable, interface-independent battle scenario definitions."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from battlesim._battle import Battle
from battlesim.distrib import Composite, Sampling


@dataclass(frozen=True)
class ArmySpec:
    """Configuration for one unit group."""

    name: str
    count: int
    position_distribution: str = "normal"
    position_parameters: tuple[float, ...] = ()
    decision_ai: str = "aggressive"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ArmySpec":
        return cls(
            name=str(data["name"]),
            count=int(data["count"]),
            position_distribution=str(data.get("position_distribution", "normal")),
            position_parameters=tuple(
                float(value) for value in data.get("position_parameters", ())
            ),
            decision_ai=str(data.get("decision_ai", "aggressive")),
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
            decision_ai=self.decision_ai,
        )


@dataclass(frozen=True)
class BattleScenario:
    """Complete input required to construct and run a battle."""

    armies: tuple[ArmySpec, ...]
    database: str | None = None
    bounds: tuple[float, float, float, float] = (0.0, 10.0, 0.0, 10.0)
    terrain: str | None = None
    terrain_resolution: float = 0.1

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
        )

    @classmethod
    def from_toml(cls, filename: str | Path) -> "BattleScenario":
        path = Path(filename)
        with path.open("rb") as stream:
            data = tomllib.load(stream)
        return cls.from_mapping(data, base_directory=path.resolve().parent)

    def run(self) -> Battle:
        battle = (
            Battle(self.database, bounds=self.bounds, use_tqdm=False)
            if self.database is not None
            else Battle(bounds=self.bounds, use_tqdm=False)
        )
        battle.create_army([army.to_composite() for army in self.armies])
        battle.apply_terrain(self.terrain, res=self.terrain_resolution)
        battle.simulate()
        return battle
