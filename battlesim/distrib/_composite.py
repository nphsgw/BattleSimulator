from ._distrib2 import Sampling


class Composite:
    """Holds an army set information."""

    def __init__(
        self,
        name: str,
        n: int,
        pos_dist=None,
        init_ai="nearest",
        rolling_ai="nearest",
        decision_ai="aggressive",
        doctrine_weights=(0.25, 0.15, 0.5, 0.1),
    ):
        self.name = name
        self.n = n
        if pos_dist is not None:
            self.pos = pos_dist
        else:
            self.pos = Sampling("normal")

        self.init_ai = init_ai
        self.rolling_ai = rolling_ai
        self.decision_ai = decision_ai
        if len(doctrine_weights) != 4:
            raise ValueError("doctrine_weights must contain four values")
        self.doctrine_weights = tuple(float(value) for value in doctrine_weights)
        if any(value < 0 for value in self.doctrine_weights):
            raise ValueError("doctrine_weights must be non-negative")
        if sum(self.doctrine_weights) <= 0:
            raise ValueError("doctrine_weights must contain a positive value")

    def __repr__(self):
        return (
            f"Composite('{self.name}', n={self.n}, pos={self.pos}, "
            + f"init_ai='{self.init_ai}', rolling_ai='{self.rolling_ai}', "
            + f"decision_ai='{self.decision_ai}', "
            + f"doctrine_weights={self.doctrine_weights})"
        )
