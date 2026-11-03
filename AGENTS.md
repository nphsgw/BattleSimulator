# AGENTS.md

## Project Goal
BattleSimulator を、明示的な戦術入力から再現可能な結果分布を生成し、
代理モデルの学習・検証に使える個人用戦闘シミュレーション環境へ拡張する。

## Source of Truth
- 全体方針は `docs/product-rules.md`
- シミュレーション仕様は `docs/simulation-rules.md`
- 現行実装仕様は `docs/current-spec.md`
- 実装ルールは `docs/implementation-rules.md`
- 実装順序は `docs/todo.md`
- 入出力契約は `docs/model-contract.md` と `docs/dataset-contract.md`
- 妥当性検証は `docs/validation-plan.md`
- 可視化方針は `docs/visualization-rules.md`
- 研究上の主張範囲は `docs/research-background-and-hypotheses.md`

`AGENTS.md` は日常作業用の要約であり、詳細または競合時は上記docsを正とする。

## Decision Priorities
- 配列順、登録順、暗黙の乱数を戦術効果として混入させない
- 入力、rules version、seed、simulator version、結果、終了理由を追跡可能にする
- 不正入力を黙って補正せず、シミュレーション開始前に場所と理由を示して拒否する
- 型検査、入力検証、意味的テストを相互補完させる
- 既存APIを壊すより、切り替え可能な拡張を優先する
- 仕様判断と回帰基準がない大規模リファクタは行わない

## Change Workflow
- 仕様変更を伴う実装では、先に対応する `docs/` を更新する
- 要件が曖昧な場合は、コードより先にdocsを更新して判断を固定する
- 戦闘ロジックと可視化の変更は分離する
- 既存の公開 API は、明示的な方針がない限り維持する
- 挙動変更には対応テスト、バグ修正には再発防止テストを追加する
- テスト実装前に、検証する主張、仕様または再現ケース、検出すべき代表的な
  誤実装、非対象を明示する
- 期待値は手計算可能なmicro scenario、契約例、独立したreferenceから導出し、
  検査対象と同じproduction helperで生成しない
- バグ修正では修正前の失敗を確認する。重要な挙動変更では可能な範囲で一時的な
  fault injectionまたはmutationにより、新規テストが誤実装を検出することを確認する
- 開発環境は `uv` と Python 3.14 以上を前提にする

## Type Safety And Input Boundaries
- `mypy` は `apps/`, `battlesim/`, `tests/` 全体へ適用する
- `mypy --strict` 相当の厳格設定の対象は `pyproject.toml` の `tool.mypy.overrides` で管理する
- 修正したNumba/legacy moduleは可能な限り厳格対象へ追加し、既存対象を縮小しない
- `Any` は未検証入力または型情報のない依存との局所的境界に限定し、伝播させない
- `type: ignore` には対象エラーコードと理由を付ける
- TOML、CLI、CSV、外部から復元したデータはPydantic v2のstrict modelで検証する
- 外部入力modelは原則 `strict=True`, `extra="forbid"`, `frozen=True` とする
- 境界で一度検証してdomain dataclassまたはNumPy配列へ変換し、
  tick処理へruntime validationを持ち込まない
- 数値入力は有限性と意味制約を検査し、閉じた値集合は `Literal` または `Enum` にする

## Simulation Invariants
- 戦闘ロジック、描画、dataset処理を分離する
- rules versionとdataset schema versionはコード定数として一元管理する
- 乱数はsubsystem別の `numpy.random.Generator` を使い、グローバル乱数へ依存しない
- 長時間batchはtrial IDで再開・重複排除できるようにする
- 意図した意味変更でbaseline分布が動く場合はrules versionを更新する
- baselineは変更検出器であり、現実妥当性の証拠として扱わない

## Extension Points
- 戦闘本体: `battlesim/_battle.py`
- ターゲティング: `battlesim/simulation/_target.py`
- AI行動: `battlesim/simulation/_ai.py`
- 地形: `battlesim/terra/_terrain.py`, `battlesim/terra/_noise.py`
- 可視化: `battlesim/plot/`

## Validation Gates
- Python変更後は原則 `make check` を実行する
- `make check` はpre-commit設定検証、Ruff lint、format check、全体mypy、厳格対象のstrict設定、pytestを含む
- 通常の `git commit` でもpre-commit hookから `make check` を毎回実行する
- dependency sync後にhookが未導入なら `make install-hooks` を実行する
- 入力変更では正常系に加え、境界値、NaN/無限大、boolと数値の混同、
  未知キー、cross-field制約を検査する
- 広い入力空間にはHypothesisを使う
- 統計テストは固定seed集合、許容差、sample数をテスト名またはdocsへ記録する
- coverage率とmutation scoreだけを仕様適合性やモデル妥当性の証拠にしない
- 重要なテスト変更では、主張と根拠、期待値の導出、境界・不変条件、
  検出確認した誤実装、非対象をレビュー可能に記録する
- 静的型検査と入力検証をモデル妥当性の証拠として扱わず、
  deterministic、metamorphic、statistical checksを維持する
- 完全なテストスイートは200-unit battleを含め30秒以内を初期予算とする

## Working Agreements
- 頼まれた範囲だけを変更する。気づいた別の問題は手を付けず報告に挙げる
- 実行していない検証を通過扱いにしない。報告には変更内容、実行した検証と結果、未検証の範囲を含める
- 検証は `make` 経由で行い、`ruff` / `mypy` / `pytest` を個別の設定で直接実行して代替しない
  （対象と設定が `make check` とずれるため。部分確認は `make lint` / `typecheck` / `format-check`）
- `skip` / `xfail` / `importorskip` を追加する場合は理由を書く。失敗を消すために追加しない
- 変更後、実装とは別セッションで `/review`（`.claude/skills/review/SKILL.md`）を実行する
