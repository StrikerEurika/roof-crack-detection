import os
import time
from PIL import Image
from PySide6.QtCore import QObject, Signal, Slot
from src.workers.batch_worker import BatchWorker
from src.controllers.history_manager import HistoryManager

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

    def __init__(self, history_manager: HistoryManager, model_cache: dict, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.model_cache = model_cache
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

    def start_batch(self, config_dict: dict):
        """Launches the background BatchWorker thread."""
        if not self.input_dir or not self.output_dir:
            self.batch_error.emit("Please configure both input and output directories.")
            return

        self.batch_started.emit()

        self.active_worker = BatchWorker(config_dict, self.input_dir, self.output_dir, self.model_cache)
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
        filename = result["filename"]
        
        # If it failed during worker execution
        if "error" in result:
            self.file_completed.emit(result)
            return

        # Save result assets to the app's global assets folder so it is visible in Recents history!
        results_obj = result.get("results_object")
        crack_detected = result["crack_detected"]
        crack_count = result["crack_count"]
        max_conf = result["max_confidence"]
        
        if results_obj:
            base_name, _ = os.path.splitext(filename)
            timestamp_slug = int(time.time())
            
            vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
            mask_filename = f"{base_name}_mask_{timestamp_slug}.png"
            
            vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
            mask_output_path = os.path.join(self.hm.results_dir, mask_filename)
            
            try:
                # Save to app global assets results
                Image.fromarray(results_obj["visualization"]).save(vis_output_path)
                Image.fromarray(results_obj["binary_mask"]).save(mask_output_path)
                
                # Save also to user configured batch output directory
                user_vis_path = os.path.join(self.output_dir, f"{base_name}_overlay.png")
                user_mask_path = os.path.join(self.output_dir, f"{base_name}_mask.png")
                Image.fromarray(results_obj["visualization"]).save(user_vis_path)
                Image.fromarray(results_obj["binary_mask"]).save(user_mask_path)
                
                # Add historical entry in database
                self.hm.add_record(
                    image_path=result["image_path"],
                    crack_detected=crack_detected,
                    confidence=max_conf,
                    crack_count=crack_count,
                    model_used=config_model_used(results_obj), # fall back to result model
                    vis_image_path=vis_output_path,
                    mask_image_path=mask_output_path,
                    elapsed_time=result["elapsed_time"]
                )
            except Exception as e:
                # Append error or emit progress warning
                self.batch_progress.emit(-1, -1, f"Warning: Failed to save result copies for {filename}: {e}")
        
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
    return results_obj.get("model_used", "Seg_UNET_CFD_actual_v2")
