import os
import time
import traceback
from PySide6.QtCore import QThread, Signal
from src.utils import get_inference_pipeline


class BatchWorker(QThread):
    """Worker thread for processing a batch of images from a folder."""
    
    started_signal = Signal()
    progress_signal = Signal(int, int, str)  # current, total, message
    file_completed_signal = Signal(dict)    # result dictionary for a single file
    finished_signal = Signal(list)          # list of summary dictionaries for all processed files
    error_signal = Signal(str)
    cancelled_signal = Signal()

    def __init__(self, pipeline_config: dict, input_dir: str, output_dir: str, model_cache=None):
        super().__init__()
        self.config = pipeline_config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.model_cache = model_cache
        self._is_cancelled = False
        
        # Valid image extensions
        self.valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.started_signal.emit()
            
            # Find all images
            if not os.path.exists(self.input_dir):
                self.error_signal.emit(f"Input directory does not exist: {self.input_dir}")
                return
                
            os.makedirs(self.output_dir, exist_ok=True)
            
            all_files = os.listdir(self.input_dir)
            image_files = [f for f in all_files if f.lower().endswith(self.valid_extensions)]
            total_images = len(image_files)
            
            if total_images == 0:
                self.error_signal.emit(f"No valid images found in input directory. Supported formats: {', '.join(self.valid_extensions)}")
                return
                
            self.progress_signal.emit(0, total_images, f"Found {total_images} images to process. Initializing model...")
            
            # Initialize model (same as in InferenceWorker)
            variant = self.config.get("model_variant", "Seg_UNET_CFD_actual_v2")
            device = self.config.get("device", "cpu")
            patch_size = self.config.get("patch_size", 512)
            overlap_ratio = self.config.get("overlap_ratio", 0.2)
            confidence_threshold = self.config.get("confidence_threshold", 0.5)
            use_tta = self.config.get("use_tta", False)
            use_clahe = self.config.get("use_clahe", True)
            clahe_clip_limit = self.config.get("clahe_clip_limit", 2.0)
            
            overlay_alpha = self.config.get("overlay_alpha", 0.4)
            overlay_color = tuple(self.config.get("overlay_color", [255, 0, 0]))
            box_color = tuple(self.config.get("box_color", [0, 255, 0]))
            box_thickness = self.config.get("box_thickness", 2)
            contour_color = tuple(self.config.get("contour_color", [0, 0, 255]))
            contour_thickness = self.config.get("contour_thickness", 2)
            
            pipeline, is_cached = get_inference_pipeline(self.config, self.model_cache)


            results_summary = []
            
            for idx, filename in enumerate(image_files):
                if self._is_cancelled:
                    self.cancelled_signal.emit()
                    return
                    
                image_path = os.path.join(self.input_dir, filename)
                self.progress_signal.emit(idx, total_images, f"Processing {filename} ({idx+1}/{total_images})...")
                
                try:
                    start_time = time.time()
                    results = pipeline.predict(image_path)
                    elapsed = time.time() - start_time
                    
                    # Store results in a dictionary for saving
                    crack_detected = len(results["bounding_boxes"]) > 0
                    max_conf = float(results["confidence_map"].max()) if results["confidence_map"].size > 0 else 0.0
                    
                    # Prepare file result dict
                    file_result = {
                        "filename": filename,
                        "image_path": image_path,
                        "crack_detected": crack_detected,
                        "crack_count": len(results["bounding_boxes"]),
                        "max_confidence": max_conf,
                        "elapsed_time": elapsed,
                        "results_object": results # Include full dict to allow saving visualization
                    }
                    
                    self.file_completed_signal.emit(file_result)
                    
                    # Add to summary (exclude raw arrays to save memory)
                    results_summary.append({
                        "filename": filename,
                        "image_path": image_path,
                        "crack_detected": crack_detected,
                        "crack_count": len(results["bounding_boxes"]),
                        "max_confidence": max_conf,
                        "elapsed_time": elapsed
                    })
                    
                except Exception as file_err:
                    print(f"Error processing file {filename}: {file_err}")
                    file_result = {
                        "filename": filename,
                        "image_path": image_path,
                        "crack_detected": False,
                        "crack_count": 0,
                        "max_confidence": 0.0,
                        "elapsed_time": 0.0,
                        "error": str(file_err)
                    }
                    self.file_completed_signal.emit(file_result)
                    results_summary.append(file_result)
                    
            self.progress_signal.emit(total_images, total_images, f"Batch processing completed. Total processed: {total_images}")
            self.finished_signal.emit(results_summary)
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(error_details)
            self.error_signal.emit(f"Error running batch processing: {str(e)}")
