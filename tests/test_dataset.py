"""Dataset, batch-resume, uncertainty, and validation tests."""

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
    assert 0 <= frame.loc[0, "hit_rate"] <= 1
    assert "input_mean_threat_damage_weight" in frame
    assert not bsm.validate_results([battle.result_])


def test_wilson_interval_contains_observed_rate():
    lower, upper = bsm.wilson_interval(7, 10)

    assert lower < 0.7 < upper


def test_parameter_sweep_expands_rules_fields():
    scenarios = bsm.expand_parameter_sweep(
        _scenario(),
        {"rules.max_ticks": [2, 4], "family": ["a", "b"]},
    )

    assert len(scenarios) == 4
    assert {scenario.rules.max_ticks for scenario in scenarios} == {2, 4}
    assert {scenario.family for scenario in scenarios} == {"a", "b"}


def test_monte_carlo_summary_and_sensitivity_analysis():
    results = []
    for seed in range(2):
        battle = _scenario().run(seed=seed)
        assert battle.result_ is not None
        results.append(battle.result_)

    summary = bsm.monte_carlo_summary(results, team_id=0)
    sensitivity = bsm.sensitivity_analysis(
        [1.0, 2.0],
        lambda _value, seed: _scenario().run(seed=seed).result_,
        replicates=2,
    )

    assert summary["trials"] == 2
    assert list(sensitivity["parameter_value"]) == [1.0, 2.0]
