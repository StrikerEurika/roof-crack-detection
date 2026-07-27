# src/view_model/history_view_model.py

import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot
from src.model import HistoryManager
from src.reports.pdf_generator import PDFReportGenerator

class HistoryViewModel(QObject):
    """ViewModel for managing inspection history listing, filtering, searching, and detail inspection."""

    history_refreshed = Signal(list, dict)  # (filtered_records, stats_dict)
    record_selected = Signal(dict)          # Emitted when a record is chosen for Detail Inspection
    back_to_list_requested = Signal()        # Emitted to return to the history list page
    record_deleted = Signal(str)            # Emitted with record ID when deleted
    history_cleared = Signal()             # Emitted when all history is cleared
    report_exported = Signal(str)           # Emitted with output PDF path
    report_export_failed = Signal(str)      # Emitted with error message

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.current_selected_record = None

    def get_history(self, search_query: str = "", filter_status: str = "All", sort_by: str = "Newest First") -> list[dict]:
        """Returns filtered and sorted history records."""
        records = list(self.hm.history)

        # 1. Search Query Filter
        if search_query:
            q = search_query.strip().lower()
            records = [
                r for r in records
                if q in r.get("image_name", "").lower()
                or q in r.get("image_path", "").lower()
                or q in r.get("model_used", "").lower()
            ]

        # 2. Status Filter
        if filter_status in ("Cracks Detected", "Cracks Only"):
            records = [r for r in records if r.get("crack_detected", False)]
        elif filter_status in ("No Cracks", "Clean Only"):
            records = [r for r in records if not r.get("crack_detected", False)]

        # 3. Sorting
        if sort_by == "Oldest First":
            records.sort(key=lambda r: r.get("timestamp", ""))
        elif sort_by == "Highest Confidence":
            records.sort(key=lambda r: r.get("confidence", 0.0), reverse=True)
        elif sort_by == "Most Cracks":
            records.sort(key=lambda r: r.get("crack_count", 0), reverse=True)
        else:  # Default: Newest First
            records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

        return records

    def compute_history_stats(self) -> dict:
        """Computes summary statistics for the history database."""
        all_records = self.hm.history
        total = len(all_records)
        cracks_count = sum(1 for r in all_records if r.get("crack_detected", False))
        clean_count = total - cracks_count
        avg_speed = (sum(r.get("elapsed_time", 0.0) for r in all_records) / total) if total > 0 else 0.0

        return {
            "total_records": total,
            "cracks_count": cracks_count,
            "clean_count": clean_count,
            "crack_rate": (cracks_count / total * 100.0) if total > 0 else 0.0,
            "avg_speed": avg_speed
        }

    def refresh_history(self, search_query: str = "", filter_status: str = "All", sort_by: str = "Newest First"):
        """Emits refreshed history list and statistics."""
        filtered_records = self.get_history(search_query, filter_status, sort_by)
        stats = self.compute_history_stats()
        self.history_refreshed.emit(filtered_records, stats)

    def select_record(self, record: dict):
        """Sets active record for Detail Inspection and emits selection signal."""
        self.current_selected_record = record
        self.record_selected.emit(record)

    def request_back_to_list(self):
        """Emits signal to return from detail inspection to list view."""
        self.current_selected_record = None
        self.back_to_list_requested.emit()

    def delete_record(self, record_id: str) -> bool:
        """Deletes a record by ID and refreshes history state."""
        success = self.hm.delete_record(record_id)
        if success:
            if self.current_selected_record and self.current_selected_record.get("id") == record_id:
                self.current_selected_record = None
                self.back_to_list_requested.emit()
            self.record_deleted.emit(record_id)
            self.refresh_history()
        return success

    def clear_history(self) -> bool:
        """Clears all history records."""
        success = self.hm.clear_history()
        if success:
            self.current_selected_record = None
            self.history_cleared.emit()
            self.refresh_history()
        return success

    def export_report(self, record: dict, output_pdf_path: str):
        """Generates PDF report for a given history record."""
        if not record:
            self.report_export_failed.emit("No inspection record provided.")
            return

        try:
            success = PDFReportGenerator.generate_report(record, output_pdf_path)
            if success:
                self.hm.update_report_path(record["id"], output_pdf_path)
                self.report_exported.emit(output_pdf_path)
            else:
                self.report_export_failed.emit("Failed to generate PDF report.")
        except Exception as e:
            self.report_export_failed.emit(f"PDF export error: {str(e)}")

    def get_default_reports_dir(self) -> str:
        return self.hm.config.get("default_reports_dir", self.hm.reports_dir)
