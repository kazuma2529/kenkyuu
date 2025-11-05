#!/usr/bin/env python3
"""GUI Launcher for 3D Particle Analysis Pipeline

This script launches the graphical user interface for the particle analysis pipeline.
The GUI provides an intuitive interface for:
- CT image folder selection
- Parameter configuration
- Real-time progress monitoring
- Result visualization
- Interactive 3D viewing
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main():
    """Launch the GUI application."""
    try:
        from particle_analysis import launch_gui, GUI_AVAILABLE
        
        if not GUI_AVAILABLE:
            print("GUI dependencies not installed.")
            print("\nTo install GUI dependencies, run:")
            print("    pip install napari[all] qtpy matplotlib")
            print("\nOr install all optional dependencies:")
            print("    pip install -r requirements.txt")
            return 1
        
        print("Launching 3D Particle Analysis GUI...")
        print("Features:")
        print("  - Interactive CT image folder selection")
        print("  - Real-time optimization progress")
        print("  - Multi-criteria analysis visualization")
        print("  - 3D particle viewer integration")
        print("  - Comprehensive result tables and graphs")
        print()
        
        # Launch GUI
        success = launch_gui()
        
        if success:
            print("GUI session completed successfully.")
            return 0
        else:
            print("GUI session failed.")
            return 1
            
    except ImportError as e:
        print(f"Import Error: {e}")
        print("\nGUI dependencies not available.")
        print("Install with: pip install napari[all] qtpy matplotlib")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 