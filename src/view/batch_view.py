""" Context:
- What: The BatchView class is a QWidget that provides a user interface for performing batch roof crack detection on multiple images from a folder.
- Path: src/view/batch_view.py
"""


import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QHeaderView, QAbstractItemView, QTableWidgetItem, QLabel
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal, Slot

from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, SubtitleLabel, TitleLabel, CaptionLabel,
    ComboBox, Slider, CheckBox, PushButton, PrimaryPushButton,
    ProgressBar, TextEdit, TableWidget, FluentIcon as FIF,
    InfoBar, InfoBarPosition
)

from src.view_model import BatchViewModel
from src import check_gpu_available, get_available_model_variants, resolve_model_variant

class BatchView(QWidget):
    """View widget for folder-level batch roof crack detection, refactored to use BatchViewModel."""
    
    batch_completed = Signal() # Emitted when batch finishes and history is updated

    def __init__(self, view_model: BatchViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        # Main horizontal layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)

        # 1. Left Control Panel
        self.setup_control_panel()

        # 2. Right Display Panel
        self.setup_queue_panel()

        # Bind ViewModel signals
        self.connect_view_model()

        # Load configurations defaults
        self.load_settings_defaults()

    def setup_control_panel(self):
        self.panel_left = QWidget(self)
        self.panel_left.setFixedWidth(300)
        left_layout = QVBoxLayout(self.panel_left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # Card 1: Folder selection
        self.card_folders = SimpleCardWidget(self.panel_left)
        folders_layout = QVBoxLayout(self.card_folders)
        folders_layout.setSpacing(8)
        
        folders_title = SubtitleLabel("1. Setup Folders", self.card_folders)
        folders_layout.addWidget(folders_title)
        
        self.btn_select_input = PushButton(FIF.FOLDER, "Input Folder...", self.card_folders)
        self.btn_select_input.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_input.clicked.connect(self.select_input_dir)
        folders_layout.addWidget(self.btn_select_input)

        self.lbl_input_dir = BodyLabel("No input directory selected", self.card_folders)
        self.lbl_input_dir.setWordWrap(True)
        self.lbl_input_dir.setStyleSheet("color: #606060; font-style: italic;")
        folders_layout.addWidget(self.lbl_input_dir)

        self.btn_select_output = PushButton(FIF.FOLDER, "Output Folder...", self.card_folders)
        self.btn_select_output.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_output.clicked.connect(self.select_output_dir)
        folders_layout.addWidget(self.btn_select_output)

        self.lbl_output_dir = BodyLabel("No output directory selected", self.card_folders)
        self.lbl_output_dir.setWordWrap(True)
        self.lbl_output_dir.setStyleSheet("color: #606060; font-style: italic;")
        folders_layout.addWidget(self.lbl_output_dir)

        left_layout.addWidget(self.card_folders)

        # Card 2: Model Configuration
        self.card_model = SimpleCardWidget(self.panel_left)
        model_layout = QVBoxLayout(self.card_model)
        model_layout.setSpacing(10)
        
        model_title = SubtitleLabel("2. Batch Settings", self.card_model)
        model_layout.addWidget(model_title)
        
        model_layout.addWidget(BodyLabel("Pre-trained Model Zoo:", self.card_model))
        self.combo_model = ComboBox(self.card_model)
        self.rebuild_model_combo()
        self.combo_model.currentIndexChanged.connect(self.on_model_selection_changed)
        model_layout.addWidget(self.combo_model)
        
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

        self.chk_clahe = CheckBox("Apply CLAHE Preprocessing", self.card_model)
        model_layout.addWidget(self.chk_clahe)
        
        self.chk_tta = CheckBox("Use Test-Time Augmentation", self.card_model)
        model_layout.addWidget(self.chk_tta)

        left_layout.addWidget(self.card_model)

        # Action Buttons
        self.btn_start = PrimaryPushButton("START BATCH INSPECTION", self.panel_left)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_batch)
        left_layout.addWidget(self.btn_start)

        self.btn_cancel = PushButton(FIF.CLOSE, "CANCEL BATCH", self.panel_left)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_batch)
        left_layout.addWidget(self.btn_cancel)
        left_layout.addStretch()

        self.layout.addWidget(self.panel_left)

    def setup_queue_panel(self):
        self.panel_right = QWidget(self)
        right_layout = QVBoxLayout(self.panel_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Header Details
        lbl_queue_title = SubtitleLabel("Batch Execution Progress", self.panel_right)
        right_layout.addWidget(lbl_queue_title)

        # Progress bar
        self.progress_bar = ProgressBar(self.panel_right)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v/%m files completed (%p%)")
        right_layout.addWidget(self.progress_bar)

        # Table showing active process queue
        self.table_queue = TableWidget(self.panel_right)
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
        self.txt_log = TextEdit(self.panel_right)
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Logs will be shown here during batch processing.")
        self.txt_log.setMaximumHeight(150)
        right_layout.addWidget(self.txt_log, stretch=1)

        self.layout.addWidget(self.panel_right)

    def connect_view_model(self):
        self.view_model.input_dir_changed.connect(self.on_input_dir_changed)
        self.view_model.output_dir_changed.connect(self.on_output_dir_changed)
        self.view_model.batch_started.connect(self.on_batch_started)
        self.view_model.batch_progress.connect(self.on_batch_progress)
        self.view_model.file_completed.connect(self.on_file_completed)
        self.view_model.batch_finished.connect(self.on_batch_finished)
        self.view_model.batch_error.connect(self.on_batch_error)
        self.view_model.batch_cancelled.connect(self.on_batch_cancelled)

    def load_settings_defaults(self):
        config = self.view_model.get_config()
        
        variant_key = resolve_model_variant(config.get("model_variant"))
        found_idx = 0
        for i in range(self.combo_model.count()):
            data = self.combo_model.itemData(i)
            if isinstance(data, dict) and data.get("key") == variant_key:
                found_idx = i
                break
        self.combo_model.setCurrentIndex(found_idx)
        
        has_gpu = check_gpu_available()
        if not has_gpu:
            self.combo_device.setCurrentText("cpu")
        else:
            self.combo_device.setCurrentText(config.get("device", "cuda"))

        self.slider_thresh.setValue(int(config.get("confidence_threshold", 0.5) * 100))
        self.lbl_thresh.setText(f"Confidence Threshold: {config.get('confidence_threshold', 0.5):.2f}")
        
        self.chk_clahe.setChecked(config.get("use_clahe", True))
        self.chk_tta.setChecked(config.get("use_tta", False))

    def on_thresh_changed(self, value):
        self.lbl_thresh.setText(f"Confidence Threshold: {value / 100:.2f}")

    def select_input_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Folder of Roof Images")
        if dir_path:
            self.view_model.set_input_dir(dir_path)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder for Results")
        if dir_path:
            self.view_model.set_output_dir(dir_path)

    @Slot(str)
    def on_input_dir_changed(self, path):
        self.lbl_input_dir.setText(path)
        self.lbl_input_dir.setToolTip(path)
        self.check_ready_state()

    @Slot(str)
    def on_output_dir_changed(self, path):
        self.lbl_output_dir.setText(path)
        self.lbl_output_dir.setToolTip(path)
        self.check_ready_state()

    def check_ready_state(self):
        if self.view_model.input_dir and self.view_model.output_dir:
            self.btn_start.setEnabled(True)
            self.txt_log.setText("Ready to start batch. Configured directories correctly.")
        else:
            self.btn_start.setEnabled(False)

    def start_batch(self):
        model_data = self.combo_model.currentData()
        model_variant = model_data.get("key") if isinstance(model_data, dict) else self.combo_model.currentText()
        pipeline_config = self.view_model.build_pipeline_config(
            model_variant=model_variant,
            device=self.combo_device.currentText(),
            confidence_threshold=self.slider_thresh.value() / 100.0,
            use_tta=self.chk_tta.isChecked(),
            use_clahe=self.chk_clahe.isChecked(),
        )
        self.view_model.start_batch(pipeline_config)

    def cancel_batch(self):
        self.view_model.cancel_batch()

    @Slot()
    def on_batch_started(self):
        self.table_queue.setRowCount(0)
        self.txt_log.clear()
        self.progress_bar.setValue(0)
        
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_select_input.setEnabled(False)
        self.btn_select_output.setEnabled(False)
        self.txt_log.append("Batch process starting...")

    @Slot(int, int, str)
    def on_batch_progress(self, current, total, msg):
        if total != -1:
            self.progress_bar.setMaximum(total)
        if current != -1:
            self.progress_bar.setValue(current)
        if msg:
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

        if "error" in result:
            self.table_queue.setItem(row_idx, 2, QTableWidgetItem("N/A"))
            self.table_queue.setItem(row_idx, 3, QTableWidgetItem("0"))
            self.table_queue.setItem(row_idx, 4, QTableWidgetItem("0.0%"))
            status_item = QTableWidgetItem("FAILED")
            status_item.setForeground(QColor("#f43f5e"))
            self.table_queue.setItem(row_idx, 5, status_item)
            return

        crack_detected = result["crack_detected"]
        crack_count = result["crack_count"]
        max_conf = result["max_confidence"]
        
        status_widget = QLabel()
        status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if crack_detected:
            status_widget.setText("YES")
            status_widget.setStyleSheet("color: #e81123; font-weight: bold; background: transparent;")
        else:
            status_widget.setText("NONE")
            status_widget.setStyleSheet("color: #107c41; font-weight: bold; background: transparent;")
        self.table_queue.setCellWidget(row_idx, 2, status_widget)

        self.table_queue.setItem(row_idx, 3, QTableWidgetItem(str(crack_count)))
        self.table_queue.setItem(row_idx, 4, QTableWidgetItem(f"{max_conf*100:.1f}%"))

        status_item = QTableWidgetItem("DONE")
        status_item.setForeground(QColor("#107c41"))
        self.table_queue.setItem(row_idx, 5, status_item)

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
        
        InfoBar.success(
            title="Batch Processing Complete",
            content=f"Successfully processed {total} images.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    @Slot(str)
    def on_batch_error(self, err):
        self.txt_log.append(f"\nCRITICAL ERROR: {err}")
        self.cleanup_batch_run()
        
        InfoBar.error(
            title="Batch Error",
            content=err,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

    @Slot()
    def on_batch_cancelled(self):
        self.txt_log.append("\nBatch execution was cancelled by user.")
        self.cleanup_batch_run()
        self.batch_completed.emit()
        
        InfoBar.warning(
            title="Batch Cancelled",
            content="Execution stopped by user.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def cleanup_batch_run(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_select_input.setEnabled(True)
        self.btn_select_output.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())

    def rebuild_model_combo(self):
        self.combo_model.clear()
        variants = get_available_model_variants()
        from PySide6.QtCore import Qt
        for entry in variants:
            icon = None
            tooltip = None
            if entry["status"] == "downloadable":
                icon = FIF.DOWNLOAD
                tooltip = "Model not installed. Click to download."
            elif entry["status"] == "unavailable":
                icon = FIF.BLOCK
                tooltip = "Model not available for download."
            label = entry["display_name"]
            if icon:
                self.combo_model.addItem(icon, label, userData=entry)
            else:
                self.combo_model.addItem(label, userData=entry)
            idx = self.combo_model.count() - 1
            if tooltip:
                self.combo_model.setItemData(idx, tooltip, Qt.ToolTipRole)
            if entry["status"] == "unavailable":
                self.combo_model.model().item(idx).setEnabled(False)

    # Handler to trigger download if needed
    @Slot(int)
    def on_model_selection_changed(self, idx):
        item = self.combo_model.itemData(idx, Qt.UserRole)
        if not item or not isinstance(item, dict):
            return
        if item.get("status") == "downloadable":
            from findcrack import load_model
            from qfluentwidgets import InfoBar
            try:
                InfoBar.info(
                    title="Model Download",
                    content=f"Downloading model: {item['display_name']}...",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                load_model(item["key"], device="cpu", force_download=True)
                InfoBar.success(
                    title="Download Complete",
                    content=f"Download complete for {item['display_name']}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            except Exception as e:
                InfoBar.error(
                    title="Download Failed",
                    content=f"Model download failed: {e}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=4000,
                    parent=self
                )
            # After download attempt, reload the ComboBox
            self.rebuild_model_combo()
            self.combo_model.setCurrentIndex(idx)
