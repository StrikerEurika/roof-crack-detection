"""
Roof Crack Inspection Suite
---------------------------
Core application package containing modular components for GUI, database controllers,
background processing workers, and PDF reporting.
"""

__version__ = "1.0.0"

from .services import (
    check_gpu_available,
    get_inference_pipeline,
    get_available_model_variants,
    resolve_model_variant,
)

__all__ = [
    "check_gpu_available",
    "get_inference_pipeline",
    "get_available_model_variants",
    "resolve_model_variant",
]
