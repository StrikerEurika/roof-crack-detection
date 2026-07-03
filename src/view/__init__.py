"""
UI Views Submodule
------------------
Individual page views/panels representing distinct tabs within the application shell.
"""

from .home_view import HomeView
from .inspection_view import InspectionView
from .batch_view import BatchView
from .settings_view import SettingsView

__all__ = [
    "HomeView",
    "InspectionView",
    "BatchView",
    "SettingsView",
]
