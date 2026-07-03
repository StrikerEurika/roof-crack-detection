import os
import time
import traceback
import numpy as np
import cv2
from PIL import Image
from PySide6.QtCore import QThread, Signal
from src.utils import get_inference_pipeline


class InferenceWorker(QThread):
    """Worker thread for running crack detection inference on a single image."""
    
    started_signal = Signal()
    progress_signal = Signal(str)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, pipeline_config: dict, image_path: str, model_cache=None):
        super().__init__()
        self.config = pipeline_config
        self.image_path = image_path
        self.model_cache = model_cache  # Dictionary to cache loaded models: {variant: pipeline_instance}

    def run(self):
        try:
            self.started_signal.emit()
            start_time = time.time()
            
            # Extract configuration parameters
            variant = self.config.get("model_variant", "Seg_UNET_CFD_actual_v2")
            device = self.config.get("device", "cpu")
            patch_size = self.config.get("patch_size", 512)
            overlap_ratio = self.config.get("overlap_ratio", 0.2)
            confidence_threshold = self.config.get("confidence_threshold", 0.5)
            use_tta = self.config.get("use_tta", False)
            use_clahe = self.config.get("use_clahe", True)
            clahe_clip_limit = self.config.get("clahe_clip_limit", 2.0)
            
            overlay_alpha = self.config.get("overlay_alpha", 0.4)
            # Ensure colors are tuples of integers
            overlay_color = tuple(self.config.get("overlay_color", [255, 0, 0]))
            box_color = tuple(self.config.get("box_color", [0, 255, 0]))
            box_thickness = self.config.get("box_thickness", 2)
            contour_color = tuple(self.config.get("contour_color", [0, 0, 255]))
            contour_thickness = self.config.get("contour_thickness", 2)

            self.progress_signal.emit(f"Initializing pipeline with model variant '{variant}' on {device}...")
            
            pipeline, is_cached = get_inference_pipeline(self.config, self.model_cache)
            if is_cached:
                self.progress_signal.emit("Using cached model weights.")


            self.progress_signal.emit("Running sliding window inference on image patches...")
            
            # Run prediction
            results = pipeline.predict(self.image_path)
            
            elapsed = time.time() - start_time
            results["elapsed_time"] = elapsed
            results["model_used"] = variant
            results["image_path"] = self.image_path
            
            self.progress_signal.emit(f"Inference completed in {elapsed:.2f} seconds.")
            self.finished_signal.emit(results)
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(error_details)
            self.error_signal.emit(f"Error running inference: {str(e)}")
