from datetime import datetime
from dataclasses import dataclass


@dataclass
class DashboardKPIs:
    total_inspected: int = 0
    cracks_detected: int = 0
    crack_rate: float = 0.0
    avg_speed: float = 0.0
    active_model: str = "N/A"
    active_model_abbr: str = "N/A"


class DashboardService:
    def __init__(self, history_manager):
        self.hm = history_manager

    def compute_kpis(self) -> DashboardKPIs:
        history = self.hm.history
        config = self.hm.config

        total_inspected = len(history)
        cracks_detected = sum(1 for rec in history if rec.get("crack_detected", False))
        crack_rate = (cracks_detected / total_inspected * 100) if total_inspected > 0 else 0.0

        avg_speed = (
            sum(rec.get("elapsed_time", 0.0) for rec in history) / total_inspected
            if total_inspected > 0
            else 0.0
        )

        active_model = config.get("model_variant", "Seg_UNET_CFD_actual_v2")
        active_model_abbr = active_model.split("_")[0]

        return DashboardKPIs(
            total_inspected=total_inspected,
            cracks_detected=cracks_detected,
            crack_rate=crack_rate,
            avg_speed=avg_speed,
            active_model=active_model,
            active_model_abbr=active_model_abbr,
        )

    def get_recent_records(self, limit: int = 10) -> list:
        return self.hm.history[:limit]

    @staticmethod
    def format_timestamp(timestamp_str: str) -> str:
        if not timestamp_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "N/A"
