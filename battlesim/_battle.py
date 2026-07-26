#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Responsible for creating a Battle object.
"""

import hashlib
import json
import warnings
from collections.abc import Callable
from numbers import Integral
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib import colors

from battlesim.contracts import BattleResult, BattleRules
from battlesim.plot._simplot import quiver_fight
from battlesim.randomness import RandomStreams, derive_trial_seed
from battlesim.simulation._tactical import simulate_tactical
from battlesim.terra import Terrain

from . import _utils
from .__defaults import default_db
from ._version import __version__
from .distrib import Composite
from .simulation import _ai as AI
from .simulation import _target

TUPLE4 = tuple[float, float, float, float]


class Battle:
    """
    This 'Battle' object provides the interface for the user of simulating
    a number of Battles.

    Each simulation follows a:
        Load -> Create -> Simulate -> Draw
    flow.
    """

    def __init__(
        self,
        db: str | dict | pd.DataFrame = default_db(),
        bounds: TUPLE4 = (0.0, 10.0, 0.0, 10.0),
        use_tqdm: bool = True,
        seed: int | None = None,
        rules: BattleRules | None = None,
    ):
        """
        Instantiate this object with a filepath leading to

        Parameters
        -------
        db : str, dict or pandas.DataFrame
            If str: Is filepath to the database object
            If dict or pandas.dataFrame: represents actual data.
            Must contain ["Name", "Allegiance", "HP", "Damage", "Accuracy", "Miss", "Movement Speed", "Range"] columns.
            See bsm.defaults.default_db() for example.
        bounds : tuple (4,)
            The left, right, top and bottom bounds of the battle. Units cannot
            leave these bounds.
        use_tqdm : bool, default=True
            Draws a progressbar with `simulate_k` if tqdm is installed
        """
        self.use_tqdm = use_tqdm
        self.seed = 0 if seed is None else int(seed)
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        self.rules = BattleRules() if rules is None else rules
        # assign with checks
        self.db_ = db
        self._M = None
        self._S = None
        self._sim = None
        self._result: BattleResult | None = None
        self._results: tuple[BattleResult, ...] = ()
        self.db_.index = self.db_.index.str.lower()
        # initialise a terra
        self._T = Terrain(bounds, res=0.1, form=None)
        # design a list of composites
        self._comps: list[Composite] | None = None
        self._decision_map = {"aggressive": 0, "hit_and_run": 1}

    @staticmethod
    def _generate_M(n: int):
        return np.zeros(
            n,
            dtype=np.dtype(
                [
                    ("id", "u4"),
                    ("target", "u4"),
                    ("x", "f4"),
                    ("y", "f4"),
                    ("hp", "f4"),
                    ("armor", "f4"),
                    ("dmg", "f4"),
                    ("range", "f4"),
                    ("speed", "f4"),
                    ("acc", "f4"),
                    ("dodge", "f4"),
                    ("utype", "u1"),
                    ("team", "u1"),
                    ("ai_func_index", "u1"),
                    ("target_ai_func_index", "u1"),
                    ("stable_id", "u8"),
                    ("cooldown", "f4"),
                    ("attack_interval", "f4"),
                    ("radius", "f4"),
                    ("move_factor", "f4"),
                    ("threat_distance_weight", "f4"),
                    ("threat_durability_weight", "f4"),
                    ("threat_damage_weight", "f4"),
                    ("threat_objective_weight", "f4"),
                ],
                align=True,
            ),
        )

    def _loading_bar(self, k: int):
        if self.use_tqdm and _utils.is_tqdm_installed(False):
            from tqdm import tqdm

            return tqdm(range(k))
        else:
            return range(k)

    def _is_instantiated(self):
        if not self._comps:
            raise AttributeError(
                "'create_army' has not been called - there are no units."
            )

    def _is_simulated(self):
        if self.sim_ is None:
            raise AttributeError(
                "No simulation has occurred, no presense of battle.sim_ object."
            )

    def _plot_simulation(self, func: Callable):
        labels = self.allegiances_.to_dict()
        cols = _utils.slice_loop(colors.BASE_COLORS.keys(), len(self.allegiances_))
        # call plotting function - with or without terra
        if self.T_ is not None:
            Q = func(self.sim_, self.T_, labels, cols)
        else:
            Q = func(self.sim_, None, labels, cols)
        return Q

    def _get_bounds_from_M(self) -> TUPLE4:
        matrix = self.M_
        assert matrix is not None
        xmin, xmax = matrix["x"].min(), matrix["x"].max()
        ymin, ymax = matrix["y"].min(), matrix["y"].max()
        return (
            float(np.floor(xmin)),
            float(np.ceil(xmax)),
            float(np.floor(ymin)),
            float(np.ceil(ymax)),
        )

    def _check_bounds_to_M(self, bounds: TUPLE4) -> None:
        xmin, xmax, ymin, ymax = self._get_bounds_from_M()
        if bounds[0] > xmin:
            raise ValueError(
                "xmin bounds value: {} > unit bound {}".format(bounds[0], xmin)
            )
        if bounds[1] < xmax:
            raise ValueError(
                "xmax bounds value: {} < unit bound {}".format(bounds[1], xmax)
            )
        if bounds[2] > ymin:
            raise ValueError(
                "ymin bounds value: {} > unit bound {}".format(bounds[2], ymin)
            )
        if bounds[3] < ymax:
            raise ValueError(
                "ymax bounds value: {} < unit bound {}".format(bounds[3], ymax)
            )

    def _expand_bounds_to_M(self) -> None:
        """Expand configured bounds only where initial units fall outside them."""
        unit_bounds = self._get_bounds_from_M()
        configured = self.T_.bounds_
        expanded = (
            min(configured[0], unit_bounds[0]),
            max(configured[1], unit_bounds[1]),
            min(configured[2], unit_bounds[2]),
            max(configured[3], unit_bounds[3]),
        )
        if expanded != configured:
            warnings.warn(
                f"Battle bounds expanded from {configured} to {expanded} "
                "to contain initial unit positions.",
                UserWarning,
                stacklevel=2,
            )
            self.T_.bounds_ = expanded

    @staticmethod
    def _sample_positions(sampling, n: int, rng: np.random.Generator) -> np.ndarray:
        try:
            return np.asarray(sampling.sample(n, rng=rng))
        except TypeError:
            return np.asarray(sampling.sample(n))

    def _presim(
        self,
        streams: RandomStreams | None = None,
        rules: BattleRules | None = None,
    ) -> None:
        streams = RandomStreams.from_seed(self.seed) if streams is None else streams
        selected_rules = self.rules if rules is None else rules
        self._M = Battle._generate_M(sum(self._unit_n))
        matrix = self._M
        assert matrix is not None
        assert self._comps is not None
        # check that groups exist in army_set
        _seg_start, _seg_end = self._segments
        decision_ai_map = {"aggressive": 0, "hit_and_run": 1}
        target_ai_map = {
            "nearest": 0,
            "random": 1,
            "close_weak": 2,
            "weakest": 3,
            "highest_threat": 4,
            "focus_fire": 5,
            "objective_priority": 6,
        }
        occurrence: dict[tuple[int, str], int] = {}

        # set initial values.
        for group, (u, n, start, end, comp) in enumerate(
            zip(self._unit_roster, self._unit_n, _seg_start, _seg_end, self._comps)
        ):
            # set mutable M values in larger matrix.
            matrix["hp"][start:end] = self.db_.loc[u, "HP"]
            matrix["armor"][start:end] = self.db_.loc[u, "Armor"]
            matrix["team"][start:end] = self.db_.loc[u, "allegiance_int"]
            matrix["id"][start:end] = group
            matrix["utype"][start:end] = np.argwhere(self.db_.index == u).flatten()[0]
            matrix["range"][start:end] = self.db_.loc[u, "Range"]
            matrix["speed"][start:end] = self.db_.loc[u, "Movement Speed"]
            matrix["dodge"][start:end] = self.db_.loc[u, "Miss"] / 100.0
            matrix["acc"][start:end] = self.db_.loc[u, "Accuracy"] / 100.0
            matrix["dmg"][start:end] = self.db_.loc[u, "Damage"]
            matrix["attack_interval"][start:end] = self.db_.loc[u, "Attack Interval"]
            matrix["radius"][start:end] = self.db_.loc[u, "Radius"]
            matrix["move_factor"][start:end] = 1.0
            (
                matrix["threat_distance_weight"][start:end],
                matrix["threat_durability_weight"][start:end],
                matrix["threat_damage_weight"][start:end],
                matrix["threat_objective_weight"][start:end],
            ) = comp.doctrine_weights
            # ai func index (0 = aggressive, 1 = hit_and_run)
            matrix["ai_func_index"][start:end] = decision_ai_map[comp.decision_ai]
            matrix["target_ai_func_index"][start:end] = target_ai_map[comp.rolling_ai]
            team = int(matrix["team"][start])
            key = (team, u)
            first_ordinal = occurrence.get(key, 0)
            for offset, unit_index in enumerate(range(start, end)):
                identity_text = f"{team}:{u}:{first_ordinal + offset}"
                identity = identity_text.encode()
                matrix["stable_id"][unit_index] = int.from_bytes(
                    hashlib.sha256(identity).digest()[:8], "little"
                )
                matrix["x"][unit_index] = self._sample_positions(
                    comp.pos,
                    1,
                    streams.keyed_generator("placement", f"{identity_text}:x"),
                )[0]
                matrix["y"][unit_index] = self._sample_positions(
                    comp.pos,
                    1,
                    streams.keyed_generator("placement", f"{identity_text}:y"),
                )[0]
            occurrence[key] = first_ordinal + n

        # Preserve configured bounds, expanding only where positions fall outside.
        self._expand_bounds_to_M()
        # Assign initial targets without index-order noise.
        for group, (start, end) in enumerate(zip(_seg_start, _seg_end)):
            init_ai = self._comps[group].init_ai
            for actor in range(start, end):
                enemies = np.where(matrix["team"] != matrix["team"][actor])[0]
                if init_ai == "random":
                    ordered = enemies[np.argsort(matrix["stable_id"][enemies])]
                    target_rng = streams.keyed_generator(
                        "targeting", int(matrix["stable_id"][actor])
                    )
                    target = int(ordered[int(target_rng.integers(ordered.size))])
                else:
                    dx = matrix["x"][enemies] - matrix["x"][actor]
                    dy = matrix["y"][enemies] - matrix["y"][actor]
                    distance = (dx * dx) + (dy * dy)
                    if init_ai in {"close_weak", "weakest", "highest_threat"}:
                        durability = matrix["hp"][enemies] + matrix["armor"][enemies]
                        d_span = float(np.ptp(distance))
                        h_span = float(np.ptp(durability))
                        distance_score = (
                            np.zeros_like(distance)
                            if d_span == 0
                            else (distance - distance.min()) / d_span
                        )
                        durability_score = (
                            np.zeros_like(durability)
                            if h_span == 0
                            else (durability - durability.min()) / h_span
                        )
                        if init_ai == "weakest":
                            score = durability
                        elif init_ai == "highest_threat":
                            expected_damage = (
                                matrix["dmg"][enemies]
                                * matrix["acc"][enemies]
                                / np.maximum(matrix["attack_interval"][enemies], 1.0)
                            )
                            e_span = float(np.ptp(expected_damage))
                            expected_score = (
                                np.zeros_like(expected_damage)
                                if e_span == 0
                                else (expected_damage - expected_damage.min()) / e_span
                            )
                            score = -(
                                matrix["threat_distance_weight"][actor]
                                * (1.0 - distance_score)
                                + matrix["threat_durability_weight"][actor]
                                * durability_score
                                + matrix["threat_damage_weight"][actor] * expected_score
                            )
                        else:
                            score = (0.7 * distance_score) + (0.3 * durability_score)
                    elif init_ai == "objective_priority" and selected_rules.objectives:
                        objective_distance = np.full(enemies.shape[0], np.inf)
                        for objective in selected_rules.objectives:
                            objective_distance = np.minimum(
                                objective_distance,
                                (matrix["x"][enemies] - objective.x) ** 2
                                + (matrix["y"][enemies] - objective.y) ** 2,
                            )
                        score = objective_distance
                    else:
                        score = distance
                    minimum = float(np.min(score))
                    tied = enemies[np.isclose(score, minimum)]
                    target = int(tied[np.argmin(matrix["stable_id"][tied])])
                matrix["target"][actor] = target

    def _scenario_id(self, rules: BattleRules | None = None) -> str:
        selected_rules = self.rules if rules is None else rules
        assert self._comps is not None
        unit_names = sorted({comp.name.casefold() for comp in self._comps})
        stat_columns = (
            "Allegiance",
            "HP",
            "Armor",
            "Damage",
            "Accuracy",
            "Miss",
            "Movement Speed",
            "Range",
            "Attack Interval",
            "Radius",
        )
        payload = {
            "armies": [
                {
                    "name": comp.name.casefold(),
                    "n": comp.n,
                    "position": repr(comp.pos),
                    "init_ai": comp.init_ai,
                    "rolling_ai": comp.rolling_ai,
                    "decision_ai": comp.decision_ai,
                    "doctrine_weights": comp.doctrine_weights,
                }
                for comp in sorted(
                    self._comps,
                    key=lambda item: (
                        str(self.db_.loc[item.name.lower(), "Allegiance"]),
                        item.name.casefold(),
                        repr(item.pos),
                    ),
                )
            ],
            "unit_stats": {
                unit_name: {
                    column: (
                        str(self.db_.loc[unit_name, column])
                        if column == "Allegiance"
                        else float(cast(Any, self.db_.loc[unit_name, column]))
                    )
                    for column in stat_columns
                }
                for unit_name in unit_names
            },
            "bounds": self.bounds_,
            "terrain": self.T_.form_,
            "terrain_resolution": self.T_.res_,
            "rules": {
                "version": selected_rules.version,
                "tick_seconds": selected_rules.tick_seconds,
                "max_ticks": selected_rules.max_ticks,
                "stalemate_ticks": selected_rules.stalemate_ticks,
                "line_of_sight": selected_rules.line_of_sight,
                "collision": selected_rules.collision,
                "slope_movement": selected_rules.slope_movement,
                "covers": [
                    {
                        "x": cover.x,
                        "y": cover.y,
                        "radius": cover.radius,
                        "hit_multiplier": cover.hit_multiplier,
                    }
                    for cover in selected_rules.covers
                ],
                "objectives": [
                    {
                        "x": objective.x,
                        "y": objective.y,
                        "radius": objective.radius,
                        "capture_ticks": objective.capture_ticks,
                    }
                    for objective in selected_rules.objectives
                ],
            },
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _scenario_features(self, matrix: np.ndarray, rules: BattleRules) -> dict:
        """Fixed-length numeric inputs for the first surrogate representation."""
        return {
            "unit_count": int(matrix.shape[0]),
            "team_count": int(np.unique(matrix["team"]).shape[0]),
            "battlefield_width": float(self.bounds_[1] - self.bounds_[0]),
            "battlefield_height": float(self.bounds_[3] - self.bounds_[2]),
            "objective_count": len(rules.objectives),
            "cover_count": len(rules.covers),
            "mean_hp": float(np.mean(matrix["hp"])),
            "mean_armor": float(np.mean(matrix["armor"])),
            "mean_damage": float(np.mean(matrix["dmg"])),
            "mean_range": float(np.mean(matrix["range"])),
            "mean_speed": float(np.mean(matrix["speed"])),
            "mean_attack_interval": float(np.mean(matrix["attack_interval"])),
            "mean_radius": float(np.mean(matrix["radius"])),
            "mean_threat_distance_weight": float(
                np.mean(matrix["threat_distance_weight"])
            ),
            "mean_threat_durability_weight": float(
                np.mean(matrix["threat_durability_weight"])
            ),
            "mean_threat_damage_weight": float(np.mean(matrix["threat_damage_weight"])),
            "mean_threat_objective_weight": float(
                np.mean(matrix["threat_objective_weight"])
            ),
        }

    @property
    def composition_(self) -> list[Composite]:
        """Determines the composition of the Battle."""
        self._is_instantiated()
        assert self._comps is not None
        return self._comps

    @property
    def n_allegiance_(self) -> pd.Series:
        """Determines the number of teams present in the fight."""
        self._is_instantiated()
        d = {
            "allegiance": [self.db_.loc[u, "Allegiance"] for u, _ in self.army_set_],
            "n": [n for _, n in self.army_set_],
        }
        return pd.DataFrame(d).groupby("allegiance")["n"].sum()

    @property
    def bounds_(self) -> TUPLE4:
        """Determine the bounds of the fight using the Terrain."""
        return self.T_.bounds_

    @bounds_.setter
    def bounds_(self, b: TUPLE4):
        if self.M_ is None:
            warnings.warn(
                "bounds {} set before units are initialised - some may be out-of-bounds".format(
                    b
                ),
                UserWarning,
            )
            self.T_.bounds_ = b
        else:
            self._check_bounds_to_M(b)
            self.T_.bounds_ = b

    @property
    def M_(self) -> np.ndarray | None:
        """The mutable (updatable) matrix information."""
        return self._M

    @property
    def sim_(self):
        """The simulation object."""
        return self._sim

    @property
    def result_(self) -> BattleResult | None:
        """Structured result from the most recent simulation."""
        return self._result

    @property
    def results_(self) -> tuple[BattleResult, ...]:
        """Structured results from the most recent repeated simulation."""
        return self._results

    @property
    def db_(self) -> pd.DataFrame:
        """The datafiles storing information on each unit."""
        return self._db

    @db_.setter
    def db_(self, db_n: str | dict | pd.DataFrame):
        if isinstance(db_n, str):
            self._db = _utils.import_and_check_unit_file(db_n)
        elif isinstance(db_n, dict):
            self._db = pd.DataFrame(db_n)
            _utils.check_unit_file(self._db)
            _utils.preprocess_unit_file(self._db)
        elif isinstance(db_n, pd.DataFrame):
            self._db = db_n.copy()
            _utils.check_unit_file(self._db)
            _utils.preprocess_unit_file(self._db)
        else:
            raise ValueError(
                "'db' must be of type [str, dict, pd.DataFrame], not {}".format(
                    type(db_n)
                )
            )

    @property
    def T_(self) -> Terrain:
        """Attribute to the Terrain object."""
        return self._T

    @property
    def army_set_(self):
        """A list of unit rosters and counts."""
        self._is_instantiated()
        return tuple(zip(self._unit_roster, self._unit_n))

    @property
    def n_armies_(self) -> int:
        """The number of army types."""
        self._is_instantiated()
        return len(self._unit_roster)

    @property
    def allegiances_(self):
        """The allegiances participating in the current army composition."""
        teams = np.unique(self._teams)
        return (
            self.db_[["Allegiance", "allegiance_int"]]
            .loc[lambda frame: frame["allegiance_int"].isin(teams)]
            .drop_duplicates()
            .set_index("allegiance_int")["Allegiance"]
        )

    @property
    def _segments(self):
        _seg_end = np.cumsum(self._unit_n)
        _seg_start = np.hstack((np.array([0], dtype=int), _seg_end[:-1]))
        return _seg_start, _seg_end

    @property
    def _teams(self) -> np.ndarray:
        self._is_instantiated()
        return np.asarray(
            [self.db_.loc[u, "allegiance_int"] for u in self._unit_roster]
        )

    def create_army(self, army_set: list[Composite] | tuple[Composite, ...]):
        """
        Armies are groupings of (<'Unit Type'>, <number of units>). You can
        create one or more of these.

        We make use of the dataset (`db`) with army_set.

        We create the 'M' matrix, which is directly fed into any 'simulation' function.

        Parameters
        -------
        army_set : list of Composite
            A list of 'army groups' given as ('Unit Type', number of units)

        Returns self
        -------
        self
        """
        if not isinstance(army_set, (list, tuple)):
            raise TypeError("`army_set` must be a List/Tuple of Composites")

        if not all(isinstance(a, Composite) for a in army_set):
            raise TypeError("all instances within `army_set` must be composites.")
        if not army_set:
            raise ValueError("`army_set` must contain at least one Composite")

        for composite in army_set:
            if not isinstance(composite.name, str):
                raise TypeError("Composite.name must be a string")
            if isinstance(composite.n, bool) or not isinstance(composite.n, Integral):
                raise TypeError("Composite.n must be an integer")
            if composite.n < 1:
                raise ValueError("Composite.n must be at least 1")
            if composite.decision_ai not in AI.get_function_names():
                raise ValueError(
                    f"unsupported decision_ai: {composite.decision_ai!r}; "
                    f"expected one of {AI.get_function_names()}"
                )
            for field_name, target_ai in (
                ("init_ai", composite.init_ai),
                ("rolling_ai", composite.rolling_ai),
            ):
                if target_ai not in _target.get_function_names():
                    raise ValueError(
                        f"unsupported {field_name}: {target_ai!r}; "
                        f"expected one of {_target.get_function_names()}"
                    )

        normalized_groups = [
            (composite.name.lower(), composite.n) for composite in army_set
        ]
        _utils.check_groups_in_db(normalized_groups, self.db_)

        self._comps = list(army_set)
        # assign unit roster, n for roster
        self._unit_roster = [u.name.lower() for u in army_set]
        self._unit_n = [u.n for u in army_set]
        self._M = None
        self._sim = None
        self._result = None
        self._results = ()
        return self

    def apply_terrain(self, t: str | Terrain | None = None, res: float = 0.1):
        """
        Applies a Z-plane to the map that the Battle is occuring on by creating
        a bsm.Terrain object.

        Parameters
        -------
        t : str or bsm.Terrain
            Choose from [None, 'grid', 'contour']. Default is None. Contour looks
            the best. Decides how big/resolution to make the terra based on the
            initialized positions of units.
        res : float
            The resolution to use for the map

        Returns
        -------
        self
        """
        self._is_instantiated()

        if isinstance(t, Terrain):
            self._T = t
            return self
        elif t in [None, "grid", "contour"]:
            # add function to t
            self.T_.res_ = res
            self.T_.form_ = t
            return self
        else:
            raise ValueError("'t' must be [grid, contour, None]")

    def set_bounds(self, bounds: TUPLE4):
        """
        Sets the boundaries of the Battle. If not initialised, this is OK but may
        produce errors down-the-line.

        Parameters
        -------
        bounds : tuple, list (4,)
            the (left, right, top, bottom) dimensions of the simulation.

        Returns
        -------
        self
        """
        self.bounds_ = bounds
        return self

    def simulate(
        self,
        verbose: int = 0,
        *,
        seed: int | None = None,
        rules: BattleRules | None = None,
    ):
        """
        Runs the 'simulate_battle' algorithm. Creates and passes a copy to simulate..

        Returns np.ndarray of frames.
        """
        self._is_instantiated()
        # check for multiple teams
        if np.unique(self._teams).shape[0] <= 1:
            warnings.warn(
                "Simulation halted - There is only one team present.", UserWarning
            )
            return self.sim_

        # set up M matrix from composition info
        selected_seed = self.seed if seed is None else int(seed)
        selected_rules = self.rules if rules is None else rules
        streams = RandomStreams.from_seed(selected_seed)
        self._presim(streams, selected_rules)
        matrix = self.M_
        assert matrix is not None
        # re-generate terrain.
        self.T_.generate(rng=streams.generator("terrain"))
        run = simulate_tactical(
            matrix,
            self.T_,
            rules=selected_rules,
            streams=streams,
            scenario_id=self._scenario_id(selected_rules),
            simulator_version=__version__,
            randomized_subsystems=("placement", "terrain", "combat"),
            scenario_features=self._scenario_features(matrix, selected_rules),
            team_labels={
                int(team): str(label) for team, label in self.allegiances_.items()
            },
        )
        self._sim = run.frames
        self._result = run.result
        self._results = (run.result,)
        return self.sim_

    def simulate_k(
        self,
        k: int = 10,
        *,
        seed: int | None = None,
        randomize: tuple[str, ...] = ("combat",),
    ):
        """
        Runs the 'simulate_battle' algorithm 'k' times. Creates and passes a copy
        to simulate.

        Parameters
        --------
        k : int
            The number of iterations. Must be at least 1.
        **kwargs : dict
            keyword arguments to pass to simulate_battle.

        Returns
        -------
        runs : pd.DataFrame
            The iteration (k), with the team victorious, and number of units remaining

        Returns the victory for each k iteration, for each team.
        """
        self._is_instantiated()

        allowed_randomization = {"placement", "terrain", "combat"}
        unknown = set(randomize) - allowed_randomization
        if unknown:
            raise ValueError(f"unknown randomize subsystem(s): {sorted(unknown)}")
        if k < 1:
            raise ValueError("'k' must be at least 1")
        else:
            # check for multiple teams
            if np.unique(self._teams).shape[0] <= 1:
                warnings.warn(
                    "Simulation halted - There is only one team present.", UserWarning
                )
                return self.sim_

            # now handles J teams (thanks kmcnayr @ https://github.com/gregparkes/BattleSimulator/issues/4)
            runs = np.zeros((k, np.unique(self._teams).shape[0]), dtype=np.int64)
            root_seed = self.seed if seed is None else int(seed)
            fixed_streams = RandomStreams.from_seed(root_seed)
            self._presim(fixed_streams)
            initialized_matrix = self.M_
            assert initialized_matrix is not None
            fixed_matrix = np.copy(initialized_matrix)
            self.T_.generate(rng=fixed_streams.generator("terrain"))
            generated_terrain = self.T_.Z_
            assert generated_terrain is not None
            fixed_terrain = np.copy(generated_terrain)
            results: list[BattleResult] = []

            for i in self._loading_bar(k):
                trial_seed = derive_trial_seed(root_seed, i)
                streams = RandomStreams.for_trial(
                    root_seed=root_seed,
                    trial_seed=trial_seed,
                    randomized=set(randomize),
                )
                if "placement" in randomize:
                    self._presim(streams)
                    randomized_matrix = self.M_
                    assert randomized_matrix is not None
                    matrix = np.copy(randomized_matrix)
                else:
                    matrix = np.copy(fixed_matrix)
                if "terrain" in randomize:
                    self.T_.generate(rng=streams.generator("terrain"))
                else:
                    self.T_._Z = np.copy(fixed_terrain)
                run = simulate_tactical(
                    matrix,
                    self.T_,
                    rules=self.rules,
                    streams=streams,
                    scenario_id=self._scenario_id(),
                    simulator_version=__version__,
                    record_events=False,
                    randomized_subsystems=randomize,
                    scenario_features=self._scenario_features(matrix, self.rules),
                    team_labels={
                        int(team): str(label)
                        for team, label in self.allegiances_.items()
                    },
                )
                results.append(run.result)
                runs[i, :] = [team.remaining_units for team in run.result.teams]
            self._results = tuple(results)
            self._result = results[-1]
            return pd.DataFrame(runs, columns=self.allegiances_.values)

    def sim_jupyter(self, func: Callable = quiver_fight, create_html: bool = False):
        """
        This convenience method uses any saved 'sim_' object to generate the code
        to output to a Jupyter Notebook. Once must simply then do:

            HTML(battle.sim_jupyter())

        And hey presto, it should all work!

        Parameters
        --------
        func : function, optional
            The plot function to call, by default is bsm.quiver_fight()
        create_html : bool, optional
            Decides whether to return the object directly, or create HTML to then use HTML()

        Returns
        -------
        s : str/object
            HTML code to feed into HTML(s)
        """
        self._is_simulated()
        # call plotting function - with
        Q = self._plot_simulation(func)

        if create_html:
            return Q.to_jshtml()
        else:
            return Q

    def sim_export(
        self,
        filename: str = "example_sim.gif",
        func: Callable = quiver_fight,
        writer: str = "pillow",
    ):
        """
        This convenience method uses any saved 'sim_' object to generate the code
        to export into a gif file.

        Parameters
        -------
        filename : str, optional
            The name of the file to output. Must end in .gif
        func : function, optional
            The plot function to call, by default is bsm.quiver_fight()
        writer : str, optional
            The type of writer to pass to funcanimation.save(). This might
            need to be tweaked on your system.
            Accepts ['imagemagick', 'ffmpeg', 'pillow']

        Returns
        -------
        None
        """
        self._is_simulated()
        # append to end if not present
        if not filename.endswith(".gif"):
            filename += ".gif"

        # call simulation
        Q = self._plot_simulation(func)

        # save
        Q.save(filename, writer=writer)
        return

    def __repr__(self) -> str:
        if self.M_ is None:
            return "bsm.Battle(init=False)"
        elif self.sim_ is None:
            return "bsm.Battle(init=True, n_armies={}, simulated=False)".format(
                self.n_armies_
            )
        else:
            return "bsm.Battle(init=True, n_armies={}, simulated=True)".format(
                self.n_armies_
            )
