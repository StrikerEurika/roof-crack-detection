from PySide6.QtCore import Slot

from qfluentwidgets import FluentWindow, NavigationItemPosition
from qfluentwidgets import FluentIcon as FIF

from src.viewmodel import HomeViewModel, InspectionViewModel, BatchViewModel, SettingsViewModel
from src.view import HomeView, InspectionView, BatchView, SettingsView

class MainWindowView(FluentWindow):
    """The main desktop application window managing navigation and view switches via QFluentWidgets and MVVM."""

    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        
        # Cache loaded pipelines in mainwindow to share weights/sessions across tabs
        self.model_cache = {}

        self.setWindowTitle("Roof Surface Crack Inspection Suite")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # 1. Setup Central Views and ViewModels
        self.setup_views()

        # 2. Setup Navigation Sidebar
        self.setup_navigation()

        # 3. Connect signals
        self.connect_signals()

        # Select Home Tab by default
        self.switchTo(self.page_home)

    def setup_views(self):
        # Initialize the ViewModels
        self.home_vm = HomeViewModel(self.hm)
        self.inspection_vm = InspectionViewModel(self.hm, self.model_cache)
        self.batch_vm = BatchViewModel(self.hm, self.model_cache)
        self.settings_vm = SettingsViewModel(self.hm)

        # Initialize the views
        self.page_home = HomeView(self.home_vm, self)
        self.page_single = InspectionView(self.inspection_vm, self)
        self.page_batch = BatchView(self.batch_vm, self)
        self.page_settings = SettingsView(self.settings_vm, self)

        # Set object names (crucial for QFluentWidgets navigation routing)
        self.page_home.setObjectName("homeView")
        self.page_single.setObjectName("inspectionView")
        self.page_batch.setObjectName("batchView")
        self.page_settings.setObjectName("settingsView")

    def setup_navigation(self):
        # Add sub-interfaces to the navigation sidebar
        self.addSubInterface(self.page_home, FIF.HOME, "Dashboard / Home")
        self.addSubInterface(self.page_single, FIF.ZOOM, "Single Inspection")
        self.addSubInterface(self.page_batch, FIF.FOLDER, "Batch Processing")
        
        # Add Settings at the bottom of the sidebar
        self.addSubInterface(
            self.page_settings, 
            FIF.SETTING, 
            "System Settings", 
            NavigationItemPosition.BOTTOM
        )

    def connect_signals(self):
        # Navigation signals from Home quick actions
        self.page_home.navigate_to_single.connect(lambda: self.switchTo(self.page_single))
        self.page_home.navigate_to_batch.connect(lambda: self.switchTo(self.page_batch))
        self.page_home.navigate_to_settings.connect(lambda: self.switchTo(self.page_settings))
        
        # Inspection list details routing
        self.page_home.view_record_signal.connect(self.on_view_historical_record)

        # Refresh dashboard when history changes
        self.page_single.inspection_completed.connect(self.page_home.refresh_dashboard)
        self.page_batch.batch_completed.connect(self.page_home.refresh_dashboard)
        self.page_settings.settings_saved.connect(self.on_settings_saved)

        # Auto-refresh when current tab switches back to dashboard page
        self.stackedWidget.currentChanged.connect(self.on_current_changed)

    def on_current_changed(self, index):
        widget = self.stackedWidget.widget(index)
        if widget == self.page_home:
            self.page_home.refresh_dashboard()

    @Slot(dict)
    def on_view_historical_record(self, record):
        """Triggered from history list to load results and view details."""
        self.switchTo(self.page_single)
        self.page_single.load_historical_record(record)

    @Slot()
    def on_settings_saved(self):
        """Updates configurations across all tabs when settings are saved."""
        self.page_home.refresh_dashboard()
        
        # Force default settings reload on the views
        self.page_single.load_settings_defaults()
        self.page_batch.load_settings_defaults()
        
        # If default settings changed, clear model cache to force reload on next runs
        self.model_cache.clear()
