"""Local Streamlit viewer for BattleSimulator."""

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

import battlesim as bsm

_DAMAGE_DEMO_SCENARIO = (
    Path(__file__).resolve().parents[1] / "scenarios" / "damage-demo.toml"
)


def _optional_round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _parameter_rows(
    parameters: tuple[bsm.UnitParameterView, ...],
) -> list[dict[str, str | float | None]]:
    return [
        {
            "No.": f"#{unit.number}",
            "Team": unit.team,
            "Type": unit.unit_type,
            "State": "Alive" if unit.alive else "Dead",
            "HP": f"{unit.hp:.1f} / {unit.max_hp:.1f}",
            "Armor": _optional_round(unit.armor),
            "Target": (
                f"#{unit.target_number}" if unit.target_number is not None else "—"
            ),
            "Height": _optional_round(unit.z),
            "Move": _optional_round(unit.move_factor),
            "Range": _optional_round(unit.effective_range),
            "Damage": _optional_round(unit.damage_factor),
        }
        for unit in parameters
    ]


def _default_index(options: list[str], name: str, fallback: int) -> int:
    try:
        return options.index(name.lower())
    except ValueError:
        return fallback


def _build_scenario(
    left_unit: str,
    left_count: int,
    right_unit: str,
    right_count: int,
    terrain: str,
) -> bsm.BattleScenario:
    return bsm.BattleScenario(
        armies=(
            bsm.ArmySpec(
                left_unit,
                left_count,
                position_parameters=(1.5, 0.6),
            ),
            bsm.ArmySpec(
                right_unit,
                right_count,
                position_parameters=(7.5, 0.6),
            ),
        ),
        terrain=None if terrain == "flat" else terrain,
        terrain_resolution=0.2,
    )


def main() -> None:
    st.set_page_config(page_title="BattleSimulator", layout="wide")
    st.title("BattleSimulator")
    st.caption("Notebook に依存しないローカル戦闘ビューア")

    st.session_state.setdefault("playback_frame", 0)
    st.session_state.setdefault("playback_playing", False)
    st.session_state.setdefault("playback_skip_advance", False)

    catalog = bsm.Battle(use_tqdm=False)
    unit_options = catalog.db_.index.tolist()

    config_column, display_column = st.columns(2)
    with config_column:
        scenario_preset = st.selectbox(
            "Scenario",
            ("Custom battle", "Damage demo"),
            key="scenario_preset",
        )
        if scenario_preset == "Custom battle":
            left_unit = st.selectbox(
                "Army 1",
                unit_options,
                index=_default_index(unit_options, "B1 battledroid", 0),
                key="left_unit",
            )
            left_count = st.number_input(
                "Army 1 count",
                min_value=1,
                max_value=100,
                value=4,
                key="left_count",
            )
            right_unit = st.selectbox(
                "Army 2",
                unit_options,
                index=_default_index(
                    unit_options,
                    "Clone Trooper",
                    min(1, len(unit_options) - 1),
                ),
                key="right_unit",
            )
            right_count = st.number_input(
                "Army 2 count",
                min_value=1,
                max_value=100,
                value=4,
                key="right_count",
            )
            terrain = st.selectbox(
                "Terrain",
                ("flat", "grid", "contour"),
                key="terrain",
            )
        else:
            st.info(
                "Armor 20 → 10 → 0 の後、HP 30 → 20 → 10 → 0 と減る"
                "5 tickの1対1デモです。"
            )
        run_simulation = st.button("Run simulation", type="primary", key="run")

    with display_column:
        show_target_lines = st.toggle(
            "Show target lines",
            value=False,
            key="show_target_lines",
        )
        playback_speed = st.select_slider(
            "Playback speed",
            options=(0.5, 1.0, 2.0, 4.0),
            value=1.0,
            format_func=lambda value: f"{value:g} fps",
            key="playback_speed",
        )

    if run_simulation:
        if scenario_preset == "Damage demo":
            scenario = bsm.BattleScenario.from_toml(_DAMAGE_DEMO_SCENARIO)
        else:
            scenario = _build_scenario(
                left_unit,
                int(left_count),
                right_unit,
                int(right_count),
                terrain,
            )
        try:
            battle = scenario.run()
        except Exception as error:
            st.exception(error)
        else:
            st.session_state["battle"] = battle
            st.session_state["playback_frame"] = 0
            st.session_state["playback_playing"] = True
            st.session_state["playback_skip_advance"] = True

    battle = st.session_state.get("battle")
    if battle is None or battle.sim_ is None:
        st.info("条件を選び、Run simulation を押してください。")
        return

    frames = battle.sim_
    run_every = (
        1.0 / float(playback_speed) if st.session_state["playback_playing"] else None
    )

    def pause_from_slider() -> None:
        st.session_state["playback_playing"] = False
        st.session_state["playback_refresh"] = True

    @st.fragment(run_every=run_every)
    def playback_view() -> None:
        reached_end = False
        if st.session_state["playback_playing"]:
            if st.session_state["playback_skip_advance"]:
                st.session_state["playback_skip_advance"] = False
            else:
                frame_i, keep_playing = bsm.advance_playback(
                    int(st.session_state["playback_frame"]),
                    frames.shape[0],
                )
                st.session_state["playback_frame"] = frame_i
                st.session_state["playback_playing"] = keep_playing
                reached_end = not keep_playing

        play_column, pause_column, restart_column = st.columns(3)
        with play_column:
            if st.button(
                "Play",
                disabled=st.session_state["playback_playing"],
                key="play",
                use_container_width=True,
            ):
                st.session_state["playback_playing"] = True
                st.session_state["playback_skip_advance"] = True
                st.rerun()
        with pause_column:
            if st.button(
                "Pause",
                disabled=not st.session_state["playback_playing"],
                key="pause",
                use_container_width=True,
            ):
                st.session_state["playback_playing"] = False
                st.rerun()
        with restart_column:
            if st.button("Replay", key="replay", use_container_width=True):
                st.session_state["playback_frame"] = 0
                st.session_state["playback_playing"] = True
                st.session_state["playback_skip_advance"] = True
                st.rerun()

        frame_i = st.slider(
            "Frame",
            min_value=0,
            max_value=frames.shape[0] - 1,
            key="playback_frame",
            on_change=pause_from_slider,
        )
        st.caption(
            f"Frame {frame_i + 1} / {frames.shape[0]}"
            + (" · Playing" if st.session_state["playback_playing"] else " · Paused")
        )
        frame_view = bsm.build_frame_view(frames, frame_i)
        team_labels = battle.allegiances_.to_dict()
        unit_type_labels = dict(enumerate(battle.db_.index.tolist()))
        parameter_views = bsm.build_unit_parameter_views(
            frame_view,
            team_labels=team_labels,
            unit_type_labels=unit_type_labels,
        )

        battle_column, parameter_column = st.columns([3, 2], gap="large")
        with battle_column:
            st.subheader("Battle")
            figure, _axes = bsm.quiver_frame_debug(
                frames,
                frame_i=frame_i,
                terrain=battle.T_,
                allegiance_label=team_labels,
                show_hp=False,
                show_target_lines=show_target_lines,
                show_terrain_text=False,
                show_unit_numbers=True,
            )
            st.pyplot(figure)

            image = BytesIO()
            figure.savefig(image, format="png")
            plt.close(figure)
            st.download_button(
                "Download current frame",
                data=image.getvalue(),
                file_name=f"battle-frame-{frame_i}.png",
                mime="image/png",
            )

        with parameter_column:
            st.subheader("Unit parameters")
            st.dataframe(
                _parameter_rows(parameter_views),
                column_order=(
                    "No.",
                    "Team",
                    "Type",
                    "State",
                    "HP",
                    "Armor",
                    "Target",
                    "Height",
                    "Move",
                    "Range",
                    "Damage",
                ),
                hide_index=True,
                height=600,
                width="stretch",
            )

        if st.session_state.pop("playback_refresh", False) or reached_end:
            st.rerun()

    playback_view()


if __name__ == "__main__":
    main()
