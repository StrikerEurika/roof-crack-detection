import os
import time
import numpy as np
from PIL import Image
from dataclasses import dataclass, field


from .base_service import BaseService


@dataclass
class ProcessedResult:
    vis_output_path: str = ""
    overlay_output_path: str = ""
    mask_output_path: str = ""
    record: dict = field(default_factory=dict)
    crack_count: int = 0
    crack_detected: bool = False
    max_conf: float = 0.0
    bounding_boxes: list = field(default_factory=list)
    severity_data: list = field(default_factory=list)


class InspectionService(BaseService):
    def save_and_record_results(self, results: dict, image_path: str, model_used: str) -> ProcessedResult:
        image_name = os.path.basename(image_path)
        base_name, _ = os.path.splitext(image_name)

        # Call base service method to save visualizations
        vis_output_path, overlay_output_path, mask_output_path = self.save_image_assets(
            base_name, results["visualization"], results["binary_mask"], results.get("overlay")
        )

        crack_count = len(results["bounding_boxes"])
        crack_detected = crack_count > 0
        max_conf = float(results["confidence_map"].max()) if results["confidence_map"].size > 0 else 0.0

        record = self.hm.add_record(
            image_path=image_path,
            crack_detected=crack_detected,
            confidence=max_conf,
            crack_count=crack_count,
            model_used=model_used,
            vis_image_path=vis_output_path,
            overlay_image_path=overlay_output_path,
            mask_image_path=mask_output_path,
            elapsed_time=results["elapsed_time"]
        )

        severity_data = []
        for box in results["bounding_boxes"]:
            w = box[2] - box[0]
            h = box[3] - box[1]
            area = w * h
            severity = self._classify_severity(area)
            severity_data.append({"area": area, "severity": severity, "box": box})

        return ProcessedResult(
            vis_output_path=vis_output_path,
            overlay_output_path=overlay_output_path,
            mask_output_path=mask_output_path,
            record=record,
            crack_count=crack_count,
            crack_detected=crack_detected,
            max_conf=max_conf,
            bounding_boxes=results["bounding_boxes"],
            severity_data=severity_data,
        )

    def _classify_severity(self, area: int) -> str:
        if area > 1000:
            return "Critical"
        elif area > 200:
            return "Medium"
        return "Minor"

    def prepare_confidence_display(self, confidence_map: np.ndarray) -> np.ndarray:
        conf_map = (confidence_map * 255).astype("uint8")
        return np.stack([conf_map, conf_map, conf_map], axis=-1)
