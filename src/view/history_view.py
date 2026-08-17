""" Context:
- What: HistoryView widget providing the History listing page and the Detail Inspection view inside it.
- Path: src/view/history_view.py
"""

import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QHeaderView,
    QAbstractItemView, QTableWidgetItem, QFileDialog, QScrollArea, QFrame
)
from PySide6.QtGui import QPixmap, QImageReader, QColor, QDesktopServices
from PySide6.QtCore import Qt, Signal, Slot, QSize, QUrl, QRectF

from qfluentwidgets import (
    SimpleCardWidget, TitleLabel, SubtitleLabel, LargeTitleLabel,
    BodyLabel, CaptionLabel, PushButton, PrimaryPushButton,
    TableWidget, TabWidget, ComboBox, LineEdit, SearchLineEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, MessageBox,
    SingleDirectionScrollArea
)

from src.view.components.image_viewer import ImageViewer
from src.view_model import HistoryViewModel

class HistoryView(QWidget):
    """Container view managing History Listing and Detail Inspection sub-pages."""

    history_changed = Signal()

    def __init__(self, view_model: HistoryViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model
        self.thumbnail_cache = {}

        # Main layout holds a stacked widget for seamless transition between List and Detail views
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget(self)
        self.main_layout.addWidget(self.stacked_widget)

        # 1. Page 0: History List View
        self.page_list = QWidget(self)
        self.setup_list_page()
        self.stacked_widget.addWidget(self.page_list)

        # 2. Page 1: Detail Inspection View
        self.page_detail = QWidget(self)
        self.setup_detail_page()
        self.stacked_widget.addWidget(self.page_detail)

        # Connect ViewModel signals
        self.connect_view_model()

    # ==========================================
    # PAGE 1: LIST PAGE SETUP
    # ==========================================
    def setup_list_page(self):
        list_layout = QVBoxLayout(self.page_list)
        list_layout.setContentsMargins(24, 24, 24, 24)
        list_layout.setSpacing(20)

        # 1. Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title = LargeTitleLabel("Inspection History", self.page_list)
        subtitle = BodyLabel("Explore, search, filter, and inspect past inferenced images and detection records", self.page_list)
        subtitle.setStyleSheet("color: #606060;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        list_layout.addLayout(header_layout)

        # 2. KPI Cards Row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(16)

        # KPI 1: Total Inspected
        self.card_total = SimpleCardWidget(self.page_list)
        tot_layout = QVBoxLayout(self.card_total)
        tot_layout.addWidget(CaptionLabel("Total Records", self.card_total))
        self.lbl_stat_total = TitleLabel("0", self.card_total)
        self.lbl_stat_total.setStyleSheet("color: #0078d4; font-weight: bold;")
        tot_layout.addWidget(self.lbl_stat_total)

        # KPI 2: Cracks Detected
        self.card_cracks = SimpleCardWidget(self.page_list)
        crk_layout = QVBoxLayout(self.card_cracks)
        crk_layout.addWidget(CaptionLabel("Cracks Detected", self.card_cracks))
        self.lbl_stat_cracks = TitleLabel("0 (0.0%)", self.card_cracks)
        self.lbl_stat_cracks.setStyleSheet("color: #e81123; font-weight: bold;")
        crk_layout.addWidget(self.lbl_stat_cracks)

        # KPI 3: Clean Roofs
        self.card_clean = SimpleCardWidget(self.page_list)
        cln_layout = QVBoxLayout(self.card_clean)
        cln_layout.addWidget(CaptionLabel("Clean Roofs", self.card_clean))
        self.lbl_stat_clean = TitleLabel("0", self.card_clean)
        self.lbl_stat_clean.setStyleSheet("color: #107c41; font-weight: bold;")
        cln_layout.addWidget(self.lbl_stat_clean)

        # KPI 4: Avg Speed
        self.card_speed = SimpleCardWidget(self.page_list)
        spd_layout = QVBoxLayout(self.card_speed)
        spd_layout.addWidget(CaptionLabel("Avg Process Time", self.card_speed))
        self.lbl_stat_speed = TitleLabel("0.00s", self.card_speed)
        self.lbl_stat_speed.setStyleSheet("color: #5c2d91; font-weight: bold;")
        spd_layout.addWidget(self.lbl_stat_speed)

        self.kpi_layout.addWidget(self.card_total)
        self.kpi_layout.addWidget(self.card_cracks)
        self.kpi_layout.addWidget(self.card_clean)
        self.kpi_layout.addWidget(self.card_speed)
        list_layout.addLayout(self.kpi_layout)

        # 3. Controls & Filter Toolbar Card
        self.card_toolbar = SimpleCardWidget(self.page_list)
        tb_layout = QHBoxLayout(self.card_toolbar)
        tb_layout.setContentsMargins(16, 12, 16, 12)
        tb_layout.setSpacing(12)

        # Search Input
        self.search_input = SearchLineEdit(self.card_toolbar)
        self.search_input.setPlaceholderText("Search by image name, path, or model...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.search_input, stretch=2)

        # Status Filter ComboBox
        self.combo_status_filter = ComboBox(self.card_toolbar)
        self.combo_status_filter.addItems(["All Inspections", "Cracks Detected", "No Cracks"])
        self.combo_status_filter.currentIndexChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.combo_status_filter, stretch=1)

        # Sorting ComboBox
        self.combo_sort = ComboBox(self.card_toolbar)
        self.combo_sort.addItems(["Newest First", "Oldest First", "Highest Confidence", "Most Cracks"])
        self.combo_sort.currentIndexChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.combo_sort, stretch=1)

        # Clear History Button
        self.btn_clear_history = PushButton(FIF.DELETE, "Clear History", self.card_toolbar)
        self.btn_clear_history.clicked.connect(self.confirm_clear_history)
        tb_layout.addWidget(self.btn_clear_history)

        list_layout.addWidget(self.card_toolbar)

        # 4. History Table
        self.table_history = TableWidget(self.page_list)
        self.table_history.setColumnCount(8)
        self.table_history.setHorizontalHeaderLabels([
            "Thumbnail", "Filename", "Date & Time", "Model Used",
            "Crack Status", "Confidence", "Elapsed", "Actions"
        ])
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_history.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_history.doubleClicked.connect(self.on_row_double_clicked)

        header = self.table_history.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        list_layout.addWidget(self.table_history, stretch=1)

    # ==========================================
    # PAGE 2: DETAIL INSPECTION PAGE SETUP
    # ==========================================
    def setup_detail_page(self):
        detail_layout = QVBoxLayout(self.page_detail)
        detail_layout.setContentsMargins(24, 24, 24, 24)
        detail_layout.setSpacing(16)

        # 1. Header Toolbar Bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        # Back Button
        self.btn_back = PushButton(FIF.LEFT_ARROW, "Back to History", self.page_detail)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.view_model.request_back_to_list)
        header_bar.addWidget(self.btn_back)

        # Title Info
        self.lbl_detail_title = TitleLabel("Detail Inspection", self.page_detail)
        header_bar.addWidget(self.lbl_detail_title)
        header_bar.addStretch()

        # Quick Action Buttons
        self.btn_detail_export = PushButton(FIF.PRINT, "Export PDF Report", self.page_detail)
        self.btn_detail_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detail_export.clicked.connect(self.export_current_detail_report)
        header_bar.addWidget(self.btn_detail_export)

        self.btn_detail_folder = PushButton(FIF.FOLDER, "Open File Location", self.page_detail)
        self.btn_detail_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detail_folder.clicked.connect(self.open_current_image_folder)
        header_bar.addWidget(self.btn_detail_folder)

        self.btn_detail_delete = PushButton(FIF.DELETE, "Delete Record", self.page_detail)
        self.btn_detail_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detail_delete.clicked.connect(self.delete_current_detail_record)
        header_bar.addWidget(self.btn_detail_delete)

        detail_layout.addLayout(header_bar)

        # 2. Main Body Split (Left: Image Tabs, Right: Inspection Details)
        body_split = QHBoxLayout()
        body_split.setSpacing(16)

        # --- Left Panel: Multi-Tab Image Viewers ---
        left_widget = QWidget(self.page_detail)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.detail_tabs = TabWidget(left_widget)

        # Tab 1: Visualization Overlay
        self.detail_viewer_vis = ImageViewer(self.detail_tabs)
        self.detail_tabs.addTab(self.detail_viewer_vis, "🔍 Visualization Overlay")

        # Tab 2: Original Image
        self.detail_viewer_orig = ImageViewer(self.detail_tabs)
        self.detail_tabs.addTab(self.detail_viewer_orig, "Original Image")

        # Tab 3: Crack Overlay
        self.detail_viewer_overlay = ImageViewer(self.detail_tabs)
        self.detail_tabs.addTab(self.detail_viewer_overlay, "Crack Overlay")

        # Tab 4: Binary Mask
        self.detail_viewer_mask = ImageViewer(self.detail_tabs)
        self.detail_tabs.addTab(self.detail_viewer_mask, "Binary Mask")

        left_layout.addWidget(self.detail_tabs, stretch=1)

        # Viewer status text
        self.detail_viewer_status = QLabel(left_widget)
        self.detail_viewer_status.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 13px;")
        left_layout.addWidget(self.detail_viewer_status)

        body_split.addWidget(left_widget, stretch=3)

        # --- Right Panel: Inspection Summary & Bounding Boxes ---
        right_scroll = SingleDirectionScrollArea(self.page_detail)
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_scroll.viewport().setStyleSheet("background: transparent;")

        right_container = QWidget()
        right_container.setStyleSheet("QWidget { background: transparent; }")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Card 1: Summary Banner & Key Details
        self.card_detail_summary = SimpleCardWidget(right_container)
        summary_card_layout = QVBoxLayout(self.card_detail_summary)
        summary_card_layout.setSpacing(10)

        self.lbl_detail_status_banner = TitleLabel("STATUS", self.card_detail_summary)
        self.lbl_detail_status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detail_status_banner.setStyleSheet("padding: 8px; border-radius: 6px;")
        summary_card_layout.addWidget(self.lbl_detail_status_banner)

        # Details list
        self.lbl_detail_info = BodyLabel("", self.card_detail_summary)
        self.lbl_detail_info.setWordWrap(True)
        self.lbl_detail_info.setStyleSheet("QLabel { background: transparent; word-break: break-all; }")
        summary_card_layout.addWidget(self.lbl_detail_info)

        right_layout.addWidget(self.card_detail_summary)

        # Card 2: Bounding Boxes Table
        self.card_detail_boxes = SimpleCardWidget(right_container)
        boxes_layout = QVBoxLayout(self.card_detail_boxes)
        boxes_layout.setSpacing(8)

        boxes_title = SubtitleLabel("Detected Crack Bounding Boxes", self.card_detail_boxes)
        boxes_layout.addWidget(boxes_title)

        self.table_detail_boxes = TableWidget(self.card_detail_boxes)
        self.table_detail_boxes.setColumnCount(3)
        self.table_detail_boxes.setHorizontalHeaderLabels(["Index", "Bounding Box [X1, Y1, X2, Y2]", "Severity / Area"])
        self.table_detail_boxes.verticalHeader().setVisible(False)
        self.table_detail_boxes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_detail_boxes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_detail_boxes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_detail_boxes.itemSelectionChanged.connect(self.on_detail_box_selected)

        boxes_header = self.table_detail_boxes.horizontalHeader()
        boxes_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        boxes_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        boxes_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_detail_boxes.setMinimumHeight(200)

        boxes_layout.addWidget(self.table_detail_boxes)
        right_layout.addWidget(self.card_detail_boxes)
        right_layout.addStretch()

        right_scroll.setWidget(right_container)
        body_split.addWidget(right_scroll, stretch=2)

        detail_layout.addLayout(body_split, stretch=1)

    # ==========================================
    # VIEW MODEL BINDINGS & REFRESH LOGIC
    # ==========================================
    def connect_view_model(self):
        self.view_model.history_refreshed.connect(self.on_history_refreshed)
        self.view_model.record_selected.connect(self.on_record_selected)
        self.view_model.back_to_list_requested.connect(self.on_back_to_list_requested)
        self.view_model.report_exported.connect(self.on_report_exported)
        self.view_model.report_export_failed.connect(self.on_report_export_failed)

    def refresh_list(self):
        """Triggers ViewModel refresh with current UI search/filter parameters."""
        query = self.search_input.text()
        status_filter = self.combo_status_filter.currentText()
        sort_by = self.combo_sort.currentText()
        self.view_model.refresh_history(query, status_filter, sort_by)

    def on_filter_changed(self):
        self.refresh_list()

    @Slot(list, dict)
    def on_history_refreshed(self, records, stats):
        # 1. Update KPI labels
        self.lbl_stat_total.setText(str(stats["total_records"]))
        self.lbl_stat_cracks.setText(f"{stats['cracks_count']} ({stats['crack_rate']:.1f}%)")
        self.lbl_stat_clean.setText(str(stats["clean_count"]))
        self.lbl_stat_speed.setText(f"{stats['avg_speed']:.2f}s")

        # Prune stale thumbnails
        valid_paths = set()
        for r in records:
            p = r.get("vis_image_path") or r.get("image_path")
            if p:
                valid_paths.add(p)
        self.thumbnail_cache = {p: pix for p, pix in self.thumbnail_cache.items() if p in valid_paths and os.path.exists(p)}

        # 2. Populate History Table
        self.table_history.setRowCount(0)
        self.table_history.setRowCount(len(records))

        for row_idx, record in enumerate(records):
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
                    reader = QImageReader(img_path)
                    reader.setAutoTransform(True)
                    orig_size = reader.size()
                    if not orig_size.isEmpty():
                        scaled_size = orig_size.scaled(QSize(64, 48), Qt.AspectRatioMode.KeepAspectRatio)
                        reader.setScaledSize(scaled_size)
                        q_img = reader.read()
                        if not q_img.isNull():
                            pix = QPixmap.fromImage(q_img)
                            self.thumbnail_cache[img_path] = pix
                            thumb_label.setPixmap(pix)
                    else:
                        pix = QPixmap(img_path)
                        if not pix.isNull():
                            scaled_pix = pix.scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            self.thumbnail_cache[img_path] = scaled_pix
                            thumb_label.setPixmap(scaled_pix)
            self.table_history.setCellWidget(row_idx, 0, thumb_label)

            # Filename
            file_item = BodyLabel(record.get("image_name", "N/A"), self.table_history)
            file_item.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            file_item.setToolTip(record.get("image_path", ""))
            self.table_history.setCellWidget(row_idx, 1, file_item)

            # Date & Time
            timestamp_str = record.get("timestamp", "")
            date_display = "N/A"
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    date_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            date_item = BodyLabel(date_display, self.table_history)
            date_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setCellWidget(row_idx, 2, date_item)

            # Model Used
            model_item = BodyLabel(record.get("model_used", "N/A"), self.table_history)
            model_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setCellWidget(row_idx, 3, model_item)

            # Crack Status
            crack_count = record.get("crack_count", 0)
            crack_detected = record.get("crack_detected", False)
            status_widget = QLabel()
            status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if crack_detected:
                status_widget.setText(f"YES ({crack_count})")
                status_widget.setStyleSheet("color: #e81123; font-weight: bold; background: transparent;")
            else:
                status_widget.setText("CLEAN")
                status_widget.setStyleSheet("color: #107c41; font-weight: bold; background: transparent;")
            self.table_history.setCellWidget(row_idx, 4, status_widget)

            # Max Confidence
            conf = record.get("confidence", 0.0)
            conf_item = BodyLabel(f"{conf * 100:.1f}%", self.table_history)
            conf_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setCellWidget(row_idx, 5, conf_item)

            # Elapsed speed
            speed_item = BodyLabel(f"{record.get('elapsed_time', 0.0):.2f}s", self.table_history)
            speed_item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_history.setCellWidget(row_idx, 6, speed_item)

            # Action Buttons Row
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            btn_inspect = PrimaryPushButton(FIF.ZOOM, "Inspect", actions_widget)
            btn_inspect.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_inspect.clicked.connect(lambda checked=False, r=record: self.view_model.select_record(r))

            btn_report = PushButton(FIF.PRINT, "", actions_widget)
            btn_report.setToolTip("Export PDF Report")
            btn_report.setFixedWidth(32)
            btn_report.clicked.connect(lambda checked=False, r=record: self.export_record_report(r))

            btn_del = PushButton(FIF.DELETE, "", actions_widget)
            btn_del.setToolTip("Delete Record")
            btn_del.setFixedWidth(32)
            btn_del.clicked.connect(lambda checked=False, rid=record["id"]: self.confirm_delete_record(rid))

            actions_layout.addWidget(btn_inspect)
            actions_layout.addWidget(btn_report)
            actions_layout.addWidget(btn_del)

            self.table_history.setCellWidget(row_idx, 7, actions_widget)
            self.table_history.setRowHeight(row_idx, 54)

    def on_row_double_clicked(self, index):
        row = index.row()
        filtered = self.view_model.get_history(
            self.search_input.text(),
            self.combo_status_filter.currentText(),
            self.combo_sort.currentText()
        )
        if 0 <= row < len(filtered):
            self.view_model.select_record(filtered[row])

    # ==========================================
    # DETAIL INSPECTION VIEW LOGIC
    # ==========================================
    def show_detail_inspection(self, record: dict):
        """Public helper to open detail inspection directly for a given record."""
        self.view_model.select_record(record)

    @Slot(dict)
    def on_record_selected(self, record):
        """Populates and displays the Detail Inspection page for the given record."""
        self.lbl_detail_title.setText(f"Detail Inspection: {record.get('image_name', 'Image')}")

        # 1. Load Images into Image Viewers
        orig_path = record.get("image_path", "")
        if orig_path and os.path.exists(orig_path):
            self.detail_viewer_orig.set_image(QPixmap(orig_path))
        else:
            self.detail_viewer_orig.clear()

        vis_path = record.get("vis_image_path", "")
        if vis_path and os.path.exists(vis_path):
            self.detail_viewer_vis.set_image(QPixmap(vis_path))
        elif orig_path and os.path.exists(orig_path):
            self.detail_viewer_vis.set_image(QPixmap(orig_path))
        else:
            self.detail_viewer_vis.clear()

        overlay_path = record.get("overlay_image_path", "") or vis_path
        if overlay_path and os.path.exists(overlay_path):
            self.detail_viewer_overlay.set_image(QPixmap(overlay_path))
        else:
            self.detail_viewer_overlay.clear()

        mask_path = record.get("mask_image_path", "")
        if mask_path and os.path.exists(mask_path):
            self.detail_viewer_mask.set_image(QPixmap(mask_path))
        else:
            self.detail_viewer_mask.clear()

        # 2. Populate Status Banner & Metadata
        crack_detected = record.get("crack_detected", False)
        crack_count = record.get("crack_count", 0)
        confidence = record.get("confidence", 0.0)
        timestamp_str = record.get("timestamp", "")
        formatted_date = "N/A"
        if timestamp_str:
            try:
                formatted_date = datetime.fromisoformat(timestamp_str).strftime("%B %d, %Y - %I:%M %p")
            except Exception:
                formatted_date = timestamp_str

        if crack_detected:
            self.lbl_detail_status_banner.setText("CRACK DETECTED — ATTENTION REQUIRED")
            self.lbl_detail_status_banner.setStyleSheet(
                "background: #ffebe9; color: #d9381e; font-weight: bold; border: 1px solid #ffc0cb; border-radius: 6px; padding: 10px;"
            )
        else:
            self.lbl_detail_status_banner.setText("ROOF SURFACE CLEAN — NO CRACKS")
            self.lbl_detail_status_banner.setStyleSheet(
                "background: #e6f4ea; color: #137333; font-weight: bold; border: 1px solid #b7e1cd; border-radius: 6px; padding: 10px;"
            )

        info_text = (
            f"<b>Detection Results:</b><br>"
            f"• <b>Cracks Count:</b> {crack_count}<br>"
            f"• <b>Max Confidence:</b> {confidence * 100:.1f}%<br>"
            f"• <b>Inference Speed:</b> {record.get('elapsed_time', 0.0):.2f} seconds<br><br>"
            f"<b>Model & File Context:</b><br>"
            f"• <b>Model Variant:</b> {record.get('model_used', 'N/A')}<br>"
            f"• <b>Inspection Date:</b> {formatted_date}<br>"
            f"• <b>File Location:</b> <span style='word-break: break-all;'>{orig_path}</span>"
        )
        self.lbl_detail_info.setText(info_text)

        # 3. Populate Bounding Boxes Table
        boxes = record.get("bounding_boxes", [])
        self.table_detail_boxes.setRowCount(0)
        self.table_detail_boxes.setRowCount(len(boxes))

        for idx, box in enumerate(boxes):
            idx_item = QTableWidgetItem(str(idx + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_detail_boxes.setItem(idx, 0, idx_item)

            coords = f"[{box[0]}, {box[1]}, {box[2]}, {box[3]}]"
            coords_item = QTableWidgetItem(coords)
            coords_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_detail_boxes.setItem(idx, 1, coords_item)

            w = box[2] - box[0]
            h = box[3] - box[1]
            area = w * h
            severity = "Minor"
            if area > 1000:
                severity = "Critical"
            elif area > 200:
                severity = "Medium"

            sev_item = QTableWidgetItem(f"{area} px² ({severity})")
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if severity == "Critical":
                sev_item.setForeground(QColor("#f43f5e"))
            elif severity == "Medium":
                sev_item.setForeground(QColor("#f59e0b"))
            else:
                sev_item.setForeground(QColor("#10b981"))
            self.table_detail_boxes.setItem(idx, 2, sev_item)

        self.detail_tabs.setCurrentIndex(0)
        self.stacked_widget.setCurrentWidget(self.page_detail)

    @Slot()
    def on_back_to_list_requested(self):
        self.stacked_widget.setCurrentWidget(self.page_list)
        self.refresh_list()

    def on_detail_box_selected(self):
        selected_ranges = self.table_detail_boxes.selectedRanges()
        rec = self.view_model.current_selected_record
        if not selected_ranges or not rec:
            return

        row = selected_ranges[0].topRow()
        boxes = rec.get("bounding_boxes", [])
        if 0 <= row < len(boxes):
            box = boxes[row]
            padding = 60
            x1 = max(0, box[0] - padding)
            y1 = max(0, box[1] - padding)
            x2 = box[2] + padding
            y2 = box[3] + padding

            self.detail_tabs.setCurrentIndex(0)
            self.detail_viewer_vis.fitInView(QRectF(x1, y1, x2 - x1, y2 - y1), Qt.AspectRatioMode.KeepAspectRatio)

    # ==========================================
    # ACTION HANDLERS (REPORT, DELETE, OPEN FOLDER)
    # ==========================================
    def export_record_report(self, record: dict):
        default_name = f"inspection_report_{record['id'][:8]}.pdf"
        output_pdf_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Inspection Report",
            os.path.join(self.view_model.get_default_reports_dir(), default_name),
            "PDF Files (*.pdf)"
        )
        if output_pdf_path:
            self.view_model.export_report(record, output_pdf_path)

    def export_current_detail_report(self):
        rec = self.view_model.current_selected_record
        if rec:
            self.export_record_report(rec)

    def open_current_image_folder(self):
        rec = self.view_model.current_selected_record
        if not rec:
            return
        img_path = rec.get("image_path")
        if img_path and os.path.exists(img_path):
            abs_path = os.path.abspath(img_path)
            if os.name == "nt":
                subprocess.run(["explorer", "/select,", abs_path])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(abs_path)))
        else:
            InfoBar.warning(
                title="File Not Found",
                content=f"Original image file no longer exists at: {img_path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def confirm_delete_record(self, record_id: str):
        w = MessageBox("Delete Record", "Are you sure you want to delete this inspection record and its saved result images?", self)
        if w.exec():
            self.view_model.delete_record(record_id)
            self.history_changed.emit()
            InfoBar.success(
                title="Record Deleted",
                content="Inspection record removed.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self
            )

    def delete_current_detail_record(self):
        rec = self.view_model.current_selected_record
        if rec:
            self.confirm_delete_record(rec["id"])

    def confirm_clear_history(self):
        w = MessageBox("Clear All History", "Are you sure you want to clear all history records and remove all generated result assets?", self)
        if w.exec():
            self.view_model.clear_history()
            self.history_changed.emit()
            InfoBar.success(
                title="History Cleared",
                content="All inspection history has been cleared.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self
            )

    @Slot(str)
    def on_report_exported(self, path):
        InfoBar.success(
            title="Report Exported",
            content=f"Report saved to: {path}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    @Slot(str)
    def on_report_export_failed(self, err):
        InfoBar.error(
            title="Export Failed",
            content=err,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )
