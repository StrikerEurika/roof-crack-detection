import os
import time
from PIL import Image
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QTabWidget, QGroupBox, QSlider, QCheckBox, 
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QProgressBar, QTextEdit
)
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt, Signal, Slot, QRectF
from .components import ImageViewer
from src.workers import InferenceWorker
from src.reports import PDFReportGenerator

class InspectionView(QWidget):
    """View widget for analyzing a single image and viewing results."""
    
    inspection_completed = Signal() # Emitted when a new inspection is saved to history

    def __init__(self, history_manager, model_cache, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.model_cache = model_cache
        self.active_worker = None
        self.current_image_path = None
        self.latest_result = None
        self.latest_record = None

        # Style Sheets
        self.setStyleSheet("""
            QWidget {
                background-color: #d4d0c8;
                color: #000000;
                font-family: 'Tahoma', 'MS Sans Serif', Arial, sans-serif;
                font-size: 11px;
            }
            QGroupBox {
                border: 2px solid;
                border-top-color: #808080;
                border-left-color: #808080;
                border-right-color: #ffffff;
                border-bottom-color: #ffffff;
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
                color: #000000;
                border-radius: 0px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QLabel {
                font-size: 11px;
                color: #000000;
            }
            QComboBox, QSlider {
                background-color: #ffffff;
                border-top: 2px solid #808080;
                border-left: 2px solid #808080;
                border-right: 2px solid #ffffff;
                border-bottom: 2px solid #ffffff;
                border-radius: 0px;
                padding: 3px;
                color: #000000;
            }
            QPushButton.primaryBtn {
                background-color: #d4d0c8;
                color: #000000;
                border-top: 1.5px solid #ffffff;
                border-left: 1.5px solid #ffffff;
                border-right: 1.5px solid #808080;
                border-bottom: 1.5px solid #808080;
                border-radius: 0px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton.primaryBtn:hover {
                background-color: #e0ded9;
            }
            QPushButton.primaryBtn:pressed {
                border-top: 1.5px solid #808080;
                border-left: 1.5px solid #808080;
                border-right: 1.5px solid #ffffff;
                border-bottom: 1.5px solid #ffffff;
                padding-top: 9px;
                padding-left: 13px;
                padding-bottom: 7px;
                padding-right: 11px;
            }
            QPushButton.primaryBtn:disabled {
                background-color: #d4d0c8;
                color: #808080;
                border-top: 1.5px solid #ffffff;
                border-left: 1.5px solid #ffffff;
                border-right: 1.5px solid #808080;
                border-bottom: 1.5px solid #808080;
            }
            QPushButton.secondaryBtn {
                background-color: #d4d0c8;
                color: #000000;
                border-top: 1.5px solid #ffffff;
                border-left: 1.5px solid #ffffff;
                border-right: 1.5px solid #808080;
                border-bottom: 1.5px solid #808080;
                border-radius: 0px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton.secondaryBtn:hover {
                background-color: #e0ded9;
            }
            QPushButton.secondaryBtn:pressed {
                border-top: 1.5px solid #808080;
                border-left: 1.5px solid #808080;
                border-right: 1.5px solid #ffffff;
                border-bottom: 1.5px solid #ffffff;
                padding-top: 7px;
                padding-left: 13px;
                padding-bottom: 5px;
                padding-right: 11px;
            }
            QTabWidget::panel {
                border-top: 2px solid #ffffff;
                border-left: 2px solid #ffffff;
                border-right: 2px solid #808080;
                border-bottom: 2px solid #808080;
                background-color: #d4d0c8;
                border-radius: 0px;
            }
            QTabBar::tab {
                background-color: #d4d0c8;
                border-top: 2px solid #ffffff;
                border-left: 2px solid #ffffff;
                border-right: 2px solid #808080;
                border-bottom: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                padding: 5px 10px;
                margin-right: 2px;
                color: #000000;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #d4d0c8;
                margin-top: -2px;
                border-bottom: none;
            }
            QProgressBar {
                border-top: 2px solid #808080;
                border-left: 2px solid #808080;
                border-right: 2px solid #ffffff;
                border-bottom: 2px solid #ffffff;
                background-color: #ffffff;
                text-align: center;
                color: #000000;
                font-weight: bold;
                border-radius: 0px;
            }
            QProgressBar::chunk {
                background-color: #000080;
                width: 8px;
                margin: 0.5px;
                border-radius: 0px;
            }
            QTableWidget {
                background-color: #ffffff;
                border-top: 2px solid #808080;
                border-left: 2px solid #808080;
                border-right: 2px solid #ffffff;
                border-bottom: 2px solid #ffffff;
                gridline-color: #d4d0c8;
                color: #000000;
                border-radius: 0px;
            }
            QTableWidget::item {
                border-bottom: 1px solid #d4d0c8;
            }
            QHeaderView::section {
                background-color: #d4d0c8;
                color: #000000;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #808080;
                border-bottom: 1px solid #808080;
                padding: 3px;
                font-weight: bold;
            }
        """)

        # Main horizontal layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)

        # 1. Left Control Panel
        self.setup_control_panel()

        # 2. Right Display Panel
        self.setup_display_panel()

    def setup_control_panel(self):
        self.panel_left = QWidget()
        self.panel_left.setFixedWidth(300)
        left_layout = QVBoxLayout(self.panel_left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Group 1: Image Source Selection
        group_source = QGroupBox("1. Select Target Roof Image")
        source_layout = QVBoxLayout(group_source)
        
        self.btn_select_file = QPushButton("📁 Browse Image File...")
        self.btn_select_file.setProperty("class", "secondaryBtn")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.clicked.connect(self.select_file)
        source_layout.addWidget(self.btn_select_file)

        self.lbl_filename = QLabel("No image file loaded")
        self.lbl_filename.setWordWrap(True)
        self.lbl_filename.setStyleSheet("color: #404040; font-style: italic;")
        source_layout.addWidget(self.lbl_filename)
        
        # Group 2: Model Configuration
        group_model = QGroupBox("2. Model & Inference Settings")
        model_layout = QVBoxLayout(group_model)
        
        # Model selector
        model_layout.addWidget(QLabel("Pre-trained Model Zoo:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Seg_UNET_CFD_actual_v2", "Seg_UNET_CFD_actual_v1", "Det_YOLOv26n-seg_crack-dataset_v1"])
        # Set default from config
        self.combo_model.setCurrentText(self.hm.config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        model_layout.addWidget(self.combo_model)
        
        # Device selector
        model_layout.addWidget(QLabel("Compute Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cuda", "cpu"])
        # Check GPU availability dynamically without requiring torch at startup
        has_gpu = False
        try:
            import onnxruntime as ort
            has_gpu = any("CUDA" in p for p in ort.get_available_providers())
        except ImportError:
            try:
                import torch
                has_gpu = torch.cuda.is_available()
            except ImportError:
                pass
                
        if not has_gpu:
            self.combo_device.setCurrentText("cpu")
        else:
            self.combo_device.setCurrentText(self.hm.config.get("device", "cuda"))
        model_layout.addWidget(self.combo_device)

        # Threshold slider
        self.lbl_thresh = QLabel(f"Confidence Threshold: {self.hm.config.get('confidence_threshold', 0.5):.2f}")
        model_layout.addWidget(self.lbl_thresh)
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setRange(10, 90)
        self.slider_thresh.setValue(int(self.hm.config.get("confidence_threshold", 0.5) * 100))
        self.slider_thresh.valueChanged.connect(self.on_thresh_changed)
        model_layout.addWidget(self.slider_thresh)

        # Patch size
        model_layout.addWidget(QLabel("Sliding Window Patch Size:"))
        self.combo_patch = QComboBox()
        self.combo_patch.addItems(["256", "512", "1024"])
        self.combo_patch.setCurrentText(str(self.hm.config.get("patch_size", 512)))
        model_layout.addWidget(self.combo_patch)

        # Overlap ratio
        self.lbl_overlap = QLabel(f"Patch Overlap Ratio: {self.hm.config.get('overlap_ratio', 0.2):.2f}")
        model_layout.addWidget(self.lbl_overlap)
        self.slider_overlap = QSlider(Qt.Orientation.Horizontal)
        self.slider_overlap.setRange(0, 50)
        self.slider_overlap.setValue(int(self.hm.config.get("overlap_ratio", 0.2) * 100))
        self.slider_overlap.valueChanged.connect(self.on_overlap_changed)
        model_layout.addWidget(self.slider_overlap)

        # Checkboxes
        self.chk_clahe = QCheckBox("Apply CLAHE Preprocessing")
        self.chk_clahe.setChecked(self.hm.config.get("use_clahe", True))
        model_layout.addWidget(self.chk_clahe)
        
        self.chk_tta = QCheckBox("Use Test-Time Augmentation (TTA)")
        self.chk_tta.setChecked(self.hm.config.get("use_tta", False))
        model_layout.addWidget(self.chk_tta)

        # Run Action
        self.btn_run = QPushButton("⚡ RUN DETECTOR")
        self.btn_run.setProperty("class", "primaryBtn")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.run_detection)

        # Log details
        self.txt_status = QTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setMaximumHeight(80)
        self.txt_status.setStyleSheet("background-color: #ffffff; border-top: 2px solid #808080; border-left: 2px solid #808080; border-right: 2px solid #ffffff; border-bottom: 2px solid #ffffff; color: #000000; font-size: 11px;")
        self.txt_status.setText("Load a roof image file to begin analysis.")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        left_layout.addWidget(group_source)
        left_layout.addWidget(group_model)
        left_layout.addWidget(self.btn_run)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.txt_status)
        left_layout.addStretch()

        self.layout.addWidget(self.panel_left)

    def setup_display_panel(self):
        self.panel_right = QWidget()
        right_layout = QVBoxLayout(self.panel_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Tabs for Image Views
        self.tab_widget = QTabWidget()
        
        # 1. Visualization tab
        self.viewer_vis = ImageViewer()
        self.viewer_vis.image_dropped.connect(self.on_image_dropped)
        self.tab_widget.addTab(self.viewer_vis, "🔍 Visualization Overlay")
        
        # 2. Original tab
        self.viewer_orig = ImageViewer()
        self.tab_widget.addTab(self.viewer_orig, "Original Image")
        
        # 3. Transparent Overlay tab
        self.viewer_overlay = ImageViewer()
        self.tab_widget.addTab(self.viewer_overlay, "Crack Overlay")

        # 4. Binary Mask tab
        self.viewer_mask = ImageViewer()
        self.tab_widget.addTab(self.viewer_mask, "Binary Mask")

        # 5. Confidence Map tab
        self.viewer_conf = ImageViewer()
        self.tab_widget.addTab(self.viewer_conf, "Confidence Heatmap")

        right_layout.addWidget(self.tab_widget, stretch=4)

        # Bottom Area: Results Table & Actions
        results_layout = QHBoxLayout()
        results_layout.setSpacing(15)

        # Results table
        table_container = QVBoxLayout()
        lbl_results_title = QLabel("Detected Crack Components")
        lbl_results_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #000000;")
        table_container.addWidget(lbl_results_title)
        
        self.table_cracks = QTableWidget()
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
        actions_container = QVBoxLayout()
        actions_container.setSpacing(10)
        actions_container.addStretch()

        self.btn_export_pdf = QPushButton("📄 Export PDF Inspection Report")
        self.btn_export_pdf.setProperty("class", "primaryBtn")
        self.btn_export_pdf.setStyleSheet("background-color: #d4d0c8; color: #000000; border-top: 1.5px solid #ffffff; border-left: 1.5px solid #ffffff; border-right: 1.5px solid #808080; border-bottom: 1.5px solid #808080; font-weight: bold;") # Green accent
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self.export_report)
        actions_container.addWidget(self.btn_export_pdf)

        self.lbl_summary = QLabel("Run Status: No current inspection.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #000000; font-size: 11px;")
        actions_container.addWidget(self.lbl_summary)
        
        results_layout.addLayout(actions_container, stretch=1)
        
        right_layout.addLayout(results_layout, stretch=1)

        self.layout.addWidget(self.panel_right)

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
            self.load_image(file_path)

    def on_image_dropped(self, file_path):
        self.load_image(file_path)

    def load_image(self, file_path):
        self.current_image_path = file_path
        self.lbl_filename.setText(os.path.basename(file_path))
        self.lbl_filename.setToolTip(file_path)
        
        # Load and show original image in viewer
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
            self.latest_result = None
            self.latest_record = None
            self.table_cracks.setRowCount(0)
            self.lbl_summary.setText("Image loaded. Press '⚡ RUN DETECTOR' to begin analysis.")
            self.txt_status.setText(f"Loaded file: {file_path}\nReady to run detection.")
            self.tab_widget.setCurrentIndex(0) # show visualization tab

    def load_historical_record(self, record):
        """Loads a historical inspection record details directly into the UI."""
        self.current_image_path = record.get("image_path")
        self.lbl_filename.setText(record.get("image_name", "N/A"))
        self.lbl_filename.setToolTip(self.current_image_path)
        
        self.latest_record = record
        self.btn_run.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        
        # Load the images
        if os.path.exists(self.current_image_path):
            self.viewer_orig.set_image(QPixmap(self.current_image_path))
            
        vis_path = record.get("vis_image_path")
        if vis_path and os.path.exists(vis_path):
            self.viewer_vis.set_image(QPixmap(vis_path))
            self.viewer_overlay.set_image(QPixmap(vis_path)) # Show visualization as overlay fallback
            
        mask_path = record.get("mask_image_path")
        if mask_path and os.path.exists(mask_path):
            self.viewer_mask.set_image(QPixmap(mask_path))
            
        # Re-populate detected cracks table if bounding boxes exist
        # We don't store boxes in history JSON explicitly, but we could if we wanted to.
        # Let's see: we can populate it if they are available, or parse from a record.
        self.table_cracks.setRowCount(0)
        self.lbl_summary.setText(f"Loaded history run: {record.get('model_used')}.\nCracks detected: {record.get('crack_count')}.")
        self.txt_status.setText(f"Loaded historical record from {record.get('timestamp')}")
        self.tab_widget.setCurrentIndex(0)

    def run_detection(self):
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.txt_status.setText("Error: Load a valid image first.")
            return

        # Prepare config
        pipeline_config = {
            "model_variant": self.combo_model.currentText(),
            "device": self.combo_device.currentText(),
            "confidence_threshold": self.slider_thresh.value() / 100.0,
            "patch_size": int(self.combo_patch.currentText()),
            "overlap_ratio": self.slider_overlap.value() / 100.0,
            "use_tta": self.chk_tta.isChecked(),
            "use_clahe": self.chk_clahe.isChecked(),
            "clahe_clip_limit": 2.0,
            "overlay_alpha": self.hm.config.get("overlay_alpha", 0.4),
            "overlay_color": self.hm.config.get("overlay_color", [255, 0, 0]),
            "box_color": self.hm.config.get("box_color", [0, 255, 0]),
            "box_thickness": self.hm.config.get("box_thickness", 2),
            "contour_color": self.hm.config.get("contour_color", [0, 0, 255]),
            "contour_thickness": self.hm.config.get("contour_thickness", 2)
        }

        # Setup worker thread
        self.btn_run.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # indeterminate spinner style
        
        self.active_worker = InferenceWorker(pipeline_config, self.current_image_path, self.model_cache)
        self.active_worker.progress_signal.connect(self.on_worker_progress)
        self.active_worker.finished_signal.connect(self.on_worker_finished)
        self.active_worker.error_signal.connect(self.on_worker_error)
        self.active_worker.start()

    @Slot(str)
    def on_worker_progress(self, msg):
        self.txt_status.append(msg)

    @Slot(dict)
    def on_worker_finished(self, results):
        self.latest_result = results
        self.btn_run.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Display images in other tabs
        self.viewer_orig.set_ndarray_image(results["original_image"])
        self.viewer_vis.set_ndarray_image(results["visualization"])
        self.viewer_overlay.set_ndarray_image(results["overlay"])
        self.viewer_mask.set_ndarray_image(results["binary_mask"])
        
        # Confidence map is grayscale [0.0 - 1.0]. Convert to grayscale display
        conf_map = (results["confidence_map"] * 255).astype("uint8")
        # Build 3D array for view
        conf_rgb = np.stack([conf_map, conf_map, conf_map], axis=-1)
        self.viewer_conf.set_ndarray_image(conf_rgb)
        
        # Save output images to assets/results folder
        image_name = os.path.basename(self.current_image_path)
        base_name, _ = os.path.splitext(image_name)
        timestamp_slug = int(time.time())
        
        vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
        mask_filename = f"{base_name}_mask_{timestamp_slug}.png"
        
        vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
        mask_output_path = os.path.join(self.hm.results_dir, mask_filename)
        
        try:
            Image.fromarray(results["visualization"]).save(vis_output_path)
            Image.fromarray(results["binary_mask"]).save(mask_output_path)
        except Exception as e:
            self.txt_status.append(f"Warning: Failed to save result assets: {e}")

        # Update History database
        crack_count = len(results["bounding_boxes"])
        crack_detected = crack_count > 0
        max_conf = float(results["confidence_map"].max()) if results["confidence_map"].size > 0 else 0.0
        
        self.latest_record = self.hm.add_record(
            image_path=self.current_image_path,
            crack_detected=crack_detected,
            confidence=max_conf,
            crack_count=crack_count,
            model_used=results["model_used"],
            vis_image_path=vis_output_path,
            mask_image_path=mask_output_path,
            elapsed_time=results["elapsed_time"]
        )
        
        # Populate table of cracks
        self.table_cracks.setRowCount(0)
        self.table_cracks.setRowCount(len(results["bounding_boxes"]))
        
        for idx, box in enumerate(results["bounding_boxes"]):
            # Index
            idx_item = QTableWidgetItem(str(idx + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cracks.setItem(idx, 0, idx_item)
            
            # Bounding box coords
            coords = f"[{box[0]}, {box[1]}, {box[2]}, {box[3]}]"
            coords_item = QTableWidgetItem(coords)
            coords_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cracks.setItem(idx, 1, coords_item)
            
            # Estimated Area/Severity
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
            # Style severity column
            if severity == "Critical":
                sev_item.setForeground(QColor("#f43f5e"))
            elif severity == "Medium":
                sev_item.setForeground(QColor("#f59e0b"))
            else:
                sev_item.setForeground(QColor("#10b981"))
            self.table_cracks.setItem(idx, 2, sev_item)

        # Update Summary
        status_msg = "CRITICAL ACTION REQUIRED" if crack_detected else "ROOF SAFE / CLEAR"
        self.lbl_summary.setText(
            f"Run Status: COMPLETED\n"
            f"Result: {status_msg}\n"
            f"Crack count: {crack_count}\n"
            f"Time elapsed: {results['elapsed_time']:.2f}s"
        )
        
        self.btn_export_pdf.setEnabled(True)
        self.inspection_completed.emit()
        self.tab_widget.setCurrentIndex(0) # show overlay visualization
        
    @Slot(str)
    def on_worker_error(self, err):
        self.btn_run.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.txt_status.append(f"Error: {err}")
        self.lbl_summary.setText(f"Run Status: FAILED\nReason: {err}")

    def on_crack_selected(self):
        """Highlights and zooms the ImageViewer to the selected crack component."""
        selected_ranges = self.table_cracks.selectedRanges()
        if not selected_ranges or self.latest_result is None:
            return
            
        row = selected_ranges[0].topRow()
        boxes = self.latest_result.get("bounding_boxes", [])
        if row < len(boxes):
            box = boxes[row]
            # Zoom to box in visualization viewer
            # Pad the view area slightly for context
            padding = 50
            x1 = max(0, box[0] - padding)
            y1 = max(0, box[1] - padding)
            x2 = box[2] + padding
            y2 = box[3] + padding
            
            # Switch to visualization tab first
            self.tab_widget.setCurrentIndex(0)
            self.viewer_vis.fitInView(QRectF(x1, y1, x2 - x1, y2 - y1), Qt.AspectRatioMode.KeepAspectRatio)

    def export_report(self):
        if not self.latest_record:
            return
            
        default_name = f"inspection_report_{self.latest_record['id'][:8]}.pdf"
        output_pdf_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Inspection Report",
            os.path.join(self.hm.reports_dir, default_name),
            "PDF Files (*.pdf)"
        )
        
        if output_pdf_path:
            self.txt_status.append("Generating PDF report...")
            success = PDFReportGenerator.generate_report(self.latest_record, output_pdf_path)
            if success:
                self.hm.update_report_path(self.latest_record["id"], output_pdf_path)
                self.txt_status.append(f"PDF Report saved successfully at:\n{output_pdf_path}")
                self.inspection_completed.emit()
            else:
                self.txt_status.append("Error: Failed to generate PDF report.")
