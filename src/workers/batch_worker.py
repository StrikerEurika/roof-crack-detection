import os
import traceback
from PySide6.QtCore import QThread, Signal

from src.services import InferenceService


class BatchWorker(QThread):
    """Worker thread for processing a batch of images from a folder."""
    
    started_signal = Signal()
    progress_signal = Signal(int, int, str)  # current, total, message
    file_completed_signal = Signal(dict)    # result dictionary for a single file
    finished_signal = Signal(list)          # list of summary dictionaries for all processed files
    error_signal = Signal(str)
    cancelled_signal = Signal()

    def __init__(self, pipeline_config: dict, input_dir: str, output_dir: str, inference_service: InferenceService):
        super().__init__()
        self.config = pipeline_config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.inference_service = inference_service
        self._is_cancelled = False
        self.valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")

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
            pipeline, is_cached = self.inference_service.get_pipeline(self.config)
            if is_cached:
                self.progress_signal.emit(0, total_images, "Using cached model weights.")

            results_summary = []
            
            for idx, filename in enumerate(image_files):
                if self._is_cancelled:
                    self.cancelled_signal.emit()
                    return
                    
                image_path = os.path.join(self.input_dir, filename)
                self.progress_signal.emit(idx, total_images, f"Processing {filename} ({idx+1}/{total_images})...")
                
                try:
                    results, elapsed = self.inference_service.run_pipeline(pipeline, self.config, image_path)
                    file_result = self.inference_service.summarize_result(filename, image_path, results, elapsed)
                    
                    self.file_completed_signal.emit(file_result)
                    
                    results_summary.append({
                        "filename": filename,
                        "image_path": image_path,
                        "crack_detected": file_result["crack_detected"],
                        "crack_count": file_result["crack_count"],
                        "max_confidence": file_result["max_confidence"],
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
