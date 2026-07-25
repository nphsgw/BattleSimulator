# Simulation Rules

## Purpose
このファイルは、戦闘シミュレーションの独自仕様を定義する正本とする。
現行実装の詳細仕様は `docs/current-spec.md` を参照する。

## Current Rule Baseline
- rules version `1.0` は、2 次元、離散時間、unit 単位の agent-based model とする
- 1 tick は 1 秒、距離は任意の一貫した距離単位、速度は距離/tick とする
- 攻撃は hitscan とし、弾丸の飛翔時間と弾薬は扱わない
- 独自仕様を追加したら、このファイルに明記する

## Current Explicit Rules
- `Terrain(form=None)` は「地形なし」を意味し、高低差補正のないフラット地形として扱う
- グループ単位の初期ターゲット割り当てでは、ターゲットは敵配列内の相対位置ではなく `M` 全体の unit index を保持する
- 選択した陣営の内部 ID が 0 始まりの連番でなくても、ターゲット探索と戦闘を実行できる
- 現在のターゲットが死亡した場合は、その時点で生存している敵だけから再選択し、同じ tick の行動には新しいターゲットへの距離と高低差を使う
- `Composite.init_ai` は初期ターゲット選択に、`Composite.rolling_ai` は対象死亡後の再選択に使用する
- rules version `1.0` の実効射程はunitの `Range` とし、legacy AIだけ
  `range * ((z^2 / 3) + 1)` を維持する
- 射程内の命中率は `acc * (1 - dodge) * (1 - 0.5 * distance / effective_range)` とし、距離係数は射手直上で 1、射程限界で 0.5 とする
- legacy `aggressive` の5%前進判定と命中判定には独立乱数を使う。
  rules version `1.0` に5%強制前進はない
- データベース列 `Miss` は後方互換のため名前を維持するが、意味はそのユニット自身のミス率ではなく、攻撃対象になったときの回避率 `dodge` とする
- rules version `legacy-0.3` の各 tick は unit index 昇順の逐次解決とする
- rules version `1.0` の各 tick は開始時 snapshot から判断し、移動後に攻撃を
  予約して tick 終了時に一括反映する。相打ちは有効とする
- 同距離時の target tie-break に配列 index を使用せず、stable unit IDを使う。
  `random` doctrineだけtargeting subsystem seedを使う
- 敵へ接近するときは射程境界を移動上限とし、移動線分の交差判定で
  高速unit同士の通り抜けも防ぐ
- 返却フレームは初期状態を frame 0 とし、各 tick の解決後の状態を追加する。最大 tick 到達時も最後の更新結果を含める
- 装甲がダメージを吸収した後の `armor` は 0 未満にせず、超過ダメージだけを HP に適用する
- ユーザー指定の戦場 bounds は最小範囲として維持し、初期配置が外側にある場合だけ該当方向へ拡張して警告する
- 戦場座標から地形配列の tile index へ変換するときは、両端の座標を有効な index 範囲へ対応させる
- 関数から生成した一定高の地形は、正規化後のフラット地形として扱い、`NaN` を生成しない
- `close_weak` は候補敵間で距離と残存耐久力 (`max(hp, 0) + max(armor, 0)`) をそれぞれ 0..1 に正規化してから重み付けする
- ユニット数値は有限値とし、`HP > 0`, `Armor >= 0`, `Damage >= 0`, `Accuracy` と `Miss` は 0..100、`Movement Speed >= 0`, `Range > 0`,
  `Attack Interval >= 1`, `Radius > 0` を満たす
- threat scoreはdistance、durability、expected damage、objective importanceを
  0..1へ正規化し、Compositeの非負doctrine weightsで合成する
- 既存データセットでの基本シミュレーションは継続して動作することを優先する

## Planned Next Rules
- 独自ユニットを追加するときは、既存ステータス列で表せる範囲から始める
- 独自 AI を追加するときは、既存 AI と同じ入力契約を維持する
- 将来 initiative を追加する場合は明示的な入力特徴量とし、配列順を使わない
- 可視化とアニメーションの詳細方針は `docs/visualization-rules.md` に分離して記録する

## Rules to Record Here
- ユニットの基本ステータス
- ダメージ計算ルール
- 射程、移動、ターゲティングのルール
- 地形補正のルール
- ランダム性の扱い
- 勝敗判定のルール

## Change Policy
- シミュレーション結果が変わる変更は、実装前または同時にここを更新する
- 後方互換を壊す場合は、その理由を記録する
- `Battle.simulate()` の frame 戻り値と `Battle.simulate_k()` の DataFrame 戻り値は
  rules version 1 でも維持し、構造化結果は `Battle.result_` へ追加する
- 再現性の保証範囲は、同一 battlesim、Python、NumPy の版と同一 platform 上とする
  platform や依存ライブラリをまたぐ bit 単位一致は保証しない

## Termination And Outcome

- `elimination`: 生存陣営が1つになった
- `mutual_destruction`: 生存陣営が0になった
- `timeout`: `max_ticks` に達した
- `stalemate`: HP、armor、位置、objective progress に一定 tick 変化がない
- winner は team ID の tuple とする。未決着・相打ちは空、同tickに別objectiveを
  達成した場合は複数を許す。複雑な同盟はrules version 1では扱わない

## Spatial Rules Version 1

- 移動補正は移動元から移動先への標高勾配で計算する
- line-of-sight は attacker と target の間を地形上で標本化し、線形補間した
  視線より地形が高い場合に遮蔽とする
- unit は `Radius` を持ち、移動線分の接触時刻で停止した後、残る重なりを
  soft separationで解消する
- armor は rules version 1 では damage を先に吸収する追加耐久値として維持する
- objective は円形 zone とし、単独陣営が占有して必要 tick を満たした場合に勝利する
