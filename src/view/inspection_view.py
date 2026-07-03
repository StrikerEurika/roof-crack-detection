import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QHeaderView, QAbstractItemView, QTableWidgetItem, QLabel
)
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt, Signal, Slot, QRectF

from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, SubtitleLabel, TitleLabel, CaptionLabel,
    ComboBox, Slider, CheckBox, PushButton, PrimaryPushButton,
    ProgressBar, TextEdit, TableWidget, TabWidget, FluentIcon as FIF,
    InfoBar, InfoBarPosition
)

from src.view.components.image_viewer import ImageViewer
from src.viewmodel import InspectionViewModel
from src import check_gpu_available

class InspectionView(QWidget):
    """View widget for analyzing a single image and viewing results, refactored to use InspectionViewModel."""
    
    inspection_completed = Signal() # Emitted when a new inspection is saved to history

    def __init__(self, view_model: InspectionViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        # Main horizontal layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)

        # 1. Left Control Panel
        self.setup_control_panel()

        # 2. Right Display Panel
        self.setup_display_panel()

        # Bind ViewModel Signals
        self.connect_view_model()

        # Load configurations defaults
        self.load_settings_defaults()

    def setup_control_panel(self):
        self.panel_left = QWidget(self)
        self.panel_left.setFixedWidth(300)
        left_layout = QVBoxLayout(self.panel_left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # Card 1: Image Source Selection
        self.card_source = SimpleCardWidget(self.panel_left)
        source_layout = QVBoxLayout(self.card_source)
        source_layout.setSpacing(8)
        
        source_title = SubtitleLabel("1. Select Target Image", self.card_source)
        source_layout.addWidget(source_title)
        
        self.btn_select_file = PushButton(FIF.FOLDER, "Browse Image File...", self.card_source)
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.clicked.connect(self.select_file)
        source_layout.addWidget(self.btn_select_file)

        self.lbl_filename = BodyLabel("No image file loaded", self.card_source)
        self.lbl_filename.setWordWrap(True)
        self.lbl_filename.setStyleSheet("color: #606060; font-style: italic;")
        source_layout.addWidget(self.lbl_filename)
        
        left_layout.addWidget(self.card_source)
        
        # Card 2: Model Configuration
        self.card_model = SimpleCardWidget(self.panel_left)
        model_layout = QVBoxLayout(self.card_model)
        model_layout.setSpacing(10)
        
        model_title = SubtitleLabel("2. Inference Settings", self.card_model)
        model_layout.addWidget(model_title)
        
        # Model selector
        model_layout.addWidget(BodyLabel("Pre-trained Model Zoo:", self.card_model))
        self.combo_model = ComboBox(self.card_model)
        self.combo_model.addItems(["Seg_UNET_CFD_actual_v2", "Seg_UNET_CFD_actual_v1", "Det_YOLOv26n-seg_crack-dataset_v1"])
        model_layout.addWidget(self.combo_model)
        
        # Device selector
        model_layout.addWidget(BodyLabel("Compute Device:", self.card_model))
        self.combo_device = ComboBox(self.card_model)
        self.combo_device.addItems(["cuda", "cpu"])
        model_layout.addWidget(self.combo_device)

        # Threshold slider
        self.lbl_thresh = BodyLabel("Confidence Threshold: 0.50", self.card_model)
        model_layout.addWidget(self.lbl_thresh)
        self.slider_thresh = Slider(Qt.Orientation.Horizontal, self.card_model)
        self.slider_thresh.setRange(10, 90)
        self.slider_thresh.valueChanged.connect(self.on_thresh_changed)
        model_layout.addWidget(self.slider_thresh)

        # Patch size
        model_layout.addWidget(BodyLabel("Sliding Window Patch Size:", self.card_model))
        self.combo_patch = ComboBox(self.card_model)
        self.combo_patch.addItems(["256", "512", "1024"])
        model_layout.addWidget(self.combo_patch)

        # Overlap ratio
        self.lbl_overlap = BodyLabel("Patch Overlap Ratio: 0.20", self.card_model)
        model_layout.addWidget(self.lbl_overlap)
        self.slider_overlap = Slider(Qt.Orientation.Horizontal, self.card_model)
        self.slider_overlap.setRange(0, 50)
        self.slider_overlap.valueChanged.connect(self.on_overlap_changed)
        model_layout.addWidget(self.slider_overlap)

        # Checkboxes
        self.chk_clahe = CheckBox("Apply CLAHE Preprocessing", self.card_model)
        model_layout.addWidget(self.chk_clahe)
        
        self.chk_tta = CheckBox("Use Test-Time Augmentation", self.card_model)
        model_layout.addWidget(self.chk_tta)

        left_layout.addWidget(self.card_model)

        # Run Action Button
        self.btn_run = PrimaryPushButton("⚡ RUN DETECTOR", self.panel_left)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.run_detection)
        left_layout.addWidget(self.btn_run)

        # Progress bar
        self.progress_bar = ProgressBar(self.panel_left)
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Log details
        self.txt_status = TextEdit(self.panel_left)
        self.txt_status.setReadOnly(True)
        self.txt_status.setMaximumHeight(80)
        self.txt_status.setPlaceholderText("Load a roof image file to begin analysis.")
        left_layout.addWidget(self.txt_status)
        left_layout.addStretch()

        self.layout.addWidget(self.panel_left)

    def setup_display_panel(self):
        self.panel_right = QWidget(self)
        right_layout = QVBoxLayout(self.panel_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Tabs for Image Views
        self.tab_widget = TabWidget(self.panel_right)
        
        # 1. Visualization tab
        self.viewer_vis = ImageViewer(self.tab_widget)
        self.viewer_vis.image_dropped.connect(self.on_image_dropped)
        self.tab_widget.addTab(self.viewer_vis, "🔍 Visualization Overlay")
        
        # 2. Original tab
        self.viewer_orig = ImageViewer(self.tab_widget)
        self.tab_widget.addTab(self.viewer_orig, "Original Image")
        
        # 3. Transparent Overlay tab
        self.viewer_overlay = ImageViewer(self.tab_widget)
        self.tab_widget.addTab(self.viewer_overlay, "Crack Overlay")

        # 4. Binary Mask tab
        self.viewer_mask = ImageViewer(self.tab_widget)
        self.tab_widget.addTab(self.viewer_mask, "Binary Mask")

        # 5. Confidence Map tab
        self.viewer_conf = ImageViewer(self.tab_widget)
        self.tab_widget.addTab(self.viewer_conf, "Confidence Heatmap")

        right_layout.addWidget(self.tab_widget, stretch=4)

        # Bottom Area: Results Table & Actions
        results_layout = QHBoxLayout()
        results_layout.setSpacing(16)

        # Results table
        table_container = QVBoxLayout()
        lbl_results_title = SubtitleLabel("Detected Crack Components", self.panel_right)
        table_container.addWidget(lbl_results_title)
        
        self.table_cracks = TableWidget(self.panel_right)
        self.table_cracks.setColumnCount(3)
        self.table_cracks.setHorizontalHeaderLabels(["Index", "Bounding Box (X1, Y1, X2, Y2)", "Size / Length Rating"])
        self.table_cracks.verticalHeader().setVisible(False)
        self.table_cracks.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_cracks.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_cracks.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_cracks.itemSelectionChanged.connect(self.on_crack_selected)
        
        header = self.table_cracks.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_cracks.setMaximumHeight(150)
        table_container.addWidget(self.table_cracks)
        
        results_layout.addLayout(table_container, stretch=3)

        # Right control summary: Reports & History Actions
        self.card_actions = SimpleCardWidget(self.panel_right)
        actions_container = QVBoxLayout(self.card_actions)
        actions_container.setSpacing(10)
        actions_container.setContentsMargins(15, 15, 15, 15)

        self.btn_export_pdf = PushButton(FIF.PRINT, "Export PDF Report", self.card_actions)
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self.export_report)
        actions_container.addWidget(self.btn_export_pdf)

        self.lbl_summary = BodyLabel("Run Status: No current inspection.", self.card_actions)
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #606060;")
        actions_container.addWidget(self.lbl_summary)
        actions_container.addStretch()
        
        results_layout.addWidget(self.card_actions, stretch=1)
        right_layout.addLayout(results_layout, stretch=1)

        self.layout.addWidget(self.panel_right)

    def connect_view_model(self):
        self.view_model.image_loaded.connect(self.on_image_loaded)
        self.view_model.record_loaded.connect(self.on_record_loaded)
        self.view_model.detection_started.connect(self.on_detection_started)
        self.view_model.detection_progress.connect(self.on_detection_progress)
        self.view_model.detection_finished.connect(self.on_detection_finished)
        self.view_model.detection_error.connect(self.on_detection_error)
        self.view_model.report_exported.connect(self.on_report_exported)
        self.view_model.report_export_failed.connect(self.on_report_export_failed)

    def load_settings_defaults(self):
        config = self.view_model.hm.config
        
        self.combo_model.setCurrentText(config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        
        has_gpu = check_gpu_available()
        if not has_gpu:
            self.combo_device.setCurrentText("cpu")
        else:
            self.combo_device.setCurrentText(config.get("device", "cuda"))

        self.slider_thresh.setValue(int(config.get("confidence_threshold", 0.5) * 100))
        self.lbl_thresh.setText(f"Confidence Threshold: {config.get('confidence_threshold', 0.5):.2f}")
        
        self.combo_patch.setCurrentText(str(config.get("patch_size", 512)))
        
        self.slider_overlap.setValue(int(config.get("overlap_ratio", 0.2) * 100))
        self.lbl_overlap.setText(f"Patch Overlap Ratio: {config.get('overlap_ratio', 0.2):.2f}")
        
        self.chk_clahe.setChecked(config.get("use_clahe", True))
        self.chk_tta.setChecked(config.get("use_tta", False))

    def on_thresh_changed(self, value):
        self.lbl_thresh.setText(f"Confidence Threshold: {value / 100:.2f}")

    def on_overlap_changed(self, value):
        self.lbl_overlap.setText(f"Patch Overlap Ratio: {value / 100:.2f}")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Roof Image File", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )
        if file_path:
            self.view_model.load_image(file_path)

    def on_image_dropped(self, file_path):
        self.view_model.load_image(file_path)

    @Slot(str)
    def on_image_loaded(self, file_path):
        self.current_image_path = file_path
        self.lbl_filename.setText(os.path.basename(file_path))
        self.lbl_filename.setToolTip(file_path)
        
        pix = QPixmap(file_path)
        if not pix.isNull():
            self.viewer_orig.set_image(pix)
            self.viewer_vis.set_image(pix)
            
            # Clear other tabs
            self.viewer_overlay.pixmap_item.setPixmap(QPixmap())
            self.viewer_mask.pixmap_item.setPixmap(QPixmap())
            self.viewer_conf.pixmap_item.setPixmap(QPixmap())
            
            # Enable buttons
            self.btn_run.setEnabled(True)
            self.btn_export_pdf.setEnabled(False)
            self.table_cracks.setRowCount(0)
            self.lbl_summary.setText("Image loaded. Press '⚡ RUN DETECTOR' to begin analysis.")
            self.txt_status.setText(f"Loaded file: {file_path}\nReady to run detection.")
            self.tab_widget.setCurrentIndex(0)

    @Slot(dict)
    def on_record_loaded(self, record):
        self.current_image_path = record.get("image_path")
        self.lbl_filename.setText(record.get("image_name", "N/A"))
        self.lbl_filename.setToolTip(self.current_image_path)
        
        self.btn_run.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        
        # Load the images
        if os.path.exists(self.current_image_path):
            self.viewer_orig.set_image(QPixmap(self.current_image_path))
            
        vis_path = record.get("vis_image_path")
        if vis_path and os.path.exists(vis_path):
            self.viewer_vis.set_image(QPixmap(vis_path))
            self.viewer_overlay.set_image(QPixmap(vis_path))
            
        mask_path = record.get("mask_image_path")
        if mask_path and os.path.exists(mask_path):
            self.viewer_mask.set_image(QPixmap(mask_path))
            
        self.table_cracks.setRowCount(0)
        self.lbl_summary.setText(f"Loaded history run: {record.get('model_used')}.\nCracks detected: {record.get('crack_count')}.")
        self.txt_status.setText(f"Loaded historical record from {record.get('timestamp')}")
        self.tab_widget.setCurrentIndex(0)

    def run_detection(self):
        pipeline_config = {
            "model_variant": self.combo_model.currentText(),
            "device": self.combo_device.currentText(),
            "confidence_threshold": self.slider_thresh.value() / 100.0,
            "patch_size": int(self.combo_patch.currentText()),
            "overlap_ratio": self.slider_overlap.value() / 100.0,
            "use_tta": self.chk_tta.isChecked(),
            "use_clahe": self.chk_clahe.isChecked(),
            "overlay_alpha": self.view_model.hm.config.get("overlay_alpha", 0.4),
            "overlay_color": self.view_model.hm.config.get("overlay_color", [255, 0, 0]),
            "box_color": self.view_model.hm.config.get("box_color", [0, 255, 0]),
            "box_thickness": self.view_model.hm.config.get("box_thickness", 2),
            "contour_color": self.view_model.hm.config.get("contour_color", [0, 0, 255]),
            "contour_thickness": self.view_model.hm.config.get("contour_thickness", 2),
        }
        self.view_model.run_detection(pipeline_config)

    @Slot()
    def on_detection_started(self):
        self.btn_run.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.txt_status.clear()

    @Slot(str)
    def on_detection_progress(self, msg):
        self.txt_status.append(msg)

    @Slot(dict)
    def on_detection_finished(self, payload):
        self.btn_run.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Display images in other tabs
        self.viewer_orig.set_ndarray_image(payload["original_image"])
        self.viewer_vis.set_ndarray_image(payload["visualization"])
        self.viewer_overlay.set_ndarray_image(payload["overlay"])
        self.viewer_mask.set_ndarray_image(payload["binary_mask"])
        
        conf_map = (payload["confidence_map"] * 255).astype("uint8")
        conf_rgb = np.stack([conf_map, conf_map, conf_map], axis=-1)
        self.viewer_conf.set_ndarray_image(conf_rgb)
        
        # Populate table of cracks
        boxes = payload["bounding_boxes"]
        self.table_cracks.setRowCount(0)
        self.table_cracks.setRowCount(len(boxes))
        
        for idx, box in enumerate(boxes):
            idx_item = QTableWidgetItem(str(idx + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cracks.setItem(idx, 0, idx_item)
            
            coords = f"[{box[0]}, {box[1]}, {box[2]}, {box[3]}]"
            coords_item = QTableWidgetItem(coords)
            coords_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cracks.setItem(idx, 1, coords_item)
            
            w = box[2] - box[0]
            h = box[3] - box[1]
            area = w * h
            severity = "Minor"
            if area > 1000:
                severity = "Critical"
            elif area > 200:
                severity = "Medium"
                
            sev_item = QTableWidgetItem(f"{area}px ({severity})")
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if severity == "Critical":
                sev_item.setForeground(QColor("#f43f5e"))
            elif severity == "Medium":
                sev_item.setForeground(QColor("#f59e0b"))
            else:
                sev_item.setForeground(QColor("#10b981"))
            self.table_cracks.setItem(idx, 2, sev_item)

        # Update Summary
        record = payload["record"]
        crack_detected = record["crack_detected"]
        crack_count = record["crack_count"]
        status_msg = "CRITICAL ACTION REQUIRED" if crack_detected else "ROOF SAFE / CLEAR"
        self.lbl_summary.setText(
            f"Run Status: COMPLETED\n"
            f"Result: {status_msg}\n"
            f"Crack count: {crack_count}\n"
            f"Time elapsed: {record['elapsed_time']:.2f}s"
        )
        
        self.btn_export_pdf.setEnabled(True)
        self.inspection_completed.emit()
        self.tab_widget.setCurrentIndex(0)

    @Slot(str)
    def on_detection_error(self, err):
        self.btn_run.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.txt_status.append(f"Error: {err}")
        self.lbl_summary.setText(f"Run Status: FAILED\nReason: {err}")
        
        InfoBar.error(
            title="Inference Error",
            content=err,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

    def on_crack_selected(self):
        selected_ranges = self.table_cracks.selectedRanges()
        if not selected_ranges or self.view_model.latest_result is None:
            return
            
        row = selected_ranges[0].topRow()
        boxes = self.view_model.latest_result.get("bounding_boxes", [])
        if row < len(boxes):
            box = boxes[row]
            padding = 50
            x1 = max(0, box[0] - padding)
            y1 = max(0, box[1] - padding)
            x2 = box[2] + padding
            y2 = box[3] + padding
            
            self.tab_widget.setCurrentIndex(0)
            self.viewer_vis.fitInView(QRectF(x1, y1, x2 - x1, y2 - y1), Qt.AspectRatioMode.KeepAspectRatio)

    def export_report(self):
        if not self.view_model.latest_record:
            return
            
        default_name = f"inspection_report_{self.view_model.latest_record['id'][:8]}.pdf"
        output_pdf_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Inspection Report",
            os.path.join(self.view_model.get_default_reports_dir(), default_name),
            "PDF Files (*.pdf)"
        )
        
        if output_pdf_path:
            self.txt_status.append("Generating PDF report...")
            self.view_model.export_report(output_pdf_path)

    @Slot(str)
    def on_report_exported(self, path):
        self.txt_status.append(f"PDF Report saved successfully at:\n{path}")
        self.inspection_completed.emit()
        InfoBar.success(
            title="Report Saved",
            content=f"Report PDF written successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    @Slot(str)
    def on_report_export_failed(self, msg):
        self.txt_status.append(f"Error: {msg}")
        InfoBar.error(
            title="Export Failed",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )
