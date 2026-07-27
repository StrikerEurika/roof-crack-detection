import os
import unittest
import tempfile
import shutil
from PySide6.QtWidgets import QApplication

from src.model import HistoryManager
from src.view_model import HistoryViewModel

# Global QApplication instance for PySide6 tests
app = QApplication.instance() or QApplication([])

class TestHistoryViewModel(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.hm = HistoryManager(self.test_dir)
        self.vm = HistoryViewModel(self.hm)

        # Add dummy history records
        self.rec1 = self.hm.add_record(
            image_path=os.path.join(self.test_dir, "test_roof_1.jpg"),
            crack_detected=True,
            confidence=0.92,
            crack_count=3,
            model_used="resnet50_unet",
            elapsed_time=0.45
        )
        self.rec2 = self.hm.add_record(
            image_path=os.path.join(self.test_dir, "test_roof_2.jpg"),
            crack_detected=False,
            confidence=0.15,
            crack_count=0,
            model_used="effnet_unet",
            elapsed_time=0.30
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_history_filtering(self):
        all_recs = self.vm.get_history(filter_status="All")
        self.assertEqual(len(all_recs), 2)

        crack_recs = self.vm.get_history(filter_status="Cracks Detected")
        self.assertEqual(len(crack_recs), 1)
        self.assertTrue(crack_recs[0]["crack_detected"])

        clean_recs = self.vm.get_history(filter_status="No Cracks")
        self.assertEqual(len(clean_recs), 1)
        self.assertFalse(clean_recs[0]["crack_detected"])

    def test_get_history_search(self):
        recs = self.vm.get_history(search_query="roof_1")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["image_name"], "test_roof_1.jpg")

    def test_select_record(self):
        selected = []
        self.vm.record_selected.connect(lambda r: selected.append(r))
        self.vm.select_record(self.rec1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["id"], self.rec1["id"])

    def test_delete_record(self):
        rec_id = self.rec1["id"]
        success = self.vm.delete_record(rec_id)
        self.assertTrue(success)
        self.assertEqual(len(self.hm.history), 1)

if __name__ == "__main__":
    unittest.main()
