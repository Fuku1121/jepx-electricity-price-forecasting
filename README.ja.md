# JEPX価格予測と蓄電池の充放電最適化

[English](README.md) · [技術文書](docs/README.md) · [設計判断](docs/DESIGN_DECISIONS.md)

## プロジェクト概要

電力価格の予測から、その予測を使った蓄電池の運用計画までをつなぐPythonプロジェクトです。
Stage 1では [Lago et al. (2021)](https://doi.org/10.1016/j.apenergy.2021.116983) の議論を参考に、
LEAR-style LASSOをJEPXの30分単位のシステムプライスに適用しました。
Stage 2では既存の予測を固定して充放電を最適化し、実価格で評価します。

データは2022〜2024年度、両段階のテスト期間は **2024-04-01〜2025-03-31の365日**です。
論文の完全再現ではなく、日本市場に合わせた簡略版を扱います。

## 研究の問い

1. 過去の価格を使うLASSOは、前日・前週価格による単純な予測を上回るか。
2. 予測誤差の改善は、同じ蓄電池条件での運用価値の改善につながるか。

## 主な結果

Stage 1は17,520コマを評価しました。単位は円/kWhです。

| モデル | MAE | RMSE |
|---|---:|---:|
| 前日同時刻 | 1.8547 | 2.9903 |
| 7日前同時刻 | 2.6453 | 3.9525 |
| 曜日に応じた前日・7日前の切替 | 1.8981 | 2.9987 |
| LEAR-style LASSO | **1.5581** | **2.2918** |

LASSOのMAEは最良naiveより **16.00%低下**しました。一方、日別では **156/365日** で負けています。
0.01円/kWh未満の予測54件も補正せず評価に残しました。
[全結果・失敗例](docs/RESULTS.md) ／ [数値の正本](results/metrics.csv)

## 方法

- **データ**：JEPX公式のシステムプライス。1,096日、52,608件。
- **特徴量**：過去の価格曲線、7日間の同時刻統計、曜日の計247列。
- **モデル**：48コマごとに独立したLASSO。標準化は学習期間だけで推定。
- **評価**：日付順に分割し、検証期間でalpha=0.1を選択。テストではalphaを固定し、過去データで毎日再学習。
- **検証**：未来価格の書き換え、データ整合性、制約・単位のテスト。
  ローカルとGitHub Actions（Python 3.11/3.12）で **52 tests passed**。

前受渡日のオークション価格曲線が予測時点で利用できることを仮定します。
[情報範囲・リーク防止](docs/METHODOLOGY.md) ／ [論文との差](docs/PAPER_NOTES.md) ／ [設計判断](docs/DESIGN_DECISIONS.md)

## Stage 2：蓄電池の充放電最適化

SciPy/HiGHSのMILPで日次の計画を作ります。仮想電池は **1 MWh・充放電各0.5 MW**、
SOC 10〜90%、日初・日末50%、各方向の効率95%（往復90.25%）です。
binary変数で同時充放電を禁止します。

運用計画は予測価格だけで固定し、その後に実価格で評価します。
未来価格を使う **Perfect-foresight upper bound** は別関数による実行不可能な比較上限です。
標準条件・劣化費用0での年間代理収益は次のとおりでした。

| 戦略 | 年間代理収益（円） | マイナスの日数 |
|---|---:|---:|
| 運用なし | 0 | 0 |
| 前日Naive予測 | 2,233,270 | 8 |
| LEAR予測 | **2,532,089** | 2 |
| Perfect-foresight upper bound | 2,899,726 | 0 |

LEARは年間で **298,819円（13.38%）** 上回りましたが、日次では **112日** 下回りました。
標準条件、往復効率80・90・95%、throughput費用1・3円/kWhの固定した全6ケースを掲載しています。
[数式・条件・再現](docs/BATTERY_OPTIMIZATION.md) ／ [損失日・全感度分析](docs/BATTERY_RESULTS.md)

## この実験から分かったこと

- 単純な前日予測が最も強いbaselineでした。LASSOの年間平均の改善は、毎日の勝利を意味しません。
- **43日** はLEARのMAEが良くても蓄電池収益が低い日でした。
  **Lower forecast error does not automatically imply higher operational value.**
- 未来価格が当日の予測に混ざらないことと、実価格が確定済みの計画を変えないことを、別々の書き換えテストで検証しました。
- system priceによる収支だけでは、実設備の運用収益を判断できません。

## 限界

1市場・1テスト年の記述的な比較です。外生予測、祝日特徴量、公表時点のデータスナップショットは未整備です。
蓄電池比較のNaive選定には既存Stage 1のtest MAE順位を再利用し、日末SOCも固定しています。
一般的な優位性や統計的有意差は、この結果だけでは結論できません。

蓄電池の結果は **仮想条件・system priceによる研究用proxy** です。実際はarea price等で決済される可能性があります。
系統料金、インバランス、市場インパクト、約定、送電制約、設備投資・固定費は未反映で、劣化も単純なthroughput費用です。
Perfect foresightは実行できず、これらの数値は商用利益の証明ではありません。[今後の課題](docs/FUTURE_WORK.md)

## 再現手順

Python 3.11以上。リポジトリ直下で実行します。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
# 公式CSVの取得方法・利用条件は data/README.md を参照
python scripts/download_or_prepare_data.py --download-years 2022 2023 2024
python scripts/run_experiment.py --output results/stage1_reproduction
python scripts/run_battery_backtest.py --predictions results/stage1_reproduction/predictions_full.csv
```

Windowsでは `.venv\Scripts\Activate.ps1` で有効化してください。
[手動データ取得](data/README.md)にも対応しています。再計算先を分けて公開済みStage 1の結果を保持します。
原データ・全予測・全スケジュールはGit管理外です。実行時の版は `requirements-lock.txt`、
[詳細手順](docs/BATTERY_OPTIMIZATION.md#reproduction--再現)には入力照合と環境差を記載しています。

## リポジトリ構成

```text
src/jepx_forecasting/  価格予測、電池モデル、MILP、バックテスト
scripts/              データ準備と実験の実行
configs/              固定した蓄電池実験条件
tests/               両段階の合成データによる検証
docs/                手法、結果、設計判断
results/              Stage 1の結果とbattery/の結果
```

## 作者の担当範囲

作者は、対象論文の考え方をJEPXへ適用し、時系列評価でnaiveと比較する方針を依頼しました。
その後、予測を使った蓄電池の意思決定への拡張を指示し、不利な結果を隠さないことと既存実験の保持を求めました。

[設計判断](docs/DESIGN_DECISIONS.md)では、確認できる依頼内容と、本人の選択理由の確認が必要な実装判断を区別しています。
[今後の開発手順](docs/DEVELOPMENT.md)に、判断と検証を記録する流れをまとめています。

## AI-assisted development

Codexを論文解釈の補助、実装、コードレビュー、テスト作成、結果分析、文書整理に使用しました。
提案は必要に応じて引用文献、元データ、コード実行、テストと照合し、その根拠を技術文書に記録しています。

作者がプロジェクトの範囲を指示し、成果物の確認に責任を持ちます。
個々の実装判断や結果解釈をすべて本人が行ったとするものではなく、本人の確認状況・理由は設計判断の記録で確認します。

独自のコード・文書は [MIT](LICENSE)。JEPXデータと論文の権利は各権利者に帰属します。
[データ利用・出所の確認](docs/RELEASE_REVIEW.md)
