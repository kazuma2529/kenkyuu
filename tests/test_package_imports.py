#!/usr/bin/env python3
"""Test package imports and basic functionality."""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPackageImports(unittest.TestCase):
    """Test that all main package components can be imported."""

    def test_main_package_import(self):
        """Test main package imports without errors."""
        try:
            import particle_analysis
            self.assertTrue(hasattr(particle_analysis, '__version__'))
        except ImportError as e:
            self.fail(f"Failed to import main package: {e}")

    def test_processing_imports(self):
        """Test processing module imports."""
        try:
            from particle_analysis.processing import clean_mask, process_masks
            self.assertTrue(callable(clean_mask))
            self.assertTrue(callable(process_masks))
        except ImportError as e:
            self.fail(f"Failed to import processing functions: {e}")

    def test_volume_imports(self):
        """Test volume module imports."""
        try:
            from particle_analysis.volume import (
                stack_masks, split_particles, optimize_radius_advanced,
                OptimizationResult, OptimizationSummary
            )
            self.assertTrue(callable(stack_masks))
            self.assertTrue(callable(split_particles))
            self.assertTrue(callable(optimize_radius_advanced))
        except ImportError as e:
            self.fail(f"Failed to import volume functions: {e}")

    def test_contact_imports(self):
        """Test contact analysis imports."""
        try:
            from particle_analysis.contact import count_contacts, save_contact_csv, analyze_contacts
            self.assertTrue(callable(count_contacts))
            self.assertTrue(callable(save_contact_csv))
            self.assertTrue(callable(analyze_contacts))
        except ImportError as e:
            self.fail(f"Failed to import contact functions: {e}")

    def test_utils_imports(self):
        """Test utility imports."""
        try:
            from particle_analysis.utils import (
                setup_logging, Timer, ensure_directory, 
                get_image_files, natural_sort_key
            )
            self.assertTrue(callable(setup_logging))
            self.assertTrue(callable(get_image_files))
            self.assertTrue(callable(natural_sort_key))
        except ImportError as e:
            self.fail(f"Failed to import utility functions: {e}")

    def test_config_imports(self):
        """Test configuration imports."""
        try:
            from particle_analysis.config import DEFAULT_CONFIG, PipelineConfig
            self.assertIsNotNone(DEFAULT_CONFIG)
            self.assertTrue(hasattr(PipelineConfig, 'splitting'))
        except ImportError as e:
            self.fail(f"Failed to import config: {e}")

    def test_gui_availability(self):
        """Test GUI import availability (should not fail even if dependencies missing)."""
        try:
            from particle_analysis.gui import GUI_AVAILABLE, launch_gui
            self.assertIsInstance(GUI_AVAILABLE, bool)
            self.assertTrue(callable(launch_gui))
        except ImportError as e:
            self.fail(f"GUI import structure broken: {e}")


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of key components."""

    def setUp(self):
        """Set up test environment."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    def test_natural_sort_functionality(self):
        """Test natural sorting utility."""
        from particle_analysis.utils import natural_sort_key
        from pathlib import Path
        
        # Test natural sorting
        test_files = ['CT1.png', 'CT10.png', 'CT2.png', 'CT20.png']
        test_paths = [Path(f) for f in test_files]
        
        # Alphabetical vs natural
        alpha_sorted = [p.name for p in sorted(test_paths)]
        natural_sorted = [p.name for p in sorted(test_paths, key=natural_sort_key)]
        
        # Natural sort should be different from alphabetical
        self.assertNotEqual(alpha_sorted, natural_sorted)
        
        # Natural sort should have correct order
        self.assertEqual(natural_sorted, ['CT1.png', 'CT2.png', 'CT10.png', 'CT20.png'])

    def test_config_structure(self):
        """Test configuration structure."""
        from particle_analysis.config import DEFAULT_CONFIG
        
        # Check main config components
        self.assertTrue(hasattr(DEFAULT_CONFIG, 'splitting'))
        self.assertTrue(hasattr(DEFAULT_CONFIG, 'contact'))
        self.assertTrue(hasattr(DEFAULT_CONFIG, 'visualization'))
        
        # Check splitting config
        self.assertTrue(hasattr(DEFAULT_CONFIG.splitting, 'erosion_radius'))
        self.assertIsInstance(DEFAULT_CONFIG.splitting.erosion_radius, int)


if __name__ == '__main__':
    unittest.main() 