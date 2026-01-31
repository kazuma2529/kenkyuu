import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# プロジェクトルートをPythonパスに追加して import を安定させる
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for p in (PROJECT_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from particle_analysis.processing import load_and_binarize_3d_volume
from particle_analysis.volume.optimizer import optimize_radius_advanced
from particle_analysis.contact.guard_volume import count_contacts_with_guard
from particle_analysis.contact.visualization import create_contact_count_map


def setup_logging() -> None:
    """基本的なロギング設定（CLI用・シンプル版）。"""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """コマンドライン引数定義。"""
    parser = argparse.ArgumentParser(
        description="Run full 3D particle analysis pipeline (CLI, no GUI).",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="TIF/TIFF画像が入ったフォルダへのパス",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="結果を出力するフォルダ（例: output/cli_run_YYYYMMDD_HHMM）",
    )
    parser.add_argument(
        "--max-radius",
        type=int,
        default=10,
        help="侵食半径 r の最大値（1〜max-radius を走査）",
    )
    parser.add_argument(
        "--connectivity",
        type=int,
        default=6,
        choices=[6, 26],
        help="接触・ラベリングの連結性（6 or 26）",
    )
    parser.add_argument(
        "--enable-clahe",
        action="store_true",
        help="CLAHE（局所コントラスト強調）を有効化する",
    )
    parser.add_argument(
        "--threshold-method",
        choices=["otsu", "triangle"],
        default="otsu",
        help="二値化のしきい値決定法（otsu または triangle）",
    )
    parser.add_argument(
        "--tau-ratio",
        type=float,
        default=0.05,
        help="τratio（largest_particle_ratio の閾値、デフォルト 0.05）",
    )
    parser.add_argument(
        "--tau-gain-rel",
        type=float,
        default=0.003,
        help="τgain_rel（粒子数増分の相対閾値、例: 0.003 = 0.3%%）",
    )
    parser.add_argument(
        "--contacts-min",
        type=int,
        default=4,
        help="平均接触数レンジの下限 cmin（デフォルト 4）",
    )
    parser.add_argument(
        "--contacts-max",
        type=int,
        default=10,
        help="平均接触数レンジの上限 cmax（デフォルト 10）",
    )
    parser.add_argument(
        "--smoothing-window",
        type=int,
        choices=[0, 1, 2],
        default=0,
        help="スムージング窓幅（0/1=なし, 2=移動平均窓2）",
    )
    parser.add_argument(
        "--backend",
        choices=["cpu", "gpu"],
        default="cpu",
        help="計算バックエンド（今はcpuのみ実装。gpuは後で追加）",
    )
    return parser.parse_args()


def save_mip_png(
    volume: np.ndarray,
    out_path: Path,
    title: str = "",
    cmap: str = "gray",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """3D配列から最大値投影(MIP)を計算し、PNGとして保存する。"""
    volume = np.asarray(volume)
    if volume.ndim != 3:
        raise ValueError("volume は (Z, Y, X) の3次元配列である必要があります")

    mip = volume.max(axis=0)  # Z方向に最大値投影

    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(mip, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_slice_png(
    volume: np.ndarray,
    out_path: Path,
    title: str = "",
    cmap: str = "gray",
    slice_axis: str = "z",
    slice_index: int | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """3D配列の代表スライス（中央など）をPNGとして保存する。"""
    volume = np.asarray(volume)
    z, y, x = volume.shape

    if slice_axis == "z":
        if slice_index is None:
            slice_index = z // 2
        img = volume[slice_index, :, :]
    elif slice_axis == "y":
        if slice_index is None:
            slice_index = y // 2
        img = volume[:, slice_index, :]
    elif slice_axis == "x":
        if slice_index is None:
            slice_index = x // 2
        img = volume[:, :, slice_index]
    else:
        raise ValueError("slice_axis は 'z', 'y', 'x' のいずれかである必要があります")

    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(img, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(f"{title} (axis={slice_axis}, index={slice_index})")
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def run_pipeline() -> None:
    """GUIなしでフルパイプラインを実行し、CSV/NPY/PNGを出力する。"""
    setup_logging()
    args = parse_args()

    input_folder = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("================================================")
    logging.info("Full pipeline (CLI) start")
    logging.info("Input folder  : %s", input_folder)
    logging.info("Output folder : %s", output_dir)
    logging.info("Backend       : %s", args.backend)
    logging.info("================================================")

    # 1. 3D 二値化
    logging.info("Step 1: 3D二値化を実行します...")
    binary_volume, bin_info = load_and_binarize_3d_volume(
        str(input_folder),
        min_object_size=100,
        closing_radius=0,
        return_info=True,
        enable_clahe=bool(args.enable_clahe),
        threshold_method=args.threshold_method,
        backend=args.backend,
    )
    logging.info(
        "3D二値化完了: shape=%s, foreground=%.2f%%",
        bin_info["volume_shape"],
        bin_info["foreground_ratio"] * 100.0,
    )

    # 2. r 最適化
    logging.info("Step 2: r最適化を実行します...")
    radii = list(range(1, args.max_radius + 1))
    smoothing_window = args.smoothing_window if args.smoothing_window not in (0, 1) else None

    summary = optimize_radius_advanced(
        vol_path=None,
        output_dir=str(output_dir),
        radii=radii,
        connectivity=args.connectivity,
        progress_callback=None,
        complete_analysis=True,
        early_stopping=False,
        plateau_threshold=0.01,
        tau_ratio=args.tau_ratio,
        tau_gain_rel=args.tau_gain_rel,
        contacts_range=(args.contacts_min, args.contacts_max),
        smoothing_window=smoothing_window,
        backend=args.backend,
        volume=binary_volume,
    )

    best_r = summary.best_radius
    logging.info("最適r: r = %s", best_r)

    # optimizer が labels_r{best}.npy を出力済み
    best_labels_path = output_dir / f"labels_r{best_r}.npy"
    if not best_labels_path.exists():
        raise FileNotFoundError(f"labels_r{best_r}.npy が見つかりません: {best_labels_path}")

    labels = np.load(best_labels_path)
    logging.info(
        "labels_r%s.npy 読み込み完了: shape=%s, max_label=%d",
        best_r,
        labels.shape,
        int(labels.max()),
    )

    # 3. Guard Volume付き接触数計算（PNG用）
    logging.info("Step 3: Guard Volume付きで接触数を計算します...")
    full_contacts, interior_contacts, guard_stats = count_contacts_with_guard(
        labels,
        connectivity=args.connectivity,
    )
    logging.info(
        "Guard Volume統計: total=%d, interior=%d, excluded=%d",
        guard_stats["total_particles"],
        guard_stats["interior_particles"],
        guard_stats["excluded_particles"],
    )

    # 4. 接触数マップ(3D)を作成
    logging.info("Step 4: 接触数マップ(3D)を作成します...")
    # PNGには「内部粒子」の接触数だけを使う
    contact_map = create_contact_count_map(labels, interior_contacts)

    viz_dir = output_dir / "png_viz"
    viz_dir.mkdir(parents=True, exist_ok=True)

    # 4-1. Contact Heatmap (MIP)
    logging.info("Contact Heatmap (MIP) PNG を保存します...")
    save_mip_png(
        contact_map,
        viz_dir / f"contact_heatmap_mip_r{best_r}.png",
        title=f"Contact Heatmap (MIP, r={best_r})",
        cmap="turbo",
    )

    # 4-2. Weak Zones (0〜4接触) のみ表示した MIP
    logging.info("Weak Zones (0〜4接触) MIP PNG を保存します...")
    weak_mask = (contact_map >= 0) & (contact_map <= 4)
    weak_map = np.where(weak_mask, contact_map, 0.0)
    save_mip_png(
        weak_map,
        viz_dir / f"weak_zones_mip_r{best_r}.png",
        title=f"Weak Zones (0-4 contacts, MIP, r={best_r})",
        cmap="turbo",
    )

    # 4-3. contact_map の代表スライスPNG（Z中央）
    logging.info("Contact Heatmap の代表スライスPNGを保存します...")
    save_slice_png(
        contact_map,
        viz_dir / f"contact_heatmap_sliceZ_r{best_r}.png",
        title=f"Contact Heatmap (Z-mid, r={best_r})",
        cmap="turbo",
        slice_axis="z",
    )

    # 4-4. 二値ボリュームのMIP PNG（前景形状の確認用）
    logging.info("Binary volume の MIP PNG を保存します...")
    save_mip_png(
        binary_volume.astype(float),
        viz_dir / "binary_volume_mip.png",
        title="Binary Volume (MIP)",
        cmap="gray",
    )

    logging.info("================================================")
    logging.info("CLIパイプライン完了")
    logging.info("出力ディレクトリ: %s", output_dir)
    logging.info("================================================")


if __name__ == "__main__":
    run_pipeline()

