# Surrogate Dataset Contract

Schema version `1.0` stores one row per trial. Required identity fields are
`scenario_id`, `trial_id`, `seed`, `simulator_version`, `rules_version`, and
`schema_version`. Outcome fields include termination reason, winner IDs, duration,
first contact, remaining force, damage, shots, hits, kills, movement, and objective
progress.
Input columns prefixed with `input_` contain fixed-length scenario aggregates.
The complete scenario feature mapping, team results, winner IDs, and randomized
subsystems are also stored as canonical JSON.

Integers are serialized as integers, continuous values as finite floats, and
collections as canonical JSON strings in tabular exports. Missing measurements use
null rather than sentinel numbers. Timeout and stalemate remain separate labels and
must not be converted to wins.

Train, validation, test, and out-of-distribution partitions are made by scenario
family, never only by seed. A dataset manifest records parameter domains, sampling
method, replicate count, rules/schema versions, and package environment.

The version 1 batch runner uses deterministic seed derivation, skips existing trial
IDs when resuming, and writes rows in scenario/trial order. Monte Carlo summaries
report sample count and binomial Wilson confidence intervals. Default stopping is a
fixed replicate count; adaptive stopping requires an explicitly requested confidence
width.
