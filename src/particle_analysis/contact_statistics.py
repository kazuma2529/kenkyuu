"""Statistical analysis of particle contacts."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def analyze_contacts(
    csv_path: str,
    out_summary: str,
    out_hist: str,
    exclude_ids: Optional[List[int]] = None,
    auto_exclude_threshold: int = 200
) -> Dict[str, float]:
    """Analyze particle contact distribution and generate summary statistics.
    
    Args:
        csv_path: Path to contact_counts.csv
        out_summary: Output path for summary CSV
        out_hist: Output path for histogram PNG
        exclude_ids: List of particle IDs to exclude
        auto_exclude_threshold: Automatically exclude particles with contacts > threshold
    
    Returns:
        Dict: Summary statistics
    """
    # Load data
    df = pd.read_csv(csv_path)
    logger.info("Loaded %d particles from %s", len(df), csv_path)
    
    # Check if data is empty
    if len(df) == 0:
        logger.warning("No particles found in CSV file")
        stats = _get_empty_stats()
        _save_empty_analysis(out_summary, out_hist, stats, "No data available")
        return stats
    
    # Apply manual exclusions
    if exclude_ids:
        excluded_manual = df[df['particle_id'].isin(exclude_ids)]
        df = df[~df['particle_id'].isin(exclude_ids)]
        logger.info("Manually excluded %d particles: %s", 
                   len(excluded_manual), exclude_ids)
    
    # Apply automatic exclusion for outliers
    outliers = df[df['contacts'] > auto_exclude_threshold]
    if len(outliers) > 0:
        logger.warning("Auto-excluding %d particles with contacts > %d:", 
                      len(outliers), auto_exclude_threshold)
        for _, row in outliers.iterrows():
            logger.warning("  Particle ID %d: %d contacts", 
                          row['particle_id'], row['contacts'])
        df = df[df['contacts'] <= auto_exclude_threshold]
    
    # Check if data is empty after exclusions
    if len(df) == 0:
        logger.warning("No particles remaining after exclusions")
        stats = _get_empty_stats()
        _save_empty_analysis(out_summary, out_hist, stats, "No data after exclusions")
        return stats
    
    # Calculate statistics
    contacts = df['contacts'].values
    stats = {
        'total_particles': len(df),
        'mean_contacts': float(np.mean(contacts)),
        'median_contacts': float(np.median(contacts)),
        'std_contacts': float(np.std(contacts)),
        'min_contacts': int(np.min(contacts)),
        'max_contacts': int(np.max(contacts)),
        'q25_contacts': float(np.percentile(contacts, 25)),
        'q75_contacts': float(np.percentile(contacts, 75))
    }
    
    logger.info("Final statistics - particles: %d, mean: %.2f, median: %.1f, max: %d",
               stats['total_particles'], stats['mean_contacts'], 
               stats['median_contacts'], stats['max_contacts'])
    
    # Save summary
    _save_summary_csv(stats, out_summary)
    
    # Create histogram
    _create_histogram(contacts, stats, out_hist)
    
    return stats


def _get_empty_stats() -> Dict[str, float]:
    """Get empty statistics dictionary."""
    return {
        'total_particles': 0,
        'mean_contacts': 0.0,
        'median_contacts': 0.0,
        'std_contacts': 0.0,
        'min_contacts': 0,
        'max_contacts': 0,
        'q25_contacts': 0.0,
        'q75_contacts': 0.0
    }


def _save_summary_csv(stats: Dict[str, float], out_summary: str) -> None:
    """Save summary statistics to CSV."""
    Path(out_summary).parent.mkdir(parents=True, exist_ok=True)
    
    summary_df = pd.DataFrame([stats])
    summary_df.to_csv(out_summary, index=False)
    logger.info("Saved summary to %s", out_summary)


def _create_histogram(contacts: np.ndarray, stats: Dict[str, float], out_hist: str) -> None:
    """Create and save contact distribution histogram."""
    Path(out_hist).parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    
    # Create histogram
    bins = min(30, max(10, int(stats['max_contacts'] / 2)))
    plt.hist(contacts, bins=bins, alpha=0.7, edgecolor='black', color='skyblue')
    
    # Add statistics as text
    plt.axvline(stats['mean_contacts'], color='red', linestyle='--', 
                label=f"Mean: {stats['mean_contacts']:.2f}")
    plt.axvline(stats['median_contacts'], color='orange', linestyle='--', 
                label=f"Median: {stats['median_contacts']:.1f}")
    
    plt.xlabel('Number of Contacts')
    plt.ylabel('Number of Particles')
    plt.title(f'Contact Distribution (n={stats["total_particles"]} particles)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add text box with statistics
    textstr = '\n'.join([
        f'Mean: {stats["mean_contacts"]:.2f}',
        f'Median: {stats["median_contacts"]:.1f}',
        f'Std: {stats["std_contacts"]:.2f}',
        f'Range: {stats["min_contacts"]}-{stats["max_contacts"]}'
    ])
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    plt.text(0.75, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
             verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    plt.savefig(out_hist, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info("Saved histogram to %s", out_hist)


def _save_empty_analysis(out_summary: str, out_hist: str, stats: Dict[str, float], message: str) -> None:
    """Save empty analysis results with appropriate message."""
    # Save empty summary
    _save_summary_csv(stats, out_summary)
    
    # Create empty histogram with message
    Path(out_hist).parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, message, ha='center', va='center', 
             transform=plt.gca().transAxes, fontsize=16)
    plt.title('Contact Analysis - No Data')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(out_hist, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info("Saved empty analysis to %s and %s", out_summary, out_hist) 