import os
import time
import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, Signal, Slot
from src.workers.inference_worker import InferenceWorker
from src.reports.pdf_generator import PDFReportGenerator
from src.controllers.history_manager import HistoryManager

class InspectionViewModel(QObject):
    """ViewModel managing single image inspection operations, state, and reports."""
    
    image_loaded = Signal(str)
    record_loaded = Signal(dict)
    detection_started = Signal()
    detection_progress = Signal(str)
    detection_finished = Signal(dict) # Contains latest record and processed arrays
    detection_error = Signal(str)
    report_exported = Signal(str)
    report_export_failed = Signal(str)

    def __init__(self, history_manager: HistoryManager, model_cache: dict, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.model_cache = model_cache
        self.active_worker = None
        self.current_image_path = None
        self.latest_result = None
        self.latest_record = None

    def load_image(self, file_path: str):
        """Loads a target image file and resets results state."""
        if not os.path.exists(file_path):
            self.detection_error.emit(f"File does not exist: {file_path}")
            return
            
        self.current_image_path = file_path
        self.latest_result = None
        self.latest_record = None
        self.image_loaded.emit(file_path)

    def load_historical_record(self, record: dict):
        """Loads historical record state directly into the ViewModel."""
        self.current_image_path = record.get("image_path")
        self.latest_record = record
        self.latest_result = None
        self.record_loaded.emit(record)

    def run_detection(self, config_dict: dict):
        """Launches the background InferenceWorker thread with selected configurations."""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.detection_error.emit("Please load a valid image file first.")
            return

        self.detection_started.emit()

        # Instantiate background worker
        self.active_worker = InferenceWorker(config_dict, self.current_image_path, self.model_cache)
        self.active_worker.progress_signal.connect(self.detection_progress.emit)
        self.active_worker.finished_signal.connect(self._on_inference_completed)
        self.active_worker.error_signal.connect(self._on_inference_error)
        self.active_worker.start()

    @Slot(dict)
    def _on_inference_completed(self, results):
        """Handles completion of the inference, saves result assets, and updates history database."""
        self.latest_result = results
        
        # Save output images to assets/results folder
        image_name = os.path.basename(self.current_image_path)
        base_name, _ = os.path.splitext(image_name)
        timestamp_slug = int(time.time())
        
        vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
        mask_filename = f"{base_name}_mask_{timestamp_slug}.png"
        
        vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
        mask_output_path = os.path.join(self.hm.results_dir, mask_filename)
        
        try:
            Image.fromarray(results["visualization"]).save(vis_output_path)
            Image.fromarray(results["binary_mask"]).save(mask_output_path)
        except Exception as e:
            self.detection_progress.emit(f"Warning: Failed to save result assets to disk: {e}")

        # Update history database
        crack_count = len(results["bounding_boxes"])
        crack_detected = crack_count > 0
        max_conf = float(results["confidence_map"].max()) if results["confidence_map"].size > 0 else 0.0
        
        # Create record in HistoryManager
        self.latest_record = self.hm.add_record(
            image_path=self.current_image_path,
            crack_detected=crack_detected,
            confidence=max_conf,
            crack_count=crack_count,
            model_used=results["model_used"],
            vis_image_path=vis_output_path,
            mask_image_path=mask_output_path,
            elapsed_time=results["elapsed_time"]
        )

        output_payload = {
            "record": self.latest_record,
            "original_image": results["original_image"],
            "visualization": results["visualization"],
            "overlay": results["overlay"],
            "binary_mask": results["binary_mask"],
            "confidence_map": results["confidence_map"],
            "bounding_boxes": results["bounding_boxes"]
        }
        
        self.detection_finished.emit(output_payload)

    @Slot(str)
    def _on_inference_error(self, err):
        self.detection_error.emit(err)

    def export_report(self, output_pdf_path: str):
        """Generates PDF report for the active record and stores paths in history."""
        if not self.latest_record:
            self.report_export_failed.emit("No active inspection record available to export.")
            return

        try:
            success = PDFReportGenerator.generate_report(self.latest_record, output_pdf_path)
            if success:
                self.hm.update_report_path(self.latest_record["id"], output_pdf_path)
                self.report_exported.emit(output_pdf_path)
            else:
                self.report_export_failed.emit("Report generator failed to output PDF.")
        except Exception as e:
            self.report_export_failed.emit(f"Error during PDF generation: {str(e)}")
