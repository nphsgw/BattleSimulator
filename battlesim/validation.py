"""Validity and sensitivity helpers for simulator and surrogate datasets."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from battlesim.contracts import BattleResult
from battlesim.dataset import result_to_record, wilson_interval


@dataclass(frozen=True)
class ValidationIssue:
    """One machine-readable validity problem."""

    code: str
    message: str
    trial_id: str | None = None


def validate_results(results: Iterable[BattleResult]) -> tuple[ValidationIssue, ...]:
    """Check provenance, numeric bounds, identity, and duplicate trials."""
    materialized = tuple(results)
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    versions = {(item.rules_version, item.schema_version) for item in materialized}
    if len(versions) > 1:
        issues.append(
            ValidationIssue(
                "mixed_versions",
                "results contain more than one rules/result schema version",
            )
        )
    for result in materialized:
        if result.trial_id in seen:
            issues.append(
                ValidationIssue(
                    "duplicate_trial", "trial_id is duplicated", result.trial_id
                )
            )
        seen.add(result.trial_id)
        team_ids = {team.team_id for team in result.teams}
        if not set(result.winner_team_ids).issubset(team_ids):
            issues.append(
                ValidationIssue(
                    "unknown_winner",
                    "winner is absent from team results",
                    result.trial_id,
                )
            )
        for team in result.teams:
            numeric = (
                team.remaining_hp,
                team.remaining_armor,
                team.damage_dealt,
                team.damage_received,
                team.movement,
            )
            if not np.isfinite(numeric).all() or min(numeric) < 0:
                issues.append(
                    ValidationIssue(
                        "invalid_numeric_state",
                        f"team {team.team_id} has negative or non-finite state",
                        result.trial_id,
                    )
                )
            if not 0 <= team.remaining_units <= team.initial_units:
                issues.append(
                    ValidationIssue(
                        "invalid_survivor_count",
                        f"team {team.team_id} survivor count is outside bounds",
                        result.trial_id,
                    )
                )
    return tuple(issues)


def monte_carlo_summary(
    results: Sequence[BattleResult],
    *,
    team_id: int,
) -> dict[str, float | int]:
    """Win probability, uncertainty, and common aggregate outcomes."""
    if not results:
        raise ValueError("results must not be empty")
    wins = sum(team_id in result.winner_team_ids for result in results)
    lower, upper = wilson_interval(wins, len(results))
    return {
        "trials": len(results),
        "wins": wins,
        "win_probability": wins / len(results),
        "win_probability_lower": lower,
        "win_probability_upper": upper,
        "mean_ticks": float(np.mean([result.ticks for result in results])),
        "undecided_rate": sum(not result.decided for result in results) / len(results),
    }


def sensitivity_analysis(
    values: Sequence[float],
    evaluator: Callable[[float, int], BattleResult],
    *,
    replicates: int,
    seed: int = 0,
    outcome: Callable[[BattleResult], float] | None = None,
) -> pd.DataFrame:
    """Evaluate a scalar parameter with common replicate seeds."""
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    measure = (lambda result: float(result.ticks)) if outcome is None else outcome
    rows: list[dict[str, Any]] = []
    for value in values:
        samples = [
            measure(evaluator(value, seed + index)) for index in range(replicates)
        ]
        rows.append(
            {
                "parameter_value": value,
                "replicates": replicates,
                "mean": float(np.mean(samples)),
                "std": float(np.std(samples)),
                "minimum": float(np.min(samples)),
                "maximum": float(np.max(samples)),
            }
        )
    return pd.DataFrame(rows)


def surrogate_frame(
    results: Iterable[BattleResult],
    *,
    scenario_family: str = "default",
) -> pd.DataFrame:
    """Create fixed-length aggregate features suitable for a first surrogate."""
    frame = pd.DataFrame(
        [
            result_to_record(result, scenario_family=scenario_family)
            for result in results
        ]
    )
    if frame.empty:
        return frame
    frame["hit_rate"] = np.where(
        frame["shots"] > 0, frame["hits"] / frame["shots"], 0.0
    )
    frame["contact_fraction"] = np.where(
        frame["ticks"] > 0,
        frame["first_contact_tick"].fillna(frame["ticks"]) / frame["ticks"],
        0.0,
    )
    return frame
