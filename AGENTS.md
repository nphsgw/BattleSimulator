# AGENTS.md

## Project Goal
BattleSimulator をベースに、自分用の戦闘シミュレーション環境として拡張する。

## Source of Truth
- 全体方針は `docs/product-rules.md`
- シミュレーション仕様は `docs/simulation-rules.md`
- 実装ルールは `docs/implementation-rules.md`
- 実装順序は `docs/todo.md`

## Working Rules
- 仕様変更を伴う実装では、先に対応する `docs/` を更新する
- 戦闘ロジックの変更と可視化の変更はなるべく分離する
- 既存の公開 API は、明示的な方針がない限り維持する
- 挙動変更時は `tests/` を追加または更新する
- 要件が曖昧な場合は、コードより先に docs を更新して判断を固定する

## Validation
- 変更後は可能な範囲で `pytest` を実行する
