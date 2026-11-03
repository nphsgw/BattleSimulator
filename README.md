# battlesim: Python でユニット同士の戦闘をモデル化し、アニメーション表示する

[![pypi](https://img.shields.io/pypi/v/battlesim)](https://img.shields.io/pypi/v/battlesim)
[![last_commit](https://img.shields.io/github/last-commit/gregparkes/BattleSimulator)](https://img.shields.io/github/last-commit/gregparkes/BattleSimulator)
[![repo_size](https://img.shields.io/github/repo-size/gregparkes/BattleSimulator)](https://img.shields.io/github/repo-size/gregparkes/BattleSimulator)
[![replit](https://repl.it/badge/github/gregparkes/BattleSimulator)](https://repl.it/github/gregparkes/BattleSimulator)

矢印同士が動き、攻撃し合う様子を眺めたくありませんか？ それならこの
**BattleSimulator** がぴったりです。
[Totally Accurate Battle Simulator](https://steamcommunity.com/app/508440) に
親しんでいる方なら、基本的なアイデアの多くがそこから来ていることに気づき、
きっと気に入ってくれるはずです。

<p align="center">
  <img src="simulations/main.gif" alt="Image not found">
</p>

## 主な機能

`battlesim` が得意とすることの一部です。

- 数行のコードで、ゼロからシミュレーションを組み立てられる。
- 明示的な seed とバージョン管理された結果による、再現可能な戦術試行。
- 柔軟性: ユニットの値はデータファイルから読み込まれ、AI の選択肢も柔軟。
- 監査可能な同時 tick 方式の戦闘と、従来の JIT カーネルの併存。
- 可視化: アニメーションの見た目をカスタマイズできる。

## インストール

`battlesim` の要件:

- python (>= 3.12)
- numpy (>= 1.11.0)
- pandas (>= 0.25.1)
- matplotlib (>= 3.1.1)
- numba (>= 0.45)

アニメーションを gif として出力する場合は、次も必要です。

- ffmpeg (>=4.2)

必須ではありませんが、次のパッケージがあると利用体験が大きく向上します。
Jupyter プロジェクトに馴染みがない場合は [こちら](https://jupyter.org/) を参照してください。

- jupyter (1.0.0)

### GitHub リポジトリをクローンする場合

この [GitHub リポジトリ](https://github.com/gregparkes/BattleSimulator) をクローンする場合は、次を実行します。

```
git clone https://github.com/gregparkes/BattleSimulator
cd BattleSimulator
uv python install 3.12
uv sync --extra all --extra notebook
```

仮想環境を手動で有効化せずにパッケージのコマンドを実行したい場合は、`uv run` を使います。

```
uv run python
uv run jupyter notebook
```

生成された仮想環境を直接有効化したい場合は次のようにします。

```
source .venv/bin/activate
jupyter notebook
```

`notebook` extra には、Jupyter 一式と、インタラクティブな可視化 notebook 用の
`ipywidgets` が含まれます。

### Notebook に依存しない可視化

主たるインタラクティブビューアは、ローカルの Web アプリケーションとして動作します。

```console
uv run --extra app streamlit run apps/battle_viewer.py
```

または:

```console
make app
```

ビューアには、戦闘の設定、フレーム再生速度の調整、再生/一時停止/リプレイ操作、
フレームスライダー、デバッグオーバーレイの切り替え、PNG ダウンロードが備わっており、
notebook は不要です。シミュレーション完了後は、既定で最初のフレームから
毎秒 1 フレームで再生が始まります。

再生中、戦闘ビューでは各ユニットに `#1`、`#2` のような固定番号が表示されます。
隣のパラメータパネルは同じ番号を使い、各ユニットの陣営、種別、状態、HP、
アーマー、ターゲット、地形由来の値を、戦闘ビューを覆うことなく表示します。

非インタラクティブに使う場合は、TOML のシナリオを直接画像へレンダリングできます。

```console
uv run battlesim-render scenarios/clone-vs-droid.toml battle.png
```

ダメージ適用の様子を分かりやすく確認するには、同梱の 5 tick の決闘シナリオを使います。
両ユニットとも、HP より先にアーマーが減ります。

```console
uv run battlesim-render scenarios/damage-demo.toml damage-demo.png --frame 3
```

`Battle.sim_jupyter()` は、互換性のため、また教材や探索的な利用のために引き続き使えます。

### テストの実行

テストとフォーマット用の依存関係は `all` extra に含まれています。
その上で次を実行します。

```
uv run pytest -v
```

### フォーマット

プロジェクトのフォーマットと lint には次を使います。

```
make format
```

推奨の読み取り専用検証ワークフローには次を使います。

```
make check
```

既定の `ruff` と `ty` のワークフローは、現状 `battlesim/` とテストスイートを対象とします。
一部のテストは実行時検証を確かめるために意図的に不正な値を渡しているため、
その意図が型検査器に明示されるよう注釈を付けています。notebook が中心の
`examples/` と `teaching/` ディレクトリは、日常的な静的解析と型検査から意図的に除外されています。

## 使い方: 基本編

まず、`uv` 環境が同期されていることを確認してください。加えて、シミュレーションを
アニメーションとして生成するには、動画変換パッケージ **ffmpeg** が必要です。

次に、パッケージを次のようにインポートします。

```python
import battlesim as bsm
```

記述量を減らすため、`bsm` という短縮名の使用を推奨します。Jupyter notebook を使う場合は、
次のコードも推奨します。

```python
battle = bsm.Battle(seed=42, rules=bsm.BattleRules(max_ticks=200))
# これまでどおり軍を設定してから:
frames = battle.simulate()
print(battle.result_.termination_reason)
print(battle.result_.winner_team_ids)
```

`simulate()` は引き続きアニメーションのフレームを返します。バージョン付きの結果、
seed、終了理由、チーム別の指標、イベントログは `result_` から取得できます。

```python
import matplotlib.pyplot as plt
plt.rcParams["animation.html"] = "html5"
```

2 行目は、アニメーションを描画する際に重要です（利用にあたっていくつか問題があるため）。
重い処理はすべて `bsm.Battle` オブジェクトが担い、行いたい操作のための簡潔なインターフェースを提供します。

```python
bat = bsm.Battle("datasets/starwars-clonewars.csv")
```

ここでは「データセット」を指定しており、ユニットの名簿はすべてここから引かれます。
このファイルの形式の詳細はドキュメントを参照してください。次に、軍を構成するユニットを
指定します。たとえばこの Star Wars の例では、クローン・トルーパーと B1 バトルドロイドの
対戦を指定できます。

これは `Composite` というメタ情報オブジェクトを使って行います。`Composite` は
特定の種別のユニットの集まりを保持します。

```python
armies = [
    bsm.Composite("B1 battledroid", 70),
    bsm.Composite("Clone Trooper", 50)
]
bat.create_army(armies)
```

内部では、シミュレーションを実行できる状態の効率的な numpy 行列が作られます。
これは `battle.M_` オブジェクト（異種混在の `ndarray`）に格納されます。既定では、
各 Composite は (0, 0) を中心とするガウス分布で重なるように配置されます。Composite の初期化時に
`Sampling` クラスで新しいサンプリングを指定することも、直接上書きすることもできます。

```python
bat.composition_[1].pos = bsm.Sampling("normal", 10., 2.)
```

それではシミュレーションを実行します（初回の実行は、JIT が大量のコードをコンパイルするため、
かなり遅い点に注意してください）。

```python
F = bat.simulate()
```

既定では、シミュレーション関数は各ステップで重要なパラメータを記録し、最後にそれらを
*ロング形式* の異種混在 `ndarray` として返します（キャッシュ要素 `sim_` としても保持されます）。
さらに、何が起きているかを見たいので、Battle オブジェクトの便利メソッドでフレームを
アニメーション化できます。

```python
bat.sim_jupyter()
```

結果は次のとおりです。

<p align="center">
  <img src="simulations/sim2.gif" alt="Image not Found">
</p>

ここで `sim_jupyter` は、各ユニットオブジェクトを 2 次元空間上の quiver 矢印
（位置と、敵のほうを向く方向）として扱います。ターゲット同士は互いに近づき、
倒し合おうとします。死亡したユニットはマップ上で十字 **'x'** で表されます。

<p align="center">
  <img src="images/quiver1.svg" alt="Image not found">
</p>

あとは自由に探索し、調整し、矢印が近づいて倒し合う様子を楽しんでください。
このリポジトリには、豊富な
[examples](https://github.com/gregparkes/BattleSimulator/tree/master/examples)
があります。

より分析向けのビューにするには、デバッグ用プロッタに切り替えられます。

```python
bat.sim_jupyter(func=bsm.quiver_fight_debug)
```

このデバッグビューは、HP バーとターゲット線を追加します。各フレームに記録された
地形由来の補正値も確認したい場合は、地形テキストのオーバーレイを有効にできます。

```python
from functools import partial

bat.sim_jupyter(
    func=partial(bsm.quiver_fight_debug, show_terrain_text=True)
)
```

同じプロッタは `sim_export()` でも使えます。

`sim_jupyter(..., create_html=True)` を使うと、現在の実装では notebook 表示用の
HTML5 動画スニペットが返されます。

## 一歩先へ: 繰り返し実行

ランダム性による偏りを排除して、複数回の実行で各チームがどれだけ戦えるかを見たい場合、
定義済みの `bsm.Battle` オブジェクトには `simulate_k()` メソッドがあります。`k` は
実行したい回数です。`simulate()` 単体とは異なり、フレームの `ndarray` は返さず、
各イテレーションで生き残った各チームのユニット数を返します。

```python
runs = battle.simulate_k(k=40)
```

これは機械学習に似たインターフェースを作る第一歩です。結果は分類（勝利チーム）や回帰
（生存ユニット数）のターゲットになり、ユニット構成やエンジンの各側面などを入力にできます。

## v0.3.6 の新機能

この [最新の更新](CHANGELOG.md) には、次のような注目すべき変更があります。

- **地形（Terrain）** の導入。アニメーション化された戦闘に 3D 的な疑似的奥行きを与える大きな拡張です。高さがユニットの移動速度に影響し、高い丘では（最大 50% の）地形ペナルティが適用されます。また、丘の上のユニットは射程が伸び、敵ユニットを高所から撃ち下ろすとダメージが増加します。
- *アーマー* の導入。アーマーは、ユニットを損傷から守るもう一つの体力バッファとして働きます。

## 教材シリーズ

本格的なパッケージシミュレータであるだけでなく、`teaching/` サブフォルダには
Jupyter notebook 形式の
[教材](https://github.com/gregparkes/BattleSimulator/tree/master/teaching)
があります。パッケージの開発過程をたどり、オブジェクト指向（OO）実装と numpy 流の実装を
比較・対照し、パフォーマンス、プロット、アニメーションなどを扱います。この教材が興味深く、
パッケージを使う際や、将来ご自身でパッケージを開発する際の助けになれば幸いです。

これまでに扱った内容:

1. 基礎: データセットのインポート、`Unit` クラス、基本的なシミュレーション
2. `Unit` クラスの改善と、パフォーマンスのためのシミュレーション早期終了
3. シミュレーションのプロットと、パフォーマンス駆動の開発

これはプロジェクトの歩みをたどり直す形で、現在も開発が進められています。
これに関連するレガシー関数はすべて *battlesim/legacy.py* にあります。

## 今後の計画

- 高さを活用する AI 行動（丘を占拠するなど）を追加する。
- 「防御的」な AI を開発する。

この資料を利用する際は、適切に出典を明記し、[ライセンス](LICENSE.txt) に従ってください。
