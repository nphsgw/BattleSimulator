"""Command-line entry points for notebook-independent visualization."""

import argparse
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt

from battlesim.plot import quiver_frame_debug
from battlesim.scenario import BattleScenario


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="battlesim-render",
        description="Run a TOML battle scenario and render one frame.",
    )
    parser.add_argument("scenario", type=Path, help="TOML scenario file")
    parser.add_argument("output", type=Path, help="output image, such as battle.png")
    parser.add_argument(
        "--frame",
        type=int,
        default=-1,
        help="frame index; -1 selects the final frame",
    )
    parser.add_argument("--hide-hp", action="store_true")
    parser.add_argument("--hide-target-lines", action="store_true")
    parser.add_argument("--show-terrain-text", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the static-frame renderer CLI."""
    args = _parser().parse_args(argv)
    scenario = BattleScenario.from_toml(args.scenario)
    battle = scenario.run()
    frames = battle.sim_
    assert frames is not None
    frame_i = frames.shape[0] - 1 if args.frame == -1 else args.frame
    figure, _axes = quiver_frame_debug(
        frames,
        frame_i=frame_i,
        terrain=battle.T_,
        allegiance_label=battle.allegiances_.to_dict(),
        show_hp=not args.hide_hp,
        show_target_lines=not args.hide_target_lines,
        show_terrain_text=args.show_terrain_text,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output)
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
