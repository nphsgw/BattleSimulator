# Visualization Rules

## Purpose
この文書は、BattleSimulator の可視化とアニメーションに関する独自仕様の正本とする。
戦闘ロジックそのものを変えずに、何をどの粒度で見せるかをここで固定する。

## Current Baseline
- 現行の標準アニメーションは `quiver_fight()` である
- 生存ユニットは矢印、死亡ユニットは `x` で描画する
- 地形がある場合は背景に地形を重ねて表示する

## Goals
- ユニットごとの状態を、戦闘の流れが追える粒度で表示する
- どの敵を狙っているかを視覚的に理解しやすくする
- 地形が移動、射程、ダメージへどう影響しているかを読み取りやすくする
- 通常観賞用の表示と、挙動解析用の表示を分けて扱えるようにする

## Non-Goals
- 可視化のために戦闘ロジックを変更しない
- 最初の段階では派手な演出やリアルタイム UI を優先しない
- 全情報を常時表示して視認性を損なう構成にしない
- notebook の実行状態を可視化機能の前提にしない

## Notebook Independence
- 可視化の正本は `battlesim/` 配下の通常の Python API とする
- 対話操作の主要 UI は、pytest から検証できるローカル Web UI とする
- notebook は教材、探索、利用例として残せるが、主要機能の実装場所にはしない
- CLI、Web UI、notebook は同じ表示モデルと描画 API を利用する
- 既存の `Battle.sim_jupyter()` は後方互換性のため維持する

## Visualization Layers
可視化は次の責務へ分離する。

1. simulation
   戦闘結果の frame を生成する
2. view model
   frame から HP 比率、target 座標、生死、地形補助値などの表示用データを生成する
3. renderer
   view model を Matplotlib の Figure や animation へ変換する
4. interface
   CLI、ローカル Web UI、notebook から renderer を呼び出す

view model は UI framework に依存させず、固定 frame を使った単体テストを可能にする。

## Display Modes

### Normal View
- 目的は戦闘全体の流れを見やすく表示すること
- 表示は軽量で、既存の `quiver_fight()` に近い見た目を維持する
- 情報量は絞り、チーム、位置、向き、生死が一目で分かることを優先する

### Debug View
- 目的は個々のユニット判断や地形補正を解析しやすくすること
- 戦闘画面とユニットパラメータ画面を横に並べる
- 戦闘画面にはユニット番号を表示し、パラメータ画面の番号と対応させる
- HP、target、地形補正などの数値情報はパラメータ画面へ表示する
- 実装上は通常表示とは別の描画関数として切り出すことを優先する

## Unit-Level Information To Show

### Required In Debug View
- 現在位置
- 現在の向き
- チーム
- 生死
- 現在 HP
- 現在 target
- unit type

### Optional In Later Iterations
- 現在 armor
- AI 種別
- 射程円
- 数値ラベルによる詳細ステータス

## Terrain Influence To Show

### Required In Debug View
- ユニット足元の地形高さ
- 地形による移動補正
- 地形による実効射程補正
- 攻撃時の高低差ダメージ補正

### Notes
- 地形高さはユニット自身の位置に対応する値を基本とする
- ダメージ補正は攻撃側と target 側の高低差から計算された値として扱う
- 表示は「高さそのもの」と「戦闘へ与える影響」の両方を分けて見せる

## Visibility Policy
- 通常表示では情報量を抑える
- ローカル Web UI の戦闘画面では、HP バーと地形補助テキストをユニットへ重畳しない
- ローカル Web UI では自由なunit選択に加え、同梱scenarioをpresetとして
  選択・実行できるようにする
- `Damage demo` presetは `scenarios/damage-demo.toml` を読み込み、parameter画面で
  Armorが先に減った後にHPが減る様子を確認できるようにする
- ローカル Web UI の戦闘画面では、固定されたユニット番号を重畳する
- target line は必要時だけ表示できるようにする
- 線、ラベル、バーは地形背景より前面に描画する
- 背景地形と overlay が干渉しすぎないよう、透明度を前提に調整する

## Unit Parameter Panel
- 戦闘画面の右側に、現在 frame の全ユニットを表示する専用領域を置く
- 行は unit index の昇順とし、表示番号は `unit index + 1` とする
- unit index は simulation frame 内で固定されるため、再生中も番号を維持する
- 少なくとも次を表示する
  - unit number
  - team
  - unit type
  - alive / dead
  - current HP / initial HP
  - current armor
  - target unit number
  - terrain height
  - movement factor
  - effective range
  - damage factor
- ユニット数が多い場合はパネル内をスクロール可能にする

## Playback Policy
- シミュレーション計算と再生速度を分離する
- シミュレーション完了後は frame 0 から自動再生を開始する
- UI は再生、一時停止、先頭から再生の操作を持つ
- 再生速度は frames per second で選択できるようにする
- frame slider を手動操作した場合は再生を一時停止する
- 最終 frame に到達した場合は自動的に一時停止する
- 再生のために simulation を再実行しない

## Implementation Policy
- まずは `quiver_fight()` を直接肥大化させず、新しい debug 描画関数を追加する
- 描画に必要な追加情報は、必要に応じて simulation frame に保持する
- 戦闘ロジックの変更が必要な場合は、可視化目的の変更とロジック変更を分離する

## First Implementation Slice
- まずは debug view で HP と target line を表示する
- 次に地形由来の `z`, `move_factor`, `effective_range` を扱えるようにする
- 最後に高低差ダメージ補正の表示を追加する

## Phase 3A Decisions

### Base Function Choice
- 通常表示の基準は既存の `quiver_fight()` とする
- overlay は `quiver_fight()` を直接複雑化させず、別関数 `quiver_fight_debug()` として追加する

### Target Line Design
- target line は debug view で既定で表示する
- 各ユニットから現在 target の位置へ細い破線を引く
- 色はそのユニットのチーム色を使い、透明度を高めにして主表示を邪魔しないようにする

### HP Display Design
- HP は各ユニットの頭上に短い横バーとして表示する
- バー長はそのユニットの初期 HP を基準に正規化する
- 色は HP 比率に応じて緑、黄、赤へ変化させる
- 死亡ユニットでは HP バーを消す

この HP overlay は `quiver_fight_debug()` の互換機能として維持する。
ローカル Web UI では使用せず、unit parameter panel に数値を表示する。

### Visibility Toggles
- debug view では `show_hp` と `show_target_lines` を切り替え可能にする
- debug view の既定値は、どちらも `True` とする

### First Public Entry Points
- `Battle.sim_jupyter(func=...)` から `quiver_fight_debug()` を渡して使えること
- `Battle.sim_export(func=...)` から `quiver_fight_debug()` を渡して使えること

## Phase 3B Decisions

### Frame Data Policy
- 地形由来の表示に必要な値は、各 frame に明示的に保存する
- まず保存する値は `z`, `target_z`, `move_factor`, `effective_range`, `damage_factor` とする
- これらは「現在 frame での地形補助情報」として扱い、戦闘ロジックの再計算を描画側で行わない

### Meaning Of Stored Values
- `z`
  ユニット足元の地形高さ
- `target_z`
  現在 target 足元の地形高さ
- `move_factor`
  地形だけが移動へ与える倍率
  rules version 1では上り勾配に対する `1 / (1 + rise)`。
  legacy frameでは `1 - z / 2`
- `effective_range`
  現在rulesで攻撃判定に使った実効射程
  rules version 1では `range`、legacy frameでは `range * ((z^2 / 3) + 1)`
- `damage_factor`
  高低差による与ダメージ倍率
  現行実装では `((z - target_z) / 2) + 1`

### Terrain Overlay Design
- 地形由来の補助情報は debug view でのみ表示する
- 最初の表示方法は、各ユニットの頭上に置く小さなテキスト overlay とする
- テキストには少なくとも `z`, `mv`, `rg` を表示する
- `damage_factor` は target が存在する場合にのみ表示する
- 背景地形と重なっても読めるよう、半透明の背景ボックスを付ける

### Visibility And Clutter Policy
- terrain overlay は `show_terrain_text` の on/off を持つ
- 既定値は `False` とし、debug view でも必要時に有効化する
- 死亡ユニットの terrain overlay は表示しない

### Notebook Controls
- 表示 UI では `show_hp`, `show_target_lines`, `show_terrain_text` を切り替えられるようにする
- 表示 UI では `frame index` を slider から調整できるようにする
- notebook 固有の widget は必須機能としない

### Background Interaction
- terrain 自体は今まで通り背景に表示する
- terrain overlay のテキストは地形背景より前面に描く
- 背景地形は `alpha` を抑え、overlay の可読性を優先する

## Validation Policy
- view model は手書きの固定 frame で値を検証する
- renderer は artist の数、座標、ラベルなどを優先して検証する
- 画像比較テストは代表的な少数ケースに限定する
- Web UI は headless な UI テストで widget 操作と例外の有無を検証する
- ランダムな実シミュレーションだけに依存する描画テストは避ける
