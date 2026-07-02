import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QAbstractItemView, QFrame
)
from PySide6.QtGui import QColor, QFont, QPixmap, QIcon
from PySide6.QtCore import Qt, Signal, QSize
from .components.custom_chart import InspectionChart

class HomeView(QWidget):
    """The landing homepage dashboard of the crack inspection desktop application."""
    
    # Navigation signals
    navigate_to_single = Signal()
    navigate_to_batch = Signal()
    navigate_to_settings = Signal()
    view_record_signal = Signal(dict)  # Signal to view details of a specific historical record

    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        
        # Styles
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel#sectionHeader {
                font-size: 20px;
                font-weight: bold;
                color: #f8fafc;
                margin-top: 15px;
                margin-bottom: 10px;
            }
            QFrame.card {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QFrame.kpiCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel.kpiVal {
                font-size: 26px;
                font-weight: bold;
                color: #3b82f6;
            }
            QLabel.kpiLabel {
                font-size: 11px;
                color: #94a3b8;
                text-transform: uppercase;
                font-weight: bold;
            }
            QPushButton.actionCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 20px;
                text-align: left;
                font-size: 15px;
                font-weight: bold;
                color: #f8fafc;
            }
            QPushButton.actionCard:hover {
                background-color: #334155;
                border: 1px solid #3b82f6;
            }
            QPushButton.actionCard QLabel {
                background-color: transparent;
            }
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #334155;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
            }
            QScrollBar:vertical {
                background-color: #1e293b;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                min-height: 20px;
                border-radius: 6px;
            }
            QPushButton.viewBtn {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton.viewBtn:hover {
                background-color: #2563eb;
            }
        """)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. Header Section
        self.setup_header()

        # 2. KPI Cards Row
        self.setup_kpis()

        # 3. Quick Actions Cards Row
        self.setup_quick_actions()

        # 4. Content Area (Splits into Recent Table and Chart)
        self.setup_content_area()

        # Load initial data
        self.refresh_dashboard()

    def setup_header(self):
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("Dashboard")
        title.setObjectName("dashboardTitle")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #f8fafc;")
        
        subtitle = QLabel("Welcome to the Roof Crack Detection & Structural Safety Hub")
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.main_layout.addLayout(header_layout)

    def setup_kpis(self):
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(15)
        
        # KPI 1: Total Inspections
        self.card_total = QFrame()
        self.card_total.setProperty("class", "kpiCard")
        tot_layout = QVBoxLayout(self.card_total)
        self.lbl_total_label = QLabel("Total Inspected")
        self.lbl_total_label.setProperty("class", "kpiLabel")
        self.lbl_total_val = QLabel("0")
        self.lbl_total_val.setProperty("class", "kpiVal")
        tot_layout.addWidget(self.lbl_total_label)
        tot_layout.addWidget(self.lbl_total_val)
        
        # KPI 2: Cracks Detected
        self.card_cracks = QFrame()
        self.card_cracks.setProperty("class", "kpiCard")
        crk_layout = QVBoxLayout(self.card_cracks)
        self.lbl_cracks_label = QLabel("Cracks Detected")
        self.lbl_cracks_label.setProperty("class", "kpiLabel")
        self.lbl_cracks_val = QLabel("0 (0%)")
        self.lbl_cracks_val.setProperty("class", "kpiVal")
        self.lbl_cracks_val.setStyleSheet("color: #f43f5e;") # red highlight
        crk_layout.addWidget(self.lbl_cracks_label)
        crk_layout.addWidget(self.lbl_cracks_val)

        # KPI 3: Speed Avg
        self.card_speed = QFrame()
        self.card_speed.setProperty("class", "kpiCard")
        spd_layout = QVBoxLayout(self.card_speed)
        self.lbl_speed_label = QLabel("Avg Process Time")
        self.lbl_speed_label.setProperty("class", "kpiLabel")
        self.lbl_speed_val = QLabel("0.00s")
        self.lbl_speed_val.setProperty("class", "kpiVal")
        self.lbl_speed_val.setStyleSheet("color: #10b981;") # green highlight
        spd_layout.addWidget(self.lbl_speed_label)
        spd_layout.addWidget(self.lbl_speed_val)

        # KPI 4: Active Model
        self.card_model = QFrame()
        self.card_model.setProperty("class", "kpiCard")
        mdl_layout = QVBoxLayout(self.card_model)
        self.lbl_model_label = QLabel("Active Model Zoo")
        self.lbl_model_label.setProperty("class", "kpiLabel")
        self.lbl_model_val = QLabel("N/A")
        self.lbl_model_val.setProperty("class", "kpiVal")
        self.lbl_model_val.setStyleSheet("color: #06b6d4; font-size: 16px; margin-top: 10px;") # teal highlight
        mdl_layout.addWidget(self.lbl_model_label)
        mdl_layout.addWidget(self.lbl_model_val)

        self.kpi_layout.addWidget(self.card_total)
        self.kpi_layout.addWidget(self.card_cracks)
        self.kpi_layout.addWidget(self.card_speed)
        self.kpi_layout.addWidget(self.card_model)
        
        self.main_layout.addLayout(self.kpi_layout)

    def setup_quick_actions(self):
        actions_header = QLabel("Quick Actions")
        actions_header.setObjectName("sectionHeader")
        self.main_layout.addWidget(actions_header)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        # Card 1: Single Image
        self.btn_action_single = QPushButton("🔍 Analyze Single Image")
        self.btn_action_single.setProperty("class", "actionCard")
        self.btn_action_single.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_single.clicked.connect(self.navigate_to_single.emit)
        
        # Card 2: Batch
        self.btn_action_batch = QPushButton("📁 Batch Process Folder")
        self.btn_action_batch.setProperty("class", "actionCard")
        self.btn_action_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_batch.clicked.connect(self.navigate_to_batch.emit)
        
        # Card 3: Settings
        self.btn_action_settings = QPushButton("⚙️ System Settings")
        self.btn_action_settings.setProperty("class", "actionCard")
        self.btn_action_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_settings.clicked.connect(self.navigate_to_settings.emit)
        
        actions_layout.addWidget(self.btn_action_single)
        actions_layout.addWidget(self.btn_action_batch)
        actions_layout.addWidget(self.btn_action_settings)
        
        self.main_layout.addLayout(actions_layout)

    def setup_content_area(self):
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)
        
        # Left Panel: Recents Table
        left_panel = QVBoxLayout()
        recents_header = QLabel("Recent Inspections")
        recents_header.setObjectName("sectionHeader")
        left_panel.addWidget(recents_header)
        
        self.table_recent = QTableWidget()
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
        chart_header = QLabel("Trends & History")
        chart_header.setObjectName("sectionHeader")
        right_panel.addWidget(chart_header)
        
        self.chart_widget = InspectionChart()
        self.chart_widget.setMinimumSize(400, 300)
        right_panel.addWidget(self.chart_widget)
        
        body_layout.addLayout(left_panel, stretch=3)
        body_layout.addLayout(right_panel, stretch=2)
        
        self.main_layout.addLayout(body_layout)

    def refresh_dashboard(self):
        """Loads data from the HistoryManager and updates KPIs, Table, and Chart."""
        history = self.hm.history
        config = self.hm.config
        
        # 1. Update KPIs
        total_inspected = len(history)
        self.lbl_total_val.setText(str(total_inspected))
        
        cracks_detected = sum(1 for rec in history if rec.get("crack_detected", False))
        crack_rate = (cracks_detected / total_inspected * 100) if total_inspected > 0 else 0
        self.lbl_cracks_val.setText(f"{cracks_detected} ({crack_rate:.1f}%)")
        
        # Set KPI highlight color based on crack rate
        if cracks_detected > 0:
            self.lbl_cracks_val.setStyleSheet("color: #f43f5e; font-size: 26px; font-weight: bold;")
        else:
            self.lbl_cracks_val.setStyleSheet("color: #10b981; font-size: 26px; font-weight: bold;")

        avg_speed = sum(rec.get("elapsed_time", 0.0) for rec in history) / total_inspected if total_inspected > 0 else 0.0
        self.lbl_speed_val.setText(f"{avg_speed:.2f}s")
        
        # Simple name display for active model
        active_model = config.get("model_variant", "Seg_UNET_CFD_actual_v2")
        self.lbl_model_val.setText(active_model)
        self.lbl_model_val.setToolTip(active_model)

        # 2. Update Trends Chart
        self.chart_widget.update_data(history)

        # 3. Update Recents Table
        self.table_recent.setRowCount(0)
        recent_records = history[:10] # Show top 10
        self.table_recent.setRowCount(len(recent_records))
        
        for row_idx, record in enumerate(recent_records):
            # Column 0: Thumbnail preview
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_label.setStyleSheet("border: none; background: transparent; padding: 2px;")
            
            # Load thumbnail (using processed overlay if available, else original image)
            img_path = record.get("vis_image_path")
            if not img_path or not os.path.exists(img_path):
                img_path = record.get("image_path")
                
            if img_path and os.path.exists(img_path):
                pix = QPixmap(img_path)
                if not pix.isNull():
                    scaled_pix = pix.scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    thumb_label.setPixmap(scaled_pix)
            self.table_recent.setCellWidget(row_idx, 0, thumb_label)
            
            # Column 1: Filename
            file_item = QTableWidgetItem(record.get("image_name", "N/A"))
            file_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            file_item.setToolTip(record.get("image_path", ""))
            self.table_recent.setItem(row_idx, 1, file_item)
            
            # Column 2: Date
            timestamp_str = record.get("timestamp", "")
            date_display = "N/A"
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    date_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            date_item = QTableWidgetItem(date_display)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_recent.setItem(row_idx, 2, date_item)
            
            # Column 3: Cracks Found / Status
            crack_count = record.get("crack_count", 0)
            crack_detected = record.get("crack_detected", False)
            
            status_widget = QLabel()
            status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if crack_detected:
                status_widget.setText(f"⚠️ YES ({crack_count})")
                status_widget.setStyleSheet("color: #f43f5e; font-weight: bold; background: transparent;")
            else:
                status_widget.setText("✅ NONE")
                status_widget.setStyleSheet("color: #10b981; font-weight: bold; background: transparent;")
            self.table_recent.setCellWidget(row_idx, 3, status_widget)
            
            # Column 4: Max Confidence
            conf = record.get("confidence", 0.0)
            conf_item = QTableWidgetItem(f"{conf*100:.1f}%")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_recent.setItem(row_idx, 4, conf_item)
            
            # Column 5: Action button
            view_btn = QPushButton("Details")
            view_btn.setProperty("class", "viewBtn")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.clicked.connect(lambda checked=False, r=record: self.view_record_signal.emit(r))
            self.table_recent.setCellWidget(row_idx, 5, view_btn)
            
            # Set row height
            self.table_recent.setRowHeight(row_idx, 52)
