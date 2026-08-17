"""
UI Views Submodule
------------------
Individual page views/panels representing distinct tabs within the application shell.
"""

from .home_view import HomeView
from .inspection_view import InspectionView
from .batch_view import BatchView
from .settings_view import SettingsView
from .history_view import HistoryView
from .documentation_view import DocumentationView

__all__ = [
    "HomeView",
    "InspectionView",
    "BatchView",
    "SettingsView",
    "HistoryView",
    "DocumentationView",
]

