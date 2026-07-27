# 妥当性検証計画

Rules version 1は、決定論的検査、metamorphic検査、統計検査、性能検査の
すべてに合格した場合にのみ受け入れる。

- 入力検査: 厳密なscalar型、必須・未知field、有限float、正のunit数・解像度・
  半径、正しく並んだbounds、閉じたenum値、cross-field不変条件
- 厳密一致検査: 同一入力・seed・version、状態量の範囲、終了理由、
  result schema、event schema
- Metamorphic検査: Composite登録順、team label交換、world全体の平行移動、
  一貫して尺度変更したflat micro scenario
- 統計検査: 固定seed集合で結果が退化しないこと、Wilson信頼区間、
  scenario family単位のpartition、保存したbaseline分布
- 戦術micro検査: 孤立したduelでのdamage単調性、cooldown周期、相打ち、
  line-of-sight、cover、collision、objective占有

`tests/baselines/` 配下のbaselineは変更検出器であり、モデルが現実を表現する
証拠ではない。意図した意味変更によってbaselineが動く場合はrules versionを
更新する。

reference Python kernelでは、200-unit battleを含む完全なテストスイートについて、
CIの初期性能予算を30秒とする。この予算を超えるdataset workloadでは、並列実行や
kernel最適化を追加する前にbenchmarkを行う。

現在、外部calibration dataは利用できない。代理モデルの予測を現実世界の推定値と
解釈する前に、明示的なcalibration dataset、provenance、測定誤差、許容parameter
範囲、holdout基準を追加する。それまでは、代理モデルをrules version 1の
emulatorとして記述し、現実の戦闘について妥当性確認済みのモデルとは扱わない。

静的型検査と入力検証は欠陥検出器であり、モデル妥当性の証拠ではない。上記の
決定論的検査、metamorphic検査、統計検査、baseline検査、外部calibration検査を
置き換えるものではない。

## テストの妥当性と証拠

テストスイートが成功することは必要条件だが、それだけでは新しいテストが妥当で
あることを示さない。挙動変更またはバグ修正のために追加する各テストは、次の
いずれかへ追跡可能でなければならない。

- `docs/` に記載されたruleまたはcontract
- 最小再現ケースを伴う、過去に観測されたfailure
- 適用条件が文書化された、明示的な不変条件

実装前に変更作成者は、検証する主張、その主張の根拠、テストが拒否すべき代表的な
誤実装を1件以上、関連する非対象を示す。仕様の大部分を重複して記載することなく、
テスト名、近接コメント、または変更説明によってこの追跡可能性を維持する。

期待値は、検査対象のproduction pathから独立させる。小さなscenarioから手計算した
値、固定したcontract例、または独立したreference実装を優先する。同じproduction
helperを呼び出したり、テスト内に同じ制御フローを再現したりして期待値を計算しては
ならない。mockとfixtureによって、正しさを主張する対象の挙動そのものを置き換えては
ならない。

バグ修正では、まず不正な挙動に対して再発防止テストが失敗し、修正後に成功する
ことを示す。それ以外の重要な挙動変更では、実行可能な場合、焦点を絞った
fault injectionまたはmutationを1件以上用いて検出能力を示す。適切なsimulation
mutationには、seedの無視、登録順の反転、境界比較の変更、非有限値の受理、
subsystem間でのrandom-number generator共有、終了理由またはversion fieldの欠落が
含まれる。一時的なmutationは必ず元へ戻し、commitしてはならない。

Mutation scoreとlineまたはbranch coverageは診断指標であり、モデル妥当性の
合格基準ではない。生存したmutationは分類し、意味のあるものには不足している
テストを追加する。同値なmutationまたは主張の対象外である場合は、その理由を
文書化する。完全なmutation analysisは初期の30秒テスト予算へ含めず、必要に応じて
対象を限定したjobまたはscheduled jobとして実行する。

## テストレビュー記録

重要なテスト変更のレビュー記録では、次の問いに回答する。

1. どの挙動を主張し、それはどこに規定されているか
2. 期待結果をどのように独立して導出したか
3. どの境界値、不正入力、または不変条件を検査するか
4. どの代表的な誤実装によってテストが失敗することを確認したか
5. 統計テストでは、どの固定seed、sample数、統計量、許容差を使用し、
   その根拠は何か
6. このテストが意図的に保証しない挙動は何か

現在の実装をそのままsnapshot化するだけのテスト、実行が完了したことだけを
assertするテスト、検査対象を過剰にmockするテスト、test orderまたはglobal random
stateへ依存するテスト、failureを消すためだけにassertionを弱めたテストは
レビューで拒否する。

最新のリポジトリ全体の棚卸し、対象を限定したmutation結果、mutation toolの判断は
`docs/test-validity-audit.md` に記録する。
