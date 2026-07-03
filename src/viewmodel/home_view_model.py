from PySide6.QtCore import QObject, Signal
from src.model import HistoryManager
from src.services import DashboardService

class HomeViewModel(QObject):
    """ViewModel for processing landing dashboard KPIs, trend charts, and recent records."""
    
    dashboard_refreshed = Signal(dict)

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.dashboard_service = DashboardService(history_manager)

    def refresh_dashboard(self):
        """Loads and processes landing dashboard statistics."""
        kpis = self.dashboard_service.compute_kpis()
        recent_records = self.dashboard_service.get_recent_records(limit=10)
        
        stats = {
            "total_inspected": kpis.total_inspected,
            "cracks_detected": kpis.cracks_detected,
            "crack_rate": kpis.crack_rate,
            "avg_speed": kpis.avg_speed,
            "active_model": kpis.active_model,
            "recent_records": recent_records,
            "full_history": self.hm.history
        }
        
        self.dashboard_refreshed.emit(stats)
        
    def delete_record(self, record_id: str):
        """Deletes a record and updates dashboard."""
        self.hm.delete_record(record_id)
        self.refresh_dashboard()
