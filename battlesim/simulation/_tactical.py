"""Reference tactical kernel with explicit randomness and simultaneous ticks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from battlesim.contracts import (
    RESULT_SCHEMA_VERSION,
    BattleEvent,
    BattleResult,
    BattleRules,
    TeamResult,
    TerminationReason,
)
from battlesim.randomness import RandomStreams

FRAME_DTYPE = np.dtype(
    [
        ("x", "f4"),
        ("y", "f4"),
        ("target", "u4"),
        ("hp", "f4"),
        ("armor", "f4"),
        ("ddx", "f4"),
        ("ddy", "f4"),
        ("team", "u1"),
        ("utype", "u1"),
        ("z", "f4"),
        ("target_z", "f4"),
        ("move_factor", "f4"),
        ("effective_range", "f4"),
        ("damage_factor", "f4"),
        ("density", "f4"),
    ],
    align=True,
)


@dataclass(frozen=True)
class TacticalRun:
    """Raw outputs from one kernel execution."""

    frames: np.ndarray
    result: BattleResult
    final_state: np.ndarray


def _height(terrain, x: float, y: float) -> float:
    z = terrain.Z_
    if z is None or z.size == 0:
        return 0.0
    xmin, xmax, ymin, ymax = terrain.bounds_
    xi = int(
        np.clip(np.interp(x, (xmin, xmax), (0, z.shape[0] - 1)), 0, z.shape[0] - 1)
    )
    yi = int(
        np.clip(np.interp(y, (ymin, ymax), (0, z.shape[1] - 1)), 0, z.shape[1] - 1)
    )
    return float(z[xi, yi])


def _has_line_of_sight(terrain, start: np.ndarray, end: np.ndarray) -> bool:
    distance = float(np.linalg.norm(end - start))
    samples = max(3, int(distance / max(float(terrain.res_), 1e-6)) + 1)
    start_z = _height(terrain, float(start[0]), float(start[1])) + 0.05
    end_z = _height(terrain, float(end[0]), float(end[1])) + 0.05
    for fraction in np.linspace(0.0, 1.0, samples)[1:-1]:
        point = start + ((end - start) * fraction)
        sight_z = start_z + ((end_z - start_z) * fraction)
        if _height(terrain, float(point[0]), float(point[1])) > sight_z:
            return False
    return True


def _target_score(M: np.ndarray, actor: int, candidates: np.ndarray) -> np.ndarray:
    dx = M["x"][candidates] - M["x"][actor]
    dy = M["y"][candidates] - M["y"][actor]
    distance = np.sqrt((dx * dx) + (dy * dy))
    durability = np.maximum(M["hp"][candidates], 0) + np.maximum(
        M["armor"][candidates], 0
    )
    distance_scale = np.ptp(distance)
    durability_scale = np.ptp(durability)
    distance_score = (
        np.zeros_like(distance)
        if distance_scale == 0
        else (distance - distance.min()) / distance_scale
    )
    durability_score = (
        np.zeros_like(durability)
        if durability_scale == 0
        else (durability - durability.min()) / durability_scale
    )
    return (0.7 * distance_score) + (0.3 * durability_score)


def _normalized(values: np.ndarray) -> np.ndarray:
    span = float(np.ptp(values))
    if span == 0:
        return np.zeros_like(values, dtype=np.float64)
    return (values - np.min(values)) / span


def _threat_score(
    M: np.ndarray,
    actor: int,
    candidates: np.ndarray,
    rules: BattleRules,
) -> np.ndarray:
    distance = np.hypot(
        M["x"][candidates] - M["x"][actor],
        M["y"][candidates] - M["y"][actor],
    )
    durability = np.maximum(M["hp"][candidates], 0) + np.maximum(
        M["armor"][candidates], 0
    )
    expected_damage = (
        M["dmg"][candidates]
        * M["acc"][candidates]
        / np.maximum(M["attack_interval"][candidates], 1.0)
    )
    objective_importance = np.zeros(candidates.shape[0], dtype=np.float64)
    if rules.objectives:
        objective_distance = np.full(candidates.shape[0], np.inf)
        for objective in rules.objectives:
            objective_distance = np.minimum(
                objective_distance,
                np.hypot(
                    M["x"][candidates] - objective.x,
                    M["y"][candidates] - objective.y,
                ),
            )
        objective_importance = 1.0 - _normalized(objective_distance)
    weights = np.array(
        [
            M["threat_distance_weight"][actor],
            M["threat_durability_weight"][actor],
            M["threat_damage_weight"][actor],
            M["threat_objective_weight"][actor],
        ],
        dtype=np.float64,
    )
    if np.sum(weights) <= 0:
        weights = np.array([0.25, 0.15, 0.5, 0.1])
    else:
        weights /= np.sum(weights)
    return (
        weights[0] * (1.0 - _normalized(distance))
        + weights[1] * _normalized(durability)
        + weights[2] * _normalized(expected_damage)
        + weights[3] * objective_importance
    )


def _select_target(
    M: np.ndarray,
    actor: int,
    rng: np.random.Generator,
    rules: BattleRules,
) -> int | None:
    candidates = np.where((M["hp"] > 0.0) & (M["team"] != M["team"][actor]))[0]
    if candidates.size == 0:
        return None
    target_ai = int(M["target_ai_func_index"][actor])
    if target_ai == 1:
        stable_order = candidates[np.argsort(M["stable_id"][candidates])]
        return int(stable_order[int(rng.integers(stable_order.size))])
    if target_ai == 2:
        scores = _target_score(M, actor, candidates)
    elif target_ai == 3:
        scores = np.maximum(M["hp"][candidates], 0) + np.maximum(
            M["armor"][candidates], 0
        )
    elif target_ai == 4:
        scores = -_threat_score(M, actor, candidates, rules)
    elif target_ai == 5:
        allies = np.where((M["hp"] > 0) & (M["team"] == M["team"][actor]))[0]
        focus_count = np.array(
            [np.sum(M["target"][allies] == candidate) for candidate in candidates]
        )
        distance = np.hypot(
            M["x"][candidates] - M["x"][actor],
            M["y"][candidates] - M["y"][actor],
        )
        scores = -focus_count.astype(np.float64) + (_normalized(distance) * 0.01)
    elif target_ai == 6 and rules.objectives:
        objective_distance = np.full(candidates.shape[0], np.inf)
        for objective in rules.objectives:
            objective_distance = np.minimum(
                objective_distance,
                np.hypot(
                    M["x"][candidates] - objective.x,
                    M["y"][candidates] - objective.y,
                ),
            )
        scores = objective_distance
    else:
        dx = M["x"][candidates] - M["x"][actor]
        dy = M["y"][candidates] - M["y"][actor]
        scores = (dx * dx) + (dy * dy)
    minimum = float(np.min(scores))
    tied = candidates[np.isclose(scores, minimum, rtol=1e-7, atol=1e-9)]
    return int(tied[np.argmin(M["stable_id"][tied])])


def _resolve_collisions(
    start: np.ndarray,
    proposed: np.ndarray,
    radii: np.ndarray,
    stable_ids: np.ndarray,
    bounds: tuple[float, float, float, float],
    active: np.ndarray,
) -> np.ndarray:
    velocities = proposed - start
    stop_fraction = np.ones(proposed.shape[0], dtype=np.float64)
    for left in range(start.shape[0]):
        if not active[left]:
            continue
        for right in range(left + 1, start.shape[0]):
            if not active[right]:
                continue
            relative_start = start[right] - start[left]
            relative_velocity = velocities[right] - velocities[left]
            a = float(np.dot(relative_velocity, relative_velocity))
            minimum = float(radii[left] + radii[right])
            if a <= 1e-12 or np.linalg.norm(relative_start) < minimum:
                continue
            b = 2.0 * float(np.dot(relative_start, relative_velocity))
            c = float(np.dot(relative_start, relative_start)) - (minimum * minimum)
            discriminant = (b * b) - (4.0 * a * c)
            if discriminant < 0:
                continue
            collision_time = (-b - np.sqrt(discriminant)) / (2.0 * a)
            if 0.0 <= collision_time <= 1.0:
                safe_time = max(float(collision_time) - 1e-6, 0.0)
                stop_fraction[left] = min(stop_fraction[left], safe_time)
                stop_fraction[right] = min(stop_fraction[right], safe_time)
    resolved = start + (velocities * stop_fraction[:, None])

    for _ in range(4):
        corrections = np.zeros_like(resolved, dtype=np.float64)
        has_overlap = False
        for left in range(resolved.shape[0]):
            if not active[left]:
                continue
            for right in range(left + 1, resolved.shape[0]):
                if not active[right]:
                    continue
                delta = resolved[right] - resolved[left]
                distance = float(np.linalg.norm(delta))
                minimum = float(radii[left] + radii[right])
                if distance >= minimum:
                    continue
                has_overlap = True
                if distance <= 1e-12:
                    digest = hashlib.sha256(
                        f"{min(stable_ids[left], stable_ids[right])}:"
                        f"{max(stable_ids[left], stable_ids[right])}".encode()
                    ).digest()
                    angle = int.from_bytes(digest[:8], "little") / 2**64 * (2 * np.pi)
                    canonical = np.array([np.cos(angle), np.sin(angle)])
                    direction = (
                        canonical
                        if stable_ids[left] < stable_ids[right]
                        else -canonical
                    )
                else:
                    direction = delta / distance
                overlap = minimum - distance
                corrections[left] -= direction * overlap * 0.5
                corrections[right] += direction * overlap * 0.5
        resolved += corrections
        resolved[:, 0] = np.clip(resolved[:, 0], bounds[0], bounds[1])
        resolved[:, 1] = np.clip(resolved[:, 1], bounds[2], bounds[3])
        if not has_overlap:
            break
    return resolved


def _make_frame(M: np.ndarray, terrain) -> np.ndarray:
    frame = np.zeros(M.shape[0], dtype=FRAME_DTYPE)
    frame["x"] = M["x"]
    frame["y"] = M["y"]
    frame["target"] = M["target"]
    frame["hp"] = M["hp"]
    frame["armor"] = M["armor"]
    frame["team"] = M["team"]
    frame["utype"] = M["utype"]
    positions = np.column_stack((M["x"], M["y"]))
    for index in range(M.shape[0]):
        target = int(M["target"][index])
        if not 0 <= target < M.shape[0]:
            target = index
        dx = float(M["x"][target] - M["x"][index])
        dy = float(M["y"][target] - M["y"][index])
        distance = max(float(np.hypot(dx, dy)), 1e-12)
        z_i = _height(terrain, float(M["x"][index]), float(M["y"][index]))
        z_j = _height(terrain, float(M["x"][target]), float(M["y"][target]))
        frame["ddx"][index] = dx / distance
        frame["ddy"][index] = dy / distance
        frame["z"][index] = z_i
        frame["target_z"][index] = z_j
        frame["move_factor"][index] = M["move_factor"][index]
        frame["effective_range"][index] = M["range"][index]
        frame["damage_factor"][index] = max(((z_i - z_j) / 2.0) + 1.0, 0.0)
        neighbor_distance = np.linalg.norm(positions - positions[index], axis=1)
        frame["density"][index] = float(
            np.sum(
                (neighbor_distance > 0)
                & (neighbor_distance <= max(float(M["radius"][index]) * 4.0, 0.5))
            )
        )
    return frame


def _termination(
    M: np.ndarray,
    teams: np.ndarray,
    ticks: int,
    rules: BattleRules,
    idle_ticks: int,
    objective_winners: tuple[int, ...],
) -> tuple[TerminationReason | None, tuple[int, ...]]:
    if objective_winners:
        return TerminationReason.OBJECTIVE, objective_winners
    living = tuple(
        int(team) for team in teams if np.any((M["hp"] > 0.0) & (M["team"] == team))
    )
    if not living:
        return TerminationReason.MUTUAL_DESTRUCTION, ()
    if len(living) == 1:
        return TerminationReason.ELIMINATION, living
    if idle_ticks >= rules.stalemate_ticks:
        return TerminationReason.STALEMATE, ()
    if ticks >= rules.max_ticks:
        return TerminationReason.TIMEOUT, ()
    return None, ()


def simulate_tactical(
    matrix: np.ndarray,
    terrain,
    *,
    rules: BattleRules,
    streams: RandomStreams,
    scenario_id: str,
    simulator_version: str,
    record_events: bool = True,
    randomized_subsystems: tuple[str, ...] = (),
    scenario_features: dict[str, object] | None = None,
    team_labels: dict[int, str] | None = None,
) -> TacticalRun:
    """Execute a rules-version-1 battle using snapshot decisions."""
    M = np.copy(matrix)
    M["move_factor"] = 1.0
    teams = np.unique(M["team"])
    initial_units = {int(team): int(np.sum(M["team"] == team)) for team in teams}
    metrics = {
        int(team): {
            "damage_dealt": 0.0,
            "damage_received": 0.0,
            "shots": 0,
            "hits": 0,
            "kills": 0,
            "movement": 0.0,
            "high_ground_ticks": 0,
            "cover_ticks": 0,
            "objective_ticks": 0,
        }
        for team in teams
    }
    events: list[BattleEvent] = []
    frames = [_make_frame(M, terrain)]
    objective_state: list[tuple[int | None, int]] = [
        (None, 0) for _ in rules.objectives
    ]
    ticks = 0
    idle_ticks = 0
    first_contact: int | None = None
    termination, winners = _termination(M, teams, ticks, rules, idle_ticks, ())

    while termination is None:
        ticks += 1
        snapshot = np.copy(M)
        M["move_factor"] = 1.0
        alive = snapshot["hp"] > 0.0
        proposed = np.column_stack((snapshot["x"], snapshot["y"])).astype(np.float64)
        starting_positions = proposed.copy()
        attack_intents: list[tuple[int, int, float]] = []
        tick_events: list[BattleEvent] = []

        actor_order = np.where(alive)[0]
        actor_order = actor_order[np.argsort(snapshot["stable_id"][actor_order])]
        for actor in actor_order:
            M["cooldown"][actor] = max(float(snapshot["cooldown"][actor]) - 1.0, 0.0)
            target = int(snapshot["target"][actor])
            if (
                target >= snapshot.shape[0]
                or snapshot["hp"][target] <= 0
                or snapshot["team"][target] == snapshot["team"][actor]
            ):
                selected = _select_target(
                    snapshot,
                    int(actor),
                    streams.keyed_generator(
                        "targeting", f"{ticks}:{int(snapshot['stable_id'][actor])}"
                    ),
                    rules,
                )
                if selected is None:
                    continue
                target = selected
                M["target"][actor] = target
                tick_events.append(
                    BattleEvent(
                        ticks,
                        "target",
                        int(snapshot["stable_id"][actor]),
                        int(snapshot["stable_id"][target]),
                    )
                )

            actor_pos = proposed[actor]
            target_pos = np.array(
                [snapshot["x"][target], snapshot["y"][target]], dtype=np.float64
            )
            delta = target_pos - actor_pos
            distance = float(np.linalg.norm(delta))
            effective_range = float(snapshot["range"][actor])
            ai_kind = int(snapshot["ai_func_index"][actor])
            move = np.zeros(2, dtype=np.float64)

            if ai_kind == 1 and distance < float(snapshot["range"][target]):
                if distance > 1e-12:
                    move = -(delta / distance) * float(snapshot["speed"][actor])
            elif distance > effective_range and distance > 1e-12:
                maximum = max(distance - effective_range, 0.0)
                move = (delta / distance) * min(
                    float(snapshot["speed"][actor]), maximum
                )

            if np.any(move):
                if rules.slope_movement:
                    destination = actor_pos + move
                    rise = _height(terrain, *destination) - _height(terrain, *actor_pos)
                    slope_factor = 1.0 / (1.0 + max(rise, 0.0))
                    move *= slope_factor
                    M["move_factor"][actor] = slope_factor
                destination = actor_pos + move
                clipped = np.array(
                    [
                        np.clip(destination[0], terrain.bounds_[0], terrain.bounds_[1]),
                        np.clip(destination[1], terrain.bounds_[2], terrain.bounds_[3]),
                    ]
                )
                if (
                    ai_kind == 1
                    and np.linalg.norm(clipped - actor_pos) < np.linalg.norm(move) * 0.5
                    and distance > 1e-12
                ):
                    direction = delta / distance
                    lateral = np.array([-direction[1], direction[0]])
                    candidates = []
                    for sign in (-1.0, 1.0):
                        candidate = actor_pos + (
                            lateral * float(snapshot["speed"][actor]) * sign
                        )
                        candidate[0] = np.clip(
                            candidate[0], terrain.bounds_[0], terrain.bounds_[1]
                        )
                        candidate[1] = np.clip(
                            candidate[1], terrain.bounds_[2], terrain.bounds_[3]
                        )
                        candidates.append(candidate)
                    clipped = max(
                        candidates,
                        key=lambda candidate: (
                            np.linalg.norm(candidate - target_pos),
                            candidate[0],
                            candidate[1],
                        ),
                    )
                proposed[actor] = clipped

        proposed[:, 0] = np.clip(proposed[:, 0], terrain.bounds_[0], terrain.bounds_[1])
        proposed[:, 1] = np.clip(proposed[:, 1], terrain.bounds_[2], terrain.bounds_[3])
        if rules.collision:
            proposed = _resolve_collisions(
                starting_positions,
                proposed,
                snapshot["radius"],
                snapshot["stable_id"],
                terrain.bounds_,
                alive,
            )
        movement = np.linalg.norm(
            proposed - np.column_stack((snapshot["x"], snapshot["y"])), axis=1
        )
        M["x"] = proposed[:, 0]
        M["y"] = proposed[:, 1]
        for actor in np.where(movement > 1e-9)[0]:
            team = int(snapshot["team"][actor])
            metrics[team]["movement"] += float(movement[actor])
            tick_events.append(
                BattleEvent(
                    ticks,
                    "move",
                    int(snapshot["stable_id"][actor]),
                    value=float(movement[actor]),
                )
            )

        terrain_mean = float(np.mean(terrain.Z_)) if terrain.Z_ is not None else 0.0
        for actor in actor_order:
            team = int(snapshot["team"][actor])
            if (
                _height(terrain, float(M["x"][actor]), float(M["y"][actor]))
                > terrain_mean
            ):
                metrics[team]["high_ground_ticks"] += 1
            if any(
                np.hypot(M["x"][actor] - cover.x, M["y"][actor] - cover.y)
                <= cover.radius
                for cover in rules.covers
            ):
                metrics[team]["cover_ticks"] += 1

        # Attack geometry is evaluated only after all movement and collision resolution.
        for actor in actor_order:
            if M["cooldown"][actor] > 0:
                continue
            target = int(M["target"][actor])
            actor_pos = proposed[actor]
            target_pos = proposed[target]
            distance = float(np.linalg.norm(target_pos - actor_pos))
            effective_range = float(snapshot["range"][actor])
            if distance > effective_range:
                continue
            visible = not rules.line_of_sight or _has_line_of_sight(
                terrain, actor_pos, target_pos
            )
            if not visible:
                continue
            chance = float(snapshot["acc"][actor]) * (
                1.0 - float(snapshot["dodge"][target])
            )
            chance *= 1.0 - (0.5 * distance / max(effective_range, 1e-12))
            for cover in rules.covers:
                target_in_cover = (
                    np.hypot(target_pos[0] - cover.x, target_pos[1] - cover.y)
                    <= cover.radius
                )
                actor_in_cover = (
                    np.hypot(actor_pos[0] - cover.x, actor_pos[1] - cover.y)
                    <= cover.radius
                )
                if target_in_cover and not actor_in_cover:
                    chance *= cover.hit_multiplier
            attack_intents.append(
                (int(actor), target, float(np.clip(chance, 0.0, 1.0)))
            )
            M["cooldown"][actor] = max(float(snapshot["attack_interval"][actor]), 1.0)

        damages: dict[int, list[tuple[int, float]]] = {}
        for actor, target, chance in attack_intents:
            team = int(snapshot["team"][actor])
            metrics[team]["shots"] += 1
            tick_events.append(
                BattleEvent(
                    ticks,
                    "shot",
                    int(snapshot["stable_id"][actor]),
                    int(snapshot["stable_id"][target]),
                    chance,
                )
            )
            if first_contact is None:
                first_contact = ticks
            hit_rng = streams.keyed_generator(
                "hit", f"{ticks}:{int(snapshot['stable_id'][actor])}"
            )
            if hit_rng.random() < chance:
                z_i = _height(terrain, float(M["x"][actor]), float(M["y"][actor]))
                z_j = _height(terrain, float(M["x"][target]), float(M["y"][target]))
                amount = max(
                    float(snapshot["dmg"][actor]) * (((z_i - z_j) / 2.0) + 1.0),
                    0.0,
                )
                damages.setdefault(target, []).append((actor, amount))
                metrics[team]["hits"] += 1
                tick_events.append(
                    BattleEvent(
                        ticks,
                        "hit",
                        int(snapshot["stable_id"][actor]),
                        int(snapshot["stable_id"][target]),
                        amount,
                    )
                )

        for target, contributions in damages.items():
            total = sum(amount for _, amount in contributions)
            armor_damage = min(float(snapshot["armor"][target]), total)
            hp_damage = min(
                float(snapshot["hp"][target]), max(total - armor_damage, 0.0)
            )
            M["armor"][target] = max(float(snapshot["armor"][target]) - total, 0.0)
            M["hp"][target] = max(float(snapshot["hp"][target]) - hp_damage, 0.0)
            receiving_team = int(snapshot["team"][target])
            metrics[receiving_team]["damage_received"] += armor_damage + hp_damage
            actual_damage = armor_damage + hp_damage
            for actor, amount in contributions:
                dealt = 0.0 if total == 0 else actual_damage * amount / total
                metrics[int(snapshot["team"][actor])]["damage_dealt"] += dealt
                tick_events.append(
                    BattleEvent(
                        ticks,
                        "damage",
                        int(snapshot["stable_id"][actor]),
                        int(snapshot["stable_id"][target]),
                        dealt,
                    )
                )
            if snapshot["hp"][target] > 0 and M["hp"][target] <= 0:
                killer = max(
                    contributions,
                    key=lambda item: (
                        item[1],
                        -int(snapshot["stable_id"][item[0]]),
                    ),
                )[0]
                metrics[int(snapshot["team"][killer])]["kills"] += 1
                tick_events.append(
                    BattleEvent(
                        ticks,
                        "kill",
                        int(snapshot["stable_id"][killer]),
                        int(snapshot["stable_id"][target]),
                    )
                )

        objective_winners: set[int] = set()
        objective_progressed = False
        for objective_index, objective in enumerate(rules.objectives):
            distances = np.hypot(M["x"] - objective.x, M["y"] - objective.y)
            occupant_indexes = np.where(
                (M["hp"] > 0) & (distances <= objective.radius)
            )[0]
            occupants = np.unique(M["team"][occupant_indexes])
            owner, progress = objective_state[objective_index]
            if occupants.size == 1:
                occupying_team = int(occupants[0])
                progress = progress + 1 if owner == occupying_team else 1
                owner = occupying_team
                objective_progressed = True
                metrics[occupying_team]["objective_ticks"] += 1
                tick_events.append(
                    BattleEvent(
                        ticks,
                        "objective",
                        int(
                            np.min(
                                M["stable_id"][
                                    occupant_indexes[
                                        M["team"][occupant_indexes] == occupying_team
                                    ]
                                ]
                            )
                        ),
                        value=float(progress),
                        metadata={"objective_index": objective_index},
                    )
                )
                if progress >= objective.capture_ticks:
                    objective_winners.add(occupying_team)
            else:
                owner, progress = None, 0
            objective_state[objective_index] = (owner, progress)

        changed = bool(
            np.any(movement > 1e-9)
            or np.any(M["hp"] != snapshot["hp"])
            or np.any(M["armor"] != snapshot["armor"])
            or objective_progressed
        )
        idle_ticks = 0 if changed else idle_ticks + 1
        if record_events:
            events.extend(tick_events)
        frames.append(_make_frame(M, terrain))
        termination, winners = _termination(
            M,
            teams,
            ticks,
            rules,
            idle_ticks,
            tuple(sorted(objective_winners)),
        )

    team_results_list: list[TeamResult] = []
    for team in teams:
        selector = (M["team"] == team) & (M["hp"] > 0)
        positions = np.column_stack((M["x"][selector], M["y"][selector]))
        dispersion = (
            0.0
            if positions.shape[0] < 2
            else float(
                np.mean(np.linalg.norm(positions - positions.mean(axis=0), axis=1))
            )
        )
        received = float(metrics[int(team)]["damage_received"])
        team_results_list.append(
            TeamResult(
                team_id=int(team),
                initial_units=initial_units[int(team)],
                remaining_units=int(np.sum(selector)),
                remaining_hp=float(np.sum(M["hp"][M["team"] == team])),
                remaining_armor=float(np.sum(M["armor"][M["team"] == team])),
                team_label=(
                    None if team_labels is None else team_labels.get(int(team))
                ),
                spatial_dispersion=dispersion,
                force_exchange_ratio=(
                    None
                    if received == 0
                    else float(metrics[int(team)]["damage_dealt"]) / received
                ),
                damage_dealt=float(metrics[int(team)]["damage_dealt"]),
                damage_received=received,
                shots=int(metrics[int(team)]["shots"]),
                hits=int(metrics[int(team)]["hits"]),
                kills=int(metrics[int(team)]["kills"]),
                movement=float(metrics[int(team)]["movement"]),
                high_ground_ticks=int(metrics[int(team)]["high_ground_ticks"]),
                cover_ticks=int(metrics[int(team)]["cover_ticks"]),
                objective_ticks=int(metrics[int(team)]["objective_ticks"]),
            )
        )
    team_results = tuple(team_results_list)
    randomization_key = ",".join(sorted(randomized_subsystems))
    trial_id = hashlib.sha256(
        f"{scenario_id}:{streams.seed}:{rules.version}:{randomization_key}".encode()
    ).hexdigest()
    assert termination is not None
    result = BattleResult(
        scenario_id=scenario_id,
        trial_id=trial_id,
        seed=streams.seed,
        simulator_version=simulator_version,
        rules_version=rules.version,
        schema_version=RESULT_SCHEMA_VERSION,
        ticks=ticks,
        termination_reason=termination,
        winner_team_ids=winners,
        first_contact_tick=first_contact,
        teams=team_results,
        scenario_features={} if scenario_features is None else scenario_features,
        randomized_subsystems=tuple(sorted(randomized_subsystems)),
        events=tuple(events),
    )
    return TacticalRun(np.asarray(frames), result, M)
