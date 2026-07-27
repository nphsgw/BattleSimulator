"""Dataset, batch-resume, uncertainty, and validation tests."""

from dataclasses import replace
from typing import Any, cast

import pytest

import battlesim as bsm


def _scenario() -> bsm.BattleScenario:
    return bsm.BattleScenario(
        armies=(
            bsm.ArmySpec(
                "B1 battledroid",
                1,
                position_parameters=(-1.0, 0.0),
            ),
            bsm.ArmySpec(
                "Clone Trooper",
                1,
                position_parameters=(1.0, 0.0),
            ),
        ),
        bounds=(-3.0, 3.0, -3.0, 3.0),
        family="small-duel",
        rules=bsm.BattleRules(max_ticks=3, line_of_sight=False),
    )


def test_batch_resume_deduplicates_trial_ids(tmp_path):
    output = tmp_path / "trials.csv"

    first = bsm.run_batch([_scenario()], trials=2, seed=4, output=output)
    resumed = bsm.run_batch([_scenario()], trials=2, seed=4, output=output)

    assert len(first) == 2
    assert len(resumed) == 2
    assert resumed["trial_id"].is_unique
    assert output.with_suffix(".csv.manifest.json").exists()


def test_surrogate_frame_has_fixed_aggregate_features():
    battle = _scenario().run(seed=5)
    assert battle.result_ is not None

    frame = bsm.surrogate_frame([battle.result_], scenario_family="small-duel")

    assert frame.loc[0, "scenario_family"] == "small-duel"
    assert frame.loc[0, "partition"] in {"train", "validation", "test", "ood"}
    assert 0 <= float(cast(Any, frame.loc[0, "hit_rate"])) <= 1
    assert "input_mean_threat_damage_weight" in frame
    assert not bsm.validate_results([battle.result_])


def test_wilson_interval_matches_hand_calculated_95_percent_bounds():
    """Dataset contract uses the Wilson score interval, not a generic range."""
    lower, upper = bsm.wilson_interval(7, 10)

    assert lower == pytest.approx(0.396773, abs=1e-6)
    assert upper == pytest.approx(0.892211, abs=1e-6)


def test_parameter_sweep_expands_rules_fields():
    scenarios = bsm.expand_parameter_sweep(
        _scenario(),
        {"rules.max_ticks": [2, 4], "family": ["a", "b"]},
    )

    assert len(scenarios) == 4
    assert {scenario.rules.max_ticks for scenario in scenarios} == {2, 4}
    assert {scenario.family for scenario in scenarios} == {"a", "b"}


def test_monte_carlo_summary_and_sensitivity_analysis():
    battle = _scenario().run(seed=0)
    assert battle.result_ is not None
    template = battle.result_
    results = [
        replace(template, trial_id="win", ticks=2, winner_team_ids=(0,)),
        replace(template, trial_id="undecided", ticks=4, winner_team_ids=()),
    ]

    summary = bsm.monte_carlo_summary(results, team_id=0)
    sensitivity = bsm.sensitivity_analysis(
        [1.0, 2.0],
        lambda value, seed: replace(template, ticks=int(value) + seed),
        replicates=2,
        seed=10,
    )

    assert summary["trials"] == 2
    assert summary["wins"] == 1
    assert summary["win_probability"] == 0.5
    assert summary["mean_ticks"] == 3.0
    assert summary["undecided_rate"] == 0.5
    assert summary["win_probability_lower"] < 0.5
    assert summary["win_probability_upper"] > 0.5
    assert list(sensitivity["parameter_value"]) == [1.0, 2.0]
    assert list(sensitivity["replicates"]) == [2, 2]
    assert list(sensitivity["mean"]) == [11.5, 12.5]
    assert list(sensitivity["std"]) == [0.5, 0.5]
    assert list(sensitivity["minimum"]) == [11.0, 12.0]
    assert list(sensitivity["maximum"]) == [12.0, 13.0]
