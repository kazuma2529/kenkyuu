#!/usr/bin/env python3
"""Quick test script to preview the new dark theme GUI.

This script launches the GUI with minimal setup to quickly preview
the modernized dark theme design.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Launch GUI to test dark theme."""
    print("=" * 60)
    print("🎨 3D Particle Analysis - Dark Theme Preview")
    print("=" * 60)
    print()
    print("✨ New Features:")
    print("   • Professional dark theme")
    print("   • Modern flat design")
    print("   • Smooth hover effects")
    print("   • Refined color scheme")
    print("   • Better visual hierarchy")
    print()
    print("🚀 Launching GUI...")
    print("-" * 60)
    
    try:
        from particle_analysis import launch_gui, GUI_AVAILABLE
        
        if not GUI_AVAILABLE:
            print("❌ GUI dependencies not installed.")
            print("\nTo install GUI dependencies, run:")
            print("    pip install napari[all] qtpy matplotlib")
            return 1
        
        # Launch with dark theme
        success = launch_gui()
        
        if success:
            print("\n✅ GUI session completed.")
            return 0
        else:
            print("\n⚠️ GUI session ended with issues.")
            return 1
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure all dependencies are installed:")
        print("    pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

