import os
import time
from PIL import Image


from .base_service import BaseService


class BatchService(BaseService):
    def save_and_record_file_result(self, result: dict, output_dir: str, model_used: str) -> dict:
        filename = result["filename"]
        crack_detected = result["crack_detected"]
        crack_count = result["crack_count"]
        max_conf = result["max_confidence"]

        results_obj = result.get("results_object")
        if results_obj:
            base_name, _ = os.path.splitext(filename)

            try:
                # Call base service method to save visualizations to history results folder
                vis_output_path, mask_output_path = self.save_image_assets(
                    base_name, results_obj["visualization"], results_obj["binary_mask"]
                )

                user_vis_path = os.path.join(output_dir, f"{base_name}_overlay.png")
                user_mask_path = os.path.join(output_dir, f"{base_name}_mask.png")
                Image.fromarray(results_obj["visualization"]).save(user_vis_path)
                Image.fromarray(results_obj["binary_mask"]).save(user_mask_path)

                self.hm.add_record(
                    image_path=result["image_path"],
                    crack_detected=crack_detected,
                    confidence=max_conf,
                    crack_count=crack_count,
                    model_used=model_used,
                    vis_image_path=vis_output_path,
                    mask_image_path=mask_output_path,
                    elapsed_time=result["elapsed_time"]
                )
            except Exception as e:
                print(f"Warning: Failed to save result copies: {e}")

        return result
