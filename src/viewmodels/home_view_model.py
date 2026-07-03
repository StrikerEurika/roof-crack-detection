from PySide6.QtCore import QObject, Signal
from src.controllers.history_manager import HistoryManager

class HomeViewModel(QObject):
    """ViewModel for processing landing dashboard KPIs, trend charts, and recent records."""
    
    dashboard_refreshed = Signal(dict)

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.hm = history_manager

    def refresh_dashboard(self):
        """Loads and processes landing dashboard statistics."""
        history = self.hm.history
        config = self.hm.config
        
        total_inspected = len(history)
        cracks_detected = sum(1 for rec in history if rec.get("crack_detected", False))
        crack_rate = (cracks_detected / total_inspected * 100) if total_inspected > 0 else 0.0
        avg_speed = sum(rec.get("elapsed_time", 0.0) for rec in history) / total_inspected if total_inspected > 0 else 0.0
        active_model = config.get("model_variant", "Seg_UNET_CFD_actual_v2")
        
        # Take the top 10 recent records
        recent_records = history[:10]
        
        stats = {
            "total_inspected": total_inspected,
            "cracks_detected": cracks_detected,
            "crack_rate": crack_rate,
            "avg_speed": avg_speed,
            "active_model": active_model,
            "recent_records": recent_records,
            "full_history": history
        }
        
        self.dashboard_refreshed.emit(stats)
        
    def delete_record(self, record_id: str):
        """Deletes a record and updates dashboard."""
        self.hm.delete_record(record_id)
        self.refresh_dashboard()
