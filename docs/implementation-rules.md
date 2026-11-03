# Implementation Rules

## Language And Structure
- 実装は既存の Python パッケージ構成に沿って進める
- 変更は責務ごとに分け、無関係なファイルへ波及させすぎない
- 開発環境は `uv` と Python 3.12 以上を基準にする

## Type Safety And Input Boundaries
- 静的型検査は `mypy` に一本化し、`battlesim/`, `apps/`, `tests/` の全体を常時検査する
- 安全性中核には `mypy --strict` 相当のフラグを適用する。`strict` はmodule単位で
  指定できないため、対象一覧は `pyproject.toml` の `tool.mypy.overrides` に
  フラグ付きで明記し、入力境界、契約、乱数、dataset、validation、および
  修正したmoduleの対応テストを含める
- 既存のNumba/legacy領域は修正したmodule単位で `tool.mypy.overrides` の
  厳格対象へ追加し、対象を縮小しない。この段階的拡大をtype-safety ratchetとする
- `Any` は未検証の外部入力や型情報を提供しない依存ライブラリとの局所的な境界に
  限定し、ドメイン層へ伝播させない
- `type: ignore` は対象エラーコードと理由を付け、未使用の抑制をエラーにする
- TOML、CLI、CSV、外部から復元した結果などの信頼境界では Pydantic v2 の
  strict model を用いる
- 外部入力 model は原則として `strict=True`, `extra="forbid"`,
  `frozen=True` とし、未知キーや暗黙の型変換を拒否する
- 外部入力は境界で一度検証し、既存の frozen dataclass や NumPy 配列へ変換する。
  tick処理や数値カーネルへ実行時validation decoratorを持ち込まない
- 浮動小数点入力は有限値であることを検査する。正値、確率、配列長、
  boundsの大小関係などは型とは別の制約として宣言する
- 閉じた値集合は `Literal` または `Enum` で表現し、自由な `str` にしない

## Design Rules
- 戦闘ロジックと描画ロジックは分離する
- 既存 API を壊す変更は慎重に扱う
- 実験的な仕様は、将来切り替えやすい形で追加する
- rules version と dataset schema version はコード定数として一元管理する
- 乱数は subsystem ごとの `numpy.random.Generator` から取得し、グローバル乱数へ
  暗黙に依存しない。ただし `Battle` が使わない legacy 低レベル API
  (`simulation.simulate_battle` など)は現状グローバル乱数を使う
- 長時間 batch は trial ID により再開・重複排除できるようにする

## Current Extension Points
- 戦闘本体の拡張は `battlesim/_battle.py` を入口にする
- ターゲティングの拡張は `battlesim/simulation/_target.py` に追加する
- AI 行動の拡張は `battlesim/simulation/_ai.py` に追加する
- 地形ルールの拡張は `battlesim/terra/_terrain.py` と `battlesim/terra/_noise.py` に追加する
- 可視化の拡張は `battlesim/plot/` 配下で行い、戦闘ロジックには直接混ぜない

## Testing Rules
- ロジック変更時は `tests/` に対応するテストを追加または更新する
- バグ修正時は、再発防止テストを優先する
- 挙動変更またはバグ修正のテストは、実装前に「検証する主張」「根拠となる
  `docs/` の節または再現ケース」「検出すべき代表的な誤実装」「非対象」を定める
- テスト名、近接コメント、または変更説明から、テストと仕様・不変条件・
  バグ再現ケースの対応を追跡可能にする
- 期待値は小さなscenarioの手計算、固定した契約例、独立したreference実装から
  導出する。検査対象と同じproduction helperや同じ制御フローで期待値を作らない
- mockやfixtureで、正しさを主張する対象そのものを置き換えない
- バグ修正と重要な挙動変更での再発防止テストの失敗確認、fault injection、
  mutation、coverage率とmutation scoreの扱いは `docs/validation-plan.md` に従う
- テスト実行は `uv run pytest -v` を基準にする
- 静的解析と型チェックは `make check` を基準にする
- 入力modelには正常系、境界値、NaN/無限大、boolと数値の混同、未知キー、
  cross-field制約の拒否テストを追加する
- 入力空間が広い制約には Hypothesis によるproperty-based testを使用する
- 統計的性質は固定 seed 集合、許容差、sample 数をテスト名または docs に記録する
- 平行移動・尺度・単調性は成立条件を限定した micro scenario で検証する

### Test Change Review

重要なテスト変更の説明には、次を簡潔に記録する。

1. 検証する主張と仕様上の根拠
2. 期待値を実装から独立して導出した方法
3. 検査する境界値、異常入力、または不変条件
4. テストを失敗させることを確認した代表的な誤実装
5. 統計テストの場合は固定seed、sample数、統計量、許容差とその根拠
6. そのテストだけでは保証しない範囲

単に例外なく終了することだけを確認するテスト、現在の実装出力を根拠なく
snapshot化するテスト、test orderやglobal random stateへ依存するテスト、
失敗を消すためだけにassertionを弱めた変更は受け入れない。

## Documentation Rules
- 挙動が変わる変更では、関連する `docs/` を更新する
- 実装前提や制約はコード中ではなく docs に残す

## Enforcement
- `make check` は pre-commit 設定の検証、Ruff lint、format check、全体mypy
  (厳格対象はstrict相当)、pytestの全てを実行する
- CIも `make check` と同じ対象を検査し、一部ファイルだけを対象にして成功扱いしない
- `pre-commit` stageでは変更ファイルの種類にかかわらず `make check` を毎回実行する
- cloneまたはdependency sync後は `make install-hooks` でGit hookを導入する
- Gitの `--no-verify` によるローカル回避は完全には禁止できないため、
  共有リポジトリでの最終強制はCIの必須status checkで行う
