_gpu_available_cache = None

def check_gpu_available() -> bool:
    """Checks if CUDA GPU acceleration is available via ONNX Runtime or PyTorch."""
    global _gpu_available_cache
    if _gpu_available_cache is not None:
        return _gpu_available_cache

    try:
        import onnxruntime as ort
        if any("CUDA" in p for p in ort.get_available_providers()):
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

def get_inference_pipeline(config: dict, model_cache: dict = None):
    """Retrieves a cached inference pipeline or instantiates a new one from configurations.
    
    If the model variant is already in the cache, it updates the runtime parameters 
    without re-loading the neural network weights from disk.
    """
    variant = config.get("model_variant", "Seg_UNET_CFD_actual_v2")
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
    
    if model_cache is not None and variant in model_cache:
        pipeline = model_cache[variant]
        # Update settings without reloading weights
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
        
        # Update components
        if hasattr(pipeline, "extractor") and pipeline.extractor is not None:
            pipeline.extractor.patch_size = patch_size
            pipeline.extractor.overlap_ratio = overlap_ratio
            
        is_cached = True
    else:
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
        if model_cache is not None:
            model_cache[variant] = pipeline
        is_cached = False
        
    return pipeline, is_cached
