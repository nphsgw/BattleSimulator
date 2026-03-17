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

主な公開メソッド:
- `create_army(army_set)`
  `Composite` の list を受け取り、軍構成を設定する
- `apply_terrain(t=None, res=0.1)`
  地形の見た目または `Terrain` オブジェクトを設定する
- `set_bounds(bounds)`
  戦場範囲を設定する
- `simulate(verbose=0)`
  1 回の戦闘を実行し、フレーム列を返す
- `simulate_k(k=10)`
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
  陣営 ID と陣営名の対応
- `bounds_`
  戦場範囲

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
  初期ターゲット選択方針
- `rolling_ai`
  戦闘中のターゲット選択方針
- `decision_ai`
  戦闘行動方針

注意:
- 現時点で実際に戦闘処理へ使われているのは主に `decision_ai` と `pos`
- `init_ai` と `rolling_ai` は API 上は保持されるが、現在の主実装では積極的には使われていない

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
- `sample(n)` で長さ `n` の 1 次元配列を返す
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
  回避率
- `utype`
  ユニット種別 ID
- `team`
  陣営 ID
- `ai_func_index`
  行動 AI の整数 ID

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
5. `simulate_battle()` を呼ぶ
6. フレーム列を `sim_` に保存して返す

### Repeated Simulation
`simulate_k(k)` は:
1. `M_` を初期状態へ構築する
2. 地形を生成する
3. 同一条件で `k` 回戦闘を繰り返す
4. 各陣営の生存数を DataFrame で返す

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
  距離と HP を混ぜて評価し、近くて弱い敵を選ぶ

### Group-Level Initial Targeting
グループ単位の初期ターゲット選択関数:
- `global_random`
- `global_nearest`
- `global_close_weak`

現実装で初期ターゲット割り当てに使っているのは `global_nearest`。

### Current Runtime Behavior
- 戦闘中に現在ターゲットが死亡していたら `_select_enemy()` で再選択する
- 再選択時にはそのユニットから見た候補敵集合が使われる

## AI Specification

### Available Decision AIs
現時点で主実装に組み込まれている AI:
- `aggressive`
- `hit_and_run`

`defensive` は定義されているが未実装で、`NotImplementedError` を送出する。

### `aggressive`
基本方針:
- 射程外なら対象へ接近する
- ただし 5% の確率で、射程内でも前進側の挙動を取る
- 射程内なら命中判定を行い、成功時にダメージを与える

### `hit_and_run`
基本方針:
- 自分の速度と射程が相手より有利なら hit-and-run を行う
- 射程外なら接近
- 相手の射程内に入りすぎたら後退
- 自分だけが射程内なら攻撃
- 優位でない場合は `aggressive` にフォールバックする

## Movement Specification

### Core Rule
移動は対象方向または対象反対方向への直線移動である。

使われる要素:
- 現在の位置差分
- 対象までの距離
- ユニットの速度
- 地形による移動補正

### Terrain Effect On Movement
移動量は概ね次の形で補正される。
- `speed * (1 - z_i / 2)`

つまり高所ほど移動速度が落ちる方向の補正が入る。

## Hit And Damage Specification

### Hit Chance
命中率は以下の考え方で計算される。
- `accuracy`
- 相手の `dodge`
- 距離によるペナルティ

現行式:
- `acc * (1 - dodge) * (1 - distance / global_penalty)`

`global_penalty` の既定値は `15.0`。

### Damage
基本ダメージは地形高低差補正を含む。

現行式:
- `base_damage * (((z_i - z_j) / 2) + 1)`

### Armor Handling
- 相手の `armor` が残っている場合、まず装甲へダメージを与える
- 装甲を超過した分だけ `hp` が減る
- 装甲がない場合は `hp` を直接減らす

## Terrain Specification

### Bounds
地形は戦場範囲 `bounds_` を持つ。
境界外へ出ないよう、シミュレーションループ内で位置補正が入る。

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

### Terrain Effect Summary
地形は以下へ影響する。
- 移動速度
- 射程
- ダメージ

現行実装では、AI 内で高低差をもとに射程やダメージが補正される。

## Output Specification

### `simulate()`
戻り値はフレーム列の構造化 NumPy 配列。

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

### `simulate_k()`
戻り値は `pandas.DataFrame`。

列:
- 各陣営名

値:
- 各試行終了時の生存ユニット数

## Plotting And Export

### Jupyter Animation
`sim_jupyter()` は `quiver_fight()` を使ったアニメーションオブジェクトを返す。
`create_html=True` の場合は `to_jshtml()` の結果を返す。

### GIF Export
`sim_export()` は `.gif` 拡張子を補完し、Matplotlib animation の `save()` を使って出力する。
既定 writer は `pillow`。

### Visual Representation
`quiver_fight()` では:
- 生存ユニットは矢印
- 死亡ユニットは `x`
- 陣営ごとに色分け

## Validation And Error Behavior

### Typical Runtime Errors
- `create_army()` 前に戦闘関連プロパティへアクセスすると `AttributeError`
- 不正な地形 form や bounds を指定すると `AttributeError` または `TypeError`
- 不正なデータベース形式を渡すと `ValueError`

### Input Validation Examples
- `create_army()` は `Composite` の list / tuple 以外を拒否する
- `Terrain.res_` は `float` で、極小値未満は拒否する
- ユニットデータには必須列がそろっている必要がある

## Known Limitations
- `Composite.init_ai` と `Composite.rolling_ai` は保持されるが、現行主実装での影響は限定的
- `AI.defensive` は未実装
- ノートブックや教材コードには本体仕様と一致しない説明が残る可能性がある
- 仕様文書は現実装に基づくため、将来変更時はこの文書も更新が必要

## Recommended Source Of Truth
この仕様を変更する場合は、少なくとも以下を同時に更新する。
- この文書
- `docs/simulation-rules.md`
- 関連テスト
- 必要なら `README.rst`
