"""The initialization for the battlesim package."""

# imports
from . import (  # noqa: F401
    __legacy,  # noqa: F401
    distrib,
    plot,
    simulation,
    terra,
)
from ._battle import Battle  # noqa: F401
from ._version import __version__  # noqa: F401
from .contracts import (  # noqa: F401
    BattleEvent,
    BattleResult,
    BattleRules,
    CoverZone,
    ObjectiveZone,
    TeamResult,
    TerminationReason,
)
from .dataset import (  # noqa: F401
    expand_parameter_sweep,
    export_results,
    result_to_record,
    run_batch,
    scenario_family_partition,
    wilson_interval,
)
from .distrib import Composite, Sampling  # noqa: F401
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
from .scenario import ArmySpec, BattleScenario  # noqa: F401
from .terra import Terrain  # noqa: F401
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
