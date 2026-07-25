# Current BattleSimulator Specification

## Purpose
この文書は、現時点の BattleSimulator 実装が持つ仕様を日本語で整理したものである。
実装の事実を優先して記述し、将来の理想仕様ではなく「今どう動くか」をまとめる。

## Package Overview
- パッケージ名は `battlesim`
- 主な公開 API は `Battle`, `Composite`, `Sampling`, `Terrain`
- シミュレーション本体は `battlesim/simulation/` 配下にある
- 描画機能は `battlesim/plot/` 配下にある
- 地形生成は `battlesim/terra/` 配下にある

## Public API

### `Battle`
戦闘シミュレーション全体を管理する中心オブジェクト。

主な責務:
- ユニットデータベースの読み込みと前処理
- 軍構成の受け取り
- シミュレーション用行列の生成
- 地形の生成と適用
- 戦闘シミュレーションの実行
- 結果の描画やエクスポート

主な初期化引数:
- `db`
  型: `str | dict | pandas.DataFrame`
  内容: ユニット定義のデータソース
- `bounds`
  型: `(xmin, xmax, ymin, ymax)` の 4 要素タプル
- `use_tqdm`
  型: `bool`
  内容: `simulate_k()` の進捗表示に `tqdm` を使うかどうか
- `seed`
  型: `int | None`
  内容: 配置、地形、target、命中などの名前付き乱数系列のroot seed
- `rules`
  型: `BattleRules | None`
  内容: tick、終了条件、空間ルール、objectiveを含むrules version 1設定

主な公開メソッド:
- `create_army(army_set)`
  `Composite` の list を受け取り、軍構成を設定する。
  構成を変更した場合は以前の内部行列とシミュレーション結果を破棄する
- `apply_terrain(t=None, res=0.1)`
  地形の見た目または `Terrain` オブジェクトを設定する
- `set_bounds(bounds)`
  戦場範囲を設定する
- `simulate(verbose=0, *, seed=None, rules=None)`
  1 回の戦闘を実行し、フレーム列を返す
- `simulate_k(k=10, *, seed=None, randomize=("combat",))`
  複数回の戦闘を実行し、各陣営の残存数を DataFrame で返す
- `sim_jupyter(func=quiver_fight, create_html=False)`
  Jupyter 向けアニメーションオブジェクトまたは HTML を返す
- `sim_export(filename="example_sim.gif", func=quiver_fight, writer="pillow")`
  戦闘アニメーションを GIF として保存する

主な公開プロパティ:
- `db_`
  前処理済みのユニット DataFrame
- `M_`
  シミュレーション用の内部構造化 NumPy 配列
- `sim_`
  直近のシミュレーション結果
- `result_`
  直近のversion付き `BattleResult`
- `results_`
  `simulate_k()` が生成した `BattleResult` のtuple
- `T_`
  現在の `Terrain`
- `composition_`
  現在の `Composite` list
- `army_set_`
  `(ユニット名, 数)` のタプル列
- `n_armies_`
  軍の種類数
- `n_allegiance_`
  陣営ごとの総ユニット数
- `allegiances_`
  現在の軍構成に参加する陣営 ID と陣営名の対応
- `bounds_`
  戦場範囲。軍構成の作成前でも参照できる

### `Composite`
1 種類のユニット群を表す設定オブジェクト。

主要フィールド:
- `name`
  ユニット名
- `n`
  生成数
- `pos`
  初期位置サンプリング設定
- `init_ai`
  初期ターゲット選択方針。`random`, `nearest`, `close_weak` に対応する
- `rolling_ai`
  現在対象の死亡後に使うターゲット再選択方針。
  `random`, `nearest`, `close_weak` に対応する
- `decision_ai`
  戦闘行動方針

注意:
- `init_ai`, `rolling_ai`, `decision_ai`, `pos` はすべて戦闘処理へ使用される

### `Sampling`
NumPy の乱数分布をラップするクラス。

対応分布:
- `beta`
- `binomial`
- `chisquare`
- `exponential`
- `laplace`
- `lognormal`
- `normal`
- `uniform`

主な動作:
- `Sampling(name, *args)` で分布名と引数を保持する
- `sample(n, rng=None)` で長さ `n` の 1 次元配列を返す
- `Composite` の初期座標生成に使う

### `Terrain`
戦場の範囲、解像度、高さマップ、描画方法を表すクラス。

主な初期化引数:
- `dim`
  `(xmin, xmax, ymin, ymax)`
- `res`
  地形解像度
- `form`
  `None`, `"grid"`, `"contour"` のいずれか
- `dtype`
  現状は `"perlin"` 前提

主な動作:
- `generate()`
  高さマップを生成する
- `plot(ax=None, **kwargs)`
  地形を描画する

重要な現行仕様:
- `form=None` は「フラット地形」を意味する
- この場合、`Z_` はすべて 0 の高さマップになる
- `form="grid"` または `"contour"` で `generate()` すると、Perlin ノイズをベースにした高さマップを生成する

## Unit Database Specification

### Accepted Input Types
`Battle(db=...)` の `db` は以下を受け取る。
- CSV ファイルパス
- Python `dict`
- `pandas.DataFrame`

### Required Columns
ユニット定義には次の列が必要:
- `Name`
- `Allegiance`
- `HP`
- `Armor`
- `Damage`
- `Accuracy`
- `Miss`
- `Movement Speed`
- `Range`

### Preprocessing
読み込み後に以下の前処理が行われる。
- `Name` 列を index に設定する
- `Allegiance` を整数化して `allegiance_int` 列を追加する
- `Battle` 初期化時に index を小文字化する

### Default Database
`Battle()` を引数なしで呼ぶと、内蔵の Star Wars 系データを使う。
このデフォルトデータには次のようなユニットが含まれる。
- Local Militia
- B1 battledroid
- Clone Trooper
- ARC Trooper
- BX-series droid commando
- Magmaguard

## Internal Battle State

### Main Matrix `M_`
戦闘処理の中心は構造化 NumPy 配列 `M_` である。
現時点の主要列:
- `id`
  Composite 単位のグループ ID
- `target`
  現在の攻撃対象の unit index
- `x`, `y`
  現在位置
- `hp`
  体力
- `armor`
  装甲値
- `dmg`
  ダメージ
- `range`
  射程
- `speed`
  移動速度
- `acc`
  命中率
- `dodge`
  回避率。後方互換列 `Miss` を 100 で割った値
- `utype`
  ユニット種別 ID
- `team`
  陣営 ID
- `ai_func_index`
  行動 AI の整数 ID
- `target_ai_func_index`
  対象死亡後に使うターゲット再選択 AI の整数 ID
- `stable_id`
  Composite登録順に依存しないtarget tie-break、event actor ID
- `cooldown`, `attack_interval`, `radius`, `move_factor`
  攻撃間隔と円形占有半径
- `threat_*_weight`
  distance、durability、expected damage、objective importanceのdoctrine重み

### Team And Group Semantics
- `team` は陣営を表す
- `id` は同一 Composite から生成されたユニット群を表す
- 初期ターゲットはグループごとに一括割り当てされる
- ターゲット値は敵配列内の相対位置ではなく、`M` 全体の absolute index を保持する

## Simulation Flow

### High-Level Flow
`Battle.simulate()` の流れは次の通り:
1. 軍構成が設定済みか確認する
2. 2 陣営以上あるか確認する
3. `M_` を再構築する
4. 地形を生成する
5. rules version 1 の `simulate_tactical()` を呼ぶ
6. フレーム列を `sim_`、構造化結果を `result_` に保存する
7. 従来どおりフレーム列を返す

### Repeated Simulation
`simulate_k(k)` は:
1. root seedからtrial seedを決定論的に導出する
2. `randomize` に指定された配置、地形、combatだけをtrialごとに再生成する
3. `k` 回戦闘を繰り返し、構造化結果を `results_` に保存する
4. 互換性のため、各陣営の生存数を DataFrame で返す

現仕様では、`simulate_k()` は各試行の勝敗ラベルではなく、各陣営の残存数を返す。

### Early Halt Conditions
以下の場合は戦闘を進めず警告を出して終了する。
- 参加陣営が 1 つ以下

## Targeting Specification

### Per-Unit Target Selection
戦闘中の個別ターゲット選択関数:
- `random`
  生存中の敵からランダムに選ぶ
- `nearest`
  最も近い敵を選ぶ
- `close_weak`
  候補内で正規化した距離と残存耐久力（HP + armor）を混ぜて、
  近くて倒しやすい敵を選ぶ
- `weakest`
  残存HPとarmorが最小の敵を選ぶ
- `highest_threat`
  正規化したdistance、durability、expected damage、objective importanceと
  Compositeのdoctrine重みで選ぶ
- `focus_fire`
  味方が最も多くtarget中の敵を優先する
- `objective_priority`
  objectiveに近い敵を優先する

### Group-Level Initial Targeting
グループ単位の初期ターゲット選択関数:
- `global_random`
- `global_nearest`
- `global_close_weak`
- `global_weakest`
- `global_highest_threat`
- `global_focus_fire`
- `global_objective_priority`

これらはlegacy低レベルAPIとして維持する。rules version 1 の`Battle`は
同じ方針をstable ID tie-break付きの決定論的初期化処理で適用する。

### Current Runtime Behavior
- 戦闘中に現在ターゲットが死亡していたら `_select_enemy()` で再選択する
- 再選択時にはそのユニットの `rolling_ai` と候補敵集合が使われる
- 候補は再選択時点で生存している敵に限定される
- 再選択した tick では、新しいターゲットへの距離、方向、高低差を使って行動する
- データベース全体で割り当てられた陣営 ID が非連続でも動作する
- rules version 1 の `nearest` は暗黙のdistance noiseを加えない
- 同点時は入力順でなくstable unit IDで決定する

## AI Specification

### Available Decision AIs
現時点で主実装に組み込まれている AI:
- `aggressive`
- `hit_and_run`

`defensive` は定義されているが未実装で、`NotImplementedError` を送出する。

### `aggressive`
rules version 1:
- 射程外なら対象へ接近する
- 全unitの移動と衝突解決後、射程・射線・命中を判定する

legacy低レベルAIでは、5%の強制前進判定と命中判定に独立乱数を使う。

### `hit_and_run`
rules version 1:
- 自分の速度と射程が相手より有利なら hit-and-run を行う
- 射程外なら接近
- 相手の射程内に入りすぎたら後退
- 境界で直接後退できなければ横移動を試し、移動後に射程内なら攻撃する
- 優位でない場合は `aggressive` にフォールバックする

legacy低レベルAIでは従来の絶対標高による実効射程式を維持する。

## Movement Specification

### Core Rule
移動は対象方向または対象反対方向への直線移動である。

使われる要素:
- 現在の位置差分
- 対象までの距離
- ユニットの速度
- 地形による移動補正

対象へ接近する移動量は射程境界を越えない。全unitの移動線分を比較し、
終点が離れていても途中で交差するunitを接触時刻の直前で停止させる。

### Terrain Effect On Movement
rules version 1では、移動元と移動先の標高差が上りの場合だけ
`1 / (1 + rise)` を移動量へ掛ける。legacy低レベルAIでは
`speed * (1 - z_i / 2)` を維持する。

## Hit And Damage Specification

### Hit Chance
命中率は以下の考え方で計算される。
- `accuracy`
- 相手の `dodge`
- 距離によるペナルティ

現行式:
- `distance_factor = 1 - 0.5 * distance / effective_range`
- `hit_chance = acc * (1 - dodge) * distance_factor`

攻撃判定は実効射程内でのみ行われるため、距離係数は射手直上で 1、
射程限界で 0.5 となる。計算結果は `[0, 1]` へ制限する。

データベース列 `Miss` は歴史的な列名として維持する。
値はそのユニットが攻撃対象になったときの回避率であり、攻撃者自身の
ミス率ではない。

### Tick Resolution
- tick開始時のsnapshotから全unitのtarget、移動、攻撃予定を計算する
- 移動予定を一括反映し、unit radiusによる位置競合を解消する
- 移動後位置から射程とline-of-sightを判定する
- 命中したdamageは予約し、tick終了時に対象単位で合算して適用する
- tick開始時に生存していたunitは、同tick内で攻撃されても予定攻撃を実行する
- 配列順でなくstable unit ID順に乱数keyを割り当てるため、相打ちと登録順不変性を表現できる
- 互換用の低レベル `_loop_units()` はlegacy逐次方式のまま残る

### Attack Timing
- 任意列 `Attack Interval` を攻撃間隔tick数として使い、省略時は1
- 攻撃後はcooldownを設定し、0になったtickに再攻撃できる

### Damage
基本ダメージは地形高低差補正を含む。

現行式:
- `base_damage * (((z_i - z_j) / 2) + 1)`

### Armor Handling
- 相手の `armor` が残っている場合、まず装甲へダメージを与える
- 装甲を超過した分だけ `hp` が減る
- 装甲がない場合は `hp` を直接減らす
- ダメージ適用後の `armor` の下限は 0 とする

## Terrain Specification

### Bounds
地形は戦場範囲 `bounds_` を持つ。
境界外へ出ないよう、シミュレーションループ内で位置補正が入る。
コンストラクタまたは `set_bounds()` で指定した範囲は最小範囲として維持する。
初期配置が範囲外にある場合は、その unit を含む方向だけ bounds を拡張し、
自動拡張したことを `UserWarning` で通知する。

### Forms
- `None`
  フラット地形
- `"grid"`
  格子状表示
- `"contour"`
  等高線表示

### Height Map Generation
- `form=None` の場合はゼロ配列
- それ以外では、Perlin ノイズベースの高さマップを生成する
- `generate(f=...)` では戦場範囲と解像度に対応する座標 grid を `f` へ渡す
- `f` が一定値の map を返した場合は、0 のフラット地形へ正規化する

### Terrain Effect Summary
地形は以下へ影響する。
- 移動速度
- line-of-sight
- ダメージ

rules version 1 の移動補正は移動先への上り勾配から計算する。
中間地形が視線より高い場合は射撃できない。`CoverZone` 内のtargetには
指定された命中率倍率を適用する。
legacy低レベルAIでは従来の絶対標高による射程・移動補正を維持する。
戦場 bounds の最大座標を含め、座標は常に有効な地形 tile index へ写像される。

## Output Specification

### `simulate()`
戻り値はフレーム列の構造化 NumPy 配列。

- frame 0 は tick 解決前の初期状態
- 以後は各 tick 解決後の状態
- 最大 tick へ到達した場合も最後の更新後状態を含む
- したがって最大フレーム数は `max_step + 1`

主な列:
- `x`
- `y`
- `target`
- `hp`
- `armor`
- `ddx`
- `ddy`
- `team`
- `utype`
- `z`
- `target_z`
- `move_factor`
- `effective_range`
- `damage_factor`
- `density`

### `simulate_k()`
戻り値は `pandas.DataFrame`。

列:
- 各陣営名

値:
- 各試行終了時の生存ユニット数

構造化結果は `results_` に保存され、seed、trial ID、終了理由、各teamの
残存戦力とcombat metricsを取得できる。

### `BattleResult`
- `scenario_id`, `trial_id`, seedと各version
- tick数、`termination_reason`, 0件以上の`winner_team_ids`
- team別の初期・残存unit数、HP、armor、damage、shot、hit、kill、移動距離
- 高所・cover・objective占有時間、空間的分散、損耗交換比
- fixed-lengthのscenario input featuresとtrialごとのrandomized subsystem
- `move`, `shot`, `hit`, `damage`, `kill`, `target`, `objective` event

### Dataset And Validation
- `run_batch()` はscenario familyごとのtrialを実行し、trial IDで再開・重複排除する
- `export_results()` はCSV、JSONL、Parquetへversion付き集約値を保存する
- `scenario_family_partition()` はfamilyをtrain/validation/test/OODへ固定分割する
- `wilson_interval()` と `monte_carlo_summary()` は勝率の不確実性を返す
- `validate_results()` はversion混在、重複、不正な状態量を検出する
- `sensitivity_analysis()` と `surrogate_frame()` は初期の代理モデル検証・入力を提供する

## Plotting And Export

### Jupyter Animation
`sim_jupyter()` は `quiver_fight()` を使ったアニメーションオブジェクトを返す。
`create_html=True` の場合は `to_jshtml()` の結果を返す。

可視化関数は `func=` で差し替えできる。
現時点で確認済みの代表例:
- `func=quiver_fight_debug`
- `func=partial(quiver_fight_debug, show_terrain_text=True)`

### GIF Export
`sim_export()` は `.gif` 拡張子を補完し、Matplotlib animation の `save()` を使って出力する。
既定 writer は `pillow`。

`sim_export()` も `func=` で debug view を受け取れる。

### Visual Representation
`quiver_fight()` では:
- 生存ユニットは矢印
- 死亡ユニットは `x`
- 陣営ごとに色分け

`quiver_fight_debug()` では、上記に加えて次を扱う。
- HP バー
- target line
- overlay の on/off 切り替え
- 地形由来の補助テキスト overlay

主な追加引数:
- `show_hp`
- `show_target_lines`
- `show_terrain_text`
- `interval`

### Notebook Interaction
`examples/debug-visualization.ipynb` は debug animation の利用例である。
現時点では `ipywidgets` による操作 UI は実装されておらず、描画関数へ渡す引数をコードセルで切り替える。

可視化の主要機能は notebook の実行状態に依存させず、通常の Python API として提供する。
notebook は教材、探索、利用例として扱う。

### Local Web UI
`apps/battle_viewer.py` は Streamlit によるローカル Web UI である。

主な操作:
- 2 つの unit group と unit 数の選択
- 地形 form の選択
- シミュレーション実行
- 再生、一時停止、先頭から再生
- 再生速度の選択
- frame slider
- target line の表示切り替え
- 表示中 frame の PNG download

UI は戦闘ロジックや描画ロジックを実装せず、`BattleScenario` と
`quiver_frame_debug()` を呼び出す interface として扱う。

`Run simulation` は全 frame の計算後、frame 0 から表示上の自動再生を開始する。
再生は保存済み frame の表示位置だけを進め、simulation 自体を再実行しない。

戦闘画面には unit index を基準にした `#1`, `#2`, ... の番号を表示する。
同じ番号を右側の unit parameter panel で使用し、現在 frame の次の情報を表示する。

- team
- unit type
- alive / dead
- HP
- armor
- target number
- `z`
- `move_factor`
- `effective_range`
- `damage_factor`

ローカル Web UI では HP bar と terrain text を戦闘画面へ重畳しない。
これらは既存描画 API の互換機能としては維持する。

### Static Rendering CLI
`battlesim-render` は TOML scenario を実行し、指定 frame を画像へ保存する。
既定では最終 frame を描画する。

同梱 scenario:
- `scenarios/clone-vs-droid.toml`

### Visualization View Model
`build_frame_view()` は構造化 NumPy frame を UI 非依存の `FrameView` へ変換する。
各 `UnitView` は次の表示用情報を保持する。

- 位置、向き、team、unit type
- HP、最大 HP、HP 比率、生死
- target index と target 座標
- frame に存在する場合は地形補助値

### Planned Visualization Direction
独自拡張では、通常表示とデバッグ表示を分けて扱う方針を取る。

- 通常表示
  現行の `quiver_fight()` に近い軽量表示を維持する
- デバッグ表示
  HP、target line、地形補助情報を重ねて、個々のユニット挙動を解析しやすくする

デバッグ表示で優先的に扱う候補は次の通り。
- ユニット単位: HP, target, unit type, alive/dead
- 地形由来: 地形高さ, 移動補正, 実効射程, 高低差ダメージ補正

詳細方針は `docs/visualization-rules.md` を参照する。

### Notebook-Independent Direction
今後の可視化は次の層へ分離する。

- simulation frame
- UI framework に依存しない view model
- Matplotlib renderer
- CLI / ローカル Web UI / notebook などの interface

既存の `sim_jupyter()` は後方互換性のため維持するが、主要な操作導線はローカル Web UI へ移す。

## Validation And Error Behavior

### Typical Runtime Errors
- `create_army()` 前に軍構成へ依存するプロパティへアクセスすると `AttributeError`
- 不正な地形 form や bounds を指定すると `AttributeError` または `TypeError`
- 未対応の地形 dtype を指定すると `ValueError`
- 不正なデータベース形式を渡すと `ValueError`

### Input Validation Examples
- `create_army()` は `Composite` の list / tuple 以外を拒否する
- `create_army()` は空の構成、1 未満の unit 数、データベースにない unit 名、
  未対応の `init_ai`, `rolling_ai`, `decision_ai` を拒否する
- `Terrain.res_` は `float` で、極小値未満は拒否する
- ユニットデータには必須列がそろっている必要がある
- unit 名は空でなく、大文字小文字を無視して一意である必要がある
- unit 数値列は有限の数値である必要がある
- `HP > 0`, `Armor >= 0`, `Damage >= 0`
- `Accuracy` と `Miss` は 0..100
- `Movement Speed >= 0`, `Range > 0`
- 任意の `Attack Interval >= 1`, `Radius > 0`

## Known Limitations
- `AI.defensive` は未実装
- rules version 1 のcollisionは円形unitのsoft separationであり、経路計画ではない
- line-of-sightは地形標本化であり、建物meshや弾丸飛翔は扱わない
- 初期の代理モデル出力は固定長集約値で、sequence/graph表現は未実装
- rules version 1 のreference kernelは監査可能性を優先し、legacy Numba kernelほど
  大規模unit数へ最適化されていない
- ノートブックや教材コードには本体仕様と一致しない説明が残る可能性がある
- 仕様文書は現実装に基づくため、将来変更時はこの文書も更新が必要

## Recommended Source Of Truth
この仕様を変更する場合は、少なくとも以下を同時に更新する。
- この文書
- `docs/simulation-rules.md`
- 関連テスト
- 必要なら `README.rst`
