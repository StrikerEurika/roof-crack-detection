import os
import time
from PIL import Image
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QGroupBox, QSlider, QCheckBox, QComboBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QProgressBar, QTextEdit
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal, Slot
from src.workers import BatchWorker

class BatchView(QWidget):
    """View widget for folder-level batch roof crack detection."""
    
    batch_completed = Signal() # Emitted when batch finishes and history is updated

    def __init__(self, history_manager, model_cache, parent=None):
        super().__init__(parent)
        self.hm = history_manager
        self.model_cache = model_cache
        self.active_worker = None
        self.input_dir = None
        self.output_dir = None
        
        # Stylesheet (Consistent with dark theme)
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
                background-color: #000080; /* navy indicator for progress */
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
                border-radius: 0px;
                color: #000000;
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

        # 2. Right Display Panel (Queue list and progress logs)
        self.setup_queue_panel()

    def setup_control_panel(self):
        self.panel_left = QWidget()
        self.panel_left.setFixedWidth(300)
        left_layout = QVBoxLayout(self.panel_left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Group 1: Source & Output Directory
        group_folders = QGroupBox("1. Setup Folders")
        folders_layout = QVBoxLayout(group_folders)
        
        self.btn_select_input = QPushButton("📁 Input Images Folder...")
        self.btn_select_input.setProperty("class", "secondaryBtn")
        self.btn_select_input.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_input.clicked.connect(self.select_input_dir)
        folders_layout.addWidget(self.btn_select_input)

        self.lbl_input_dir = QLabel("No input directory selected")
        self.lbl_input_dir.setWordWrap(True)
        self.lbl_input_dir.setStyleSheet("color: #404040; font-style: italic;")
        folders_layout.addWidget(self.lbl_input_dir)

        self.btn_select_output = QPushButton("📁 Output Results Folder...")
        self.btn_select_output.setProperty("class", "secondaryBtn")
        self.btn_select_output.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_output.clicked.connect(self.select_output_dir)
        folders_layout.addWidget(self.btn_select_output)

        self.lbl_output_dir = QLabel("No output directory selected")
        self.lbl_output_dir.setWordWrap(True)
        self.lbl_output_dir.setStyleSheet("color: #404040; font-style: italic;")
        folders_layout.addWidget(self.lbl_output_dir)

        # Group 2: Model Configuration
        group_model = QGroupBox("2. Model & Batch Settings")
        model_layout = QVBoxLayout(group_model)
        
        model_layout.addWidget(QLabel("Pre-trained Model Zoo:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Seg_UNET_CFD_actual_v2", "Seg_UNET_CFD_actual_v1", "Det_YOLOv26n-seg_crack-dataset_v1"])
        self.combo_model.setCurrentText(self.hm.config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        model_layout.addWidget(self.combo_model)
        
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

        self.chk_clahe = QCheckBox("Apply CLAHE Preprocessing")
        self.chk_clahe.setChecked(self.hm.config.get("use_clahe", True))
        model_layout.addWidget(self.chk_clahe)
        
        self.chk_tta = QCheckBox("Use Test-Time Augmentation (TTA)")
        self.chk_tta.setChecked(self.hm.config.get("use_tta", False))
        model_layout.addWidget(self.chk_tta)

        # Action Buttons
        self.btn_start = QPushButton("⚡ START BATCH INSPECTION")
        self.btn_start.setProperty("class", "primaryBtn")
        self.btn_start.setStyleSheet("background-color: #d4d0c8; color: #000000; border-top: 1.5px solid #ffffff; border-left: 1.5px solid #ffffff; border-right: 1.5px solid #808080; border-bottom: 1.5px solid #808080; font-weight: bold;") # green
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_batch)

        self.btn_cancel = QPushButton("🛑 CANCEL BATCH")
        self.btn_cancel.setProperty("class", "primaryBtn")
        self.btn_cancel.setStyleSheet("background-color: #d4d0c8; color: #000000; border-top: 1.5px solid #ffffff; border-left: 1.5px solid #ffffff; border-right: 1.5px solid #808080; border-bottom: 1.5px solid #808080; font-weight: bold;") # red
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_batch)

        left_layout.addWidget(group_folders)
        left_layout.addWidget(group_model)
        left_layout.addWidget(self.btn_start)
        left_layout.addWidget(self.btn_cancel)
        left_layout.addStretch()

        self.layout.addWidget(self.panel_left)

    def setup_queue_panel(self):
        self.panel_right = QWidget()
        right_layout = QVBoxLayout(self.panel_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Header Details
        lbl_queue_title = QLabel("Batch Execution Progress")
        lbl_queue_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #000000;")
        right_layout.addWidget(lbl_queue_title)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v/%m files completed (%p%)")
        right_layout.addWidget(self.progress_bar)

        # Table showing active process queue
        self.table_queue = QTableWidget()
        self.table_queue.setColumnCount(6)
        self.table_queue.setHorizontalHeaderLabels(["Index", "Filename", "Cracks Detected", "Count", "Max Conf", "Status"])
        self.table_queue.verticalHeader().setVisible(False)
        self.table_queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_queue.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        header = self.table_queue.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        right_layout.addWidget(self.table_queue, stretch=3)

        # Log details
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #ffffff; border-top: 2px solid #808080; border-left: 2px solid #808080; border-right: 2px solid #ffffff; border-bottom: 2px solid #ffffff; color: #000000; font-size: 11px;")
        self.txt_log.setPlaceholderText("Logs will be shown here during batch processing.")
        self.txt_log.setMaximumHeight(150)
        right_layout.addWidget(self.txt_log, stretch=1)

        self.layout.addWidget(self.panel_right)

    def on_thresh_changed(self, value):
        self.lbl_thresh.setText(f"Confidence Threshold: {value / 100:.2f}")

    def select_input_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Folder of Roof Images")
        if dir_path:
            self.input_dir = dir_path
            self.lbl_input_dir.setText(dir_path)
            self.lbl_input_dir.setToolTip(dir_path)
            
            # Default output folder: input_folder_results
            if not self.output_dir:
                self.output_dir = os.path.join(dir_path, "results")
                self.lbl_output_dir.setText(self.output_dir)
                self.lbl_output_dir.setToolTip(self.output_dir)
                
            self.check_ready_state()

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder for Results")
        if dir_path:
            self.output_dir = dir_path
            self.lbl_output_dir.setText(dir_path)
            self.lbl_output_dir.setToolTip(dir_path)
            self.check_ready_state()

    def check_ready_state(self):
        if self.input_dir and self.output_dir:
            self.btn_start.setEnabled(True)
            self.txt_log.setText("Ready to start batch. Configured directories correctly.")
        else:
            self.btn_start.setEnabled(False)

    def start_batch(self):
        if not self.input_dir or not self.output_dir:
            return

        pipeline_config = {
            "model_variant": self.combo_model.currentText(),
            "device": self.combo_device.currentText(),
            "confidence_threshold": self.slider_thresh.value() / 100.0,
            "patch_size": int(self.hm.config.get("patch_size", 512)),
            "overlap_ratio": float(self.hm.config.get("overlap_ratio", 0.2)),
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

        # Clear UI components
        self.table_queue.setRowCount(0)
        self.txt_log.clear()
        self.progress_bar.setValue(0)
        
        # Toggle buttons
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_select_input.setEnabled(False)
        self.btn_select_output.setEnabled(False)

        # Start background thread
        self.active_worker = BatchWorker(pipeline_config, self.input_dir, self.output_dir, self.model_cache)
        self.active_worker.started_signal.connect(self.on_batch_started)
        self.active_worker.progress_signal.connect(self.on_batch_progress)
        self.active_worker.file_completed_signal.connect(self.on_file_completed)
        self.active_worker.finished_signal.connect(self.on_batch_finished)
        self.active_worker.error_signal.connect(self.on_batch_error)
        self.active_worker.cancelled_signal.connect(self.on_batch_cancelled)
        self.active_worker.start()

    def cancel_batch(self):
        if self.active_worker:
            self.txt_log.append("Cancellation requested. Stopping thread...")
            self.active_worker.cancel()
            self.btn_cancel.setEnabled(False)

    @Slot()
    def on_batch_started(self):
        self.txt_log.append("Batch process starting...")

    @Slot(int, int, str)
    def on_batch_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.txt_log.append(msg)

    @Slot(dict)
    def on_file_completed(self, result):
        filename = result["filename"]
        row_idx = self.table_queue.rowCount()
        self.table_queue.insertRow(row_idx)

        # Index
        self.table_queue.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
        
        # Filename
        fn_item = QTableWidgetItem(filename)
        fn_item.setToolTip(result["image_path"])
        self.table_queue.setItem(row_idx, 1, fn_item)

        # If file failed with exception
        if "error" in result:
            self.table_queue.setItem(row_idx, 2, QTableWidgetItem("N/A"))
            self.table_queue.setItem(row_idx, 3, QTableWidgetItem("0"))
            self.table_queue.setItem(row_idx, 4, QTableWidgetItem("0.0%"))
            status_item = QTableWidgetItem("FAILED")
            status_item.setForeground(QColor("#f43f5e"))
            self.table_queue.setItem(row_idx, 5, status_item)
            return

        # Crack detected
        crack_detected = result["crack_detected"]
        crack_count = result["crack_count"]
        max_conf = result["max_confidence"]
        
        status_widget = QLabel()
        status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if crack_detected:
            status_widget.setText("⚠️ YES")
            status_widget.setStyleSheet("color: #dc2626; font-weight: bold; background: transparent;")
        else:
            status_widget.setText("✅ NONE")
            status_widget.setStyleSheet("color: #16a34a; font-weight: bold; background: transparent;")
        self.table_queue.setCellWidget(row_idx, 2, status_widget)

        # Crack count
        self.table_queue.setItem(row_idx, 3, QTableWidgetItem(str(crack_count)))

        # Max conf
        self.table_queue.setItem(row_idx, 4, QTableWidgetItem(f"{max_conf*100:.1f}%"))

        # Status
        status_item = QTableWidgetItem("DONE")
        status_item.setForeground(QColor("#10b981"))
        self.table_queue.setItem(row_idx, 5, status_item)

        # Save result assets to the app's global assets folder so it is visible in Recents history!
        results_obj = result.get("results_object")
        if results_obj:
            # We copy / save the results inside the application results directory
            base_name, _ = os.path.splitext(filename)
            timestamp_slug = int(time.time())
            
            vis_filename = f"{base_name}_vis_{timestamp_slug}.png"
            mask_filename = f"{base_name}_mask_{timestamp_slug}.png"
            
            vis_output_path = os.path.join(self.hm.results_dir, vis_filename)
            mask_output_path = os.path.join(self.hm.results_dir, mask_filename)
            
            try:
                Image.fromarray(results_obj["visualization"]).save(vis_output_path)
                Image.fromarray(results_obj["binary_mask"]).save(mask_output_path)
                
                # Save also to user configured batch output directory
                user_vis_path = os.path.join(self.output_dir, f"{base_name}_overlay.png")
                user_mask_path = os.path.join(self.output_dir, f"{base_name}_mask.png")
                Image.fromarray(results_obj["visualization"]).save(user_vis_path)
                Image.fromarray(results_obj["binary_mask"]).save(user_mask_path)
                
                # Add historical entry
                self.hm.add_record(
                    image_path=result["image_path"],
                    crack_detected=crack_detected,
                    confidence=max_conf,
                    crack_count=crack_count,
                    model_used=self.combo_model.currentText(),
                    vis_image_path=vis_output_path,
                    mask_image_path=mask_output_path,
                    elapsed_time=result["elapsed_time"]
                )
            except Exception as e:
                self.txt_log.append(f"Warning: Failed to save result copies: {e}")

        # Scroll to bottom of table
        self.table_queue.scrollToBottom()

    @Slot(list)
    def on_batch_finished(self, summary_list):
        self.txt_log.append("\n=== Batch processing completed ===")
        total = len(summary_list)
        cracked = sum(1 for r in summary_list if r.get("crack_detected", False))
        failed = sum(1 for r in summary_list if "error" in r)
        self.txt_log.append(f"Total processed: {total}")
        self.txt_log.append(f"Cracks detected: {cracked} ({cracked/total*100:.1f}%)")
        if failed > 0:
            self.txt_log.append(f"Failures: {failed}")
            
        self.cleanup_batch_run()
        self.batch_completed.emit()

    @Slot(str)
    def on_batch_error(self, err):
        self.txt_log.append(f"\nCRITICAL ERROR: {err}")
        self.cleanup_batch_run()

    @Slot()
    def on_batch_cancelled(self):
        self.txt_log.append("\nBatch execution was cancelled by user.")
        self.cleanup_batch_run()
        self.batch_completed.emit()

    def cleanup_batch_run(self):
        self.active_worker = None
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_select_input.setEnabled(True)
        self.btn_select_output.setEnabled(True)
        # Update progress bar fully
        self.progress_bar.setValue(self.progress_bar.maximum())
