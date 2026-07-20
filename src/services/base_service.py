import os
import time
from PIL import Image

class BaseService:
    def __init__(self, history_manager):
        self.hm = history_manager

    def build_pipeline_config(self, model_variant, device, confidence_threshold,
                               patch_size, overlap_ratio, use_tta, use_clahe,
                               config_overrides=None) -> dict:
        """Builds a pipeline configuration dictionary based on provided parameters and optional overrides."""
        config = {
            "model_variant": model_variant,
            "device": device,
            "confidence_threshold": confidence_threshold,
            "patch_size": patch_size,
            "overlap_ratio": overlap_ratio,
            "use_tta": use_tta,
            "use_clahe": use_clahe,
            "clahe_clip_limit": 2.0,
            "overlay_alpha": self.hm.config.get("overlay_alpha", 0.4),
            "overlay_color": self.hm.config.get("overlay_color", [255, 0, 0]),
            "box_color": self.hm.config.get("box_color", [0, 255, 0]),
            "box_thickness": self.hm.config.get("box_thickness", 2),
            "contour_color": self.hm.config.get("contour_color", [0, 0, 255]),
            "contour_thickness": self.hm.config.get("contour_thickness", 2),
        }
        if config_overrides:
            config.update(config_overrides)
        return config

    def save_image_assets(self, base_name: str, visualization: object, binary_mask: object, overlay: object = None) -> tuple:
        """Saves visualization, transparent overlay, and binary mask to the historical results folder."""
        timestamp_slug = int(time.time())
        vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
        overlay_filename = f"{base_name}_overlay_{timestamp_slug}.png"
        mask_filename = f"{base_name}_mask_{timestamp_slug}.png"

        vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
        overlay_output_path = os.path.join(self.hm.results_dir, overlay_filename)
        mask_output_path = os.path.join(self.hm.results_dir, mask_filename)

        try:
            Image.fromarray(visualization).save(vis_output_path)
            if overlay is not None:
                Image.fromarray(overlay).save(overlay_output_path)
            else:
                overlay_output_path = vis_output_path
            Image.fromarray(binary_mask).save(mask_output_path)
        except Exception as e:
            print(f"Warning: Failed to save result assets: {e}")
            raise e

        return vis_output_path, overlay_output_path, mask_output_path
