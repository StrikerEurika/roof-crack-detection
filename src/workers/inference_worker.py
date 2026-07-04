import traceback
from PySide6.QtCore import QThread, Signal

from src.services import InferenceService


class InferenceWorker(QThread):
    """Worker thread for running crack detection inference on a single image."""
    
    started_signal = Signal()
    progress_signal = Signal(str)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, pipeline_config: dict, image_path: str, inference_service: InferenceService):
        super().__init__()
        self.config = pipeline_config
        self.image_path = image_path
        self.inference_service = inference_service

    def run(self):
        try:
            self.started_signal.emit()
            variant = self.inference_service.get_variant(self.config)
            device = self.config.get("device", "cpu")

            self.progress_signal.emit(f"Initializing pipeline with model variant '{variant}' on {device}...")
            pipeline, is_cached = self.inference_service.get_pipeline(self.config)
            if is_cached:
                self.progress_signal.emit("Using cached model weights.")

            self.progress_signal.emit("Running sliding window inference on image patches...")
            results, elapsed = self.inference_service.run_pipeline(pipeline, self.config, self.image_path)
            self.progress_signal.emit(f"Inference completed in {elapsed:.2f} seconds.")
            self.finished_signal.emit(results)

        except Exception as e:
            error_details = traceback.format_exc()
            print(error_details)
            self.error_signal.emit(f"Error running inference: {str(e)}")
