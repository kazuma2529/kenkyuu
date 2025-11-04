#!/usr/bin/env python3
"""Test script for the new Simple UX redesign.

This script launches the GUI with the new simplified 1-screen flow.
Perfect for testing the UX improvements.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Launch GUI to test simple UX."""
    print("=" * 70)
    print("🎨 3D Particle Analysis - Simple UX Test")
    print("=" * 70)
    print()
    print("✨ New UX Features:")
    print("   • 2-step simple workflow")
    print("   • Step 1: Select folder")
    print("   • Step 2: Press GO")
    print("   • Advanced settings hidden by default")
    print("   • Click ⚙️ button to show advanced options")
    print()
    print("📊 New Layout:")
    print("   • Top: Simple controls (2 big buttons)")
    print("   • Middle: Real-time progress & results")
    print("   • Bottom: Advanced settings (collapsible)")
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
        
        # Launch with new simple UX
        success = launch_gui()
        
        if success:
            print("\n✅ GUI session completed.")
            print("\n💡 Testing Tips:")
            print("   1. Notice the simplified 2-step interface")
            print("   2. Try clicking 'Advanced Settings' button")
            print("   3. Check that folder selection enables GO button")
            print("   4. Verify real-time results appear in tabs")
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

