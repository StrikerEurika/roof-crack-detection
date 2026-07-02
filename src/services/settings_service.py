class SettingsService:
    COLOR_MAP = {
        "Red": [255, 0, 0],
        "Green": [0, 255, 0],
        "Blue": [0, 0, 255],
        "Yellow": [255, 255, 0],
    }

    REVERSE_COLOR_MAP = {
        (255, 0, 0): "Red",
        (0, 255, 0): "Green",
        (0, 0, 255): "Blue",
        (255, 255, 0): "Yellow",
    }

    def __init__(self, history_manager):
        self.hm = history_manager

    def color_to_rgb(self, name: str) -> list:
        return self.COLOR_MAP.get(name, [255, 0, 0])

    def rgb_to_color_name(self, rgb: list) -> str:
        return self.REVERSE_COLOR_MAP.get(tuple(rgb), "Red")

    def build_config_from_state(self, model_variant, device, confidence_threshold,
                                overlay_alpha, overlay_color_name, box_color_name,
                                contour_color_name, reports_dir) -> dict:
        return {
            "model_variant": model_variant,
            "device": device,
            "confidence_threshold": confidence_threshold,
            "overlay_alpha": overlay_alpha,
            "overlay_color": self.color_to_rgb(overlay_color_name),
            "box_color": self.color_to_rgb(box_color_name),
            "contour_color": self.color_to_rgb(contour_color_name),
            "default_reports_dir": reports_dir,
        }
