# 論文に基づくJEPX電力価格予測

**2段階の研究ポートフォリオです。** Stage 1はJEPX価格予測、Stage 2はその予測を使う蓄電池の充放電最適化です。予測をMILPへ入力し、制約を満たす計画を固定してから、実価格でout-of-sample評価します。
[蓄電池の数式・設計](docs/BATTERY_OPTIMIZATION.md) ／ [実行済み結果](docs/BATTERY_RESULTS.md)


[English](README.md) · [実験方法](docs/METHODOLOGY.md) · [詳細な結果](docs/RESULTS.md) · [論文ノート](docs/PAPER_NOTES.md)

Lago et al. (2021) の電力価格予測研究を読み、日本のJEPXスポット市場に
**LEAR-style LASSOモデルを適用した、AI支援による独立した研究・実装プロジェクト**です。
論文の完全再現ではなく、価格履歴と曜日を用いた簡略版を検証しています。

## 研究の問いと結論

**過去の価格と曜日だけを使うLASSOは、前日・前週の価格を使う単純な予測より、
翌日の48コマを正確に予測できるか。**

JEPX公式データを用い、2024年4月1日〜2025年3月31日の365日、17,520コマを評価しました。
今回の期間では、最良のbaselineに対してMAEが**16.00%減少**しました。
この比較だけで統計的有意差、別期間での優位性、収益性を主張することはできません。

| モデル | MAE（円/kWh） | RMSE（円/kWh） |
|---|---:|---:|
| 前日同時刻 | 1.8547 | 2.9903 |
| 7日前同時刻 | 2.6453 | 3.9525 |
| 曜日に応じた前日・7日前の切替 | 1.8981 | 2.9987 |
| **LEAR-style LASSO** | **1.5581** | **2.2918** |

数値の正本：[metrics.csv](results/metrics.csv)。出所：日本卸電力取引所（JEPX）。

![同じテスト期間でのMAE比較](results/figures/model_mae.png)

## 実装した内容

- **データ**：公式の2022〜2024年度CSV。2022年4月〜2025年3月の52,608件。
  対象はシステムプライス、単位は円/kWh、時間帯は日本時間です。
- **モデル**：48コマごとに独立したLASSO回帰。前日・2日前・7日前の全価格曲線、
  過去7日間の同時刻平均・標準偏差、曜日の計247特徴量を使います。
- **評価**：日付順に学習・検証・テストを分割し、検証期間だけでalphaを選択。
  テスト中はalpha=0.1に固定し、予測日より前のデータで毎日再学習します。
- **検証**：当日・未来の価格を書き換えても、その時点の特徴量・予測が変わらない
  テストとStage 2の蓄電池テストを含め、52件のpytestがローカルおよび
  GitHub Actions（Python 3.11 / 3.12）で成功しています。

データ取得・特徴量生成・学習・評価は別モジュールに分離しています。
本プロジェクトでは、第三者の予測リポジトリのソースコードを、実装の参照資料として意図的に利用したり、コピーしたりしていません。
LASSOの学習にはscikit-learnの最適化器を利用しています。

## 設計で重視した点

**受渡日と価格が決まる日を区別すること。** 翌日分のスポット価格は前日に約定するため、
予測時点に利用できる過去の約定価格だけを使います。履歴CSVから当時の公開・改訂時刻
までは検証できないため、その仮定も明記しています。

**未来の情報を前処理やモデル選択に混ぜないこと。** 標準化は毎日の学習データだけで行い、
移動統計は価格を過去にずらしてから計算します。テスト期間の成績を見てalphaを選び直しません。

**良くない結果も残すこと。** LASSOは156/365日で前日baselineに負け、
0.01円/kWh未満の予測を54件出しています。これらは除外・補正せず評価に含めました。

## 論文との差と限界

参考論文は複数市場の時間単位価格を対象に、外生変数、頑健な価格変換、複数の学習窓、
モデル平均化や統計検定を扱います。今回は日本の30分価格・1市場・1テスト年を対象とし、
外生変数や頑健変換、ensemble、DM/GW検定は実装していません。

次の研究課題は、入札時点で利用できた需要・再エネ予測を追加し、別の未使用年で再評価することです。
[蓄電池運用最適化](docs/BATTERY_OPTIMIZATION.md) はStage 2として実装・評価済みです。実市場の約定・費用・不確実性への対応は [今後の課題](docs/FUTURE_WORK.md) です。

## 再現とレビュー

| 確認したい内容 | 資料 |
|---|---|
| 論文の理解と今回の設計判断 | [PAPER_NOTES.md](docs/PAPER_NOTES.md) |
| 情報の利用可能時点・特徴量・分割 | [METHODOLOGY.md](docs/METHODOLOGY.md) |
| 結果・失敗例・数値の検証方法 | [RESULTS.md](docs/RESULTS.md) |
| 実行手順 | [English README / Reproduction](README.md#reproduction) |
| 公式データ取得・出所・利用条件 | [data/README.md](data/README.md) |
| コードとリークテスト | [src](src/jepx_forecasting/) · [tests](tests/) |
| 実行環境・データハッシュ | [run_metadata.json](results/run_metadata.json) |

原データと全期間の予測CSVはGit管理から除外し、集計結果・図・最初の7日分のサンプルを掲載しています。
完全な数値再計算には、公式データを取得して実験を再実行してください。

## 参考論文

Lago, J., Marcjasz, G., De Schutter, B., & Weron, R. (2021).
*Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms,
best practices and an open-access benchmark*. Applied Energy, 293, 116983.
[DOI](https://doi.org/10.1016/j.apenergy.2021.116983) · [arXiv](https://arxiv.org/abs/2008.08004)

## AI支援とライセンス

Codexを論文の解釈支援、実装、レビュー、テスト、文書作成に使用しました。
本人がすべて独力で作成したという意味ではありません。解釈・設計・結論の確認は著者の責任です。

独自のコード・文書は[MIT](LICENSE)。JEPXデータと引用論文の権利はそれぞれの権利者に帰属します。

## 蓄電池の充放電最適化

**研究の問い：** 同じ電池条件で、LEARの予測から作る計画は、既存の最良naive予測から作る計画より実現代理収益を改善するか。
既存の予測値、期間分割、alpha、モデル、Stage 1の結果は変更していません。

**Hypothetical research battery：** 容量1 MWh、充放電各0.5 MW、SOC 10〜90%、日初・日末50%、充電効率95%・放電効率95%（往復90.25%）。
単位を理解しやすい規模、容量の上下余裕、対称な初期状態、変換損失を説明するための仮想設定で、実在設備の模倣ではありません。

**数理最適化：** SciPy/HiGHSのMILPで、予測価格による売買差額からthroughput費用を引いた目的関数を最大化します。SOC更新、出力・容量上限、日末SOC固定、binary変数による同時充放電禁止を入れます。
MW × 0.5時間 × 1000 = kWhとして計算します。標準ケースは劣化費用0です。

**バックテスト：** 2024-04-01〜2025-03-31の365日・1日48コマ。
運用停止、前日naive予測、LEAR予測、Perfect-foresight upper boundを同じ条件で比較します。
前日naiveは既存Stage 1のtest MAE順位に基づく指定であり、新しい未使用データによるモデル選択ではありません。
予測だけで計画を固定し、その後に実価格で評価します。未来実価格を最適化に渡すのは、実行不可能な上限benchmarkだけです。

| Strategy | Annual proxy net revenue (JPY) | Negative days |
|---|---:|---:|
| No-operation | 0 | 0 |
| Naive forecast optimization | 2,233,270 | 8 |
| LEAR forecast optimization | 2,532,089 | 2 |
| Perfect-foresight upper bound | 2,899,726 | 0 |

標準条件ではLEARがNaiveを **298,819円（13.38%）** 上回りました。ただし日次収益では **112日** 下回り、うち **43日** はMAEが良くても収益が低い日です。
**Lower forecast error does not automatically imply higher operational value.**
予測誤差の改善がそのまま運用価値の改善を保証するわけではありません。損失日も隠さず、事前固定した往復効率80・90・95%、throughput費用1・3円/kWhの全感度結果を掲載しています。

JEPX system priceを用いた**研究用proxy**です。実設備はarea priceや別契約で決済される可能性があります。grid fees（系統料金）、imbalance costs、market impact、bid acceptance、transmission constraints、設備投資・固定運転費を考慮せず、全計画量の約定を仮定します。劣化コストは仮想の線形throughput費用で、寿命モデルではありません。電池条件も仮想設定です。Perfect foresightは実行不可能であり、この収益は商用運用・利益の証明ではありません。

[実行済み結果・失敗日・全感度分析](docs/BATTERY_RESULTS.md) ／ [数式と再現手順](docs/BATTERY_OPTIMIZATION.md)

```bash
python scripts/run_battery_backtest.py --predictions results/predictions_full.csv
python -m pytest -q
```

full予測ファイルはGit管理外です。新規cloneでは上記再現手順に従い、Stage 1の再計算先を別ディレクトリにして既存結果を保護してください。
Stage 2もAI支援による実装・検証・文書作成です。本人が内容を確認し、自分の言葉で説明する責任があります。
