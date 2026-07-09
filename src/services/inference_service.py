import time


_gpu_available_cache = None


def check_gpu_available() -> bool:
    """Checks if CUDA GPU acceleration is available via ONNX Runtime or PyTorch."""
    global _gpu_available_cache
    if _gpu_available_cache is not None:
        return _gpu_available_cache

    try:
        import onnxruntime as ort

        if any("CUDA" in provider for provider in ort.get_available_providers()):
            _gpu_available_cache = True
            return True
    except Exception:
        pass

    try:
        import torch

        if torch.cuda.is_available():
            _gpu_available_cache = True
            return True
    except Exception:
        pass

    _gpu_available_cache = False
    return False


class InferenceService:
    """Owns model pipeline loading, cache updates, and inference result shaping."""

    DEFAULT_VARIANT = "Seg_UNET_CFD_actual_v2"

    def __init__(self, model_cache: dict | None = None):
        self.model_cache = model_cache if model_cache is not None else {}

    def clear_cache(self):
        self.model_cache.clear()

    def get_variant(self, config: dict) -> str:
        return config.get("model_variant", self.DEFAULT_VARIANT)

    def get_pipeline(self, config: dict):
        variant = self.get_variant(config)
        device = config.get("device", "cpu")
        patch_size = config.get("patch_size", 512)
        overlap_ratio = config.get("overlap_ratio", 0.2)
        confidence_threshold = config.get("confidence_threshold", 0.5)
        use_tta = config.get("use_tta", False)
        use_clahe = config.get("use_clahe", True)
        clahe_clip_limit = config.get("clahe_clip_limit", 2.0)
        overlay_alpha = config.get("overlay_alpha", 0.4)
        overlay_color = tuple(config.get("overlay_color", [255, 0, 0]))
        box_color = tuple(config.get("box_color", [0, 255, 0]))
        box_thickness = config.get("box_thickness", 2)
        contour_color = tuple(config.get("contour_color", [0, 0, 255]))
        contour_thickness = config.get("contour_thickness", 2)

        if variant in self.model_cache:
            pipeline = self.model_cache[variant]
            self._apply_runtime_config(
                pipeline,
                device,
                patch_size,
                overlap_ratio,
                confidence_threshold,
                use_tta,
                use_clahe,
                clahe_clip_limit,
                overlay_alpha,
                overlay_color,
                box_color,
                box_thickness,
                contour_color,
                contour_thickness,
            )
            return pipeline, True

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
            contour_thickness=contour_thickness,
        )
        self.model_cache[variant] = pipeline
        return pipeline, False

    def predict_image(self, config: dict, image_path: str) -> tuple[dict, bool, float]:
        pipeline, is_cached = self.get_pipeline(config)
        results, elapsed = self.run_pipeline(pipeline, config, image_path)
        return results, is_cached, elapsed

    def run_pipeline(self, pipeline, config: dict, image_path: str) -> tuple[dict, float]:
        start_time = time.time()
        results = pipeline.predict(image_path)
        elapsed = time.time() - start_time
        results["elapsed_time"] = elapsed
        results["model_used"] = self.get_variant(config)
        results["image_path"] = image_path
        return results, elapsed

    def summarize_result(self, filename: str, image_path: str, results: dict, elapsed: float) -> dict:
        bounding_boxes = results["bounding_boxes"]
        confidence_map = results["confidence_map"]
        return {
            "filename": filename,
            "image_path": image_path,
            "crack_detected": len(bounding_boxes) > 0,
            "crack_count": len(bounding_boxes),
            "max_confidence": float(confidence_map.max()) if confidence_map.size > 0 else 0.0,
            "elapsed_time": elapsed,
            "results_object": results,
        }

    def _apply_runtime_config(
        self,
        pipeline,
        device,
        patch_size,
        overlap_ratio,
        confidence_threshold,
        use_tta,
        use_clahe,
        clahe_clip_limit,
        overlay_alpha,
        overlay_color,
        box_color,
        box_thickness,
        contour_color,
        contour_thickness,
    ):
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

        if hasattr(pipeline, "extractor") and pipeline.extractor is not None:
            pipeline.extractor.patch_size = patch_size
            pipeline.extractor.overlap_ratio = overlap_ratio


def get_inference_pipeline(config: dict, model_cache: dict | None = None):
    """Compatibility wrapper for legacy callers."""
    return InferenceService(model_cache).get_pipeline(config)
