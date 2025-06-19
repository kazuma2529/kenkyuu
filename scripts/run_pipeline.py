#!/usr/bin/env python3
"""Main pipeline for 3D particle analysis from CT slices.

This script orchestrates the complete workflow:
1. Mask processing (clean_mask)
2. 3D volume creation
3. Particle splitting (erosion-watershed)
4. Contact counting
5. Analysis and visualization
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from particle_analysis.config import DEFAULT_CONFIG, PipelineConfig
from particle_analysis.utils.common import setup_logging, Timer, ensure_directory
from particle_analysis.processing import process_masks
from particle_analysis.volume_ops import stack_masks, split_particles
from particle_analysis.contact_analysis import count_contacts, save_contact_csv, analyze_contacts


def run_mask_processing(
    img_dir: str,
    mask_dir: str, 
    output_dir: str,
    config: PipelineConfig
) -> Path:
    """Step 1: Process masks through clean_mask."""
    masks_pred_dir = Path(output_dir) / "masks_pred"
    
    with Timer("Mask processing"):
        processed_count = process_masks(
            img_dir=img_dir,
            mask_dir=mask_dir,
            out_dir=str(masks_pred_dir.parent),
            force=True
        )
    
    logging.info(f"Processed {processed_count} masks")
    return masks_pred_dir


def run_volume_creation(
    masks_dir: Path,
    output_dir: str,
    config: PipelineConfig
) -> Path:
    """Step 2: Create 3D volume from masks."""
    volume_path = Path(output_dir) / "volume.npy"
    
    with Timer("Volume creation"):
        stack_masks(
            mask_dir=str(masks_dir),
            out_vol=str(volume_path),
            dtype="bool"
        )
    
    return volume_path


def run_particle_splitting(
    volume_path: Path,
    output_dir: str,
    config: PipelineConfig
) -> Path:
    """Step 3: Split touching particles."""
    labels_path = Path(output_dir) / f"labels_r{config.splitting.erosion_radius}.npy"
    
    with Timer("Particle splitting"):
        num_particles = split_particles(
            vol_path=str(volume_path),
            out_labels=str(labels_path),
            radius=config.splitting.erosion_radius,
            connectivity=config.splitting.connectivity
        )
    
    logging.info(f"Detected {num_particles} particles")
    
    if num_particles < config.splitting.min_particles:
        logging.warning(f"Low particle count: {num_particles} < {config.splitting.min_particles}")
    elif num_particles > config.splitting.max_particles:
        logging.warning(f"High particle count: {num_particles} > {config.splitting.max_particles}")
    
    return labels_path


def run_contact_counting(
    labels_path: Path,
    output_dir: str,
    config: PipelineConfig
) -> Path:
    """Step 4: Count particle contacts."""
    import numpy as np
    
    csv_path = Path(output_dir) / "contact_counts.csv"
    
    with Timer("Contact counting"):
        # Load labels and count contacts
        labels = np.load(labels_path)
        
        # Count contacts
        contacts_dict = count_contacts(labels)
        
        # Save to CSV
        save_contact_csv(contacts_dict, str(csv_path))
    
    return csv_path


def run_contact_analysis(
    csv_path: Path,
    output_dir: str,
    config: PipelineConfig
) -> tuple:
    """Step 5: Analyze contact distribution."""
    summary_path = Path(output_dir) / "contacts_summary.csv"
    hist_path = Path(output_dir) / "hist_contacts.png"
    
    with Timer("Contact analysis"):
        stats = analyze_contacts(
            csv_path=str(csv_path),
            out_summary=str(summary_path),
            out_hist=str(hist_path),
            auto_exclude_threshold=config.contact.auto_exclude_threshold
        )
    
    return summary_path, hist_path, stats


def main():
    parser = argparse.ArgumentParser(
        description="3D Particle Analysis Pipeline",
        epilog="""
Examples:
  # Use optimized settings (default erosion_radius=5)
  python scripts/run_pipeline.py --mask_dir data/masks_otsu
  
  # Use custom erosion radius
  python scripts/run_pipeline.py --mask_dir data/masks_otsu --erosion_radius 3
  
  # Use predefined optimized config file
  python scripts/run_pipeline.py --config config/optimized_sand_particles.yaml
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--img_dir", default="data/images",
                       help="Directory containing CT images")
    parser.add_argument("--mask_dir", default="data/masks_otsu", 
                       help="Directory containing input masks")
    parser.add_argument("--output_dir", default="output",
                       help="Base output directory")
    parser.add_argument("--config", type=str,
                       help="Path to configuration file (e.g., config/optimized_sand_particles.yaml)")
    parser.add_argument("--skip_train", action="store_true",
                       help="Skip training phase (use baseline masks)")
    parser.add_argument("--erosion_radius", type=int, default=5,
                       help="Erosion radius for particle splitting (default=5, optimized for sand particles)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--interactive", action="store_true",
                       help="Launch napari viewer after volume/label creation")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    # Load configuration
    if args.config:
        config = PipelineConfig.load_from_file(args.config)
    else:
        config = DEFAULT_CONFIG
    
    # Override config with command line arguments
    if args.erosion_radius:
        config.splitting.erosion_radius = args.erosion_radius
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = Path(args.output_dir) / f"run_{timestamp}"
    ensure_directory(output_dir)
    
    logging.info(f"Starting pipeline with output directory: {output_dir}")
    
    try:
        # Step 1: Mask processing
        masks_dir = run_mask_processing(
            args.img_dir, args.mask_dir, str(output_dir), config
        )
        
        # Step 2: Volume creation
        volume_path = run_volume_creation(masks_dir, str(output_dir), config)
        
        # Step 3: Particle splitting
        labels_path = run_particle_splitting(volume_path, str(output_dir), config)
        
        # Optional interactive view
        if args.interactive:
            try:
                from particle_analysis.visualize import view_volume
                view_volume(volume_path, labels_path)
            except Exception as e:
                logging.error(f"Interactive view failed: {e}")
        
        # Step 4: Contact counting
        csv_path = run_contact_counting(labels_path, str(output_dir), config)
        
        # Step 5: Contact analysis (only if we have contact data)
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        if len(df) > 0 and df['contacts'].sum() > 0:
            summary_path, hist_path, stats = run_contact_analysis(
                csv_path, str(output_dir), config
            )
            
            # Final summary
            logging.info("Pipeline completed successfully!")
            logging.info(f"Results saved to: {output_dir}")
            logging.info(f"Particles analyzed: {stats['total_particles']}")
            logging.info(f"Mean contacts: {stats['mean_contacts']:.2f}")
            logging.info(f"Summary: {summary_path}")
            logging.info(f"Histogram: {hist_path}")
            
            print(f"\n{'='*60}")
            print("PIPELINE COMPLETED SUCCESSFULLY")
            print(f"{'='*60}")
            print(f"Output directory: {output_dir}")
            print(f"Particles: {stats['total_particles']}")
            print(f"Mean contacts: {stats['mean_contacts']:.2f}")
            print(f"Median contacts: {stats['median_contacts']:.1f}")
            print(f"Contact range: {stats['min_contacts']}-{stats['max_contacts']}")
        else:
            logging.warning("No contact data to analyze - skipping contact analysis")
            print(f"\n{'='*60}")
            print("PIPELINE COMPLETED (NO CONTACT DATA)")
            print(f"{'='*60}")
            print(f"Output directory: {output_dir}")
            print("Note: No contact analysis performed due to insufficient data")
        
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 