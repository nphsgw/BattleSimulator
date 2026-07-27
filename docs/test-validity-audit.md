# Test Validity Audit

## Scope And Method

2026-07-27に `tests/test_*.py` の全12ファイルを、次の観点で棚卸しした。

- `docs/` の仕様、不変条件、または再現ケースへ対応付けられるか
- 期待値が検査対象のproduction pathから独立しているか
- 正常終了だけでなく、結果、境界、異常入力、metamorphic relationを検査するか
- mockやsnapshotが検査対象そのものを正解としていないか
- 代表的な誤実装を失敗として検出できるか

棚卸し前の全体テストは124件が成功し、実測24.82秒だった。起動等を含む
コマンド全体は28.43秒で、200-unit battleを含む30秒の初期予算内だった。

## File Audit

| Test file | Primary basis | Assessment and disposition |
|---|---|---|
| `test_app.py` | `visualization-rules.md` | 固定入力によるUI操作と入力拒否を検査する。画像の意味までは主張しないsmoke testとして妥当 |
| `test_battle.py` | `current-spec.md`, public API change policy | 到達不能だった不正入力ケースをparameterizeし、army構成、frame schema、result provenanceのassertionを追加 |
| `test_composite.py` | `model-contract.md` | 生成できることだけを見ていたため、明示した全army設定が保持される契約テストへ置換 |
| `test_dataset.py` | `dataset-contract.md` | Wilson区間を手計算値で検査し、summaryとsensitivityを制御した結果から数値検査するよう補強 |
| `test_input_validation.py` | input boundary rules | strict type、未知キー、境界、有限性、cross-field制約を直接検査しており妥当 |
| `test_plot.py` | `visualization-rules.md` | rendererの戻り値、引数伝播、artist labelを検査する。pixel一致を保証しない方針と整合 |
| `test_scenario.py` | `model-contract.md`, `current-spec.md` | 固定scenario、明示配置、scenario IDを具体値・関係で検査しており妥当 |
| `test_simulation.py` | `simulation-rules.md` legacy rules | 手作りmatrixでdamage、target、射程、frameを検査する。index順テストはlegacy kernel限定でありrules v1の同時解決とは競合しない |
| `test_tactical.py` | `simulation-rules.md`, `model-contract.md`, `validation-plan.md` | deterministic、metamorphic、statistical、micro scenarioを併用。RNG stream分離とresult version契約を追加 |
| `test_targeting.py` | `simulation-rules.md` | 小さな固定matrixと尺度変換でabsolute index、durability、doctrineを検査しており妥当 |
| `test_terrain.py` | `simulation-rules.md`, `current-spec.md` | 不正入力と固定関数によるshape・有限性・flat化を検査しており妥当 |
| `test_viewmodel.py` | `visualization-rules.md` | 手書きframeから独立した期待値を検査しており妥当 |

今回確認した範囲に、production helperで同じ値を計算する明白な自己証明テストは
残っていない。baseline distributionは引き続き変更検出器に限定し、現実妥当性の
証拠にはしない。

## Focused Mutation Trial

一時mutationを1件ずつ適用し、下表の対象テストが失敗した後、production codeを
元へ戻した。mutationはcommit対象に含めていない。

| Fault | Mutated behavior | Killing test |
|---|---|---|
| seed無視 | `Battle`が指定seedの代わりに常に0を保存 | `test_different_seeds_produce_non_degenerate_outcomes`, `test_result_records_version_seed_and_termination_contract` |
| 登録順依存 | scenario ID生成時のComposite sortを除去 | `test_composite_registration_order_does_not_change_aggregate_result` |
| 境界比較 | boundsの`>=`拒否を`>`へ弱体化 | `test_bounds_must_be_ordered_and_non_degenerate` |
| 非有限値受理 | external inputのpositive floatから`FiniteFloat`を除去 | `test_non_finite_terrain_resolution_is_rejected` |
| 乱数系列共有 | 全subsystemへ同一Generator instanceを割り当て | `test_named_random_streams_are_isolated_between_subsystems` |
| version欠落 | resultの`rules_version`を空文字へ変更 | `test_result_records_version_seed_and_termination_contract` |
| 終了理由固定 | resultの終了理由を常に`timeout`へ変更 | `test_simultaneous_damage_allows_mutual_destruction`, `test_timeout_and_stalemate_are_distinct` |

境界と有限性のmutationはexternal Pydantic modelを通過した後にdomain validationで
拒否されたが、テストは信頼境界での拒否型が変わったことも検出した。これは境界で
一度検証する契約を守るための意味のある失敗である。

## Mutation Tool Decision

候補は `mutmut 3.6.0`、Cosmic Ray、Mutatestとした。

- Mutatest 3.1.0は公式文書上Python 3.7/3.8を対象とするため、Python 3.12以上を
  前提とする本プロジェクトでは除外した。
- `mutmut 3.6.0`はPython 3.12とpytest、対象pathの限定、incremental実行を
  サポートするため第一候補とした。`randomness.py`, `contracts.py`,
  `_scenario_input.py`を対象に実試行したが、mutmutの同一process内pytest実行で
  NumPy再importが発生し、baseline収集が
  `ImportError: cannot load module more than once per process` で失敗した。
- Cosmic Rayはtest commandをmutationごとに実行できるが、session管理とtimeout設定が
  必要である。対象pytestの起動だけで約2秒、全体suiteは約25秒のため、広い対象を
  local distributorで回すと通常CI予算を大幅に超える。distributed実行にはmutant
  ごとに独立したsource copyも必要となる。

このため現時点ではmutation dependency、`make` target、scheduled CIを追加しない。
重要変更では上表と同じ局所的な手動fault injectionを行い、変更説明へ結果を残す。
自動化を再評価する条件は次とする。

- NumPyを利用するpytest suiteを安定して分離実行できる
- 対象moduleと関連testを限定したpilotが5分以内に完了する
- equivalent mutationとNumba生成物を除外できる
- survivorを件数だけでなく意味の有無で分類して記録できる

初期の自動化対象は純Pythonの `randomness.py`, `contracts.py`,
`_scenario_input.py` とし、Numba/legacy kernel、renderer、UI、生成物は除外する。
