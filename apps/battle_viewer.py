"""Local Streamlit viewer for BattleSimulator."""

from io import BytesIO
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from streamlit.components.v2 import component

import battlesim as bsm

_DAMAGE_DEMO_SCENARIO = (
    Path(__file__).resolve().parents[1] / "scenarios" / "damage-demo.toml"
)
_BATTLE_BOUNDS = (0.0, 10.0, 0.0, 10.0)

_PLACEMENT_COMPONENT = component(
    "battle_placement_map",
    html='<div id="placement-root"></div>',
    css="""
        #placement-root { width: 100%; }
        svg {
            width: 100%;
            max-height: 520px;
            border: 1px solid var(--st-border-color);
            border-radius: 0.5rem;
            background: var(--st-secondary-background-color);
            cursor: crosshair;
            touch-action: none;
        }
        .grid { stroke: var(--st-border-color); stroke-width: 0.025; }
        .axis-label { fill: var(--st-text-color); font-size: 0.32px; }
        .unit { stroke: white; stroke-width: 0.08; }
        .selected { stroke: #ffbf00; stroke-width: 0.16; }
        .unit-label {
            fill: white;
            font-size: 0.3px;
            font-weight: 700;
            text-anchor: middle;
            dominant-baseline: central;
            pointer-events: none;
        }
    """,
    js="""
        export default function(component) {
            const { data, parentElement, setTriggerValue } = component;
            const root = parentElement.querySelector("#placement-root");
            const ns = "http://www.w3.org/2000/svg";
            const svg = document.createElementNS(ns, "svg");
            svg.setAttribute("viewBox", "-0.55 -0.25 11 10.8");
            svg.setAttribute("aria-label", "Initial unit placement map");

            for (let i = 0; i <= 10; i += 1) {
                for (const vertical of [true, false]) {
                    const line = document.createElementNS(ns, "line");
                    line.setAttribute("class", "grid");
                    line.setAttribute("x1", vertical ? i : 0);
                    line.setAttribute("x2", vertical ? i : 10);
                    line.setAttribute("y1", vertical ? 0 : i);
                    line.setAttribute("y2", vertical ? 10 : i);
                    svg.appendChild(line);
                }
                const xLabel = document.createElementNS(ns, "text");
                xLabel.setAttribute("class", "axis-label");
                xLabel.setAttribute("x", i);
                xLabel.setAttribute("y", 10.45);
                xLabel.setAttribute("text-anchor", "middle");
                xLabel.textContent = String(i);
                svg.appendChild(xLabel);

                const yLabel = document.createElementNS(ns, "text");
                yLabel.setAttribute("class", "axis-label");
                yLabel.setAttribute("x", -0.18);
                yLabel.setAttribute("y", 10 - i + 0.1);
                yLabel.setAttribute("text-anchor", "end");
                yLabel.textContent = String(i);
                svg.appendChild(yLabel);
            }

            data.positions.forEach((position, index) => {
                const circle = document.createElementNS(ns, "circle");
                circle.setAttribute(
                    "class",
                    index === data.selected ? "unit selected" : "unit"
                );
                circle.setAttribute("cx", position.x);
                circle.setAttribute("cy", 10 - position.y);
                circle.setAttribute("r", index === data.selected ? 0.34 : 0.27);
                circle.setAttribute(
                    "fill",
                    position.team === "Army 1" ? "#e05252" : "#3977d4"
                );
                svg.appendChild(circle);

                const label = document.createElementNS(ns, "text");
                label.setAttribute("class", "unit-label");
                label.setAttribute("x", position.x);
                label.setAttribute("y", 10 - position.y);
                label.textContent = String(index + 1);
                svg.appendChild(label);
            });

            svg.onpointerdown = (event) => {
                const point = svg.createSVGPoint();
                point.x = event.clientX;
                point.y = event.clientY;
                const local = point.matrixTransform(svg.getScreenCTM().inverse());
                const x = Math.max(0, Math.min(10, local.x));
                const y = Math.max(0, Math.min(10, 10 - local.y));
                setTriggerValue("place", {
                    x: Math.round(x * 100) / 100,
                    y: Math.round(y * 100) / 100,
                    event_id: `${Date.now()}-${event.pointerId}`,
                });
            };

            root.replaceChildren(svg);
        }
    """,
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
    placement_rows: list[dict[str, object]],
) -> bsm.BattleScenario:
    validated_rows = bsm.validate_placement_rows(
        placement_rows,
        bounds=_BATTLE_BOUNDS,
    )
    left_positions = tuple((row["x"], row["y"]) for row in validated_rows[:left_count])
    right_positions = tuple((row["x"], row["y"]) for row in validated_rows[left_count:])
    return bsm.BattleScenario(
        armies=(
            bsm.ArmySpec(
                left_unit,
                left_count,
                initial_positions=left_positions,
            ),
            bsm.ArmySpec(
                right_unit,
                right_count,
                initial_positions=right_positions,
            ),
        ),
        bounds=_BATTLE_BOUNDS,
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

    placement_rows: list[dict[str, object]] = []
    if scenario_preset == "Custom battle":
        placement_signature = (
            left_unit,
            int(left_count),
            right_unit,
            int(right_count),
        )
        if st.session_state.get("placement_signature") != placement_signature:
            st.session_state["placement_signature"] = placement_signature
            st.session_state["placement_rows"] = bsm.initial_placement_rows(
                *placement_signature
            )
            st.session_state["placement_revision"] = (
                int(st.session_state.get("placement_revision", 0)) + 1
            )

        st.subheader("Initial placement")
        st.caption(
            "X/Yを直接編集するか、unitを選んで戦場をクリックしてください。"
            "座標範囲は0〜10です。"
        )
        editor_column, map_column = st.columns([3, 4], gap="large")
        with editor_column:
            placement_frame = pd.DataFrame(st.session_state["placement_rows"])
            edited_frame = st.data_editor(
                placement_frame,
                column_order=("No.", "Team", "Type", "X", "Y"),
                column_config={
                    "No.": st.column_config.NumberColumn("No.", disabled=True),
                    "Team": st.column_config.TextColumn("Team", disabled=True),
                    "Type": st.column_config.TextColumn("Type", disabled=True),
                    "X": st.column_config.NumberColumn(
                        "X",
                        min_value=_BATTLE_BOUNDS[0],
                        max_value=_BATTLE_BOUNDS[1],
                        step=0.1,
                        format="%.2f",
                        required=True,
                    ),
                    "Y": st.column_config.NumberColumn(
                        "Y",
                        min_value=_BATTLE_BOUNDS[2],
                        max_value=_BATTLE_BOUNDS[3],
                        step=0.1,
                        format="%.2f",
                        required=True,
                    ),
                },
                disabled=("No.", "Team", "Type"),
                hide_index=True,
                width="stretch",
                height=420,
                key=f"placement_editor_{st.session_state['placement_revision']}",
            )
            placement_rows = cast(
                list[dict[str, object]],
                edited_frame.to_dict(orient="records"),
            )
            st.session_state["placement_rows"] = placement_rows
            unit_labels = [
                f"#{row['No.']} · {row['Team']} · {row['Type']}"
                for row in placement_rows
            ]
            selected_label = st.selectbox(
                "Mouse placement unit",
                unit_labels,
                key="placement_unit",
            )
            selected_index = unit_labels.index(selected_label)

        with map_column:
            try:
                validated_positions = bsm.validate_placement_rows(
                    placement_rows,
                    bounds=_BATTLE_BOUNDS,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                placement_result = _PLACEMENT_COMPONENT(
                    data={
                        "selected": selected_index,
                        "positions": [
                            {
                                "x": position["x"],
                                "y": position["y"],
                                "team": placement_rows[index]["Team"],
                            }
                            for index, position in enumerate(validated_positions)
                        ],
                    },
                    key="placement_map",
                    height=520,
                    on_place_change=lambda: None,
                )
                placed = placement_result.place
                if placed and placed.get("event_id") != st.session_state.get(
                    "last_placement_event"
                ):
                    st.session_state["last_placement_event"] = placed["event_id"]
                    st.session_state["placement_rows"] = bsm.apply_mouse_placement(
                        placement_rows,
                        selected_index,
                        placed.get("x"),
                        placed.get("y"),
                        bounds=_BATTLE_BOUNDS,
                    )
                    st.session_state["placement_revision"] += 1
                    st.rerun()

    run_simulation = st.button("Run simulation", type="primary", key="run")

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
                placement_rows,
            )
        try:
            new_battle = scenario.run()
        except Exception as error:
            st.exception(error)
        else:
            st.session_state["battle"] = new_battle
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
