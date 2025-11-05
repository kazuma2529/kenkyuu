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
5. [出力ファイル（現行仕様）](#出力ファイル現行仕様)
6. [トラブルシューティング](#トラブルシューティング)

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

### 3) GUI の起動

```bash
python scripts/run_gui.py
```

GUI 上で「📁 Select CT Images Folder」から TIF/TIFF 画像フォルダを選択し、「🚀 分析開始！(GO)」を押してください。

---

## 🏗️ フォルダ構成（現行）

```
kenkyuu/
│
├── README.md
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
- GUI タブで接触数/体積の分布ヒストグラムを表示（ファイル出力なし）

---

## 📊 出力ファイル（現行仕様）

解析完了後、`output/gui_run_YYYYMMDD_HHMM/` に以下のみ保存します：

| ファイル名                 | 説明                                                                            | 形式  |
| -------------------------- | ------------------------------------------------------------------------------- | ----- |
| `optimization_results.csv` | r ごとの集計（`radius, particle_count, largest_particle_ratio, mean_contacts`） | CSV   |
| `labels_r{best}.npy`       | 採択 r のラベル 3D 配列（int32）                                                | NumPy |

保存しないもの（設計方針）

- `volume.npy`（ボリュームはインメモリ処理）
- 中間の `labels_r*.npy`（採択 r のみ保存）
- `contact_counts.csv`, `contacts_summary.csv`, ヒスト PNG（GUI 内の可視化に限定）

必要に応じて `contact/core.py` の `save_contact_csv()` / `analyze_contacts()` を呼び出せば CSV 保存を追加できます（GUI 既定では未保存）。

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

### メモリ不足

- 現行実装はインメモリ処理。大規模データでは RAM 余裕のある環境を推奨
- 画像を間引く/領域を切り出す、最大半径を抑える、で軽減可能

---

**3D Particle Analysis Pipeline v2.x** — 研究用途の再現性と操作性を両立する、GUI 主導の最新実装
