# 3D Particle Analysis Pipeline

A comprehensive pipeline for analyzing 3D particle structures from CT slice images, specifically designed for flan casting sand analysis.

## 🎯 Overview

This pipeline processes CT slice images to:

1. **Clean and enhance masks** using CLAHE, Gaussian blur, and Otsu thresholding
2. **Create 3D volumes** from 2D mask stacks
3. **Split touching particles** using erosion-watershed algorithm
4. **Count particle contacts** with 26-connectivity analysis
5. **Generate statistical analysis** and visualizations

## 📊 Results Summary

- **Evaluation**: Dice coefficient = 0.930 (excellent mask quality)
- **Detection**: 1,174 particles identified from 196 CT slices
- **Contacts**: Mean = 1.61, Median = 1.0, Max = 19 contacts per particle
- **Processing time**: ~5 minutes for full dataset

## 🏗️ Project Structure

```
├── src/                          # Core package
│   ├── particle_analysis/        # Main analysis modules
│   │   ├── processing.py         # Image processing and mask cleaning
│   │   ├── volume_ops.py         # 3D volume operations and particle splitting
│   │   ├── contact_analysis.py   # Contact counting and analysis
│   │   └── evaluation.py         # Evaluation metrics (Dice, IoU)
│   ├── utils/                    # Utility functions
│   │   └── common.py            # Logging, timers, file operations
│   └── config.py                # Configuration management
├── scripts/                      # Command-line scripts
│   ├── run_pipeline.py          # Main pipeline orchestrator
│   └── evaluate_baseline.py     # Baseline evaluation script
├── tests/                       # Test suite
│   └── test_pipeline_end2end.py # End-to-end integration tests
├── requirements.txt             # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Full Pipeline

```bash
# Basic usage with default settings
python scripts/run_pipeline.py \
    --img_dir data/images \
    --mask_dir data/masks_otsu \
    --output_dir output

# With custom erosion radius and verbose output
python scripts/run_pipeline.py \
    --img_dir data/images \
    --mask_dir data/masks_otsu \
    --output_dir output \
    --erosion_radius 3 \
    --verbose
```

### 3. Evaluate Against Ground Truth

```bash
python scripts/evaluate_baseline.py \
    --img_dir data/images \
    --mask_dir data/masks_otsu \
    --gt_dir data/ground_truth \
    --out_csv evaluation_results.csv
```

## 📋 Command Reference

| Script                 | Purpose                | Key Options                     |
| ---------------------- | ---------------------- | ------------------------------- |
| `run_pipeline.py`      | Full analysis pipeline | `--erosion_radius`, `--verbose` |
| `evaluate_baseline.py` | Mask evaluation        | `--gt_dir`, `--out_csv`         |

### Pipeline Options

- `--img_dir`: Directory containing CT images (default: `data/images`)
- `--mask_dir`: Directory containing input masks (default: `data/masks_otsu`)
- `--output_dir`: Base output directory (default: `output`)
- `--erosion_radius`: Erosion radius for particle splitting (default: 2)
- `--verbose`: Enable detailed logging
- `--config`: Custom configuration file (YAML)

## 📁 Output Structure

```
output/run_YYYYMMDD_HHMM/
├── masks_pred/              # Processed masks
├── volume.npy              # 3D boolean volume
├── labels_r2.npy           # Labeled particles (radius=2)
├── contact_counts.csv      # Per-particle contact counts
├── contacts_summary.csv    # Statistical summary
└── hist_contacts.png       # Contact distribution histogram
```

## 🔬 Algorithm Details

### 1. Mask Processing

- **CLAHE**: Contrast enhancement with configurable clip limit
- **Gaussian Blur**: Noise reduction
- **Otsu Thresholding**: Automatic binary segmentation
- **Morphological Operations**: Small object removal and closing

### 2. Particle Splitting

- **Erosion**: Separate touching particles (configurable radius)
- **Watershed**: Restore original particle boundaries
- **Connectivity**: 6-connected or 26-connected labeling

### 3. Contact Analysis

- **26-Connectivity**: Comprehensive neighbor scanning
- **Duplicate Removal**: Bidirectional contact counting
- **Statistical Analysis**: Mean, median, quartiles, outlier detection

## 🧪 Testing

```bash
# Run end-to-end tests
python tests/test_pipeline_end2end.py

# Test individual modules
python -c "from src.particle_analysis.processing import clean_mask; print('Import successful')"
```

## 🔧 Configuration

The pipeline uses a hierarchical configuration system. Create a YAML file to customize parameters:

```yaml
postprocess:
  clahe_clip_limit: 2.0
  gaussian_kernel: [3, 3]
  min_object_size: 100

splitting:
  erosion_radius: 2
  connectivity: 6
  min_particles: 100
  max_particles: 5000

contact:
  auto_exclude_threshold: 1000
```

## 📈 Performance Metrics

- **Processing Speed**: ~30 slices/second
- **Memory Usage**: ~2GB for 196 slices (512×512)
- **Accuracy**: Dice = 0.930 vs ground truth
- **Particle Detection**: 1000+ particles from initially merged structures

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src/` is in Python path
2. **Memory Issues**: Reduce batch size or image resolution
3. **No Particles Detected**: Check erosion radius (try smaller values)
4. **Contact Analysis Fails**: Verify particle labels are non-zero

### Debug Tips

- Use `--verbose` flag for detailed logging
- Check intermediate outputs in timestamped directories
- Verify input data format (PNG masks, proper naming)

## 📚 Dependencies

- **Core**: numpy, scipy, scikit-image, opencv-python
- **Analysis**: pandas, matplotlib
- **UI**: tqdm (progress bars)
- **Testing**: unittest (built-in)

## 🤝 Contributing

1. Follow the existing package structure
2. Add tests for new functionality
3. Update documentation
4. Use type hints and docstrings

## 📄 License

This project is part of 3D particle analysis research. Please cite appropriately if used in academic work.

---

**Status**: Production Ready ✅  
**Last Updated**: 2025-06-18  
**Version**: 1.0.0

## 🖥️ Interactive 3-D Viewing (napari)

Install optional dependency:

```bash
pip install "napari[all]"
```

### Launch viewer directly

```bash
python scripts/view_volume.py \
    --volume output/run_*/volume.npy \
    --labels output/run_*/labels_r2.npy \
    --rendering mip   # mip | attenuated_mip | iso
```

### Launch viewer automatically after pipeline

```bash
python scripts/run_pipeline.py \
    --img_dir data/images \
    --mask_dir data/masks_otsu \
    --interactive   # ← これを付けるだけ
```

操作方法:

- マウスドラッグ: 回転
- ホイール: ズーム
- 右クリック+ドラッグ: 平行移動
- ラベルレイヤを左クリックすると **StatusBar に粒子 ID** が表示されます。
