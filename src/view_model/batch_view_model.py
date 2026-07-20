# src/view_model/batch_view_model.py

import os
from PySide6.QtCore import QObject, Signal, Slot
from src.workers.batch_worker import BatchWorker
from src.model import HistoryManager
from src.services import BatchService, InferenceService

class BatchViewModel(QObject):
    """ViewModel managing folder-level batch processing execution and states."""
    
    input_dir_changed = Signal(str)
    output_dir_changed = Signal(str)
    batch_started = Signal()
    batch_progress = Signal(int, int, str)  # current, total, message
    file_completed = Signal(dict)           # completed file result
    batch_finished = Signal(list)           # final list of summary results
    batch_error = Signal(str)
    batch_cancelled = Signal()

    def __init__(self, history_manager: HistoryManager, inference_service: InferenceService, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.inference_service = inference_service
        self.batch_service = BatchService(history_manager)
        self.active_worker = None
        self.input_dir = None
        self.output_dir = None

    def set_input_dir(self, dir_path: str):
        """Sets the input directory and calculates default output directory if unset."""
        if not os.path.exists(dir_path):
            self.batch_error.emit(f"Input directory does not exist: {dir_path}")
            return
            
        self.input_dir = dir_path
        self.input_dir_changed.emit(dir_path)
        
        if not self.output_dir:
            self.set_output_dir(os.path.join(dir_path, "results"))

    def set_output_dir(self, dir_path: str):
        """Sets the custom output folder path for saving visualizations."""
        self.output_dir = dir_path
        self.output_dir_changed.emit(dir_path)

    def get_config(self) -> dict:
        return self.hm.config

    def build_pipeline_config(
        self,
        model_variant: str,
        device: str,
        confidence_threshold: float,
        use_tta: bool,
        use_clahe: bool,
    ) -> dict:
        config = self.hm.config
        return self.batch_service.build_pipeline_config(
            model_variant=model_variant,
            device=device,
            confidence_threshold=confidence_threshold,
            patch_size=int(config.get("patch_size", 512)),
            overlap_ratio=float(config.get("overlap_ratio", 0.2)),
            use_tta=use_tta,
            use_clahe=use_clahe,
        )

    def start_batch(self, config_dict: dict):
        """Launches the background BatchWorker thread."""
        if not self.input_dir or not self.output_dir:
            self.batch_error.emit("Please configure both input and output directories.")
            return

        self.batch_started.emit()

        self.active_worker = BatchWorker(config_dict, self.input_dir, self.output_dir, self.inference_service)
        self.active_worker.started_signal.connect(self._on_batch_started)
        self.active_worker.progress_signal.connect(self.batch_progress.emit)
        self.active_worker.file_completed_signal.connect(self._on_file_completed)
        self.active_worker.finished_signal.connect(self._on_batch_finished)
        self.active_worker.error_signal.connect(self._on_batch_error)
        self.active_worker.cancelled_signal.connect(self._on_batch_cancelled)
        self.active_worker.start()

    def cancel_batch(self):
        """Requests cancellation of the active batch job."""
        if self.active_worker:
            self.active_worker.cancel()

    @Slot()
    def _on_batch_started(self):
        # Forward or handle initial progress
        pass

    @Slot(dict)
    def _on_file_completed(self, result):
        """Handles completion of a single file in batch. Saves copies and adds history record."""
        if "error" in result:
            self.file_completed.emit(result)
            return

        results_obj = result.get("results_object")
        model_used = config_model_used(results_obj)
        
        try:
            # Delegate to BatchService to save assets and log history record
            updated_result = self.batch_service.save_and_record_file_result(
                result, self.output_dir, model_used
            )
            self.file_completed.emit(updated_result)
        except Exception as e:
            self.batch_progress.emit(-1, -1, f"Warning: Failed to save result copies for {result.get('filename', 'N/A')}: {e}")
            self.file_completed.emit(result)

    @Slot(list)
    def _on_batch_finished(self, summary_list):
        self.active_worker = None
        self.batch_finished.emit(summary_list)

    @Slot(str)
    def _on_batch_error(self, err):
        self.active_worker = None
        self.batch_error.emit(err)

    @Slot()
    def _on_batch_cancelled(self):
        self.active_worker = None
        self.batch_cancelled.emit()

def config_model_used(results_obj) -> str:
    """Helper to extract model_used safely."""
    from src.services.inference_service import resolve_model_variant
    if results_obj:
        return resolve_model_variant(results_obj.get("model_used"))
    return resolve_model_variant(None)
