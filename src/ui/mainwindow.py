import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtCore import Qt, Slot

from .home_view import HomeView
from .inspection_view import InspectionView
from .batch_view import BatchView
from .settings_view import SettingsView

class MainWindow(QMainWindow):
    """The main desktop application window managing navigation and view switches."""

    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        
        # Cache loaded pipelines in mainwindow to share weights/sessions across tabs
        self.model_cache = {}

        self.setWindowTitle("Roof Surface Crack Inspection Suite")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # Base Application Stylesheet (Win32 Retro Classic Theme)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #d4d0c8;
            }
            QWidget#centralWidget {
                background-color: #d4d0c8;
            }
            QFrame#sidebarPanel {
                background-color: #d4d0c8;
                border-right: 2px solid #808080;
            }
            QLabel#sidebarTitle {
                color: #ffffff;
                background-color: #000080;
                font-family: 'Tahoma', 'MS Sans Serif', Arial;
                font-size: 12px;
                font-weight: bold;
                padding: 6px;
                border-top: 1.5px solid #ffffff;
                border-left: 1.5px solid #ffffff;
                border-right: 1.5px solid #808080;
                border-bottom: 1.5px solid #808080;
                margin-bottom: 15px;
            }
            QPushButton.navBtn {
                background-color: #d4d0c8;
                color: #000000;
                border-top: 1.5px solid #ffffff;
                border-left: 1.5px solid #ffffff;
                border-right: 1.5px solid #808080;
                border-bottom: 1.5px solid #808080;
                border-radius: 0px;
                padding: 8px 12px;
                text-align: left;
                font-family: 'Tahoma', 'MS Sans Serif', Arial;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton.navBtn:hover {
                background-color: #e0ded9;
            }
            QPushButton.navBtn:checked {
                background-color: #d4d0c8;
                color: #000000;
                border-top: 1.5px solid #808080;
                border-left: 1.5px solid #808080;
                border-right: 1.5px solid #ffffff;
                border-bottom: 1.5px solid #ffffff;
                padding-top: 9px;
                padding-left: 13px;
                padding-bottom: 7px;
                padding-right: 11px;
            }
            QLabel#sidebarFooter {
                color: #404040;
                font-family: 'Tahoma', Arial;
                font-size: 10px;
                font-weight: bold;
            }
        """)

        # Central Widget & Main Layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Setup Left Sidebar Navigation Panel
        self.setup_sidebar()

        # 2. Setup Central Views Stack
        self.setup_views()

        # Connect page switches and signals
        self.connect_signals()

        # Select Home Tab by default
        self.btn_nav_home.setChecked(True)
        self.on_nav_changed(0)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebarPanel")
        self.sidebar.setFixedWidth(240)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 15)
        sidebar_layout.setSpacing(10)

        # Logo / Branding Header
        logo = QLabel("🏢 ROOF ANALYTICS")
        logo.setObjectName("sidebarTitle")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(15)

        # Navigation Buttons Group
        self.btn_nav_home = QPushButton("🏠   Dashboard / Home")
        self.btn_nav_home.setProperty("class", "navBtn")
        self.btn_nav_home.setCheckable(True)
        self.btn_nav_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_home.clicked.connect(lambda: self.on_nav_changed(0))
        
        self.btn_nav_single = QPushButton("🔍   Single Inspection")
        self.btn_nav_single.setProperty("class", "navBtn")
        self.btn_nav_single.setCheckable(True)
        self.btn_nav_single.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_single.clicked.connect(lambda: self.on_nav_changed(1))

        self.btn_nav_batch = QPushButton("📁   Batch Processing")
        self.btn_nav_batch.setProperty("class", "navBtn")
        self.btn_nav_batch.setCheckable(True)
        self.btn_nav_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_batch.clicked.connect(lambda: self.on_nav_changed(2))

        self.btn_nav_settings = QPushButton("⚙️   System Settings")
        self.btn_nav_settings.setProperty("class", "navBtn")
        self.btn_nav_settings.setCheckable(True)
        self.btn_nav_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_settings.clicked.connect(lambda: self.on_nav_changed(3))

        # Add Nav items to layout
        sidebar_layout.addWidget(self.btn_nav_home)
        sidebar_layout.addWidget(self.btn_nav_single)
        sidebar_layout.addWidget(self.btn_nav_batch)
        sidebar_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addStretch()

        # Check acceleration framework dynamically
        backend_info = "ONNX Runtime"
        try:
            import torch
            if torch.cuda.is_available():
                backend_info = "Torch CUDA"
            else:
                backend_info = "Torch CPU"
        except ImportError:
            try:
                import onnxruntime as ort
                if any("CUDA" in p for p in ort.get_available_providers()):
                    backend_info = "ORT CUDA"
                else:
                    backend_info = "ORT CPU"
            except ImportError:
                backend_info = "CPU"
                
        # Footer details
        footer = QLabel(f"V1.0.0 ({backend_info})\n© 2026 Material AI Labs")
        footer.setObjectName("sidebarFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer)

        self.main_layout.addWidget(self.sidebar)

    def setup_views(self):
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # Page 0: Home view
        self.page_home = HomeView(self.hm)
        self.stacked_widget.addWidget(self.page_home)

        # Page 1: Single image inspection
        self.page_single = InspectionView(self.hm, self.model_cache)
        self.stacked_widget.addWidget(self.page_single)

        # Page 2: Batch processing view
        self.page_batch = BatchView(self.hm, self.model_cache)
        self.stacked_widget.addWidget(self.page_batch)

        # Page 3: Settings panel
        self.page_settings = SettingsView(self.hm)
        self.stacked_widget.addWidget(self.page_settings)

    def connect_signals(self):
        # Navigation signals from Home quick actions
        self.page_home.navigate_to_single.connect(lambda: self.switch_to_page(1))
        self.page_home.navigate_to_batch.connect(lambda: self.switch_to_page(2))
        self.page_home.navigate_to_settings.connect(lambda: self.switch_to_page(3))
        
        # Inspection list details routing: double clicking details navigates to single inspection page and loads historical details
        self.page_home.view_record_signal.connect(self.on_view_historical_record)

        # Refresh dashboard when history changes
        self.page_single.inspection_completed.connect(self.page_home.refresh_dashboard)
        self.page_batch.batch_completed.connect(self.page_home.refresh_dashboard)
        self.page_settings.settings_saved.connect(self.on_settings_saved)

    def switch_to_page(self, index):
        """Helper to switch checked states and show corresponding index."""
        # Uncheck all
        self.btn_nav_home.setChecked(False)
        self.btn_nav_single.setChecked(False)
        self.btn_nav_batch.setChecked(False)
        self.btn_nav_settings.setChecked(False)

        if index == 0:
            self.btn_nav_home.setChecked(True)
        elif index == 1:
            self.btn_nav_single.setChecked(True)
        elif index == 2:
            self.btn_nav_batch.setChecked(True)
        elif index == 3:
            self.btn_nav_settings.setChecked(True)

        self.stacked_widget.setCurrentIndex(index)

    @Slot(int)
    def on_nav_changed(self, index):
        self.switch_to_page(index)
        # Specific updates on page entering
        if index == 0:
            self.page_home.refresh_dashboard()

    @Slot(dict)
    def on_view_historical_record(self, record):
        """Triggered from history list to load results and view details."""
        self.switch_to_page(1)
        self.page_single.load_historical_record(record)

    @Slot()
    def on_settings_saved(self):
        """Updates configurations across all tabs when settings are saved."""
        self.page_home.refresh_dashboard()
        
        # Sync values in single/batch settings
        config = self.hm.config
        
        # Single Inspection defaults sync
        self.page_single.combo_model.setCurrentText(config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        self.page_single.combo_device.setCurrentText(config.get("device", "cuda"))
        self.page_single.slider_thresh.setValue(int(config.get("confidence_threshold", 0.5) * 100))
        self.page_single.slider_overlap.setValue(int(config.get("overlap_ratio", 0.2) * 100))
        self.page_single.combo_patch.setCurrentText(str(config.get("patch_size", 512)))
        
        # Batch View defaults sync
        self.page_batch.combo_model.setCurrentText(config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        self.page_batch.combo_device.setCurrentText(config.get("device", "cuda"))
        self.page_batch.slider_thresh.setValue(int(config.get("confidence_threshold", 0.5) * 100))
        
        # If default settings changed, clear model cache to force reload on next runs
        self.model_cache.clear()
