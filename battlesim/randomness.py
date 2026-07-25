"""Stable named random streams for reproducible simulations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

STREAM_NAMES = (
    "placement",
    "terrain",
    "targeting",
    "action",
    "hit",
    "damage",
    "batch",
)


@dataclass(frozen=True)
class RandomStreams:
    """Generators derived from one root seed without cross-subsystem coupling."""

    seed: int
    _generators: dict[str, np.random.Generator]
    _subsystem_seeds: dict[str, int]

    @classmethod
    def from_seed(cls, seed: int | None) -> "RandomStreams":
        normalized = 0 if seed is None else int(seed)
        if normalized < 0:
            raise ValueError("seed must be non-negative")
        sequences = np.random.SeedSequence(normalized).spawn(len(STREAM_NAMES))
        return cls(
            normalized,
            {
                name: np.random.default_rng(sequence)
                for name, sequence in zip(STREAM_NAMES, sequences, strict=True)
            },
            {name: normalized for name in STREAM_NAMES},
        )

    @classmethod
    def for_trial(
        cls,
        *,
        root_seed: int,
        trial_seed: int,
        randomized: set[str],
    ) -> "RandomStreams":
        """Mix fixed and trial-varying subsystem roots."""
        combat_names = {"targeting", "action", "hit", "damage"}
        subsystem_seeds = {
            name: (
                trial_seed
                if (
                    name in randomized
                    or ("combat" in randomized and name in combat_names)
                )
                else root_seed
            )
            for name in STREAM_NAMES
        }
        generators = {
            name: np.random.default_rng(
                np.random.SeedSequence([subsystem_seed, STREAM_NAMES.index(name)])
            )
            for name, subsystem_seed in subsystem_seeds.items()
        }
        return cls(trial_seed, generators, subsystem_seeds)

    def generator(self, name: str) -> np.random.Generator:
        try:
            return self._generators[name]
        except KeyError as error:
            raise KeyError(f"unknown random stream: {name!r}") from error

    def keyed_generator(self, name: str, key: str | int) -> np.random.Generator:
        """Create an order-independent generator for one stable entity."""
        if name not in STREAM_NAMES:
            raise KeyError(f"unknown random stream: {name!r}")
        digest = hashlib.sha256(f"{name}:{key}".encode()).digest()
        words = np.frombuffer(digest[:16], dtype=np.uint32)
        return np.random.default_rng(
            np.random.SeedSequence([self._subsystem_seeds[name], *words])
        )


def derive_trial_seed(seed: int, trial_index: int) -> int:
    """Derive a stable uint64 seed for a trial."""
    if seed < 0 or trial_index < 0:
        raise ValueError("seed and trial_index must be non-negative")
    sequence = np.random.SeedSequence([int(seed), int(trial_index)])
    return int(sequence.generate_state(1, dtype=np.uint64)[0])
