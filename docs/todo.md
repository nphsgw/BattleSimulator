# TODO

## Phase 1
- ルール文書を整備する
- どの挙動を独自仕様にするか決める
- 既存コードのどこを拡張するか整理する

## Phase 2
- 小さな仕様変更を 1 つ選んで実装する
- テストを追加する
- 必要ならサンプルやデータセットを更新する

## Phase 3
- 独自ユニットや独自 AI の追加を検討する
- 可視化やアニメーションの調整を検討する

## Review Follow-Ups

### High Priority
- `battlesim/simulation/_target.py` の `global_nearest` と `global_close_weak` が返す target index を見直し、敵配列内の相対 index ではなく `M` 全体の index を返すように修正する
- `battlesim/terra/_terrain.py` の `Terrain.generate()` で `form=None` のときに Perlin 地形で上書きされないように修正する

### Medium Priority
- `battlesim/_battle.py` の `sim_export()` で `filename.append(".gif")` を `str` に対して使っている箇所を修正する
- `battlesim/_battle.py` の `_is_instantiated()` を見直し、`create_army()` 前に不自然な例外へ流れないようにする

### Low Priority
- `battlesim/` 全体の型ヒントを Python 3.12 向けの書き方へ寄せる
  例: `List[...]` -> `list[...]`, `Optional[...]` -> `X | None`
- `numba` 利用箇所の `@jit` を見直し、必要に応じて `@njit` または `nopython=True` 前提へ寄せる
- `tests/test_battle.py` の `type(...) == ...` を `isinstance(...)` に修正する

### Notebook / Teaching Cleanup
- `examples/` と `teaching/` の notebook にある Ruff 指摘を別タスクとして整理する
- 教材 notebook の unused import、`not in`、`lambda` 代入などの古い書き方を必要に応じて更新する
