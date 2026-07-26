"""Strict, external-input models for scenario configuration."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

PositiveInt = Annotated[StrictInt, Field(gt=0)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveFloat = Annotated[FiniteFloat, Field(gt=0)]
Probability = Annotated[FiniteFloat, Field(ge=0, le=1)]
NonEmptyString = Annotated[StrictStr, Field(min_length=1)]

PositionDistribution = Literal[
    "beta",
    "binomial",
    "chisquare",
    "exponential",
    "laplace",
    "lognormal",
    "normal",
    "uniform",
]
TargetAI = Literal[
    "nearest",
    "random",
    "close_weak",
    "weakest",
    "highest_threat",
    "focus_fire",
    "objective_priority",
]
DecisionAI = Literal["aggressive", "hit_and_run"]
TerrainForm = Literal["grid", "contour"]


class StrictInputModel(BaseModel):
    """Common policy for data crossing into the simulation."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ObjectiveZoneInput(StrictInputModel):
    x: FiniteFloat
    y: FiniteFloat
    radius: PositiveFloat
    capture_ticks: PositiveInt


class CoverZoneInput(StrictInputModel):
    x: FiniteFloat
    y: FiniteFloat
    radius: PositiveFloat
    hit_multiplier: Probability = 0.6


class BattleRulesInput(StrictInputModel):
    version: NonEmptyString = "1.0"
    tick_seconds: PositiveFloat = 1.0
    max_ticks: PositiveInt = 100
    stalemate_ticks: PositiveInt = 20
    simultaneous: StrictBool = True
    line_of_sight: StrictBool = True
    collision: StrictBool = True
    slope_movement: StrictBool = True
    cover_hit_multiplier: Probability = 0.6
    covers: list[CoverZoneInput] = Field(default_factory=list)
    objectives: list[ObjectiveZoneInput] = Field(default_factory=list)


class ArmySpecInput(StrictInputModel):
    name: NonEmptyString
    count: PositiveInt
    position_distribution: PositionDistribution = "normal"
    position_parameters: list[FiniteFloat] = Field(default_factory=list)
    init_ai: TargetAI = "nearest"
    rolling_ai: TargetAI = "nearest"
    decision_ai: DecisionAI = "aggressive"
    doctrine_weights: list[FiniteFloat] = Field(
        default_factory=lambda: [0.25, 0.15, 0.5, 0.1],
        min_length=4,
        max_length=4,
    )

    @model_validator(mode="after")
    def validate_doctrine_weights(self) -> Self:
        if any(weight < 0 for weight in self.doctrine_weights):
            raise ValueError("doctrine_weights must be non-negative")
        if sum(self.doctrine_weights) <= 0:
            raise ValueError("doctrine_weights must contain a positive value")
        return self


class BattleScenarioInput(StrictInputModel):
    armies: list[ArmySpecInput]
    database: NonEmptyString | None = None
    bounds: list[FiniteFloat] = Field(
        default_factory=lambda: [0.0, 10.0, 0.0, 10.0],
        min_length=4,
        max_length=4,
    )
    terrain: TerrainForm | None = None
    terrain_resolution: PositiveFloat = 0.1
    seed: NonNegativeInt = 0
    family: NonEmptyString = "default"
    rules: BattleRulesInput = Field(default_factory=BattleRulesInput)

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if len(self.armies) < 2:
            raise ValueError("scenario must contain at least two armies")
        xmin, xmax, ymin, ymax = self.bounds
        if xmin >= xmax:
            raise ValueError("scenario xmin must be less than xmax")
        if ymin >= ymax:
            raise ValueError("scenario ymin must be less than ymax")
        return self
