"""Check actual file count in a folder to debug the duplicate counting issue.

Usage:
    python scripts/check_file_count.py <folder_path>
"""

import sys
from pathlib import Path

def check_files(folder_path):
    """Check files in folder and report details."""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    print("=" * 70)
    print(f"📁 Checking folder: {folder}")
    print("=" * 70)
    
    # Get all files
    all_files = list(folder.glob("*"))
    print(f"\n📊 Total items in folder: {len(all_files)}")
    
    # Count by extension
    extensions = {}
    for f in all_files:
        if f.is_file():
            ext = f.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1
    
    print("\n📋 Files by extension:")
    for ext, count in sorted(extensions.items()):
        print(f"   {ext}: {count} files")
    
    # TIF/TIFF files
    tif_patterns = ["*.tif", "*.tiff", "*.TIF", "*.TIFF"]
    
    print("\n🔍 Checking TIF/TIFF files with different patterns:")
    all_tif_files = set()
    for pattern in tif_patterns:
        matched = list(folder.glob(pattern))
        print(f"   {pattern}: {len(matched)} files")
        # Add to set (will remove duplicates)
        for f in matched:
            all_tif_files.add(f)
    
    print(f"\n✅ Unique TIF/TIFF files (case-insensitive): {len(all_tif_files)}")
    
    # Show first few files
    print("\n📄 First 5 TIF/TIFF files:")
    for i, f in enumerate(sorted(all_tif_files)[:5]):
        print(f"   {i+1}. {f.name}")
    
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_file_count.py <folder_path>")
        print("\nExample:")
        print("  python scripts/check_file_count.py D:\\data\\ct_images")
        sys.exit(1)
    
    check_files(sys.argv[1])

