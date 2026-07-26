"""Framework-independent helpers for the local placement editor."""

from __future__ import annotations

import math
from numbers import Real


def initial_placement_rows(
    left_unit: str,
    left_count: int,
    right_unit: str,
    right_count: int,
) -> list[dict[str, object]]:
    """Create a readable, deterministic starting formation for two armies."""
    rows: list[dict[str, object]] = []
    unit_number = 1
    for team, unit_type, count, x in (
        ("Army 1", left_unit, left_count, 2.0),
        ("Army 2", right_unit, right_count, 8.0),
    ):
        for offset in range(count):
            y = 5.0 if count == 1 else 1.0 + (8.0 * offset / (count - 1))
            rows.append(
                {
                    "No.": unit_number,
                    "Team": team,
                    "Type": unit_type,
                    "X": x,
                    "Y": y,
                }
            )
            unit_number += 1
    return rows


def validate_placement_rows(
    rows: list[dict[str, object]],
    *,
    bounds: tuple[float, float, float, float],
) -> list[dict[str, float]]:
    """Validate numeric editor values before constructing a scenario."""
    validated: list[dict[str, float]] = []
    xmin, xmax, ymin, ymax = bounds
    for index, row in enumerate(rows):
        values: dict[str, float] = {}
        for column, lower, upper in (("X", xmin, xmax), ("Y", ymin, ymax)):
            raw_value = row.get(column)
            if (
                isinstance(raw_value, bool)
                or not isinstance(raw_value, Real)
                or not math.isfinite(float(raw_value))
            ):
                raise ValueError(f"Unit #{index + 1} {column} must be a finite number")
            value = float(raw_value)
            if not lower <= value <= upper:
                raise ValueError(
                    f"Unit #{index + 1} {column} must be between {lower:g} "
                    f"and {upper:g}"
                )
            values[column.lower()] = value
        validated.append(values)
    return validated


def apply_mouse_placement(
    rows: list[dict[str, object]],
    selected_index: int,
    x: object,
    y: object,
    *,
    bounds: tuple[float, float, float, float],
) -> list[dict[str, object]]:
    """Return placement rows with one selected unit moved to a clicked point."""
    updated = [dict(row) for row in rows]
    if not 0 <= selected_index < len(updated):
        raise ValueError("selected unit is outside the placement table")
    candidate = dict(updated[selected_index])
    candidate["X"] = x
    candidate["Y"] = y
    validate_placement_rows([candidate], bounds=bounds)
    updated[selected_index] = candidate
    return updated
