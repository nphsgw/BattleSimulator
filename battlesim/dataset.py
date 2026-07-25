"""Deterministic batch execution and surrogate-ready tabular exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from battlesim.contracts import (
    DATASET_SCHEMA_VERSION,
    BattleResult,
    BattleRules,
)
from battlesim.randomness import derive_trial_seed
from battlesim.scenario import BattleScenario


def wilson_interval(
    successes: int, trials: int, z: float = 1.96
) -> tuple[float, float]:
    """Binomial Wilson score interval."""
    if trials < 1:
        raise ValueError("trials must be at least 1")
    if not 0 <= successes <= trials:
        raise ValueError("successes must be in [0, trials]")
    proportion = successes / trials
    denominator = 1 + (z * z / trials)
    centre = (proportion + (z * z / (2 * trials))) / denominator
    margin = (
        z
        * np.sqrt(
            (proportion * (1 - proportion) / trials) + (z * z / (4 * trials * trials))
        )
        / denominator
    )
    return float(centre - margin), float(centre + margin)


def result_to_record(
    result: BattleResult,
    *,
    scenario_family: str = "default",
) -> dict[str, Any]:
    """Flatten stable aggregate features while preserving per-team JSON."""
    teams = [asdict(team) for team in result.teams]
    team_labels = {team.team_id: team.team_label for team in result.teams}
    total_initial = sum(team.initial_units for team in result.teams)
    total_remaining = sum(team.remaining_units for team in result.teams)
    total_hp = sum(team.remaining_hp for team in result.teams)
    total_armor = sum(team.remaining_armor for team in result.teams)
    record = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "result_schema_version": result.schema_version,
        "rules_version": result.rules_version,
        "simulator_version": result.simulator_version,
        "scenario_family": scenario_family,
        "partition": scenario_family_partition(scenario_family),
        "scenario_id": result.scenario_id,
        "trial_id": result.trial_id,
        "seed": result.seed,
        "randomized_subsystems": json.dumps(result.randomized_subsystems),
        "termination_reason": result.termination_reason.value,
        "winner_team_ids": json.dumps(result.winner_team_ids),
        "winner_team_labels": json.dumps(
            [team_labels[team_id] for team_id in result.winner_team_ids]
        ),
        "ticks": result.ticks,
        "first_contact_tick": result.first_contact_tick,
        "total_initial_units": total_initial,
        "total_remaining_units": total_remaining,
        "survival_rate": total_remaining / total_initial if total_initial else 0.0,
        "remaining_hp": total_hp,
        "remaining_armor": total_armor,
        "damage_dealt": sum(team.damage_dealt for team in result.teams),
        "shots": sum(team.shots for team in result.teams),
        "hits": sum(team.hits for team in result.teams),
        "kills": sum(team.kills for team in result.teams),
        "movement": sum(team.movement for team in result.teams),
        "high_ground_ticks": sum(team.high_ground_ticks for team in result.teams),
        "cover_ticks": sum(team.cover_ticks for team in result.teams),
        "objective_ticks": sum(team.objective_ticks for team in result.teams),
        "mean_spatial_dispersion": float(
            np.mean([team.spatial_dispersion for team in result.teams])
        ),
        "team_results": json.dumps(teams, sort_keys=True, separators=(",", ":")),
        "scenario_features": json.dumps(
            result.scenario_features, sort_keys=True, separators=(",", ":")
        ),
    }
    record.update(
        {
            f"input_{name}": value
            for name, value in result.scenario_features.items()
            if isinstance(value, (int, float, str, bool))
        }
    )
    return record


def export_results(
    results: Iterable[BattleResult],
    filename: str | Path,
    *,
    scenario_families: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Write CSV, JSONL, or Parquet based on the filename suffix."""
    path = Path(filename)
    family_map = {} if scenario_families is None else scenario_families
    records = [
        result_to_record(
            result,
            scenario_family=family_map.get(result.scenario_id, "default"),
        )
        for result in results
    ]
    frame = pd.DataFrame(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame.to_csv(path, index=False)
    elif suffix in {".jsonl", ".ndjson"}:
        frame.to_json(path, orient="records", lines=True)
    elif suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        raise ValueError("dataset filename must end in .csv, .jsonl, or .parquet")
    return frame


def _scenario_fingerprint(scenario: BattleScenario) -> int:
    canonical = json.dumps(
        asdict(scenario),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return int.from_bytes(hashlib.sha256(canonical.encode()).digest()[:8], "little")


def run_batch(
    scenarios: Iterable[BattleScenario],
    *,
    trials: int,
    seed: int = 0,
    output: str | Path | None = None,
    resume: bool = True,
    manifest: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Run scenario families deterministically and optionally resume an export."""
    scenario_list = tuple(scenarios)
    if trials < 1:
        raise ValueError("trials must be at least 1")
    existing = pd.DataFrame()
    existing_trial_ids: set[str] = set()
    existing_versions: set[tuple[str, str]] = set()
    path = Path(output) if output is not None else None
    if resume and path is not None and path.exists():
        if path.suffix.casefold() == ".csv":
            existing = pd.read_csv(path)
        elif path.suffix.casefold() in {".jsonl", ".ndjson"}:
            existing = pd.read_json(path, orient="records", lines=True)
        elif path.suffix.casefold() == ".parquet":
            existing = pd.read_parquet(path)
        existing_trial_ids = set(existing.get("trial_id", ()))
        if not existing.empty:
            existing_versions = set(
                zip(
                    existing["rules_version"].astype(str),
                    existing["schema_version"].astype(str),
                    strict=True,
                )
            )

    records: list[dict[str, Any]] = []
    for scenario in sorted(
        scenario_list, key=lambda item: (_scenario_fingerprint(item), item.family)
    ):
        scenario_seed = seed ^ _scenario_fingerprint(scenario)
        for trial_index in range(trials):
            trial_seed = derive_trial_seed(scenario_seed, trial_index)
            battle = scenario.run(seed=trial_seed)
            result = battle.result_
            assert result is not None
            result_versions = (result.rules_version, DATASET_SCHEMA_VERSION)
            if existing_versions and result_versions not in existing_versions:
                raise ValueError("refusing to mix rules/schema versions in one dataset")
            if result.trial_id not in existing_trial_ids:
                records.append(
                    result_to_record(result, scenario_family=scenario.family)
                )
                existing_trial_ids.add(result.trial_id)
                existing_versions.add(result_versions)

    combined = pd.concat([existing, pd.DataFrame(records)], ignore_index=True)
    if not combined.empty:
        combined = combined.drop_duplicates("trial_id").sort_values(
            ["scenario_id", "trial_id"]
        )
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.casefold() == ".csv":
            combined.to_csv(path, index=False)
        elif path.suffix.casefold() in {".jsonl", ".ndjson"}:
            combined.to_json(path, orient="records", lines=True)
        elif path.suffix.casefold() == ".parquet":
            combined.to_parquet(path, index=False)
        else:
            raise ValueError("dataset filename must end in .csv, .jsonl, or .parquet")
        manifest_path = path.with_suffix(path.suffix + ".manifest.json")
        manifest_record = {
            "schema_version": DATASET_SCHEMA_VERSION,
            "root_seed": seed,
            "replicates_per_scenario": trials,
            "scenario_families": sorted(
                {scenario.family for scenario in scenario_list}
            ),
            "sampling_method": "fixed_replicates",
            "rows": len(combined),
            **({} if manifest is None else dict(manifest)),
        }
        manifest_path.write_text(
            json.dumps(manifest_record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return combined.reset_index(drop=True)


def expand_parameter_sweep(
    base: BattleScenario,
    parameters: Mapping[str, Sequence[Any]],
) -> tuple[BattleScenario, ...]:
    """Expand top-level or `rules.*` dataclass fields into a deterministic grid."""
    names = tuple(sorted(parameters))
    expanded: list[BattleScenario] = []
    for values in product(*(parameters[name] for name in names)):
        scenario = base
        rules: BattleRules = scenario.rules
        top_level: dict[str, Any] = {}
        for name, value in zip(names, values, strict=True):
            if name.startswith("rules."):
                rules = replace(rules, **{name.removeprefix("rules."): value})
            else:
                top_level[name] = value
        expanded.append(replace(scenario, rules=rules, **top_level))
    return tuple(expanded)


def scenario_family_partition(family: str) -> str:
    """Stable 80/10/5/5 train/validation/test/OOD family partition."""
    bucket = (
        int.from_bytes(hashlib.sha256(family.encode()).digest()[:8], "little") % 100
    )
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    if bucket < 95:
        return "test"
    return "ood"
