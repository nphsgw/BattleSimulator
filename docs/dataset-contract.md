# Surrogate Dataset Contract

Schema version `1.0` stores one row per trial. Required identity fields are
`scenario_id`, `trial_id`, `seed`, `simulator_version`, `rules_version`,
`schema_version`, and `result_schema_version`. Outcome columns are
`termination_reason`, `winner_team_ids`, `winner_team_labels`, `ticks`,
`first_contact_tick`, `total_initial_units`, `total_remaining_units`,
`survival_rate`, `remaining_hp`, `remaining_armor`, `damage_dealt`, `shots`,
`hits`, `kills`, `movement`, `high_ground_ticks`, `cover_ticks`,
`objective_ticks`, and `mean_spatial_dispersion`. Per-team values such as
damage received are stored only in the `team_results` JSON.
Input columns prefixed with `input_` contain fixed-length scenario aggregates.
The complete scenario feature mapping, team results, winner IDs, and randomized
subsystems are also stored as canonical JSON.

Integers are serialized as integers, continuous values as finite floats, and
collections as canonical JSON strings in tabular exports. Missing measurements use
null rather than sentinel numbers. Timeout and stalemate remain separate labels and
must not be converted to wins.

Train, validation, test, and out-of-distribution partitions are made by scenario
family, never only by seed.

A dataset export writes `<output>.manifest.json` next to the table. The runner
records `schema_version`, `result_schema_version`, `rules_version`,
`simulator_version`, `root_seed`, `replicates_per_scenario`, `scenario_families`,
`sampling_method`, `rows`, and `package_environment` (Python, numpy, pandas
versions). Parameter domains are not known to the runner, which receives expanded
scenarios; the caller supplies them through the `manifest` argument, whose keys are
merged last and not standardized. A resumed run rewrites the manifest with the
current run's `root_seed` and `replicates_per_scenario`, so resuming with different
values leaves the manifest inconsistent with earlier rows; resume with the same
values. The package environment is stored only in the manifest, never in rows.

The version 1 batch runner uses deterministic seed derivation, skips existing trial
IDs when resuming, and writes rows in scenario/trial order. Monte Carlo summaries
report sample count and binomial Wilson confidence intervals. Default stopping is a
fixed replicate count. Adaptive stopping is a future extension, not implemented;
if added it must require an explicitly requested confidence width.
