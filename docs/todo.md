# TODO

旧ロードマップは `docs/history/todo-before-surrogate-roadmap.md` に保存する。

## Tactical Simulator For Surrogate Modeling

### Goal And Design Principles

戦術シミュレーターから代理モデル用の学習データを生成することを目標とする。
写実性を無制限に増やすのではなく、次を優先する。

- [x] 同じ入力と seed から同じ結果を再現できる
- [x] 配列順、Composite 登録順、暗黙の乱数などの実装都合を戦術効果へ混ぜない
- [x] 入力、内部ルール、終了理由、出力の因果関係を説明可能にする
- [x] simulation rules と出力 schema に version を付ける
- [x] simulator version が異なるデータを代理モデルの学習時に区別できるようにする

### Phase 0: Model Contract

- [x] シミュレーターの抽象度を「2 次元、離散時間、unit 単位の agent-based model」として文書化する
- [x] 1 tick の時間的意味と、距離、速度、射程、攻撃間隔の単位を定義する
- [x] 当面の攻撃を hitscan とし、弾速や弾丸 object を対象外にするか決定する
- [x] 基本終了条件を elimination、timeout、stalemate、mutual destruction に分類する
- [x] 勝利確率、生存率、戦闘時間、損耗交換比を最初の代理モデル目的変数とする

### Phase 1: Reproducibility And Result Contract

- [x] `Battle` / `BattleScenario` に明示的な seed を追加する
- [x] 初期配置、地形、target、行動、命中、damage 用の乱数系列を分離する
- [x] 同一入力、同一 seed、同一 rules version で完全一致するテストを追加する
- [x] winner、termination reason、ticks、team 別残存数・HP・armor を持つ `BattleResult` を追加する
- [x] timeout を勝利として扱わず、未決着として識別する
- [x] scenario ID、trial ID、seed、simulator version、rules version を結果へ保存する

### Phase 2: Simultaneous Tick Resolution

unit index 順の逐次解決を、代理モデルが登録順バイアスとして学習しないようにする。

- [x] tick 開始時点の immutable snapshot から全 unit の判断を行う
- [x] 全 unit の target と行動予定を先に決定する
- [x] 全移動予定を計算してから衝突解決とともに一括反映する
- [x] 移動後の位置から射程、射線、命中率を計算する
- [x] 全攻撃と damage を予約し、tick 終了時に一括反映する
- [x] 相打ちを表現できるようにする
- [x] Composite の登録順を交換しても結果分布が変わらない統計テストを追加する
- [x] 将来 initiative を追加する場合は、暗黙の配列順ではなく明示的な入力特徴量とする

### Phase 3: Combat Timing And Targeting

- [x] unit stat に `Attack Interval` または cooldown を追加する
- [x] `Aim Time` と `Burst Size` は v1 では追加せず、cooldown で連射差を表すと決定する
- [x] 高威力・低連射と低威力・高連射を区別できるテストを追加する
- [x] `nearest` から暗黙の距離 noise を除去する
- [x] 同距離時の tie-break は入力順に依存しない stable unit ID とする
- [x] `weakest`, `highest_threat`, `focus_fire`, `objective_priority` を target AI として追加する
- [x] distance、durability、expected damage、objective importance を正規化した説明可能な threat score を設計する
- [x] AI doctrine の重みを scenario 入力および代理モデル特徴量として扱えるようにする
- [x] hit-and-run が境界で後退不能な場合は横移動を試し、射程内なら攻撃へfallbackする

### Phase 4: Terrain And Spatial Tactics

- [x] 移動補正を絶対標高ではなく進行方向の勾配から計算する
- [x] 高所による射程、命中率、damage 補正の必要性と上限を再設計する
- [x] attacker と target の中間地形を使った line-of-sight 判定を追加する
- [x] 地形または cover object による遮蔽と命中率補正を追加する
- [x] unit に占有半径 `Radius` を追加する
- [x] 味方同士の soft separation を追加する
- [x] unit の無制限な重なり、敵の通り抜け、境界での重なりを防ぐ
- [x] 密集度を将来の範囲攻撃や被弾補正へ利用できる表示値として保持する

### Phase 5: Armor And Additional Tactical Rules

- [x] armor を単純な追加 HP として維持するか、damage reduction として再設計するか決定する
- [x] armor の意味を列名、docs、代理モデル特徴量で一貫させる
- [x] projectile、範囲攻撃、suppression、morale、撤退は v1 の対象外と決定する
- [x] objective zone と占有時間による勝敗ルールを追加する
- [x] multi-team battle の targetと勝敗条件を明文化し、複雑な同盟は v1 の対象外とする

### Phase 6: Monte Carlo And Dataset Generation

- [x] `simulate_k()` で randomize 対象を指定できるようにする
  例: `("combat",)` または `("placement", "terrain", "combat")`
- [x] 配置・地形固定の条件付き勝率と、すべてを変える総合勝率を分離する
- [x] 各 trial で何を randomize したかを結果へ保存する
- [x] scenario family 単位で parameter sweep を実行する batch runner を追加する
- [x] 代理モデル用 dataset schema と保存形式を決定する
- [x] train / validation / test を seed だけでなく scenario family 単位で分割する
- [x] rules version をまたぐ dataset を誤って混合しない検査を追加する

### Phase 7: Surrogate Modeling Outputs

- [x] winner と termination reason を出力する
- [x] battle duration と初回接敵 tick を出力する
- [x] team 別の生存数、生存率、残存 HP、残存 armor を出力する
- [x] 与 damage、被 damage、kill 数、射撃数、命中数を出力する
- [x] unit / team 別の移動距離を出力する
- [x] 高所、cover、objective の占有時間を出力する
- [x] force exchange ratio と終了時の空間的分散を出力する
- [x] v1 は可変 unit 数を固定長集約特徴として代理モデルへ渡す

### Phase 8: Simulation Validity Tests

- [x] team 名を交換すると結果分布も交換されることを確認する
- [x] Composite 登録順を交換しても結果分布が変わらないことを確認する
- [x] 全worldを平行移動したmicro scenarioで結果が変わらないことを確認する
- [x] 単位系を一貫して拡大縮小した場合の性質を定義して検証する
- [x] 同じ seed では完全一致し、異なる seed では適切な分散を持つことを確認する
- [x] Damageの単調性を成立条件を限定したmicro scenarioで検証する
- [x] HP、armor、cooldownなどの状態量が許容範囲外にならないことを確認する
- [x] 全滅、timeout、stalemate が正しい終了理由になることを確認する
- [x] baseline scenario の結果分布を保存し、統計的回帰テストを追加する

### Recommended Implementation Order

1. [x] 旧TODOの履歴整理
2. [x] product goal・解決順序・互換性方針の決定
3. [x] 時間、単位、終了条件、multi-team結果schema
4. [x] seed派生規約、`BattleResult`、イベントログ
5. [x] 再現性・対称性の基礎テスト
6. [x] cooldownと決定論的targeting
7. [x] 同時解決方式と位置競合ルール
8. [x] Monte Carlo、dataset schema、batch runner
9. [x] terrain、LOS、cover、collision
10. [x] objective等の追加戦術
11. [x] 感度分析、妥当性検証、代理モデル用export
