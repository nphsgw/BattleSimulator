from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


class Sampling:
    """Wrapper class for handling numpy.random distributions."""

    def __init__(self, name: str, *args: object) -> None:
        """name must be one of []"""
        self.__accepted_dists: set[str] = {
            "beta",
            "binomial",
            "chisquare",
            "exponential",
            "laplace",
            "lognormal",
            "normal",
            "uniform",
        }
        self.name = name
        self.args: tuple[object, ...] = args

    @property
    def name(self) -> str:
        """The name of the numpy distribution to call."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if name not in self.__accepted_dists:
            raise ValueError(f"name {name} must be in {self.__accepted_dists}")
        self._name = name

    @property
    def f(self) -> Any:
        """Returns the np.random function associated with the name"""
        return getattr(np.random, self.name)

    def sample(
        self,
        n: int,
        rng: np.random.Generator | None = None,
    ) -> NDArray[Any]:
        """Samples a 1d from random."""
        if rng is None:
            return np.asarray(self.f(*self.args, size=(n,)))
        return np.asarray(getattr(rng, self.name)(*self.args, size=(n,)))

    def __repr__(self) -> str:
        return f"Sampling('{self.name}', {self.args})"
