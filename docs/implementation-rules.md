# Implementation Rules

## Language And Structure
- 実装は既存の Python パッケージ構成に沿って進める
- 変更は責務ごとに分け、無関係なファイルへ波及させすぎない

## Design Rules
- 戦闘ロジックと描画ロジックは分離する
- 既存 API を壊す変更は慎重に扱う
- 実験的な仕様は、将来切り替えやすい形で追加する

## Testing Rules
- ロジック変更時は `tests/` に対応するテストを追加または更新する
- バグ修正時は、再発防止テストを優先する

## Documentation Rules
- 挙動が変わる変更では、関連する `docs/` を更新する
- 実装前提や制約はコード中ではなく docs に残す
