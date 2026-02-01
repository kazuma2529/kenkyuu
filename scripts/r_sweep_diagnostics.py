#!/usr/bin/env python3
import argparse
import csv
import inspect
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _call_load_and_binarize(folder: str, *, min_object_size: int, closing_radius: int, polarity: str):
    from particle_analysis.processing import load_and_binarize_3d_volume

    sig = inspect.signature(load_and_binarize_3d_volume)
    kwargs = {
        "folder_path": folder,
        "min_object_size": min_object_size,
        "closing_radius": closing_radius,
        "return_info": True,
    }

    if "polarity" in sig.parameters:
        kwargs["polarity"] = polarity

    if "thresholding" in sig.parameters:
        kwargs["thresholding"] = getattr(_call_load_and_binarize, "thresholding")
    if "roi_mode" in sig.parameters:
        kwargs["roi_mode"] = getattr(_call_load_and_binarize, "roi_mode")
    if "sauvola_window" in sig.parameters:
        kwargs["sauvola_window"] = getattr(_call_load_and_binarize, "sauvola_window")
    if "sauvola_k" in sig.parameters:
        kwargs["sauvola_k"] = getattr(_call_load_and_binarize, "sauvola_k")
    if "norm_p_low" in sig.parameters:
        kwargs["norm_p_low"] = getattr(_call_load_and_binarize, "norm_p_low")
    if "norm_p_high" in sig.parameters:
        kwargs["norm_p_high"] = getattr(_call_load_and_binarize, "norm_p_high")

    return load_and_binarize_3d_volume(**kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="CT tif/tiff folder path (e.g. D:\\paisen-CT1)")
    parser.add_argument("--out", required=True, help="Output directory under which CSV/PNG are saved")
    parser.add_argument("--r-min", type=int, default=1)
    parser.add_argument("--r-max", type=int, default=10)
    parser.add_argument("--connectivity", type=int, default=6, choices=[6, 26])
    parser.add_argument("--polarity", type=str, default="auto", choices=["auto", "bright", "dark"])
    parser.add_argument(
        "--thresholding",
        type=str,
        default="otsu3d",
        choices=["otsu3d", "otsu3d_roi", "sauvola2d_roi"],
    )
    parser.add_argument("--roi-mode", type=str, default="none")
    parser.add_argument("--sauvola-window", type=int, default=51)
    parser.add_argument("--sauvola-k", type=float, default=0.2)
    parser.add_argument("--norm-p-low", type=float, default=1.0)
    parser.add_argument("--norm-p-high", type=float, default=99.0)
    parser.add_argument("--min-object-size", type=int, default=100)
    parser.add_argument("--closing-radius", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Binarization
    _call_load_and_binarize.thresholding = args.thresholding
    _call_load_and_binarize.roi_mode = args.roi_mode
    _call_load_and_binarize.sauvola_window = args.sauvola_window
    _call_load_and_binarize.sauvola_k = args.sauvola_k
    _call_load_and_binarize.norm_p_low = args.norm_p_low
    _call_load_and_binarize.norm_p_high = args.norm_p_high

    binary_volume, info = _call_load_and_binarize(
        args.data,
        min_object_size=args.min_object_size,
        closing_radius=args.closing_radius,
        polarity=args.polarity,
    )

    # 2) R sweep
    from particle_analysis.volume.core import split_particles_in_memory
    from particle_analysis.volume.metrics.basic import calculate_largest_particle_ratio

    results = []
    for r in range(args.r_min, args.r_max + 1):
        labels = split_particles_in_memory(binary_volume, radius=r, connectivity=args.connectivity)
        particle_count = int(labels.max())
        largest_ratio, _, _ = calculate_largest_particle_ratio(labels)
        results.append((r, particle_count, float(largest_ratio)))
        print(f"r={r}: particles={particle_count}, largest_ratio={largest_ratio:.4f}")

    # 3) Save CSV
    csv_path = out_dir / "r_sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["r", "particle_count", "largest_particle_ratio"])
        w.writerows(results)

    # 4) Plot
    r_vals = [x[0] for x in results]
    counts = [x[1] for x in results]
    ratios = [x[2] for x in results]

    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=150)

    ax1.plot(r_vals, counts, marker="o", linewidth=2)
    ax1.set_xlabel("R (erosion radius)")
    ax1.set_ylabel("Particle count")
    ax1.grid(True, which="both", axis="both", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(r_vals, ratios, marker="s", linewidth=2)
    ax2.set_ylabel("Largest particle ratio")
    ax2.set_ylim(0.0, 1.0)

    title_parts = [
        f"data={Path(args.data).name}",
        f"polarity={args.polarity}",
        f"conn={args.connectivity}",
    ]
    ax1.set_title("R sweep diagnostics (particle count & largest ratio)\n" + ", ".join(title_parts))

    fig.tight_layout()
    png_path = out_dir / "r_sweep.png"
    fig.savefig(png_path)
    plt.close(fig)

    # 5) Minimal binarization info dump
    info_path = out_dir / "binarization_info.txt"
    with info_path.open("w", encoding="utf-8") as f:
        for k, v in info.items():
            f.write(f"{k}: {v}\n")

    print(f"Saved CSV: {csv_path}")
    print(f"Saved PNG: {png_path}")
    print(f"Saved info: {info_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
