import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from src.model.history_manager import HistoryManager
from src.services.base_service import BaseService
from src.services.inference_service import InferenceService
from src.view_model.inspection_view_model import InspectionViewModel


class TestStorageAndCaching(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hm = HistoryManager(self.test_dir)
        self.inference_service = InferenceService()
        self.base_service = BaseService(self.hm)

        # Create dummy high-res image
        self.dummy_image_path = os.path.join(self.test_dir, "test_highres.jpg")
        arr = np.zeros((1000, 1000, 3), dtype=np.uint8)
        Image.fromarray(arr).save(self.dummy_image_path, "JPEG")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_optimized_image_saving(self):
        vis = np.zeros((1000, 1000, 3), dtype=np.uint8)
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        overlay = np.zeros((1000, 1000, 3), dtype=np.uint8)

        vis_path, overlay_path, mask_path = self.base_service.save_image_assets(
            "roof_test", vis, mask, overlay
        )

        self.assertTrue(os.path.exists(vis_path))
        self.assertTrue(os.path.exists(overlay_path))
        self.assertTrue(os.path.exists(mask_path))

        # Check extensions (JPEG for fast vis & overlay, PNG for mask)
        self.assertTrue(vis_path.endswith(".jpg"))
        self.assertTrue(overlay_path.endswith(".jpg"))
        self.assertTrue(mask_path.endswith(".png"))

        # Check that saved file sizes are reasonably small
        vis_size = os.path.getsize(vis_path)
        self.assertLess(vis_size, 500000) # Fast JPEG should be under 500KB

    def test_history_clearing_deletes_files_and_resets_viewmodel(self):
        # Add a record
        rec = self.hm.add_record(
            image_path=self.dummy_image_path,
            crack_detected=True,
            confidence=0.95,
            crack_count=2,
            model_used="test_model",
            vis_image_path=os.path.join(self.hm.results_dir, "test_vis.jpg"),
            overlay_image_path=os.path.join(self.hm.results_dir, "test_overlay.jpg"),
            mask_image_path=os.path.join(self.hm.results_dir, "test_mask.png"),
            bounding_boxes=[[10, 10, 50, 50]]
        )

        # Touch dummy files in results_dir
        with open(rec["vis_image_path"], "w") as f:
            f.write("dummy")
        with open(rec["overlay_image_path"], "w") as f:
            f.write("dummy")
        with open(rec["mask_image_path"], "w") as f:
            f.write("dummy")

        self.assertEqual(len(self.hm.history), 1)
        self.assertTrue(os.path.exists(rec["vis_image_path"]))

        # Test InspectionViewModel clear_inspection
        vm = InspectionViewModel(self.hm, self.inference_service)
        vm.load_historical_record(rec)
        self.assertEqual(vm.current_image_path, self.dummy_image_path)
        self.assertIsNotNone(vm.latest_record)
        self.assertIsNotNone(vm.latest_result) # Bounding boxes preserved

        cleared_signal_emitted = []
        vm.inspection_cleared.connect(lambda: cleared_signal_emitted.append(True))

        vm.clear_inspection()
        self.assertTrue(cleared_signal_emitted)
        self.assertIsNone(vm.current_image_path)
        self.assertIsNone(vm.latest_record)
        self.assertIsNone(vm.latest_result)

        # Test HistoryManager clear_history
        self.hm.clear_history()
        self.assertEqual(len(self.hm.history), 0)
        self.assertFalse(os.path.exists(rec["vis_image_path"]))
        self.assertFalse(os.path.exists(rec["overlay_image_path"]))
        self.assertFalse(os.path.exists(rec["mask_image_path"]))


if __name__ == "__main__":
    unittest.main()
