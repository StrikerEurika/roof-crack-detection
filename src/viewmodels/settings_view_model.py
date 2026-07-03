from PySide6.QtCore import QObject, Signal, Slot
from src.controllers.history_manager import HistoryManager

class SettingsViewModel(QObject):
    """ViewModel for handling application settings and database maintenance."""
    
    settings_loaded = Signal(dict)
    settings_saved = Signal(dict)
    history_cleared = Signal()
    error_occurred = Signal(str)

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.hm = history_manager

    def load_settings(self):
        """Loads default and custom settings from HistoryManager."""
        try:
            config = self.hm.config
            self.settings_loaded.emit(config)
        except Exception as e:
            self.error_occurred.emit(f"Failed to load settings: {str(e)}")

    def save_settings(self, new_config: dict):
        """Saves settings via HistoryManager."""
        try:
            success = self.hm.save_config(new_config)
            if success:
                self.settings_saved.emit(self.hm.config)
            else:
                self.error_occurred.emit("Failed to save settings file to disk.")
        except Exception as e:
            self.error_occurred.emit(f"Error saving settings: {str(e)}")

    def clear_history(self) -> bool:
        """Clears all records and associated visualizations."""
        try:
            success = self.hm.clear_history()
            if success:
                self.history_cleared.emit()
                return True
            else:
                self.error_occurred.emit("Failed to clear history files.")
                return False
        except Exception as e:
            self.error_occurred.emit(f"Error clearing history: {str(e)}")
            return False

    def get_default_reports_dir(self) -> str:
        """Returns the current reports directory path."""
        return self.hm.config.get("default_reports_dir", self.hm.reports_dir)
