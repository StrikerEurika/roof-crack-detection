# src/view_model/inspection_view_model.py

import os
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from src.workers.inference_worker import InferenceWorker
from src.reports.pdf_generator import PDFReportGenerator
from src.model import HistoryManager
from src.services import InferenceService, InspectionService

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

    def __init__(self, history_manager: HistoryManager, inference_service: InferenceService, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.inference_service = inference_service
        self.inspection_service = InspectionService(history_manager)
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

    def get_config(self) -> dict:
        return self.hm.config

    def get_default_reports_dir(self) -> str:
        return self.hm.config.get("default_reports_dir", self.hm.reports_dir)

    def build_pipeline_config(
        self,
        model_variant: str,
        device: str,
        confidence_threshold: float,
        patch_size: int,
        overlap_ratio: float,
        use_tta: bool,
        use_clahe: bool,
    ) -> dict:
        return self.inspection_service.build_pipeline_config(
            model_variant=model_variant,
            device=device,
            confidence_threshold=confidence_threshold,
            patch_size=patch_size,
            overlap_ratio=overlap_ratio,
            use_tta=use_tta,
            use_clahe=use_clahe,
        )

    def run_detection(self, config_dict: dict):
        """Launches the background InferenceWorker thread with selected configurations."""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.detection_error.emit("Please load a valid image file first.")
            return

        self.detection_started.emit()

        # Instantiate background worker
        self.active_worker = InferenceWorker(config_dict, self.current_image_path, self.inference_service)
        self.active_worker.progress_signal.connect(self.detection_progress.emit)
        self.active_worker.finished_signal.connect(self._on_inference_completed)
        self.active_worker.error_signal.connect(self._on_inference_error)
        self.active_worker.start()

    @Slot(dict)
    def _on_inference_completed(self, results):
        """Handles completion of the inference, saves result assets, and updates history database."""
        self.latest_result = results
        
        try:
            processed = self.inspection_service.save_and_record_results(
                results, self.current_image_path, results["model_used"]
            )
            self.latest_record = processed.record

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
        except Exception as e:
            self.detection_error.emit(f"Failed to process and record inspection results: {str(e)}")

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
