# Implementation Rules

## Language And Structure
- 実装は既存の Python パッケージ構成に沿って進める
- 変更は責務ごとに分け、無関係なファイルへ波及させすぎない
- 開発環境は `uv` と Python 3.12 以上を基準にする

## Design Rules
- 戦闘ロジックと描画ロジックは分離する
- 既存 API を壊す変更は慎重に扱う
- 実験的な仕様は、将来切り替えやすい形で追加する

## Current Extension Points
- 戦闘本体の拡張は `battlesim/_battle.py` を入口にする
- ターゲティングの拡張は `battlesim/simulation/_target.py` に追加する
- AI 行動の拡張は `battlesim/simulation/_ai.py` に追加する
- 地形ルールの拡張は `battlesim/terra/_terrain.py` と `battlesim/terra/_noise.py` に追加する
- 可視化の拡張は `battlesim/plot/` 配下で行い、戦闘ロジックには直接混ぜない

## Testing Rules
- ロジック変更時は `tests/` に対応するテストを追加または更新する
- バグ修正時は、再発防止テストを優先する
- テスト実行は `uv run pytest -v` を基準にする
- 静的解析と型チェックは `make check` を基準にする

## Documentation Rules
- 挙動が変わる変更では、関連する `docs/` を更新する
- 実装前提や制約はコード中ではなく docs に残す
