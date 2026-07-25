# Validation Plan

Rules version 1 is accepted only when deterministic, metamorphic, statistical, and
performance checks all pass.

- Exact checks: same input/seed/version, state bounds, termination labels, result and
  event schemas.
- Metamorphic checks: Composite order, team-label exchange, whole-world translation,
  and consistently scaled flat micro scenarios.
- Statistical checks: non-degenerate outcomes across fixed seeds, Wilson confidence
  intervals, scenario-family partitions, and a stored baseline distribution.
- Tactical micro checks: damage monotonicity in an isolated duel, cooldown cadence,
  mutual destruction, line-of-sight, cover, collision, and objective capture.

The baseline under `tests/baselines/` is a change detector, not evidence that the
model represents reality. A rules version change is required when an intentional
semantic change moves that baseline.

The reference Python kernel has an initial CI performance budget of 30 seconds for
the complete test suite, including a 200-unit battle. Dataset workloads that exceed
this budget must benchmark before parallel execution or kernel optimization is added.

External calibration data is not currently available. Before interpreting surrogate
predictions as real-world estimates, add an explicit calibration dataset, provenance,
measurement error, accepted parameter ranges, and holdout criteria. Until then, the
surrogate is documented as an emulator of rules version 1, not a validated model of
real combat.
