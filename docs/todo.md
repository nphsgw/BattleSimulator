# TODO

## Phase 1
- [x] ルール文書を整備する
- [x] どの挙動を独自仕様にするか決める
- [x] 既存コードのどこを拡張するか整理する

## Phase 2
- [x] 小さな仕様変更を 1 つ選んで実装する
- [x] テストを追加する
- 必要ならサンプルやデータセットを更新する

## Phase 3
- 独自ユニットや独自 AI の追加を検討する
- 可視化やアニメーションの調整を検討する

### Visualization / Animation Plan
- [x] 可視化の目的と非目的を `docs/` に整理する
- [x] 通常表示とデバッグ表示の役割を分ける
- [x] ユニットごとに表示したい情報を確定する
  例: HP, target, team, alive/dead, unit type
- [x] 地形の影響として表示したい値を確定する
  例: 地形高さ, 移動補正, 実効射程, 高低差ダメージ補正

### Phase 3A: Minimal Overlay
- [x] 現行の `quiver_fight()` を基準に、拡張方針を決める
- [x] target line を表示する描画方法を設計する
- [x] HP を見やすく表示する方法を決める
  例: バー表示, 色段階, 数値ラベル
- [x] 情報過多を避けるため、表示の on/off 方針を決める
- [x] 最小構成の可視化を新規描画関数として実装する
  例: `quiver_fight_debug()`
- [x] `sim_jupyter()` と `sim_export()` から切り替えて使えるようにする

### Phase 3B: Terrain Influence Overlay
- [x] 描画に必要な地形由来データを frame に保存する方針を決める
- [x] simulation 側で各 frame に地形由来の補助情報を保持できるようにする
  例: `z`, `move_factor`, `effective_range`
- [x] ユニット足元の地形高さを可視化する方法を決める
- [x] 移動補正と射程補正を可視化する方法を決める
- [x] 攻撃時の高低差ダメージ補正を可視化する方法を決める
- [x] 背景地形とユニット overlay が干渉しすぎないように調整する

### Phase 3C: Validation
- [x] 可視化用の最小回帰テストを追加する
- [x] 代表的な battle 条件で `sim_jupyter()` を確認する
- [x] 代表的な battle 条件で `sim_export()` を確認する
- [x] `docs/current-spec.md` に可視化仕様を追記する

## Review Follow-Ups

### High Priority
- [x] `battlesim/simulation/_target.py` の `global_nearest` と `global_close_weak` が返す target index を見直し、敵配列内の相対 index ではなく `M` 全体の index を返すように修正する
- [x] `battlesim/terra/_terrain.py` の `Terrain.generate()` で `form=None` のときに Perlin 地形で上書きされないように修正する

### Medium Priority
- [x] `battlesim/_battle.py` の `sim_export()` で `filename.append(".gif")` を `str` に対して使っている箇所を修正する
- [x] `battlesim/_battle.py` の `_is_instantiated()` を見直し、`create_army()` 前に不自然な例外へ流れないようにする

### Low Priority
- [x] `battlesim/` 全体の型ヒントを Python 3.12 向けの書き方へ寄せる
  例: `List[...]` -> `list[...]`, `Optional[...]` -> `X | None`
- [x] `numba` 利用箇所の `@jit` を見直し、必要に応じて `@njit` または `nopython=True` 前提へ寄せる
- [x] `tests/test_battle.py` の `type(...) == ...` を `isinstance(...)` に修正する

### Notebook / Teaching Cleanup
- `examples/` と `teaching/` の notebook にある Ruff 指摘を別タスクとして整理する
- 教材 notebook の unused import、`not in`、`lambda` 代入などの古い書き方を必要に応じて更新する
