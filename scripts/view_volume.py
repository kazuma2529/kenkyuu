#!/usr/bin/env python3
"""Launch an interactive napari viewer for a saved volume/labels."""

import argparse
from pathlib import Path
import sys

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from particle_analysis.visualize import view_volume, NapariUnavailable


def main():
    p = argparse.ArgumentParser(description="Visualize 3D volume and labels with napari")
    p.add_argument("--volume", required=True, help="Path to volume.npy")
    p.add_argument("--labels", help="Path to labels.npy (optional)")
    p.add_argument("--rendering", default="mip", choices=["mip", "attenuated_mip", "iso"],
                   help="napari 3D rendering mode")
    args = p.parse_args()

    try:
        view_volume(args.volume, args.labels, rendering=args.rendering)
    except NapariUnavailable as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main() 