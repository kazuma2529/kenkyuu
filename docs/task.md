# task.md — MVP Build Plan

_Each task is tiny, self-contained, and has an obvious “start ⇢ finish” definition._

---

## 0. Repo Bootstrap

| ID       | Task                                                                                 | Start ⇢ Done                                                                                  |
| -------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| **T0-1** | **Create skeleton folders & blank scripts**<br>`data/`, `models/`, `output/`, `src/` | _Start_: empty workspace ⇢ _Done_: folders + placeholder `__init__.py` files exist            |
| **T0-2** | **Pin dependencies**<br>Write `requirements.txt` (torch, skimage, …)                 | _Start_: none ⇢ _Done_: file committed & `pip install -r requirements.txt` runs without error |

---

## 1. Pre-processing & Baseline Check

| ID       | Task                                                                                       | Start ⇢ Done                                                                  |
| -------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| **T1-1** | **Implement `src/postprocess.py`**<br>function `clean_mask(gray_img)` returns cleaned mask | _Start_: blank script ⇢ _Done_: unit test passes (mask shrinks noise < 50 px) |
| **T1-2** | **Write `src/eval_baseline.py`**<br>computes Dice / IoU of 3 GT vs Otsu                    | _Start_: postprocess ready ⇢ _Done_: prints/CSV with metrics                  |

---

## 2. Training Infrastructure (only if Dice < 0.75)

| ID       | Task                                                                    | Start ⇢ Done                                                               |
| -------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **T2-1** | **`src/dataset.py` PatchDataset**<br>256 × 256 patches + albumentations | _Start_: none ⇢ _Done_: `next(iter(loader))[0].shape == (B, 3, 256, 256)`  |
| **T2-2** | **`src/train.py` mini-trainer**<br>U-Net + ResNet34, Dice + BCE         | _Start_: dataset OK ⇢ _Done_: saves `models/model_final.pt` after ≥1 epoch |

---

## 3. Inference Pipeline

| ID       | Task                                                                                  | Start ⇢ Done                                                                                      |
| -------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **T3-1** | **`src/infer.py`**<br>predicts masks for all slices, applies `postprocess.clean_mask` | _Start_: model file present (or `--skip_train`) ⇢ _Done_: `output/*/masks_pred/*.png` (196 files) |
| **T3-2** | **`src/stack2volume.py`**<br>stack masks → `volume.npy` (bool)                        | _Start_: masks*pred exists ⇢ \_Done*: file saved, shape == (196, H, W)                            |

---

## 4. 3-D Analysis

| ID       | Task                                                                                | Start ⇢ Done                                                                               |
| -------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **T4-1** | **`src/label3d.py`**<br>connected-components → labeled volume                       | _Start_: volume.npy present ⇢ _Done_: returns #particles > 0                               |
| **T4-2** | **`src/count_contacts.py`**<br>26-neighbour contact counting → `contact_counts.csv` | _Start_: labeled volume present ⇢ _Done_: CSV with `particle_id,contacts` rows             |
| **T4-3** | **`src/analyze_contacts.py`**<br>mean, median, histogram → summary CSV + PNG        | _Start_: contact*counts.csv exists ⇢ \_Done*: `contacts_summary.csv` + `hist_contacts.png` |

---

## 5. Orchestration & QA

| ID       | Task                                                                                | Start ⇢ Done                                                                         |
| -------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **T5-1** | **`src/pipeline.py` CLI**<br>sequentially calls all scripts, handles `--skip_train` | _Start_: individual scripts ready ⇢ _Done_: one command runs full flow without error |
| **T5-2** | **Smoke test script**<br>`tests/test_pipeline.sh` runs pipeline on 3 sample slices  | _Start_: pipeline OK ⇢ _Done_: CI passes & outputs created                           |
| **T5-3** | **Update `README.md`**<br>quick-start + command examples                            | _Start_: placeholder README ⇢ _Done_: copy-paste runnable instructions               |

---

### 💡 進め方ヒント

1. 完了したタスクは **即コミット＋プッシュ**。ユーザーは非エンジニアなので優しく丁寧に補佐してあげる。
2. “Dice < 0.75” 判定が出れば **T2 block** へ進み、良ければスキップ。
3. 最終確認は **T5-1** のワンコマンドが通るか。レポート素材は T4-3 で自動生成。

_Small, focused tasks → steady progress 🔧🚀_
