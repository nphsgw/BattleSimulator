# Tactical Model Contract

## Inputs

The canonical scenario contains armies, battlefield bounds, terrain, seed,
`max_ticks`, rules version, and optional objectives. Units use HP, armor, damage,
accuracy, dodge, movement speed, range, attack interval, and radius. Numeric units
are interpreted consistently within a scenario; one tick is one second.

`scenario_id` is the SHA-256 digest of canonical JSON with sorted keys and excludes
the trial seed. It includes the unit-stat values used by the scenario. `trial_id`
combines the scenario ID, seed, rules version, and randomized subsystem set.

## Random Streams

A root `SeedSequence` deterministically derives named streams for placement, terrain,
targeting, action, hit, damage, and batch sampling. Stream names and their order are
part of rules version 1. Adding draws to one subsystem must not perturb another.

## Result

`BattleResult` records schema/rules/simulator versions, scenario and trial IDs,
seed, ticks, termination reason, zero or more winner team IDs, per-team remaining
units/HP/armor, aggregate combat metrics, and an event log.
It also records fixed-length numeric scenario features, including doctrine weights,
so inputs are not lost when results become training rows.

The event types in schema version 1 are `move`, `shot`, `hit`, `damage`, `kill`,
`target`, and `objective`. Events contain tick, actor stable ID, optional target ID,
and numeric value.

## Validity Boundary

Translation invariance only applies when units, terrain, bounds, cover, and objectives
are translated together. Scale checks apply only when position, bounds, range, speed,
radius, and terrain resolution are scaled together. HP/damage/range monotonicity is
tested only in isolated micro scenarios and is not claimed as a global tactical law.

Baseline distributions detect unreviewed changes; the legacy baseline is not a
correctness oracle.
