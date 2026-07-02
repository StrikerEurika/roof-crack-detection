import os
import time
from PIL import Image


class BatchService:
    def __init__(self, history_manager):
        self.hm = history_manager

    def save_and_record_file_result(self, result: dict, output_dir: str, model_used: str) -> dict:
        filename = result["filename"]
        crack_detected = result["crack_detected"]
        crack_count = result["crack_count"]
        max_conf = result["max_confidence"]

        results_obj = result.get("results_object")
        if results_obj:
            base_name, _ = os.path.splitext(filename)
            timestamp_slug = int(time.time())

            vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
            mask_filename = f"{base_name}_mask_{timestamp_slug}.png"

            vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
            mask_output_path = os.path.join(self.hm.results_dir, mask_filename)

            try:
                Image.fromarray(results_obj["visualization"]).save(vis_output_path)
                Image.fromarray(results_obj["binary_mask"]).save(mask_output_path)

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
