"""The initialization for the battlesim package."""

# imports
from . import (  # noqa: F401
    __legacy,  # noqa: F401
    distrib,
    plot,
    simulation,
    terra,
)
from ._battle import Battle as Battle
from ._version import __version__  # noqa: F401
from .contracts import (
    BattleEvent as BattleEvent,
)
from .contracts import (
    BattleResult as BattleResult,
)
from .contracts import (
    BattleRules as BattleRules,
)
from .contracts import (
    CoverZone as CoverZone,
)
from .contracts import (
    ObjectiveZone as ObjectiveZone,
)
from .contracts import (
    TeamResult as TeamResult,
)
from .contracts import (
    TerminationReason as TerminationReason,
)
from .dataset import (  # noqa: F401
    expand_parameter_sweep,
    export_results,
    result_to_record,
    run_batch,
    scenario_family_partition,
    wilson_interval,
)
from .distrib import Composite as Composite
from .distrib import Sampling as Sampling
from .plot import (  # noqa: F401
    FrameView,
    UnitParameterView,
    UnitView,
    advance_playback,
    build_frame_view,
    build_unit_parameter_views,
    quiver_fight,
    quiver_fight_debug,
    quiver_frame_debug,
)
from .scenario import ArmySpec as ArmySpec
from .scenario import BattleScenario as BattleScenario
from .terra import Terrain as Terrain
from .validation import (  # noqa: F401
    ValidationIssue,
    monte_carlo_summary,
    sensitivity_analysis,
    surrogate_frame,
    validate_results,
)

__name__ = "battlesim"  # noqa: W0622
__doc__ = """
battlesim - Modelling and animating simulated battles between units in Python.
==============================================================================

**battlesim** is a Python package providing TABS (totally-accurate-battle-simulator)-
style combat designed to entertain, inform and acts as a platform for simulation and
modelling within a games-design context. Simulations are designed not only to be
comprehensive and flexible, but also fast by relying on just-in-time compiling.

Main Features
-------------
Here are just a few things that battlesim aims to do well:

    - Formulate your simulation in a few lines of code from scratch.
    - Scales up to thousands (and 10s of thousands) of units
    - Flexibility: unit values are taken from a data file with flexible AI options
    - Performance: Just-in-time compiling (JIT) can manage thousands of units
    - Visualisation: Animations can be customized to change look-and-feel
"""
