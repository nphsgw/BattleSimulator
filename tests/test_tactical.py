"""Contract, reproducibility, symmetry, and tactical-kernel tests."""

import json
from pathlib import Path

import numpy as np

import battlesim as bsm
from battlesim.randomness import RandomStreams
from battlesim.simulation._tactical import simulate_tactical


def _database(
    *,
    hp: float = 10,
    damage: float = 2,
    attack_interval: float = 1,
) -> dict[str, list[object]]:
    return {
        "Name": ["A unit", "B unit"],
        "Allegiance": ["A", "B"],
        "HP": [hp, hp],
        "Armor": [0, 0],
        "Damage": [damage, damage],
        "Accuracy": [100, 100],
        "Miss": [0, 0],
        "Movement Speed": [0, 0],
        "Range": [10, 10],
        "Attack Interval": [attack_interval, attack_interval],
        "Radius": [0.1, 0.1],
    }


def _battle(*, seed: int = 3, rules: bsm.BattleRules | None = None) -> bsm.Battle:
    battle = bsm.Battle(
        _database(),
        bounds=(-10.0, 10.0, -10.0, 10.0),
        use_tqdm=False,
        seed=seed,
        rules=rules,
    )
    battle.create_army(
        [
            bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", -1, 0)),
            bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 1, 0)),
        ]
    )
    return battle


def test_same_seed_produces_identical_result_and_frames():
    battle = _battle(seed=99)

    first_frames = battle.simulate().copy()
    first_result = battle.result_
    second_frames = battle.simulate().copy()

    assert np.array_equal(first_frames, second_frames)
    assert first_result == battle.result_


def test_composite_registration_order_does_not_change_aggregate_result():
    first = _battle(seed=7)
    second = bsm.Battle(
        _database(),
        bounds=(-10.0, 10.0, -10.0, 10.0),
        use_tqdm=False,
        seed=7,
    )
    second.create_army(list(reversed(first.composition_)))

    first.simulate()
    second.simulate()

    assert first.result_ is not None
    assert second.result_ is not None
    assert first.result_.scenario_id == second.result_.scenario_id
    assert first.result_.termination_reason == second.result_.termination_reason
    assert first.result_.winner_team_ids == second.result_.winner_team_ids
    assert first.result_.teams == second.result_.teams


def test_simultaneous_damage_allows_mutual_destruction():
    rules = bsm.BattleRules(max_ticks=2, line_of_sight=False, collision=False)
    battle = bsm.Battle(
        _database(hp=1, damage=1),
        bounds=(-2.0, 2.0, -2.0, 2.0),
        use_tqdm=False,
        rules=rules,
    )
    battle.create_army(
        [
            bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
            bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
        ]
    )

    battle.simulate()

    assert battle.result_ is not None
    assert battle.result_.termination_reason == bsm.TerminationReason.MUTUAL_DESTRUCTION
    assert battle.result_.winner_team_ids == ()


def test_attack_interval_controls_shot_ticks():
    rules = bsm.BattleRules(max_ticks=4, line_of_sight=False, collision=False)
    battle = bsm.Battle(
        _database(hp=100, damage=0, attack_interval=2),
        bounds=(-2.0, 2.0, -2.0, 2.0),
        use_tqdm=False,
        rules=rules,
    )
    battle.create_army(
        [
            bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", -1, 0)),
            bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 1, 0)),
        ]
    )

    battle.simulate()

    assert battle.result_ is not None
    shot_ticks = [event.tick for event in battle.result_.events if event.kind == "shot"]
    assert shot_ticks == [1, 1, 3, 3]


def test_collision_separates_overlapping_living_units():
    matrix = bsm.Battle._generate_M(2)
    matrix["stable_id"] = [10, 20]
    matrix["team"] = [0, 1]
    matrix["target"] = [1, 0]
    matrix["hp"] = 10
    matrix["range"] = 0.1
    matrix["radius"] = 0.5
    matrix["attack_interval"] = 1
    terrain = bsm.Terrain((-2.0, 2.0, -2.0, 2.0), 1.0, None).generate()

    run = simulate_tactical(
        matrix,
        terrain,
        rules=bsm.BattleRules(
            max_ticks=1,
            line_of_sight=False,
            collision=True,
        ),
        streams=RandomStreams.from_seed(1),
        scenario_id="collision",
        simulator_version=bsm.__version__,
    )

    positions = np.column_stack((run.final_state["x"], run.final_state["y"]))
    assert np.linalg.norm(positions[0] - positions[1]) >= 0.99


def test_collision_prevents_high_speed_enemy_pass_through():
    matrix = bsm.Battle._generate_M(2)
    matrix["stable_id"] = [10, 20]
    matrix["team"] = [0, 1]
    matrix["target"] = [1, 0]
    matrix["hp"] = 10
    matrix["x"] = [-4, 4]
    matrix["speed"] = 10
    matrix["range"] = 0.1
    matrix["radius"] = 0.5
    matrix["attack_interval"] = 1
    terrain = bsm.Terrain((-5.0, 5.0, -5.0, 5.0), 1.0, None).generate()

    run = simulate_tactical(
        matrix,
        terrain,
        rules=bsm.BattleRules(
            max_ticks=1,
            line_of_sight=False,
            collision=True,
        ),
        streams=RandomStreams.from_seed(1),
        scenario_id="crossing",
        simulator_version=bsm.__version__,
    )

    assert run.final_state["x"][0] < run.final_state["x"][1]
    assert run.final_state["x"][1] - run.final_state["x"][0] >= 0.99
    assert "density" in run.frames.dtype.names


def test_objective_can_end_battle_without_elimination():
    rules = bsm.BattleRules(
        max_ticks=10,
        line_of_sight=False,
        collision=False,
        objectives=(bsm.ObjectiveZone(0, 0, 0.5, 2),),
    )
    battle = bsm.Battle(
        _database(hp=10, damage=0),
        bounds=(-5.0, 5.0, -5.0, 5.0),
        use_tqdm=False,
        rules=rules,
    )
    battle.create_army(
        [
            bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
            bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 4, 0)),
        ]
    )

    battle.simulate()

    assert battle.result_ is not None
    assert battle.result_.termination_reason == bsm.TerminationReason.OBJECTIVE
    assert battle.result_.winner_team_ids == (0,)


def _spatial_matrix() -> np.ndarray:
    matrix = bsm.Battle._generate_M(2)
    matrix["stable_id"] = [10, 20]
    matrix["team"] = [0, 1]
    matrix["target"] = [1, 0]
    matrix["hp"] = 100
    matrix["dmg"] = 1
    matrix["acc"] = 1
    matrix["range"] = 20
    matrix["attack_interval"] = 1
    matrix["radius"] = 0.1
    matrix["x"] = [1, 9]
    matrix["y"] = [5, 5]
    return matrix


def test_intermediate_terrain_blocks_line_of_sight():
    matrix = _spatial_matrix()
    terrain = bsm.Terrain((0.0, 10.0, 0.0, 10.0), 1.0, "grid")
    terrain._Z = np.zeros((10, 10))
    terrain._Z[4:6, :] = 1

    run = simulate_tactical(
        matrix,
        terrain,
        rules=bsm.BattleRules(
            max_ticks=1,
            line_of_sight=True,
            collision=False,
        ),
        streams=RandomStreams.from_seed(1),
        scenario_id="los",
        simulator_version=bsm.__version__,
    )

    assert not [event for event in run.result.events if event.kind == "shot"]


def test_uphill_movement_records_applied_slope_factor():
    matrix = _spatial_matrix()
    matrix["range"] = 0.1
    matrix["speed"] = [2, 0]
    terrain = bsm.Terrain((0.0, 10.0, 0.0, 10.0), 1.0, "grid")
    terrain._Z = np.repeat(np.linspace(0, 1, 10)[:, None], 10, axis=1)

    run = simulate_tactical(
        matrix,
        terrain,
        rules=bsm.BattleRules(
            max_ticks=1,
            line_of_sight=False,
            collision=False,
        ),
        streams=RandomStreams.from_seed(1),
        scenario_id="slope",
        simulator_version=bsm.__version__,
    )

    assert 0 < run.frames["move_factor"][-1, 0] < 1
    assert run.final_state["x"][0] - matrix["x"][0] < matrix["speed"][0]


def test_cover_reduces_recorded_hit_probability():
    matrix = _spatial_matrix()
    terrain = bsm.Terrain((0.0, 10.0, 0.0, 10.0), 1.0, None).generate()
    cover = bsm.CoverZone(9, 5, 1, hit_multiplier=0.5)

    run = simulate_tactical(
        matrix,
        terrain,
        rules=bsm.BattleRules(
            max_ticks=1,
            line_of_sight=False,
            collision=False,
            covers=(cover,),
        ),
        streams=RandomStreams.from_seed(1),
        scenario_id="cover",
        simulator_version=bsm.__version__,
    )

    shot = next(
        event
        for event in run.result.events
        if event.kind == "shot" and event.actor_id == 10
    )
    assert np.isclose(shot.value, 0.4)


def test_translation_and_scale_preserve_flat_micro_scenario_outcome():
    base = _spatial_matrix()
    translated = base.copy()
    translated["x"] += 100
    translated["y"] -= 50
    scaled = base.copy()
    for field in ("x", "y", "range", "speed", "radius"):
        scaled[field] *= 2

    def run(matrix, bounds, scenario_id):
        terrain = bsm.Terrain(bounds, 1.0, None).generate()
        return simulate_tactical(
            matrix,
            terrain,
            rules=bsm.BattleRules(
                max_ticks=3,
                line_of_sight=False,
                collision=False,
            ),
            streams=RandomStreams.from_seed(8),
            scenario_id=scenario_id,
            simulator_version=bsm.__version__,
        ).result

    reference = run(base, (0.0, 10.0, 0.0, 10.0), "base")
    shifted = run(translated, (100.0, 110.0, -50.0, -40.0), "translated")
    doubled = run(scaled, (0.0, 20.0, 0.0, 20.0), "scaled")

    assert reference.termination_reason == shifted.termination_reason
    assert reference.winner_team_ids == shifted.winner_team_ids
    assert reference.ticks == shifted.ticks
    assert reference.termination_reason == doubled.termination_reason
    assert reference.winner_team_ids == doubled.winner_team_ids
    assert reference.ticks == doubled.ticks


def test_different_seeds_produce_non_degenerate_outcomes():
    database = _database(hp=1, damage=1)
    database["Accuracy"] = [50, 50]
    outcomes = set()
    for seed in range(16):
        battle = bsm.Battle(
            database,
            bounds=(-2.0, 2.0, -2.0, 2.0),
            use_tqdm=False,
            seed=seed,
            rules=bsm.BattleRules(
                max_ticks=1,
                stalemate_ticks=2,
                line_of_sight=False,
                collision=False,
            ),
        )
        battle.create_army(
            [
                bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
                bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
            ]
        )
        battle.simulate()
        assert battle.result_ is not None
        outcomes.add(
            (battle.result_.termination_reason, battle.result_.winner_team_ids)
        )

    assert len(outcomes) > 1


def test_damage_is_monotonic_in_an_isolated_duel():
    def duration(damage: float) -> int:
        database = _database(hp=10, damage=0)
        database["Damage"] = [damage, 0]
        battle = bsm.Battle(
            database,
            bounds=(-2.0, 2.0, -2.0, 2.0),
            use_tqdm=False,
            rules=bsm.BattleRules(
                max_ticks=20,
                line_of_sight=False,
                collision=False,
            ),
        )
        battle.create_army(
            [
                bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
                bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
            ]
        )
        battle.simulate()
        assert battle.result_ is not None
        return battle.result_.ticks

    assert duration(5) <= duration(1)


def test_timeout_and_stalemate_are_distinct():
    def terminate(rules: bsm.BattleRules) -> bsm.TerminationReason:
        battle = bsm.Battle(
            _database(hp=10, damage=0),
            bounds=(-2.0, 2.0, -2.0, 2.0),
            use_tqdm=False,
            rules=rules,
        )
        battle.create_army(
            [
                bsm.Composite("A unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
                bsm.Composite("B unit", 1, pos_dist=bsm.Sampling("normal", 0, 0)),
            ]
        )
        battle.simulate()
        assert battle.result_ is not None
        return battle.result_.termination_reason

    assert (
        terminate(
            bsm.BattleRules(
                max_ticks=10,
                stalemate_ticks=2,
                line_of_sight=False,
                collision=False,
            )
        )
        == bsm.TerminationReason.STALEMATE
    )
    assert (
        terminate(
            bsm.BattleRules(
                max_ticks=2,
                stalemate_ticks=10,
                line_of_sight=False,
                collision=False,
            )
        )
        == bsm.TerminationReason.TIMEOUT
    )


def test_multi_team_result_and_state_bounds():
    database = {
        "Name": ["A", "B", "C"],
        "Allegiance": ["A", "B", "C"],
        "HP": [1, 1, 1],
        "Armor": [0, 0, 0],
        "Damage": [2, 2, 2],
        "Accuracy": [100, 100, 100],
        "Miss": [0, 0, 0],
        "Movement Speed": [0, 0, 0],
        "Range": [10, 10, 10],
    }
    battle = bsm.Battle(
        database,
        bounds=(-2.0, 2.0, -2.0, 2.0),
        use_tqdm=False,
        rules=bsm.BattleRules(
            max_ticks=2,
            line_of_sight=False,
            collision=False,
        ),
    )
    battle.create_army(
        [
            bsm.Composite(name, 1, pos_dist=bsm.Sampling("normal", 0, 0))
            for name in ("A", "B", "C")
        ]
    )

    battle.simulate()

    assert battle.result_ is not None
    assert len(battle.result_.teams) == 3
    assert all(team.remaining_hp >= 0 for team in battle.result_.teams)
    assert all(team.remaining_armor >= 0 for team in battle.result_.teams)


def test_team_label_exchange_exchanges_reported_winner_label():
    first = _battle(seed=4)
    swapped_database = _database()
    swapped_database["Allegiance"] = ["B", "A"]
    second = bsm.Battle(
        swapped_database,
        bounds=(-10.0, 10.0, -10.0, 10.0),
        use_tqdm=False,
        seed=4,
    )
    second.create_army(first.composition_)

    first.simulate()
    second.simulate()

    assert first.result_ is not None
    assert second.result_ is not None
    assert first.result_.winner_team_ids == second.result_.winner_team_ids
    if first.result_.winner_team_ids:
        winner = first.result_.winner_team_ids[0]
        first_team = next(
            team for team in first.result_.teams if team.team_id == winner
        )
        second_team = next(
            team for team in second.result_.teams if team.team_id == winner
        )
        assert first_team.team_label != second_team.team_label


def test_tactical_v1_baseline_distribution():
    baseline_path = Path(__file__).parent / "baselines" / "tactical-v1.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    scenario = bsm.BattleScenario(
        armies=(
            bsm.ArmySpec("B1 battledroid", 1, position_parameters=(-1.0, 0.0)),
            bsm.ArmySpec("Clone Trooper", 1, position_parameters=(1.0, 0.0)),
        ),
        bounds=(-3.0, 3.0, -3.0, 3.0),
        family="baseline-duel",
        rules=bsm.BattleRules(
            max_ticks=20,
            line_of_sight=False,
            collision=False,
        ),
    )
    results = []
    for seed in range(baseline["seeds"]):
        battle = scenario.run(seed=seed)
        assert battle.result_ is not None
        results.append(battle.result_)

    assert (
        sum(0 in result.winner_team_ids for result in results)
        == baseline["team_0_wins"]
    )
    assert (
        sum(1 in result.winner_team_ids for result in results)
        == baseline["team_1_wins"]
    )
    assert sum(not result.decided for result in results) == baseline["undecided"]
    assert np.isclose(
        np.mean([result.ticks for result in results]),
        baseline["mean_ticks"],
    )
