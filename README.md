# 3D Particle Analysis Pipeline

**CT スライス画像から 3D 粒子構造を自動解析する GUI ツール**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GUI](https://img.shields.io/badge/GUI-Available-blue.svg)](src/particle_analysis/gui/)

---

## 📖 目次

1. [目的](#目的)
2. [リポジトリの取得と起動](#リポジトリの取得と起動)
3. [フォルダ構成](#フォルダ構成)
4. [処理の流れ](#処理の流れ)
5. [最適 R 選択ロジック（v2.1 PeakCount 方式）](#-最適-r-選択ロジックv21-peakcount-方式)
6. [接触数可視化機能（Napari 5レイヤー表示）](#-接触数可視化機能napari-5レイヤー表示)
7. [Guard Volume（ガードレール）機能](#️-guard-volumeガードレール機能)
8. [出力ファイル](#出力ファイル)
9. [GUI 設定一覧](#-gui-設定一覧)
10. [トラブルシューティング](#トラブルシューティング)
11. [変更履歴](#変更履歴)

---

## 🎯 目的

**CT スキャンで撮影した複数の TIF/TIFF スライス画像から、3D 空間内の粒子（砂粒など）を高精度に二値化・分割し、接触数の傾向を評価しつつ最適な分割半径 r を自動決定**するツールです。GUI からマウス操作のみで実行できます。

---

## 🚀 リポジトリの取得と起動

### 1) クローン

```bash
git clone <YOUR_REPO_URL>
cd kenkyuu
```

### 2) 依存関係インストール

```bash
pip install -r requirements.txt

# GUI を使う場合（推奨）
pip install "napari[all]" qtpy matplotlib PySide6
```

### 3) （推奨）CT画像の前処理（コントラスト付与）

撮影した CT の TIF/TIFF を **そのまま GUI に入れるよりも**、先に `CT_Processor_APP.py` でコントラストを調整すると、二値化や分割が安定します。

```bash
python CT_Processor_APP.py
```

- **入力フォルダ**: 元の TIF/TIFF が直接並んでいるフォルダ
- **保存先フォルダ**: 前処理後画像の出力先（自動作成）

### 4) GUI の起動

```bash
python scripts/run_gui.py
```

「📁 Select CT Images Folder」→ 前処理済みフォルダを選択 →「🚀 分析開始！(GO)」

---

## 🏗️ フォルダ構成

```
kenkyuu/
├── README.md
├── CT_Processor_APP.py              # CT画像の前処理（コントラスト一括変換）
├── requirements.txt
├── config/
│   └── optimized_sand_particles.yaml
├── scripts/
│   ├── run_gui.py                   # GUI ランチャ
│   └── view_volume.py               # 3D 可視化（補助）
└── src/particle_analysis/           # メインパッケージ (v2.1.0)
    ├── __init__.py                  # パッケージ公開 API
    ├── processing.py                # 3D 二値化（2段階 Otsu, uint16 精度）
    ├── visualize.py                 # Napari 可視化ユーティリティ
    ├── config.py                    # パイプライン設定（dataclass 群）
    ├── utils/
    │   ├── common.py                # Timer, setup_logging
    │   └── file_utils.py            # 画像ファイル取得（自然順ソート）
    ├── contact/
    │   ├── core.py                  # 接触数計算（隣接ラベル走査）
    │   ├── guard_volume.py          # Guard Volume（境界粒子除外）
    │   └── visualization.py         # 接触数マップ生成（create_contact_count_map）
    ├── volume/
    │   ├── core.py                  # 侵食→種→EDT→Watershed 分割
    │   ├── optimizer.py             # r 最適化オーケストレーション + R 選択ロジック
    │   ├── data_structures.py       # OptimizationResult / OptimizationSummary
    │   ├── metrics/
    │   │   ├── basic.py             # 粒子体積・最大粒子割合
    │   │   ├── dominance.py         # HHI・Gini・Top-k share
    │   │   └── stability.py         # VI（Variation of Information）・Dice
    │   └── optimization/
    │       ├── utils.py             # 膝点検出（kneedle）
    │       └── algorithms.py        # Pareto+distance（フォールバック用）
    └── gui/
        ├── main_window.py           # メイン UI（簡単操作＋詳細設定 + 5タブ結果表示）
        ├── workers.py               # バックグラウンド最適化ワーカー（QThread）
        ├── pipeline_handler.py      # 3D 二値化パイプライン呼び出し
        ├── widgets.py               # カスタムウィジェット（ResultsTable, MplWidget 等）
        ├── metrics_calculator.py    # GUI 用メトリクス計算
        ├── results_export.py        # 後処理分析 + CSV 出力（InteriorAnalysis）
        ├── napari_integration.py    # Napari 連携（NapariViewerManager: 3D 表示 3種）
        ├── config.py                # GUI 定数（Napari 設定含む）
        ├── plot_utils.py            # Matplotlib ダークテーマ描画ヘルパー
        ├── utils.py                 # GUI 汎用ユーティリティ（Napari エラー処理等）
        ├── launcher.py              # GUI 起動エントリポイント
        └── style.qss                # Qt スタイルシート（ダークテーマ）
```

---

## 🔄 処理の流れ

### ステップ 1: 📸 高精度 3D 二値化（インメモリ）

- TIF/TIFF を uint16 のまま積層し 3D ボリューム化
- 2 段階 Otsu（全体 → 前景抽出後の再 Otsu）
- 前景極性の自動判定（明/暗）
- 小物体除去・任意クロージング

実装: `processing.load_and_binarize_3d_volume()`

### ステップ 2: ✂️ 粒子分割（半径 r を走査）

- 半径 r の球状構造要素で侵食 → 種領域ラベル
- EDT を用いた負距離で Watershed 復元
- 粒子数・最大粒子割合・平均接触数（Guard Volume 内部粒子のみ）を各 r で計算
- 処理はすべてインメモリ。最適 r のラベル配列のみ最後に保存

実装: `volume.core.split_particles_in_memory()`

### ステップ 3: 🎯 r の自動選択（ハード制約＋ピーク粒子数＋接触レンジ）

**[詳細は次セクション参照](#-最適-r-選択ロジックv21-peakcount-方式)**

実装: `volume.optimizer.select_radius_by_constraints()`
出力: 最適 r、全 r の指標テーブル（CSV）、最適 r のラベル配列（npy）

### ステップ 4: � 後処理・グラフ表示

解析完了後、バックグラウンドワーカーが最適 r のラベルを再読み込みし、Guard Volume フィルタリングを経て接触数・体積を集計します。結果は GUI の 5 つのタブに表示されます：

| タブ            | 内容                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| 📊 最適化の進捗 | 各 r のリアルタイム結果テーブル（粒子数・平均接触数・最大粒子割合 等） |
| 📊 接触分布     | Guard Volume 内部粒子の接触数ヒストグラム                              |
| 📊 体積分布     | Guard Volume 内部粒子の体積ヒストグラム                                |
| 📊 体積vs接触数 | 体積 vs 接触数の散布図（線形回帰・相関係数付き）                       |
| 🎯 最終結果     | 最適 r・選択理由・統計サマリ + 3D 表示ボタン                           |

### ステップ 5: � 3D 可視化（任意）

「🎯 最終結果」タブの 2 つのボタンから Napari を起動できます：

- 「🔍 View 3D Results」: ベスト r のラベルを Napari でそのまま表示
- 「🎨 View 3D (Color by Contacts)」: 接触数に基づく 5 レイヤー可視化 **[→ 詳細](#-接触数可視化機能napari-5レイヤー表示)**

---

## 🎯 最適 R 選択ロジック（v2.1 PeakCount 方式）

v2.1 で R 選択ロジックを全面的に刷新しました。旧方式（限界効用プラトー検出）を廃止し、**ピーク粒子数方式**を導入しています。

### 背景と動機

旧方式は「粒子数の変化量が閾値以下になった点＝プラトー」として R を決定していましたが、以下の問題がありました：

- プラトーと判定された点が、実は粒子数が**減少し始めた**直後である可能性がある
- 過収縮（erosion が強すぎて粒子が消滅し始めた状態）を最適値として選んでしまうリスク

### 新しい選択ロジック

3つの評価基準に基づいて最適な R を決定します：

#### 基準 ①: 最大粒子割合（largest_particle_ratio ≤ 3%）

- **r\*** = `largest_particle_ratio ≤ τratio (0.03)` を最初に満たす R
- これにより、分割不足の R を除外する

#### 基準 ②: ピーク粒子数（R_peak）

- r\* 以降かつ `lpr ≤ τratio` を満たす R 群の中で、**粒子数が最大**となる R を `R_peak` とする
- 旧方式のプラトー検出と異なり、「粒子が減少し始める直前（＝最も多くの粒子が検出できた点）」を重視する

#### 基準 ③: 平均接触数（mean_contacts ∈ [5, 9]）

- 振とう充填の理論値（平均接触数 ≈ 7）に基づき、物理的に妥当な接触数の範囲を [5, 9] に設定

### 選択優先順位

| 優先度           | 条件                                     | reason フラグ       |
| ---------------- | ---------------------------------------- | ------------------- |
| **(A)** 最優先   | R_peak の接触数が [5, 9] 内              | `peak_and_contacts` |
| **(B)**          | r\* 以降で接触数が [5, 9] に入る最初の R | `contacts_only`     |
| **(C)**          | R_peak（接触数制約なし）                 | `r_peak`            |
| **(D)**          | r\*（接触数・ピーク制約なし）            | `r_star`            |
| **(E)** 最終手段 | 最大 R                                   | `max_r`             |

### フォールバック

上記の制約ベース選択が例外で失敗した場合は、**Pareto + normalized distance** 法にフォールバックします（HHI・膝点距離・VI安定性の3目的最適化）。

### デフォルトパラメータ

| パラメータ         | デフォルト | 説明                                |
| ------------------ | ---------- | ----------------------------------- |
| `tau_ratio`        | 0.03 (3%)  | 最大粒子割合の閾値                  |
| `contacts_range`   | (5, 9)     | 許容平均接触数の範囲                |
| `smoothing_window` | None       | 移動平均窓（安定化用、1 or 2 推奨） |

---

## 🎨 接触数可視化機能（Napari 5レイヤー表示）

GUI の「🎨 View 3D (Color by Contacts)」から、粒子の接触数に基づく 5 レイヤー構成の 3 次元可視化が可能です。実装: `gui.napari_integration.NapariViewerManager.load_best_labels_with_contacts()`

### Layer 1: All Particles Heatmap【デフォルト: 可視】

- **カラーマップ**: `turbo`（青→緑→黄→赤）
- 全粒子の 3D 形状を接触数で色付け（MIP レンダリング）
- `full_contacts`（Guard Volume 外を含む全粒子）を使用し、空間的な全体像を把握

### Layer 2: Guard Volume Boundary【デフォルト: 可視】

- Guard Volume の境界シェル（厚さ 2 voxels）を半透明で表示
- カラーマップ: `green`、opacity: 0.3
- 内部粒子と境界粒子の区画を視覚的に確認できる

### Layer 3: Boundary Particles（除外粒子）【デフォルト: 非表示】

- Guard Volume 外の境界粒子のみグレーで表示
- 統計から除外された粒子数をレイヤー名に表示

### Layer 4: Weak Zones（破断予測マップ）【デフォルト: 非表示】

- **内部粒子のみ**、接触数 0～4 の粒子を `turbo` カラーマップで強調
- 破断起点の候補となる低接触領域を信頼性の高いデータのみで可視化

### Layer 5 ※ Centroids（重心点群）

> 現在の実装では Layer 5 は追加されていません（将来の拡張用）

---

## 🛡️ Guard Volume（ガードレール）機能

境界効果を排除し、より正確な平均接触数を算出するための機能です。

### 動作原理

1. **マージン計算**: `margin = max(max_particle_radius × 2.0, 10 voxels)`
2. **内部粒子の判定**: マージン内に完全に含まれる粒子のみを「内部粒子」として判定
3. **統計計算**: 内部粒子のみの接触数で平均値を計算

実装: `contact/guard_volume.py`

---

## 📊 出力ファイル

解析完了後、`output/gui_run_YYYYMMDD_HHMM/` に保存されます：

### 最適化結果

| ファイル名                 | 説明                                                                                                                               | 形式  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----- |
| `optimization_results.csv` | r ごとの集計（radius, particle_count, largest_particle_ratio, mean_contacts, interior_particle_count, excluded_particle_count 等） | CSV   |
| `labels_r{best}.npy`       | 採択 r のラベル 3D 配列（int32）。Napari で直接読み込み可能                                                                        | NumPy |

### グラフデータ（Guard Volume 内部粒子のみ）

| ファイル名                 | 説明                                      |
| -------------------------- | ----------------------------------------- |
| `contact_distribution.csv` | 接触数分布（ヘッダに統計情報）            |
| `volume_distribution.csv`  | 体積分布（ヘッダに統計情報）              |
| `volume_vs_contacts.csv`   | 体積 vs 接触数（ヘッダに回帰傾き・相関R） |

---

## 🧩 GUI 設定一覧

| 設定                       | デフォルト      | 場所              |
| -------------------------- | --------------- | ----------------- |
| 最大半径                   | 7               | Advanced Settings |
| 連結性                     | 6（面接触のみ） | Advanced Settings |
| τratio（最大粒子割合閾値） | 0.03 (3%)       | Advanced Settings |
| 接触数レンジ [min, max]    | [5, 9]          | Advanced Settings |
| 平滑窓                     | None            | Advanced Settings |

> **連結性の選択肢**
>
> - `6-Neighborhood`（推奨）: 面接触のみ。物理的接触の評価に適切
> - `26-Neighborhood`: 辺・頂点接触も含む。密充填の場合に使用

---

## 🔧 トラブルシューティング

### GUI 依存の不足

```bash
pip install "napari[all]" qtpy matplotlib PySide6
```

### Qt バックエンド問題

```bash
pip uninstall -y PySide6 PyQt5 PyQt6
pip install PySide6
```

### 画像が見つからない / 読み込めない

- TIF/TIFF 形式を使用（GUI は TIF/TIFF のみ認識）
- 画像が直接並ぶフォルダを選択（サブフォルダ不可）
- コントラストが低い場合は `CT_Processor_APP.py` で前処理

### メモリ不足

- インメモリ処理のため RAM に余裕が必要
- 画像間引き・領域切出し・最大半径の抑制で軽減可能

---

## 📝 変更履歴

### v2.0.0

- GUI ベースの解析パイプライン（3D Otsu → Watershed → R 最適化）
- Guard Volume による境界粒子除外
- 接触数ベース 3D 可視化
- CSV 自動出力（接触分布・体積分布・散布図）

### v2.1.0 — R 選択ロジック刷新・リファクタリング・Napari 拡張

#### R 選択ロジックの変更

- **旧**: 限界効用プラトー検出（`τgain_rel` パラメータ）で R を決定
- **新**: ピーク粒子数方式（`R_peak`）で R を決定
  - `largest_particle_ratio ≤ 3%` を満たす R 群の中で粒子数最大の R を `R_peak` とする
  - `R_peak` の接触数が [5, 9] 内なら最優先で採用

#### デフォルト値の変更

| パラメータ           | 旧        | 新            | 理由                                     |
| -------------------- | --------- | ------------- | ---------------------------------------- |
| `tau_ratio`          | 0.05 (5%) | **0.03 (3%)** | 5% では分割不足が残る                    |
| `contacts_range`     | [4, 10]   | **[5, 9]**    | 振とう充填理論値（平均接触数≈7）に基づく |
| `tau_gain_rel`       | 0.003     | **削除**      | プラトー検出自体を廃止                   |
| `DEFAULT_MAX_RADIUS` | 10        | **7**         | 過収縮を避けるためデフォルトを抑制       |

#### Napari 可視化の拡張（2レイヤー → 4レイヤー）

- **旧**: All Particles Heatmap + Weak Zones の 2 レイヤー
- **新**: 上記 2 レイヤーに加え、Guard Volume Boundary シェル + Boundary Particles（除外粒子）を追加
- `NapariViewerManager` クラスに集約（`load_best_labels`, `load_best_labels_with_contacts`, `load_all_radii`）

#### GUI の変更

- **τgain スピンボックスを完全削除**（ロジック廃止に伴い不要）
- τratio のデフォルトを 0.03 に変更
- 接触数レンジのデフォルトを [5, 9] に変更
- 結果タブを 5 タブ構成に整理（最適化進捗 / 接触分布 / 体積分布 / 体積vs接触数 / 最終結果）

#### コード整理（リファクタリング）

- **レガシー関数を削除**:
  - `determine_best_radius_advanced()`（重み付き複合スコア方式）
  - `calculate_composite_score()`（複合スコア計算）
  - `calculate_coordination_score()`（配位数スコア計算）
- **未使用 import の削除**: `asdict`, `OrderedDict`, `math`
- **`__init__.py` 群の整理**: レガシー関数の re-export を全て削除
- **`results_export.py` の追加**: 後処理分析（`InteriorAnalysis`）と CSV 出力を GUI ロジックから分離
- **バージョンを 2.1.0 に更新**

---

**3D Particle Analysis Pipeline v2.1** — 研究用途の再現性と操作性を両立する、GUI 主導の粒子解析ツール
