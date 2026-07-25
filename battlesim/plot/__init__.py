#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A subpackage for special types of plots."""

from ._simplot import quiver_fight, quiver_fight_debug, quiver_frame_debug
from ._viewmodel import (
    FrameView,
    UnitParameterView,
    UnitView,
    advance_playback,
    build_frame_view,
    build_unit_parameter_views,
)

__all__ = [
    "FrameView",
    "UnitParameterView",
    "UnitView",
    "advance_playback",
    "build_frame_view",
    "build_unit_parameter_views",
    "quiver_fight",
    "quiver_fight_debug",
    "quiver_frame_debug",
]
