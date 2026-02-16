# 3D Particle Analysis Pipeline

**CT スライス画像から 3D 粒子構造を自動解析する GUI ツール（現行実装ベース）**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GUI](https://img.shields.io/badge/GUI-Available-blue.svg)](src/particle_analysis/gui/)

---

## 📖 目次

1. [このシステムは何をするのか](#目的)
2. [リポジトリの取得と起動](#リポジトリの取得と起動)
3. [フォルダ構成（現行）](#フォルダ構成現行)
4. [処理の流れ（現行実装）](#処理の流れ現行実装)
5. [接触数可視化機能（3レイヤー表示）](#-接触数可視化機能3レイヤー表示)
6. [Guard Volume（ガードレール）機能](#️-guard-volumeガードレール機能)
7. [出力ファイル（現行仕様）](#出力ファイル現行仕様)
8. [トラブルシューティング](#トラブルシューティング)

---

## 🎯 目的

このシステムは、**CT スキャンで撮影した複数の TIF/TIFF スライス画像から、3D 空間内の粒子（砂粒など）を高精度に二値化・分割し、接触数の傾向を評価しつつ最適な分割半径 r を自動決定**するためのツールです。GUI からマウス操作のみで実行できます。

---

## 🚀 リポジトリの取得と起動

### 1) クローン

```bash
git clone <YOUR_REPO_URL>
cd kenkyuu
```

Windows PowerShell をお使いの場合は、上記コマンドを PowerShell/Terminal にそのまま貼り付けてください。

### 2) 依存関係インストール

```bash
pip install -r requirements.txt

# GUI を使う場合（推奨）
pip install "napari[all]" qtpy matplotlib PySide6
```

注: GUI 依存はスリム化のため `requirements.txt` に必ずしも含めていません。GUI 利用時に上記を追加インストールしてください。

### 3) （推奨）CT画像の前処理（コントラスト付与）

撮影した CT の TIF/TIFF を **そのまま GUI に入れるよりも**、先に `CT_Processor_APP.py` を使ってコントラストを調整した画像に置き換えると、二値化や分割が安定して **より良い結果になりやすい**ことが分かっています。

```bash
python CT_Processor_APP.py
```

起動後、GUI 上で以下を指定してください。

- **入力フォルダ**: 元の TIF/TIFF が直接並んでいるフォルダ
- **保存先フォルダ**: 前処理後画像の出力先フォルダ（自動作成されます）

前処理後は、保存先フォルダに **同名の TIF/TIFF** が出力されます。以降の解析は、この保存先フォルダを入力として使ってください。

### 4) GUI の起動

```bash
python scripts/run_gui.py
```

GUI 上で「📁 Select CT Images Folder」から **前処理後の TIF/TIFF 画像フォルダ（推奨）**を選択し、「🚀 分析開始！(GO)」を押してください。

---

## 🏗️ フォルダ構成（現行）

```
kenkyuu/
│
├── README.md
├── CT_Processor_APP.py        # CT画像の前処理（コントラスト一括変換）
├── requirements.txt
├── config/
│   └── optimized_sand_particles.yaml
├── scripts/
│   ├── run_gui.py              # GUI ランチャ
│   └── view_volume.py          # 3D 可視化（補助）
└── src/particle_analysis/
    ├── __init__.py
    ├── processing.py           # 3D 二値化（高精度 M2 実装）
    ├── visualize.py            # Napari 可視化ユーティリティ
    ├── config.py               # パイプライン設定（構造体）
    ├── utils/
    │   ├── common.py
    │   └── file_utils.py       # 画像ファイル取得（自然順）
    ├── contact/
    │   └── core.py             # 接触数計算・統計（保存APIは任意利用）
    ├── volume/
    │   ├── core.py             # 分割アルゴリズム（侵食→種→EDT→Watershed）
    │   ├── optimizer.py        # r 最適化と結果保存（CSV/labels）
    │   ├── data_structures.py  # 結果データ構造
    │   └── metrics/
    │       ├── basic.py        # 最大粒子割合など
    │       └── ...
    └── gui/
        ├── main_window.py      # メインUI（簡単操作＋詳細設定）
        ├── pipeline_handler.py # 3D 二値化（インメモリ、非保存）
        ├── workers.py          # 最適化ワーカー（バックグラウンド）
        ├── config.py           # GUI 定数（出力名など）
        ├── napari_integration.py, widgets.py, ...
```

---

## 🔄 処理の流れ（現行実装）

### ステップ 1: 📸 高精度 3D 二値化（インメモリ）

- TIF/TIFF を uint16 のまま積層し 3D ボリューム化
- 2 段階 Otsu（全体 → 前景抽出後の再 Otsu）
- 前景極性の自動判定（明/暗）
- 小物体除去・任意クロージング

実装: `processing.load_and_binarize_3d_volume()`
出力: 二値ボリューム（メモリ内）、統計情報（GUI ログに表示）

### ステップ 2: ✂️ 粒子分割（半径 r を走査）

- 半径 r の球状構造要素で侵食 → 種領域ラベル
- EDT を用いた負距離で Watershed 復元
- 粒子数、最大粒子割合（largest_particle_ratio）を計算
- （オプション）同一ラベルから接触数平均を計算（6/26 連結性は GUI で選択）

実装: `volume.core.split_particles_in_memory()`、`volume.metrics.basic.calculate_largest_particle_ratio()`

### ステップ 3: 🎯 r の自動選択（ハード制約＋限界効用＋接触レンジ）

1. r\* を決定: 最初に `largest_particle_ratio ≤ τratio` を満たす r
2. r ≥ r\* で同時成立を探索: `Δcount ≤ τgain_abs` かつ `mean_contacts ∈ [cmin, cmax]`
3. フォールバック: (同時成立) → (接触レンジのみ) → (r\*) → (max r)

既定: τratio=0.05、τgain_rel=0.003（=0.3% of base）、[cmin,cmax]=[4,10]、平滑化オプションあり

実装: `volume.optimizer.optimize_radius_advanced()` 内 `select_radius_by_constraints()`
出力: 最適 r、全 r の指標テーブル（CSV）、最適 r のラベル配列（npy）

### ステップ 4: 👀 可視化（任意）

- GUI の「🔍 View 3D Results」で Napari 表示（ベスト r のラベル）
- GUI の「🎨 View 3D (Color by Contacts)」で接触数に基づく3レイヤー可視化
- GUI タブで以下の分布グラフを表示（ファイル出力なし、すべて Guard Volume 内部粒子のみ）:
  - 「📊 接触分布」: 接触数ヒストグラム（Guard Volume Interior）
  - 「📊 体積分布」: 粒子体積ヒストグラム（Guard Volume Interior）
  - 「📊 体積vs接触数」: 粒子体積と接触数の散布図（回帰直線・相関係数 R 付き）

---

## 🎨 接触数可視化機能（3レイヤー表示）

GUI の「🎨 View 3D (Color by Contacts)」ボタンから、粒子の接触数に基づく3次元可視化が可能です。以下の3つのレイヤーが表示され、Napari上で切り替え可能です。

### Layer 1: Contact Heatmap（粒子接触ヒートマップ）【デフォルト表示: 可視】

- **手法**: Property Mapping
- **説明**: 各粒子の3D形状全体を、その粒子の接触数に応じて色付けします
- **カラーマップ**: `turbo`（青→緑→黄→赤のグラデーション）
  - **青系（低接触）**: 接触数が少ない粒子（0～4接触）
  - **緑系（中接触）**: 中程度の接触数（5～9接触）
  - **黄～赤系（高接触）**: 接触数が多い粒子（10接触以上）
- **表示方法**: Maximum Intensity Projection (MIP) レンダリング
- **用途**: 粒子形状そのものを見ながら、接触数の分布を直感的に把握
- **色の詳細**:
  - 接触数が少ないほど青に近く、多いほど赤に近い色で表示されます
  - 連続的なグラデーションにより、接触数の微細な違いも視覚的に識別可能

### Layer 2: Weak Zones（破断予測・危険地帯マップ）【デフォルト: 非表示】

- **手法**: Thresholding & Transparency
- **説明**: 構造的な弱点（低接触粒子）のみを強調表示します
- **表示条件**:
  - **接触数 0～4**: 100%不透明度で表示（警告色として強調）
  - **接触数 5以上**: 完全に透明（非表示）
- **カラーマップ**: `turbo`（Layer 1と同じ）
  - **接触数 0～4**: 青～緑系の色で表示（低接触領域を強調）
  - **接触数 5以上**: 完全に透明（非表示）
- **用途**: 破断起点の候補となる低接触領域を「血管のように」浮き上がらせて可視化
- **色の詳細**:
  - 接触数0～4の粒子のみが表示され、接触数が少ないほど青に近い色になります
  - 5接触以上の粒子は完全に非表示になるため、弱い結合部分だけが視覚的に浮き上がります

### Layer 3: Centroids（重心点群）【デフォルト: 非表示】

- **手法**: Point Cloud
- **説明**: 各粒子の重心位置を点として表示し、接触数に応じて色分けします
- **色分けルール**（離散的3段階）:
  - **接触数 0～4**: 明るい黄緑 `(0.6, 0.9, 0.2, 1.0)` - 低接触（潜在的な弱いゾーン）
  - **接触数 5～9**: 明るめシアン `(0.10, 0.70, 0.90, 1.0)` - 中接触（一般的）
  - **接触数 10以上**: 明るい赤橙 `(1.00, 0.35, 0.15, 1.0)` - 高接触（高密度・強度が高い）
- **点のサイズ**: 3ピクセル
- **用途**: 内部構造を迅速に把握。表面レンダリングでは隠れる内部粒子も確認可能

### 使用方法

1. GUIで解析を実行
2. 解析完了後、「🎨 View 3D (Color by Contacts)」ボタンをクリック
3. Napariが開き、3つのレイヤーが自動的に追加されます
4. Napariのレイヤーリストで各レイヤーの表示/非表示を切り替え可能

---

## 🛡️ Guard Volume（ガードレール）機能

境界効果を排除し、より正確な平均接触数を算出するための機能です。

### 目的

ボリュームの端にある粒子は、本来の接触数を正確に反映できないため、統計から除外します。ただし、内部粒子との接触数計算には境界粒子も含まれます。

### 動作原理

1. **マージン計算**: 最大粒子の等価半径に基づいて、適切なマージン（境界からの距離）を自動計算
   - 計算式: `margin = max(max_particle_radius × 0.3, 10 voxels)`
   - ただし、各次元の6%を超えないように制限（内部領域が88%以上を確保）
   - 1 voxel = 14μm の場合、最小マージンは約140μm

2. **内部粒子の判定**: マージン以内の領域（Guard Volume）に完全に含まれる粒子のみを「内部粒子」として判定

3. **統計計算**: 内部粒子のみの接触数で平均値を計算

### 実装詳細

- **モジュール**: `src/particle_analysis/contact/guard_volume.py`
- **主要関数**:
  - `calculate_guard_margin()`: マージンサイズの計算
  - `create_guard_volume_mask()`: 内部領域のマスク作成
  - `filter_interior_particles()`: 内部粒子の抽出
  - `count_contacts_with_guard()`: Guard Volume適用での接触数計算

### 統計情報

解析結果には以下の情報が含まれます：

- **内部粒子数**: Guard Volume内に完全に含まれる粒子数
- **除外粒子数**: 境界に接する粒子数
- **平均接触数（内部粒子のみ）**: より正確な統計値

---

## 📊 出力ファイル（現行仕様）

解析完了後、`output/gui_run_YYYYMMDD_HHMM/` に以下のファイルが保存されます：

### 最適化結果

| ファイル名                 | 説明                                                                            | 形式  |
| -------------------------- | ------------------------------------------------------------------------------- | ----- |
| `optimization_results.csv` | r ごとの集計（`radius, particle_count, largest_particle_ratio, mean_contacts`） | CSV   |
| `labels_r{best}.npy`       | 採択 r のラベル 3D 配列（int32）                                                | NumPy |

### グラフデータ（Excel等での再作成用）

解析完了時に、Guard Volume 内部粒子のみを対象とした以下の CSV が自動出力されます：

| ファイル名                 | 列                                              | 説明                                                            |
| -------------------------- | ----------------------------------------------- | --------------------------------------------------------------- |
| `contact_distribution.csv` | `particle_id`, `contact_count`                  | 接触数分布（ヘッダに平均・中央値・内部/除外粒子数を記載）       |
| `volume_distribution.csv`  | `particle_id`, `volume_voxels`                  | 体積分布（ヘッダに平均・中央値・内部/除外粒子数を記載）         |
| `volume_vs_contacts.csv`   | `particle_id`, `volume_voxels`, `contact_count` | 体積 vs 接触数散布図（ヘッダに線形回帰傾き・相関係数 R を記載） |

**注**: 各 CSV の先頭行は `#` で始まる統計情報コメントです。Excel で開く際はそのまま開けます。

### 保存しないもの（設計方針）

- `volume.npy`（ボリュームはインメモリ処理のみ）
- 中間の `labels_r*.npy`（採択 r のみ保存）
- グラフ画像（PNG 等）— GUI 内の可視化に限定

---

## 🧩 よく使う設定（GUI）

- 最大半径: デフォルト 10（`Advanced Settings` で変更）
- 連結性: デフォルト 6（面接触のみ。26 は辺・頂点も含み過大評価傾向）
- τ 比・限界効用・接触レンジ・平滑窓: `Advanced Settings` から変更可

---

## 🔧 トラブルシューティング

### GUI 依存の不足

```bash
pip install "napari[all]" qtpy matplotlib PySide6
```

### Qt バックエンド問題（競合解消）

```bash
pip uninstall -y PySide6 PyQt5 PyQt6
pip install -y PySide6
```

### 画像が見つからない / 読み込めない

- フォーマットは TIF/TIFF を推奨（GUI は TIF/TIFF のみを 3D Otsu 対象に認識）
- サブフォルダではなく「画像が直接並ぶフォルダ」を選択してください
- 画像のコントラストが低く二値化が不安定な場合は、事前に `CT_Processor_APP.py` で前処理したフォルダを入力にしてください

### メモリ不足

- 現行実装はインメモリ処理。大規模データでは RAM 余裕のある環境を推奨
- 画像を間引く/領域を切り出す、最大半径を抑える、で軽減可能

---

**3D Particle Analysis Pipeline v2.x** — 研究用途の再現性と操作性を両立する、GUI 主導の最新実装
