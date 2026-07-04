""" Context:
- What: The HomeView class is a QWidget that provides the main dashboard interface for the roof crack detection application.
- Path: src/view/home_view.py
"""


import os
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QHeaderView, QAbstractItemView, QTableWidgetItem
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, Slot

from qfluentwidgets import (
    SimpleCardWidget, TitleLabel, SubtitleLabel, LargeTitleLabel,
    BodyLabel, CaptionLabel, PushButton, TableWidget, FluentIcon as FIF
)

from src.view.components.custom_chart import InspectionChart
from src.view_model.home_view_model import HomeViewModel

class HomeView(QWidget):
    """The landing homepage dashboard of the crack inspection desktop application, refactored using MVVM."""
    
    # Navigation signals
    navigate_to_single = Signal()
    navigate_to_batch = Signal()
    navigate_to_settings = Signal()
    view_record_signal = Signal(dict)

    def __init__(self, view_model: HomeViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model
        self.thumbnail_cache = {}

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(20)

        # 1. Header Section
        self.setup_header()

        # 2. KPI Cards Row
        self.setup_kpis()

        # 3. Quick Actions Cards Row
        self.setup_quick_actions()

        # 4. Content Area (Splits into Recent Table and Chart)
        self.setup_content_area()

        # Bind ViewModel Signals
        self.connect_view_model()

        # Load initial data
        self.refresh_dashboard()

    def setup_header(self):
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = LargeTitleLabel("Dashboard", self)
        subtitle = BodyLabel("Welcome to the Roof Crack Detection & Structural Safety Hub", self)
        subtitle.setStyleSheet("color: #606060;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.main_layout.addLayout(header_layout)

    def setup_kpis(self):
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(16)
        
        # KPI 1: Total Inspections
        self.card_total = SimpleCardWidget(self)
        tot_layout = QVBoxLayout(self.card_total)
        self.lbl_total_label = CaptionLabel("Total Inspected", self)
        self.lbl_total_val = TitleLabel("0", self)
        self.lbl_total_val.setStyleSheet("color: #0078d4; font-weight: bold;")
        tot_layout.addWidget(self.lbl_total_label)
        tot_layout.addWidget(self.lbl_total_val)
        
        # KPI 2: Cracks Detected
        self.card_cracks = SimpleCardWidget(self)
        crk_layout = QVBoxLayout(self.card_cracks)
        self.lbl_cracks_label = CaptionLabel("Cracks Detected", self)
        self.lbl_cracks_val = TitleLabel("0 (0%)", self)
        self.lbl_cracks_val.setStyleSheet("color: #e81123; font-weight: bold;")
        crk_layout.addWidget(self.lbl_cracks_label)
        crk_layout.addWidget(self.lbl_cracks_val)

        # KPI 3: Speed Avg
        self.card_speed = SimpleCardWidget(self)
        spd_layout = QVBoxLayout(self.card_speed)
        self.lbl_speed_label = CaptionLabel("Avg Process Time", self)
        self.lbl_speed_val = TitleLabel("0.00s", self)
        self.lbl_speed_val.setStyleSheet("color: #107c41; font-weight: bold;")
        spd_layout.addWidget(self.lbl_speed_label)
        spd_layout.addWidget(self.lbl_speed_val)

        # KPI 4: Active Model
        self.card_model = SimpleCardWidget(self)
        mdl_layout = QVBoxLayout(self.card_model)
        self.lbl_model_label = CaptionLabel("Active Model", self)
        self.lbl_model_val = SubtitleLabel("N/A", self)
        self.lbl_model_val.setStyleSheet("color: #5c2d91; font-weight: bold;")
        mdl_layout.addWidget(self.lbl_model_label)
        mdl_layout.addWidget(self.lbl_model_val)

        self.kpi_layout.addWidget(self.card_total)
        self.kpi_layout.addWidget(self.card_cracks)
        self.kpi_layout.addWidget(self.card_speed)
        self.kpi_layout.addWidget(self.card_model)
        
        self.main_layout.addLayout(self.kpi_layout)

    def setup_quick_actions(self):
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)
        
        # Card 1: Single Image
        self.btn_action_single = PushButton(FIF.ZOOM, "Analyze Single Image", self)
        self.btn_action_single.clicked.connect(self.navigate_to_single.emit)
        
        # Card 2: Batch
        self.btn_action_batch = PushButton(FIF.FOLDER, "Batch Process Folder", self)
        self.btn_action_batch.clicked.connect(self.navigate_to_batch.emit)
        
        # Card 3: Settings
        self.btn_action_settings = PushButton(FIF.SETTING, "System Settings", self)
        self.btn_action_settings.clicked.connect(self.navigate_to_settings.emit)
        
        actions_layout.addWidget(self.btn_action_single)
        actions_layout.addWidget(self.btn_action_batch)
        actions_layout.addWidget(self.btn_action_settings)
        
        self.main_layout.addLayout(actions_layout)

    def setup_content_area(self):
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)
        
        # Left Panel: Recent Table
        left_panel = QVBoxLayout()
        recents_header = SubtitleLabel("Recent Inspections", self)
        left_panel.addWidget(recents_header)
        
        self.table_recent = TableWidget(self)
        self.table_recent.setColumnCount(6)
        self.table_recent.setHorizontalHeaderLabels(["Thumbnail", "Filename", "Date", "Cracks Found", "Max Conf", "Action"])
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_recent.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_recent.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Column stretching
        header = self.table_recent.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_recent.setMinimumHeight(300)
        left_panel.addWidget(self.table_recent)
        
        # Right Panel: Analytics Chart
        right_panel = QVBoxLayout()
        chart_header = SubtitleLabel("Trends & History", self)
        right_panel.addWidget(chart_header)
        
        self.chart_widget = InspectionChart(self)
        self.chart_widget.setMinimumSize(400, 300)
        right_panel.addWidget(self.chart_widget)
        
        body_layout.addLayout(left_panel, stretch=3)
        body_layout.addLayout(right_panel, stretch=2)
        
        self.main_layout.addLayout(body_layout)

    def connect_view_model(self):
        self.view_model.dashboard_refreshed.connect(self.on_dashboard_refreshed)

    def refresh_dashboard(self):
        self.view_model.refresh_dashboard()

    @Slot(dict)
    def on_dashboard_refreshed(self, stats):
        total_inspected = stats["total_inspected"]
        cracks_detected = stats["cracks_detected"]
        crack_rate = stats["crack_rate"]
        avg_speed = stats["avg_speed"]
        active_model = stats["active_model"]
        recent_records = stats["recent_records"]
        history = stats["full_history"]

        # 1. Update KPIs
        self.lbl_total_val.setText(str(total_inspected))
        self.lbl_cracks_val.setText(f"{cracks_detected} ({crack_rate:.1f}%)")
        
        if cracks_detected > 0:
            self.lbl_cracks_val.setStyleSheet("color: #e81123; font-weight: bold;")
        else:
            self.lbl_cracks_val.setStyleSheet("color: #107c41; font-weight: bold;")

        self.lbl_speed_val.setText(f"{avg_speed:.2f}s")
        self.lbl_model_val.setText(active_model.split("_")[0])
        self.lbl_model_val.setToolTip(active_model)

        # 2. Update Trends Chart
        self.chart_widget.update_data(history)

        # 3. Update Table
        self.table_recent.setRowCount(0)
        self.table_recent.setRowCount(len(recent_records))
        
        for row_idx, record in enumerate(recent_records):
            # Thumbnail preview
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_label.setStyleSheet("border: none; background: transparent; padding: 2px;")
            
            img_path = record.get("vis_image_path")
            if not img_path or not os.path.exists(img_path):
                img_path = record.get("image_path")
                
            if img_path and os.path.exists(img_path):
                if img_path in self.thumbnail_cache:
                    thumb_label.setPixmap(self.thumbnail_cache[img_path])
                else:
                    pix = QPixmap(img_path)
                    if not pix.isNull():
                        scaled_pix = pix.scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.thumbnail_cache[img_path] = scaled_pix
                        thumb_label.setPixmap(scaled_pix)
            self.table_recent.setCellWidget(row_idx, 0, thumb_label)
            
            # Filename
            file_item = BodyLabel(record.get("image_name", "N/A"), self.table_recent)
            file_item.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            file_item.setToolTip(record.get("image_path", ""))
            self.table_recent.setCellWidget(row_idx, 1, file_item)
            
            # Date
            timestamp_str = record.get("timestamp", "")
            date_display = "N/A"
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    date_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            date_item = BodyLabel(date_display, self.table_recent)
            date_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_recent.setCellWidget(row_idx, 2, date_item)
            
            # Cracks Found / Status
            crack_count = record.get("crack_count", 0)
            crack_detected = record.get("crack_detected", False)
            
            status_widget = QLabel()
            status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if crack_detected:
                status_widget.setText(f"YES ({crack_count})")
                status_widget.setStyleSheet("color: #e81123; font-weight: bold; background: transparent;")
            else:
                status_widget.setText("NONE")
                status_widget.setStyleSheet("color: #107c41; font-weight: bold; background: transparent;")
            self.table_recent.setCellWidget(row_idx, 3, status_widget)
            
            # Max Confidence
            conf = record.get("confidence", 0.0)
            conf_item = BodyLabel(f"{conf*100:.1f}%", self.table_recent)
            conf_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_recent.setCellWidget(row_idx, 4, conf_item)
            
            # Action button
            view_btn = PushButton("Details", self.table_recent)
            view_btn.clicked.connect(lambda checked=False, r=record: self.view_record_signal.emit(r))
            self.table_recent.setCellWidget(row_idx, 5, view_btn)
            
            # Set row height
            self.table_recent.setRowHeight(row_idx, 52)
