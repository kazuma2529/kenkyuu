# 二値化処理の問題分析と解決策

## 1. 現在の二値化処理の実装詳細

### 1.1 処理フロー全体

現在の二値化処理は `src/particle_analysis/processing.py` の `load_and_binarize_3d_volume()` 関数で実装されています。処理は以下の6つのステップで構成されています：

```
Step 1: 画像ファイルの読み込み
  ↓
Step 2: 3Dボリュームへの統合（uint16精度を保持）
  ↓
Step 3.5: CLAHEコントラスト強調（オプション）
  ↓
Step 4: 2段階閾値処理（Stage 1: ROI検出、Stage 2: 粒子/空隙分離）
  ↓
Step 5: 自動極性検出（Polarity Detection）
  ↓
Step 6: 後処理（Binary Closing、小オブジェクト除去）
```

### 1.2 各ステップの詳細実装

#### Step 1: 画像ファイルの読み込み

```python
# TIF/TIFFファイルをスキャン
image_files = get_image_files(folder, supported_formats=["*.tif", "*.tiff"])

# 最初の画像で次元を取得
first_img = cv2.imread(str(image_files[0]), cv2.IMREAD_UNCHANGED)
height, width = first_img.shape
dtype = first_img.dtype  # 通常は uint16
z_slices = len(image_files)
```

**重要なポイント:**
- `cv2.IMREAD_UNCHANGED` により、元のデータ型（uint16）を保持
- 8ビットへのダウンスケールは行わない

#### Step 2: 3Dボリュームへの統合

```python
volume = np.zeros((z_slices, height, width), dtype=dtype)  # uint16配列

for i, img_path in enumerate(image_files):
    img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
    volume[i] = img
```

**重要なポイント:**
- 全スライスをメモリ上に読み込み、3D配列として統合
- データ型は元の画像のまま（uint16）を保持

#### Step 3.5: CLAHEコントラスト強調（オプション）

```python
if enable_clahe:
    # 各スライスに対してCLAHEを適用
    vol_float = img_as_float(volume)  # float64 [0, 1] に変換
    enhanced_volume = np.zeros_like(vol_float)
    
    for i in range(z_slices):
        enhanced_volume[i] = equalize_adapthist(
            vol_float[i], 
            kernel_size=None, 
            clip_limit=0.01, 
            nbins=256
        )
    volume = enhanced_volume  # float64 [0, 1] のボリューム
```

**重要なポイント:**
- CLAHE有効時は、ボリュームが `float64 [0, 1]` に変換される
- CLAHE無効時は、元の `uint16` のまま

#### Step 4: 2段階閾値処理（重要）

このステップが二値化の核心部分です。

##### Stage 1: ROI（Region of Interest）検出

```python
# 全体のボリュームに対してOtsu法を適用
threshold1 = threshold_otsu(volume)
# threshold1: 容器+粒子 vs 背景（空気/黒）を分離する閾値

# ROIマスクを作成（閾値より大きい領域 = 容器+粒子）
roi_mask = volume > threshold1
roi_voxels = volume[roi_mask]  # ROI内のボクセル値のみを抽出
```

**目的:**
- 背景（空気や黒い領域）を除外し、容器と粒子を含む領域（ROI）を特定
- この段階では、粒子と空隙はまだ分離されていない

**重要なポイント:**
- `threshold_otsu(volume)` は、ボリューム全体のヒストグラムから最適な閾値を計算
- ROI内には「粒子（高輝度）」と「空隙（低輝度）」の両方が含まれる

##### Stage 2: 粒子と空隙の分離

```python
if len(roi_voxels) == 0:
    threshold_val = threshold1  # ROIが空の場合、Stage 1の閾値を使用
else:
    if threshold_method == "triangle":
        threshold_val = threshold_triangle(roi_voxels)  # Triangle法
    else:  # "otsu"
        threshold_val = threshold_otsu(roi_voxels)  # Otsu法（デフォルト）
```

**目的:**
- ROI内のボクセル値のみに対して閾値処理を適用
- 粒子（高輝度）と空隙（低輝度）を分離する

**重要なポイント:**
- `threshold_otsu(roi_voxels)` は、ROI内のボクセル値のヒストグラムから閾値を計算
- ROI内のヒストグラムが**二峰性**（粒子と空隙が明確に分離）であることが前提
- もしROI内のヒストグラムが**単峰性**（粒子と空隙が混在）の場合、Otsu法は適切な閾値を設定できない

#### Step 5: 自動極性検出（Polarity Detection）

```python
# 最終閾値の上下で統計を計算
below_threshold = volume <= threshold_val
above_threshold = volume > threshold_val

count_below = below_threshold.sum()  # 閾値以下のボクセル数
count_above = above_threshold.sum()  # 閾値より大きいボクセル数

# 少数派を粒子として判定
if count_below < count_above:
    # 閾値以下が少数派 → 粒子は閾値以下（暗い）
    binary_volume = below_threshold
    polarity = "inverted (foreground is darker)"
else:
    # 閾値より大きいが少数派 → 粒子は閾値より大きい（明るい）
    binary_volume = above_threshold
    polarity = "normal (foreground is brighter)"
```

**目的:**
- CTスキャンでは、粒子は通常「少数派」であるという前提で動作
- 閾値の上下どちらが少数派かを判定し、それを粒子として選択

**重要なポイント:**
- この判定は「ボクセル数のみ」に基づいている
- もし二値化が失敗し、粒子と空隙が正しく分離されていない場合、この判定も誤る可能性がある

#### Step 6: 後処理

```python
# Binary Closing（小さい穴を埋める）
if closing_radius > 0:
    selem = ball(closing_radius)
    binary_volume = binary_closing(binary_volume, selem)

# 小オブジェクト除去（ノイズ除去）
if min_object_size > 0:
    binary_volume = remove_small_objects(
        binary_volume,
        min_size=min_object_size,
        connectivity=1  # 6-connectivity
    )
```

**目的:**
- 二値化結果の品質を向上させる
- ノイズや小さな欠陥を除去

### 1.3 処理の流れ図

```
[元のCT画像] (uint16, 例: 0-65535)
    ↓
[CLAHE処理] (オプション)
    ↓ float64 [0, 1] に変換
[Stage 1: ROI検出]
    threshold1 = Otsu(全体)
    roi_mask = volume > threshold1
    ↓
[Stage 2: 粒子/空隙分離]
    threshold_val = Otsu(ROI内のボクセル)
    ↓
[極性検出]
    if count_below < count_above:
        binary = below_threshold  # 粒子は暗い
    else:
        binary = above_threshold  # 粒子は明るい
    ↓
[後処理]
    Binary Closing (オプション)
    小オブジェクト除去
    ↓
[最終的な二値化ボリューム] (bool配列)
```

## 2. 現在の問題点と結果の一貫性のなさ

### 2.1 観察された問題

添付された結果から、以下の異常が確認されています：

| r値 | 粒子数 | 最大粒子割合(%) | 平均接触数 | 処理時間(秒) |
|-----|--------|----------------|-----------|------------|
| 1   | 2051   | 98.7           | 1.6       | 813.7      |
| 2   | 2601   | 89.6           | 2.8       | 1405.4     |
| 3   | 5446   | 22.6           | 7.2       | 2925.4     |
| 4   | 5958   | 18.9           | 8.0       | 3508.6     |
| 5   | 5093   | 17.3           | 8.4       | 2168.8     |

**問題点:**

1. **r=1で最大粒子割合が98.7%**
   - ほぼ1つの粒子が全体の98.7%を占めている
   - これは、粒子が正しく分離されず、大きな塊として認識されていることを示す

2. **r=5で粒子数が減少**
   - r=4で5958個だった粒子が、r=5で5093個に減少
   - 通常、rを増やすと粒子数は増加するはず（より細かく分割される）
   - この減少は異常

3. **最大粒子割合が依然として大きい**
   - r=5でも最大粒子割合が17.3%と大きい
   - 正常な粒子分離ができていれば、最大粒子割合は5%以下になるはず

4. **二値化テストでは良好な結果**
   - `binarization_test_v2.png` では、Masked Otsuが適切に二値化できているように見える
   - しかし、実際の3Dボリューム処理では異なる結果になっている

### 2.2 結果の一貫性のなさの原因

#### 問題1: 二値化の失敗による粒子の連続化

**症状:**
- r=1で最大粒子割合98.7% → ほぼ1つの大きな塊として認識
- rを増やしても、最大粒子割合が17.3%と大きいまま

**原因の仮説:**
1. **Stage 2のOtsuが適切な閾値を設定できていない**
   - ROI内のヒストグラムが単峰性（粒子と空隙が混在）
   - Otsu法は二峰性のヒストグラムを前提としているため、単峰性では適切な閾値を設定できない
   - 結果として、粒子と空隙が正しく分離されず、大きな連続した塊になる

2. **極性検出の誤り**
   - 二値化が失敗している場合、極性検出も誤る可能性がある
   - 粒子が多数派として誤検出され、空隙が少数派として扱われている可能性

3. **2Dスライスと3Dボリュームの違い**
   - 2Dスライスでは良好な二値化結果が得られている
   - しかし、3Dボリューム全体では異なる結果になっている
   - これは、3Dボリューム全体のヒストグラムが2Dスライスのヒストグラムと異なるため

#### 問題2: 粒子分割の限界

**症状:**
- r=5で粒子数が減少
- 最大粒子割合が依然として大きい

**原因の仮説:**
- 二値化の結果、粒子が大きな連続した塊になっている
- erosion-watershedアルゴリズムは、このような大きな塊を細かく分割するには不十分
- rを増やしても、元の二値化結果に大きな塊が残っている限り、適切な分割は困難

### 2.3 問題の連鎖反応

```
[二値化の失敗]
    ↓
[粒子と空隙が正しく分離されない]
    ↓
[粒子が大きな連続した塊になる]
    ↓
[erosion-watershedで分割できない]
    ↓
[最大粒子割合が大きいまま]
    ↓
[rを増やしても改善しない]
```

## 3. 問題の原因と解決策

### 3.1 根本原因の分析

#### 原因1: Stage 2のOtsuがROI内のヒストグラム特性を考慮していない

**問題:**
- ROI内のヒストグラムが単峰性の場合、Otsu法は適切な閾値を設定できない
- 粒子と空隙のコントラストが低い場合、ヒストグラムが単峰性になる

**証拠:**
- 2Dスライスでは良好な二値化結果が得られている
- しかし、3Dボリューム全体では異なる結果になっている
- これは、3Dボリューム全体のヒストグラムが2Dスライスのヒストグラムと異なるため

#### 原因2: 極性検出が単純すぎる

**問題:**
- 現在の極性検出は「ボクセル数のみ」に基づいている
- 二値化が失敗している場合、この判定も誤る可能性がある

**証拠:**
- r=1で最大粒子割合98.7% → ほぼ1つの大きな塊として認識
- これは、粒子が多数派として誤検出され、空隙が少数派として扱われている可能性

#### 原因3: 2Dスライスと3Dボリュームの処理の違い

**問題:**
- 2Dスライスでは良好な二値化結果が得られている
- しかし、3Dボリューム全体では異なる結果になっている

**証拠:**
- `binarization_test_v2.png` では、Masked Otsuが適切に二値化できている
- しかし、実際の3Dボリューム処理では異なる結果になっている

### 3.2 解決策の提案

#### 解決策1: ROI内のヒストグラム特性を確認し、適切な閾値法を選択

**実装方針:**
1. ROI内のヒストグラムを計算
2. ヒストグラムの峰の数を判定（単峰性 vs 二峰性）
3. 単峰性の場合は、Triangle法や手動閾値を検討
4. 二峰性の場合は、Otsu法を使用

**コード例:**
```python
# ROI内のヒストグラムを計算
hist, bins = np.histogram(roi_voxels, bins=256)

# 峰の数を判定（簡易版）
# より高度な方法として、scipy.signal.find_peaks を使用
from scipy.signal import find_peaks
peaks, _ = find_peaks(hist, height=hist.max() * 0.1)

if len(peaks) < 2:
    # 単峰性 → Triangle法を使用
    threshold_val = threshold_triangle(roi_voxels)
    logger.info("ROI histogram is unimodal, using Triangle method")
else:
    # 二峰性 → Otsu法を使用
    threshold_val = threshold_otsu(roi_voxels)
    logger.info("ROI histogram is bimodal, using Otsu method")
```

#### 解決策2: 極性検出の改善

**実装方針:**
1. ボクセル数だけでなく、平均輝度値も考慮
2. 粒子は通常「高輝度」であるという前提を追加
3. 二値化結果の品質を評価し、極性を決定

**コード例:**
```python
# 現在の方法（ボクセル数のみ）
count_below = below_threshold.sum()
count_above = above_threshold.sum()

# 改善案: 平均輝度値も考慮
mean_below = volume[below_threshold].mean() if below_threshold.any() else 0
mean_above = volume[above_threshold].mean() if above_threshold.any() else 0

# 粒子は通常「高輝度」であるという前提
# ただし、ボクセル数が少ない方を優先
if count_below < count_above:
    # 閾値以下が少数派 → 粒子は閾値以下（暗い）
    binary_volume = below_threshold
    polarity = "inverted (foreground is darker)"
elif count_above < count_below:
    # 閾値より大きいが少数派 → 粒子は閾値より大きい（明るい）
    binary_volume = above_threshold
    polarity = "normal (foreground is brighter)"
else:
    # ボクセル数が同じ場合、平均輝度で判定
    if mean_above > mean_below:
        binary_volume = above_threshold
        polarity = "normal (foreground is brighter)"
    else:
        binary_volume = below_threshold
        polarity = "inverted (foreground is darker)"
```

#### 解決策3: 2Dスライスベースの処理への回帰検討

**実装方針:**
1. 各スライスに対して2D二値化を適用
2. 各スライスの結果を統合して3Dボリュームを作成
3. 2Dスライスでは良好な結果が得られているため、この方法を検討

**注意点:**
- この方法は、スライス間の一貫性を保つ必要がある
- 各スライスで異なる閾値が設定される可能性がある

#### 解決策4: 二値化結果の品質評価とログ出力

**実装方針:**
1. 二値化結果の品質を評価（foreground_ratio、ヒストグラム特性など）
2. 異常な値が検出された場合、警告を出力
3. ユーザーに手動での確認を促す

**コード例:**
```python
foreground_ratio = foreground_after / binary_volume.size

# 異常な値の検出
if foreground_ratio > 0.7:
    logger.warning(
        f"Foreground ratio is very high ({foreground_ratio:.2%}). "
        "This may indicate incorrect polarity detection or binarization failure."
    )
elif foreground_ratio < 0.05:
    logger.warning(
        f"Foreground ratio is very low ({foreground_ratio:.2%}). "
        "This may indicate incorrect polarity detection or binarization failure."
    )
```

### 3.3 推奨される調査手順

1. **二値化結果の確認**
   - `foreground_ratio` がどの程度か確認
   - 粒子は通常10-30%程度であるべき
   - 50%以上なら、極性が逆になっている可能性が高い

2. **ROI内のヒストグラムの可視化**
   - ROI内のヒストグラムを可視化し、二峰性か単峰性かを確認
   - 単峰性の場合、Otsu法は適切な閾値を設定できない

3. **Stage 1とStage 2の閾値の確認**
   - Stage 1の閾値（ROI検出）が適切か確認
   - Stage 2の閾値（粒子/空隙分離）が適切か確認

4. **中間結果の可視化**
   - 二値化後のボリュームを可視化し、粒子が連続した塊になっていないか確認
   - r=1の分割結果を可視化し、大きな塊が残っていないか確認

### 3.4 実装の優先順位

1. **最優先: 二値化結果の品質評価とログ出力**
   - 異常な値が検出された場合、警告を出力
   - ユーザーに手動での確認を促す

2. **高優先: ROI内のヒストグラム特性の確認**
   - ヒストグラムの峰の数を判定
   - 単峰性の場合は、Triangle法や手動閾値を検討

3. **中優先: 極性検出の改善**
   - ボクセル数だけでなく、平均輝度値も考慮
   - 粒子は通常「高輝度」であるという前提を追加

4. **低優先: 2Dスライスベースの処理への回帰検討**
   - 2Dスライスでは良好な結果が得られているため、この方法を検討
   - ただし、スライス間の一貫性を保つ必要がある

## 4. まとめ

### 4.1 現在の問題の本質

1. **二値化の失敗**: Stage 2のOtsuがROI内のヒストグラム特性を考慮していない
2. **極性検出の誤り**: ボクセル数のみに基づく判定が不十分
3. **2Dと3Dの処理の違い**: 2Dスライスでは良好な結果が得られているが、3Dボリューム全体では異なる結果になっている

### 4.2 解決策の方向性

1. **ROI内のヒストグラム特性を確認し、適切な閾値法を選択**
2. **極性検出の改善（ボクセル数と平均輝度値の両方を考慮）**
3. **二値化結果の品質評価とログ出力**

### 4.3 次のステップ

1. 二値化処理のログ（特に `foreground_ratio` と `polarity`）を確認
2. ROI内のヒストグラムを可視化し、二峰性か単峰性かを確認
3. 上記の解決策を段階的に実装し、結果を検証
