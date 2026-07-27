import os
import importlib
from PySide6.QtCore import Slot, QFileSystemWatcher
from PySide6.QtGui import QIcon, QPixmap

from qfluentwidgets import FluentWindow, NavigationItemPosition
from qfluentwidgets import FluentIcon as FIF

from src.model import HistoryManager
from src.services import InferenceService
from src.view_model import HomeViewModel, InspectionViewModel, BatchViewModel, SettingsViewModel, HistoryViewModel
from src.view import HomeView, InspectionView, BatchView, SettingsView, HistoryView

class MainWindow(FluentWindow):
    """The main desktop application window managing navigation and view switches via QFluentWidgets and MVVM."""

    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.context = app_context
        self.hm = self._resolve_history_manager(app_context)
        self.inference_service = self._resolve_inference_service(app_context)

        self.setWindowTitle("Roof Surface Crack Inspection Suite")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons", "icons-05.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(QPixmap(icon_path)))

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

    def _resolve_history_manager(self, app_context) -> HistoryManager:
        if hasattr(app_context, "history_manager"):
            return app_context.history_manager
        return app_context

    def _resolve_inference_service(self, app_context) -> InferenceService:
        if hasattr(app_context, "inference_service"):
            return app_context.inference_service
        return InferenceService()

    def setup_views(self):
        # Initialize the ViewModels
        self.home_view_model = HomeViewModel(self.hm)
        self.inspection_view_model = InspectionViewModel(self.hm, self.inference_service)
        self.batch_view_model = BatchViewModel(self.hm, self.inference_service)
        self.history_view_model = HistoryViewModel(self.hm)
        self.settings_view_model = SettingsViewModel(self.hm)

        # Initialize the views
        self.page_home = HomeView(self.home_view_model, self)
        self.page_single = InspectionView(self.inspection_view_model, self)
        self.page_batch = BatchView(self.batch_view_model, self)
        self.page_history = HistoryView(self.history_view_model, self)
        self.page_settings = SettingsView(self.settings_view_model, self)

        # Set object names (crucial for QFluentWidgets navigation routing)
        self.page_home.setObjectName("homeView")
        self.page_single.setObjectName("inspectionView")
        self.page_batch.setObjectName("batchView")
        self.page_history.setObjectName("historyView")
        self.page_settings.setObjectName("settingsView")

    def setup_navigation(self):
        # Add sub-interfaces to the navigation sidebar
        self.addSubInterface(self.page_home, FIF.HOME, "Dashboard")
        self.addSubInterface(self.page_single, FIF.ZOOM, "Single Inspection")
        self.addSubInterface(self.page_batch, FIF.FOLDER, "Batch Processing")
        self.addSubInterface(self.page_history, FIF.HISTORY, "History")
        
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

        # Refresh dashboard and history when history changes
        self.page_single.inspection_completed.connect(self.on_new_inspection_completed)
        self.page_batch.batch_completed.connect(self.on_new_inspection_completed)
        self.page_history.history_changed.connect(self.page_home.refresh_dashboard)
        self.page_settings.settings_saved.connect(self.on_settings_saved)
        self.settings_view_model.history_cleared.connect(self.on_history_cleared)

        # Auto-refresh when current tab switches back to dashboard or history page
        self.stackedWidget.currentChanged.connect(self.on_current_changed)

    def on_new_inspection_completed(self):
        self.page_home.refresh_dashboard()
        self.page_history.refresh_list()

    def on_current_changed(self, index):
        widget = self.stackedWidget.widget(index)
        if widget == self.page_home:
            self.page_home.refresh_dashboard()
        elif widget == self.page_history:
            self.page_history.refresh_list()

    @Slot(dict)
    def on_view_historical_record(self, record):
        """Triggered from history list to load results and view details."""
        self.switchTo(self.page_history)
        self.page_history.show_detail_inspection(record)

    @Slot()
    def on_history_cleared(self):
        """Resets loaded inspection views and clears memory caches when history is cleared."""
        self.inspection_view_model.clear_inspection()
        self.page_history.refresh_list()
        self.page_home.thumbnail_cache.clear()
        self.page_home.refresh_dashboard()
        self.inference_service.clear_cache()


    @Slot()
    def on_settings_saved(self):
        """Updates configurations across all tabs when settings are saved."""
        self.page_home.refresh_dashboard()
        
        # Force default settings reload on the views
        self.page_single.load_settings_defaults()
        self.page_batch.load_settings_defaults()
        
        self.inference_service.clear_cache()

    def setup_hot_reload(self):
        """Sets up the filesystem watcher for all View files."""      
        import sys
        if getattr(sys, "frozen", False):
            return
        self.watcher = QFileSystemWatcher(self)
        view_dir = os.path.dirname(os.path.abspath(__file__))
        views_to_watch = [
            "home_view.py", 
            "inspection_view.py", 
            "batch_view.py", 
            "history_view.py",
            "settings_view.py",
            ".",
        ]
        for view_file in views_to_watch:
            path = os.path.join(view_dir, view_file)
            if os.path.exists(path):
                self.watcher.addPath(path)
        self.watcher.fileChanged.connect(self.hot_reload_view)


    def hot_reload_view(self, file_path):
        """Dynamic in-place swap of modified views, preserving ViewModel state."""
        filename = os.path.basename(file_path)
        print(f"Hot-reloading view because of modification in: {filename}")
        
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
                new_page = src.view.home_view.HomeView(self.home_view_model, self)
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
                new_page = src.view.inspection_view.InspectionView(self.inspection_view_model, self)
                new_page.setObjectName("inspectionView")
                self.stackedWidget.addWidget(new_page)
                self.page_single = new_page
                
                # Reconnect signals
                self.page_single.inspection_completed.connect(self.on_new_inspection_completed)
                
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
                new_page = src.view.batch_view.BatchView(self.batch_view_model, self)
                new_page.setObjectName("batchView")
                self.stackedWidget.addWidget(new_page)
                self.page_batch = new_page
                
                # Reconnect signals
                self.page_batch.batch_completed.connect(self.on_new_inspection_completed)
                
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

            elif filename == "history_view.py":
                import src.view.history_view
                importlib.reload(src.view.history_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_history)
                
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                self.stackedWidget.removeWidget(self.page_history)
                self.page_history.deleteLater()
                new_page = src.view.history_view.HistoryView(self.history_view_model, self)
                new_page.setObjectName("historyView")
                self.stackedWidget.addWidget(new_page)
                self.page_history = new_page
                
                # Reconnect signals
                self.page_history.history_changed.connect(self.page_home.refresh_dashboard)
                
                # Update QFluentWidgets sidebar navigation onClick callback
                nav_item = self.navigationInterface.widget("historyView")
                if nav_item:
                    nav_item.clicked.disconnect()
                    nav_item.clicked.connect(self.navigationInterface.panel._onWidgetClicked)
                    nav_item.clicked.connect(lambda: self.switchTo(self.page_history))
                
                self.stackedWidget.blockSignals(False)
                self.stackedWidget.view.blockSignals(False)
                
                if is_current:
                    self.switchTo(self.page_history)
                    self.page_history.refresh_list()
                print("✨ HistoryView reloaded in-place successfully!")

            elif filename == "settings_view.py":
                import src.view.settings_view
                importlib.reload(src.view.settings_view)
                
                is_current = (self.stackedWidget.currentWidget() == self.page_settings)
                
                self.stackedWidget.blockSignals(True)
                self.stackedWidget.view.blockSignals(True)
                
                self.stackedWidget.removeWidget(self.page_settings)
                self.page_settings.deleteLater()
                new_page = src.view.settings_view.SettingsView(self.settings_view_model, self)
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
                print("SettingsView reloaded in-place successfully!")

        except Exception as e:
            print(f"Failed to hot-reload view {filename}: {e}")
            
        # Re-add watched path (some editors recreate files on save)
        self.watcher.addPath(file_path)

