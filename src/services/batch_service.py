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
                vis_output_path, overlay_output_path, mask_output_path = self.save_image_assets(
                    base_name, results_obj["visualization"], results_obj["binary_mask"], results_obj.get("overlay")
                )

                user_vis_path = os.path.join(output_dir, f"{base_name}_vis.jpg")
                user_mask_path = os.path.join(output_dir, f"{base_name}_mask.png")

                vis_img = Image.fromarray(results_obj["visualization"])
                if vis_img.mode != "RGB":
                    vis_img = vis_img.convert("RGB")
                vis_img.save(user_vis_path, "JPEG", quality=88, optimize=False)

                if "overlay" in results_obj and results_obj["overlay"] is not None:
                    overlay_arr = results_obj["overlay"]
                    has_alpha = len(overlay_arr.shape) == 3 and overlay_arr.shape[2] == 4
                    user_overlay_path = os.path.join(output_dir, f"{base_name}_overlay.{'png' if has_alpha else 'jpg'}")
                    overlay_img = Image.fromarray(overlay_arr)
                    if has_alpha:
                        overlay_img.save(user_overlay_path, "PNG", compress_level=1)
                    else:
                        if overlay_img.mode != "RGB":
                            overlay_img = overlay_img.convert("RGB")
                        overlay_img.save(user_overlay_path, "JPEG", quality=88, optimize=False)

                mask_img = Image.fromarray(results_obj["binary_mask"])
                if mask_img.mode not in ("L", "1"):
                    mask_img = mask_img.convert("L")
                mask_img.save(user_mask_path, "PNG", compress_level=1)

                self.hm.add_record(
                    image_path=result["image_path"],
                    crack_detected=crack_detected,
                    confidence=max_conf,
                    crack_count=crack_count,
                    model_used=model_used,
                    vis_image_path=vis_output_path,
                    overlay_image_path=overlay_output_path,
                    mask_image_path=mask_output_path,
                    elapsed_time=result["elapsed_time"]
                )
            except Exception as e:
                print(f"Warning: Failed to save result copies: {e}")

        return result
