# src/model/history_manager.py

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

class HistoryManager:
    """Manages system configuration and inspection history database."""
    
    def __init__(self, workspace_dir: str):
        import sys
        if getattr(sys, "frozen", False):
            self.workspace_dir = os.path.join(os.path.expanduser("~"), ".roof-crack-detection")
        else:
            self.workspace_dir = workspace_dir
            
        self.settings_dir = os.path.join(self.workspace_dir, "settings")
        self.assets_dir = os.path.join(self.workspace_dir, "assets")
        self.results_dir = os.path.join(self.assets_dir, "results")
        self.reports_dir = os.path.join(self.workspace_dir, "reports")
        
        # Create directories if they do not exist
        os.makedirs(self.settings_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        
        self.config_path = os.path.join(self.settings_dir, "config.json")
        self.history_path = os.path.join(self.settings_dir, "history.json")
        
        self.config = self._load_config()
        self.history = self._load_history()

    def _load_config(self) -> Dict:
        from src.services.inference_service import resolve_model_variant

        default_config = {
            "model_variant": resolve_model_variant(None),
            "device": "cpu",
            "confidence_threshold": 0.5,
            "patch_size": 512,
            "overlap_ratio": 0.2,
            "use_tta": False,
            "use_clahe": True,
            "clahe_clip_limit": 2.0,
            "overlay_alpha": 0.4,
            "overlay_color": [255, 0, 0],
            "box_color": [0, 255, 0],
            "box_thickness": 2,
            "contour_color": [0, 0, 255],
            "contour_thickness": 2,
            "theme_mode": "light",
            "default_reports_dir": self.reports_dir
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    user_config = json.load(f)
                    # Merge user config with defaults to ensure all keys exist
                    default_config.update(user_config)
            except Exception as e:
                print(f"Error loading config.json, resetting to defaults: {e}")
                
        default_config["model_variant"] = resolve_model_variant(default_config.get("model_variant"))
        return default_config

    def save_config(self, new_config: Dict = None) -> bool:
        if new_config:
            self.config.update(new_config)
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config.json: {e}")
            return False

    def _load_history(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history.json, resetting: {e}")
        return []

    def save_history(self) -> bool:
        try:
            with open(self.history_path, "w") as f:
                json.dump(self.history, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving history.json: {e}")
            return False

    def add_record(self, image_path: str, crack_detected: bool, 
                   confidence: float, crack_count: int, model_used: str,
                   vis_image_path: str = None, overlay_image_path: str = None, mask_image_path: str = None,
                   elapsed_time: float = 0.0, bounding_boxes: List[Dict[str, Any]] = None) -> Dict:
        """Adds an inspection record and saves history."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "image_path": os.path.abspath(image_path),
            "image_name": os.path.basename(image_path),
            "timestamp": datetime.now().isoformat(),
            "crack_detected": crack_detected,
            "confidence": float(confidence),
            "crack_count": int(crack_count),
            "model_used": model_used,
            "vis_image_path": vis_image_path,
            "overlay_image_path": overlay_image_path,
            "mask_image_path": mask_image_path,
            "elapsed_time": float(elapsed_time),
            "report_path": "",
            "bounding_boxes": bounding_boxes or []
        }
        self.history.insert(0, record) # Put latest at the beginning
        self.save_history()
        return record

    def delete_record(self, record_id: str) -> bool:
        """Deletes a record and its associated result images from assets."""
        found_idx = -1
        for idx, rec in enumerate(self.history):
            if rec["id"] == record_id:
                found_idx = idx
                break
                
        if found_idx != -1:
            rec = self.history.pop(found_idx)
            # Remove associated result files if they exist
            for key in ["vis_image_path", "overlay_image_path", "mask_image_path"]:
                path = rec.get(key)
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Failed to delete result asset {path}: {e}")
            self.save_history()
            return True
        return False

    def clear_history(self) -> bool:
        """Clears all records and associated result files."""
        for rec in list(self.history):
            self.delete_record(rec["id"])
        self.history = []
        
        # Clean up any remaining cached files in results_dir
        if os.path.exists(self.results_dir):
            for file in os.listdir(self.results_dir):
                file_path = os.path.join(self.results_dir, file)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Failed to remove cached file {file_path}: {e}")

        return self.save_history()

    def update_report_path(self, record_id: str, report_path: str) -> bool:
        """Updates the report path for a specific inspection record."""
        for rec in self.history:
            if rec["id"] == record_id:
                rec["report_path"] = os.path.abspath(report_path)
                self.save_history()
                return True
        return False
