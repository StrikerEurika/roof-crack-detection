import os
import importlib
from PySide6.QtCore import Slot, QFileSystemWatcher

from qfluentwidgets import FluentWindow, NavigationItemPosition
from qfluentwidgets import FluentIcon as FIF

from src.view_model import HomeViewModel, InspectionViewModel, BatchViewModel, SettingsViewModel
from src.view import HomeView, InspectionView, BatchView, SettingsView

class MainWindow(FluentWindow):
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

        # 4. Setup Hot-Reload Watcher for Views
        self.setup_hot_reload()

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

    def setup_hot_reload(self):
        """Sets up the filesystem watcher for all View files."""
        self.watcher = QFileSystemWatcher(self)
        view_dir = os.path.dirname(os.path.abspath(__file__))
        views_to_watch = ["home_view.py", "inspection_view.py", "batch_view.py", "settings_view.py"]
        for view_file in views_to_watch:
            path = os.path.join(view_dir, view_file)
            if os.path.exists(path):
                self.watcher.addPath(path)
        self.watcher.fileChanged.connect(self.hot_reload_view)

    def hot_reload_view(self, file_path):
        """Dynamic in-place swap of modified views, preserving ViewModel state."""
        filename = os.path.basename(file_path)
        print(f"🔥 Hot-reloading view because of modification in: {filename}")
        
        try:
            if filename == "home_view.py":
                # Reload module
                import src.view.home_view
                importlib.reload(src.view.home_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_home)
                
                # Block signals to prevent intermediate routing errors
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                # Replace in StackedWidget using addWidget to sync PopUpAniInfo correctly
                self.stackedWidget.removeWidget(self.page_home)
                self.page_home.deleteLater()
                new_page = src.view.home_view.HomeView(self.home_vm, self)
                new_page.setObjectName("homeView")
                self.stackedWidget.addWidget(new_page)
                self.page_home = new_page
                
                # Reconnect home signals
                self.page_home.navigate_to_single.connect(lambda: self.switchTo(self.page_single))
                self.page_home.navigate_to_batch.connect(lambda: self.switchTo(self.page_batch))
                self.page_home.navigate_to_settings.connect(lambda: self.switchTo(self.page_settings))
                self.page_home.view_record_signal.connect(self.on_view_historical_record)
                
                # Update QFluentWidgets sidebar navigation onClick callback
                nav_item = self.navigationInterface.widget("homeView")
                if nav_item:
                    nav_item.clicked.disconnect()
                    nav_item.clicked.connect(self.navigationInterface.panel._onWidgetClicked)
                    nav_item.clicked.connect(lambda: self.switchTo(self.page_home))
                
                # Unblock signals
                self.stackedWidget.blockSignals(False)
                self.stackedWidget.view.blockSignals(False)
                
                if is_current:
                    self.switchTo(self.page_home)
                    self.page_home.refresh_dashboard()
                print("✨ HomeView reloaded in-place successfully!")

            elif filename == "inspection_view.py":
                import src.view.inspection_view
                importlib.reload(src.view.inspection_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_single)
                
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                self.stackedWidget.removeWidget(self.page_single)
                self.page_single.deleteLater()
                new_page = src.view.inspection_view.InspectionView(self.inspection_vm, self)
                new_page.setObjectName("inspectionView")
                self.stackedWidget.addWidget(new_page)
                self.page_single = new_page
                
                # Reconnect signals
                self.page_single.inspection_completed.connect(self.page_home.refresh_dashboard)
                
                # Update QFluentWidgets sidebar navigation onClick callback
                nav_item = self.navigationInterface.widget("inspectionView")
                if nav_item:
                    nav_item.clicked.disconnect()
                    nav_item.clicked.connect(self.navigationInterface.panel._onWidgetClicked)
                    nav_item.clicked.connect(lambda: self.switchTo(self.page_single))
                
                self.stackedWidget.blockSignals(False)
                self.stackedWidget.view.blockSignals(False)
                
                if is_current:
                    self.switchTo(self.page_single)
                print("✨ InspectionView reloaded in-place successfully!")

            elif filename == "batch_view.py":
                import src.view.batch_view
                importlib.reload(src.view.batch_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_batch)
                
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                self.stackedWidget.removeWidget(self.page_batch)
                self.page_batch.deleteLater()
                new_page = src.view.batch_view.BatchView(self.batch_vm, self)
                new_page.setObjectName("batchView")
                self.stackedWidget.addWidget(new_page)
                self.page_batch = new_page
                
                # Reconnect signals
                self.page_batch.batch_completed.connect(self.page_home.refresh_dashboard)
                
                # Update QFluentWidgets sidebar navigation onClick callback
                nav_item = self.navigationInterface.widget("batchView")
                if nav_item:
                    nav_item.clicked.disconnect()
                    nav_item.clicked.connect(self.navigationInterface.panel._onWidgetClicked)
                    nav_item.clicked.connect(lambda: self.switchTo(self.page_batch))
                
                self.stackedWidget.blockSignals(False)
                self.stackedWidget.view.blockSignals(False)
                
                if is_current:
                    self.switchTo(self.page_batch)
                print("✨ BatchView reloaded in-place successfully!")

            elif filename == "settings_view.py":
                import src.view.settings_view
                importlib.reload(src.view.settings_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_settings)
                
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                self.stackedWidget.removeWidget(self.page_settings)
                self.page_settings.deleteLater()
                new_page = src.view.settings_view.SettingsView(self.settings_vm, self)
                new_page.setObjectName("settingsView")
                self.stackedWidget.addWidget(new_page)
                self.page_settings = new_page
                
                # Reconnect signals
                self.page_settings.settings_saved.connect(self.on_settings_saved)
                
                # Update QFluentWidgets sidebar navigation onClick callback
                nav_item = self.navigationInterface.widget("settingsView")
                if nav_item:
                    nav_item.clicked.disconnect()
                    nav_item.clicked.connect(self.navigationInterface.panel._onWidgetClicked)
                    nav_item.clicked.connect(lambda: self.switchTo(self.page_settings))
                
                self.stackedWidget.blockSignals(False)
                self.stackedWidget.view.blockSignals(False)
                
                if is_current:
                    self.switchTo(self.page_settings)
                print("✨ SettingsView reloaded in-place successfully!")

        except Exception as e:
            print(f"❌ Failed to hot-reload view {filename}: {e}")
            
        # Re-add watched path (some editors recreate files on save)
        self.watcher.addPath(file_path)
