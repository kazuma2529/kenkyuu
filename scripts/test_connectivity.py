#!/usr/bin/env python3
"""Test script for the new connectivity selection feature.

This script launches the GUI with the new 6/26-neighborhood selection.
Perfect for testing the contact analysis improvements.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Launch GUI to test connectivity selection."""
    print("=" * 70)
    print("🔗 3D Particle Analysis - Connectivity Selection Test")
    print("=" * 70)
    print()
    print("✨ New Connectivity Features:")
    print("   • 6-Neighborhood (Face Contact) 🔷 Recommended")
    print("     - Only face-to-face contacts")
    print("     - More accurate for physical analysis")
    print("     - Typical result: ~6 contacts per particle")
    print()
    print("   • 26-Neighborhood (Face+Edge+Corner)")
    print("     - Includes all 26 directions")
    print("     - Useful for dense packing studies")
    print("     - Typical result: ~12 contacts per particle")
    print()
    print("🎯 How to Test:")
    print("   1. Launch GUI")
    print("   2. Click '⚙️ Advanced Settings'")
    print("   3. Change 'Connectivity' dropdown")
    print("   4. Notice the description updates dynamically")
    print("   5. Run analysis and compare results")
    print()
    print("🚀 Launching GUI...")
    print("-" * 70)
    
    try:
        from particle_analysis import launch_gui, GUI_AVAILABLE
        
        if not GUI_AVAILABLE:
            print("❌ GUI dependencies not installed.")
            print("\nTo install GUI dependencies, run:")
            print("    pip install napari[all] qtpy matplotlib")
            return 1
        
        # Launch with new connectivity selection
        success = launch_gui()
        
        if success:
            print("\n✅ GUI session completed.")
            print("\n💡 Testing Tips:")
            print("   • Default is 6-neighborhood (recommended)")
            print("   • Try both options on same dataset")
            print("   • Compare mean contact numbers")
            print("   • Check 'Final Results' tab for connectivity info")
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

