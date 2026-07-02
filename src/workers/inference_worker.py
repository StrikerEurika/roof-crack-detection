import os
import time
import traceback
import numpy as np
import cv2
from PIL import Image
from PySide6.QtCore import QThread, Signal

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
            
            # Check model cache
            pipeline = None
            if self.model_cache is not None and variant in self.model_cache:
                # If cached, update pipeline parameters without reloading weights
                pipeline = self.model_cache[variant]
                pipeline.device = device
                pipeline.patch_size = patch_size
                pipeline.overlap_ratio = overlap_ratio
                pipeline.confidence_threshold = confidence_threshold
                pipeline.use_tta = use_tta
                pipeline.preprocessor.use_clahe = use_clahe
                pipeline.preprocessor.clip_limit = clahe_clip_limit
                pipeline.overlay_alpha = overlay_alpha
                pipeline.overlay_color = overlay_color
                pipeline.box_color = box_color
                pipeline.box_thickness = box_thickness
                pipeline.contour_color = contour_color
                pipeline.contour_thickness = contour_thickness
                # Update PatchExtractor
                pipeline.extractor.patch_size = patch_size
                pipeline.extractor.overlap_ratio = overlap_ratio
                self.progress_signal.emit("Using cached model weights.")
            else:
                # Import and load model
                from findcrack.inference import CrackInferencePipeline
                
                pipeline = CrackInferencePipeline.from_pretrained(
                    variant=variant,
                    device=device,
                    patch_size=patch_size,
                    overlap_ratio=overlap_ratio,
                    confidence_threshold=confidence_threshold,
                    use_tta=use_tta,
                    use_clahe=use_clahe,
                    clahe_clip_limit=clahe_clip_limit,
                    overlay_alpha=overlay_alpha,
                    overlay_color=overlay_color,
                    box_color=box_color,
                    box_thickness=box_thickness,
                    contour_color=contour_color,
                    contour_thickness=contour_thickness
                )
                
                if self.model_cache is not None:
                    self.model_cache[variant] = pipeline

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
