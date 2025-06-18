#!/usr/bin/env python3
"""End-to-end pipeline test for CI/CD."""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os
import subprocess

# Add src to path for the new package structure
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestPipelineEnd2End(unittest.TestCase):
    """End-to-end test for the complete pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment with sample data."""
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.data_dir = cls.test_dir / "data"
        cls.images_dir = cls.data_dir / "images"
        cls.masks_dir = cls.data_dir / "masks_otsu"
        cls.output_dir = cls.test_dir / "output"
        
        # Create directories
        cls.images_dir.mkdir(parents=True)
        cls.masks_dir.mkdir(parents=True)
        cls.output_dir.mkdir(parents=True)
        
        # Generate minimal test data
        cls._generate_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.test_dir, ignore_errors=True)
    
    @classmethod
    def _generate_test_data(cls):
        """Generate minimal test CT images and masks."""
        import numpy as np
        import cv2
        
        # Create 3 simple test images and masks
        for i in range(3):
            # Create a simple test image (64x64)
            img = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
            img_path = cls.images_dir / f"slice_{i:03d}.png"
            cv2.imwrite(str(img_path), img)
            
            # Create a simple test mask with a few particles
            mask = np.zeros((64, 64), dtype=np.uint8)
            # Add some circular particles that might touch each other
            cv2.circle(mask, (16, 16), 6, 255, -1)
            cv2.circle(mask, (22, 16), 5, 255, -1)  # Close to first particle
            cv2.circle(mask, (48, 16), 5, 255, -1)
            cv2.circle(mask, (32, 48), 6, 255, -1)
            cv2.circle(mask, (40, 45), 5, 255, -1)  # Close to previous particle
            
            mask_path = cls.masks_dir / f"slice_{i:03d}.png"
            cv2.imwrite(str(mask_path), mask)
    
    def test_individual_modules(self):
        """Test individual modules using the new package structure."""
        from particle_analysis.processing import process_masks
        from particle_analysis.volume_ops import stack_masks, split_particles
        from particle_analysis.contact_analysis import count_contacts, save_contact_csv
        
        # Test 1: process_masks
        processed_count = process_masks(
            img_dir=str(self.images_dir),
            mask_dir=str(self.masks_dir),
            out_dir=str(self.output_dir),
            force=True
        )
        self.assertGreater(processed_count, 0, "No masks processed")
        
        # Test 2: stack_masks
        volume_path = self.output_dir / "volume.npy"
        stack_masks(
            mask_dir=str(self.output_dir / "masks_pred"),
            out_vol=str(volume_path),
            dtype="bool"
        )
        self.assertTrue(volume_path.exists(), "Volume not created")
        
        # Test 3: split_particles
        labels_path = self.output_dir / "labels.npy"
        num_particles = split_particles(
            vol_path=str(volume_path),
            out_labels=str(labels_path),
            radius=1  # Small radius for test data
        )
        self.assertGreater(num_particles, 0, "No particles detected")
        
        # Test 4: count_contacts
        import numpy as np
        labels = np.load(labels_path)
        contacts_dict = count_contacts(labels)
        
        csv_path = self.output_dir / "contact_counts.csv"
        save_contact_csv(contacts_dict, str(csv_path))
        self.assertTrue(csv_path.exists(), "Contact CSV not created")
    
    def test_full_pipeline(self):
        """Test the complete pipeline script."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        
        result = subprocess.run([
            sys.executable, str(scripts_dir / "run_pipeline.py"),
            "--img_dir", str(self.images_dir),
            "--mask_dir", str(self.masks_dir),
            "--output_dir", str(self.output_dir / "pipeline_test"),
            "--erosion_radius", "1",  # Small radius for test data
            "--verbose"
        ], capture_output=True, text=True)
        
        print(f"Pipeline stdout: {result.stdout}")
        print(f"Pipeline stderr: {result.stderr}")
        
        self.assertEqual(result.returncode, 0, f"Pipeline failed: {result.stderr}")
        
        # Check that all expected outputs exist
        pipeline_outputs = list((self.output_dir / "pipeline_test").glob("run_*"))
        self.assertTrue(len(pipeline_outputs) > 0, "No pipeline output directory created")
        
        pipeline_output = pipeline_outputs[0]
        
        # Required files
        required_files = [
            "masks_pred",
            "volume.npy",
            "contact_counts.csv"
        ]
        
        # Optional files (may not exist for small test data)
        optional_files = [
            "contacts_summary.csv",
            "hist_contacts.png"
        ]
        
        for required_file in required_files:
            file_path = pipeline_output / required_file
            self.assertTrue(file_path.exists(), f"Missing required output file: {required_file}")
        
        for optional_file in optional_files:
            file_path = pipeline_output / optional_file
            if not file_path.exists():
                print(f"Optional file not generated (acceptable for test data): {optional_file}")
        
        # Verify final statistics (if generated)
        summary_path = pipeline_output / "contacts_summary.csv"
        if summary_path.exists():
            import pandas as pd
            df = pd.read_csv(summary_path)
            self.assertTrue(len(df) > 0, "No summary statistics generated")
        else:
            print("Summary statistics not generated (acceptable for small test data)")


def run_ci_test():
    """Run CI-friendly test with minimal output."""
    print("Starting end-to-end pipeline test...")
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPipelineEnd2End)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_ci_test()) 