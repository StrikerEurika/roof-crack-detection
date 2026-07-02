import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSlider, QComboBox, QMessageBox, QFileDialog, QDialog
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal

class SettingsView(QWidget):
    """View widget for modifying system configurations and database utility."""
    
    settings_saved = Signal()

    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.hm = history_manager

        # Stylesheet (Consistent with dark theme)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
                color: #e2e8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QLabel {
                font-size: 12px;
                color: #cbd5e1;
            }
            QComboBox, QSlider {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px;
                color: #f8fafc;
            }
            QPushButton.primaryBtn {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton.primaryBtn:hover {
                background-color: #2563eb;
            }
            QPushButton.dangerBtn {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton.dangerBtn:hover {
                background-color: #dc2626;
            }
            QPushButton.secondaryBtn {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton.secondaryBtn:hover {
                background-color: #334155;
                border: 1px solid #3b82f6;
            }
        """)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # Title
        title = QLabel("System Settings")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #f8fafc;")
        self.main_layout.addWidget(title)

        # 1. Model Defaults Group
        self.setup_model_defaults()

        # 2. Visualization Style Group
        self.setup_visualization_styles()

        # 3. Directories & Data Group
        self.setup_data_settings()

        # Bottom save buttons
        self.setup_save_actions()

        # Load initial values
        self.load_settings()

    def setup_model_defaults(self):
        group = QGroupBox("Model & Inference Defaults")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # Model variant
        layout.addWidget(QLabel("Default Model Zoo Variant:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Seg_UNET_CFD_actual_v2", "Seg_UNET_CFD_actual_v1", "Det_YOLOv26n-seg_crack-dataset_v1"])
        layout.addWidget(self.combo_model)

        # Compute device
        layout.addWidget(QLabel("Default Compute Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cuda", "cpu"])
        layout.addWidget(self.combo_device)

        # Confidence slider
        self.lbl_thresh = QLabel("Default Confidence Threshold: 0.50")
        layout.addWidget(self.lbl_thresh)
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setRange(10, 90)
        self.slider_thresh.valueChanged.connect(self.on_thresh_changed)
        layout.addWidget(self.slider_thresh)

        self.main_layout.addWidget(group)

    def setup_visualization_styles(self):
        group = QGroupBox("Visualization Overlay Customization")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Overlay transparency
        self.lbl_alpha = QLabel("Overlay Transparency (Alpha): 0.40")
        layout.addWidget(self.lbl_alpha)
        self.slider_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_alpha.setRange(10, 90)
        self.slider_alpha.valueChanged.connect(self.on_alpha_changed)
        layout.addWidget(self.slider_alpha)

        # Color configurations
        colors_layout = QHBoxLayout()
        
        # 1. Overlay color
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Overlay Color:"))
        self.combo_color_overlay = QComboBox()
        self.combo_color_overlay.addItems(["Red", "Blue", "Green", "Yellow"])
        col1.addWidget(self.combo_color_overlay)
        colors_layout.addLayout(col1)

        # 2. Box color
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Bounding Box Color:"))
        self.combo_color_box = QComboBox()
        self.combo_color_box.addItems(["Green", "Red", "Blue", "Yellow"])
        col2.addWidget(self.combo_color_box)
        colors_layout.addLayout(col2)

        # 3. Contour color
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Contour Outline Color:"))
        self.combo_color_contour = QComboBox()
        self.combo_color_contour.addItems(["Blue", "Red", "Green", "Yellow"])
        col3.addWidget(self.combo_color_contour)
        colors_layout.addLayout(col3)

        layout.addLayout(colors_layout)
        self.main_layout.addWidget(group)

    def setup_data_settings(self):
        group = QGroupBox("Directories & History Maintenance")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Default Reports directory selection
        dir_layout = QHBoxLayout()
        self.lbl_reports_dir = QLabel("Reports Directory: ")
        self.lbl_reports_dir.setWordWrap(True)
        dir_layout.addWidget(self.lbl_reports_dir, stretch=4)

        self.btn_select_reports = QPushButton("📁 Change...")
        self.btn_select_reports.setProperty("class", "secondaryBtn")
        self.btn_select_reports.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_reports.clicked.connect(self.select_reports_dir)
        dir_layout.addWidget(self.btn_select_reports, stretch=1)
        layout.addLayout(dir_layout)

        # Database cleaner
        db_layout = QHBoxLayout()
        lbl_db_info = QLabel("Delete all local inspection records and output asset cache permanently:")
        db_layout.addWidget(lbl_db_info, stretch=4)
        
        self.btn_clear_db = QPushButton("🗑️ Clear Inspection History")
        self.btn_clear_db.setProperty("class", "dangerBtn")
        self.btn_clear_db.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_db.clicked.connect(self.clear_inspection_db)
        db_layout.addWidget(self.btn_clear_db, stretch=1)
        layout.addLayout(db_layout)

        self.main_layout.addWidget(group)

    def setup_save_actions(self):
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        self.btn_save = QPushButton("💾 Save Configurations")
        self.btn_save.setProperty("class", "primaryBtn")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_settings)
        actions_layout.addWidget(self.btn_save)

        self.main_layout.addLayout(actions_layout)
        self.main_layout.addStretch()

    def on_thresh_changed(self, value):
        self.lbl_thresh.setText(f"Default Confidence Threshold: {value / 100:.2f}")

    def on_alpha_changed(self, value):
        self.lbl_alpha.setText(f"Overlay Transparency (Alpha): {value / 100:.2f}")

    def select_reports_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Default PDF Reports Save Location")
        if dir_path:
            self.lbl_reports_dir.setText(f"Reports Directory: {dir_path}")
            self.lbl_reports_dir.setToolTip(dir_path)

    def clear_inspection_db(self):
        reply = QMessageBox.question(
            self, "Clear Inspection Database?",
            "Are you sure you want to permanently clear all inspection records and delete cached result visualizations?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.hm.clear_history()
            if success:
                QMessageBox.information(self, "Success", "Inspection history and output cache cleared successfully.")
                self.settings_saved.emit() # Refresh dashboard
            else:
                QMessageBox.warning(self, "Error", "Failed to fully clear history files.")

    def color_to_rgb(self, name: str) -> list:
        mapping = {
            "Red": [255, 0, 0],
            "Green": [0, 255, 0],
            "Blue": [0, 0, 255],
            "Yellow": [255, 255, 0]
        }
        return mapping.get(name, [255, 0, 0])

    def rgb_to_color_name(self, rgb: list) -> str:
        mapping = {
            (255, 0, 0): "Red",
            (0, 255, 0): "Green",
            (0, 0, 255): "Blue",
            (255, 255, 0): "Yellow"
        }
        return mapping.get(tuple(rgb), "Red")

    def load_settings(self):
        config = self.hm.config
        
        # Model & device
        self.combo_model.setCurrentText(config.get("model_variant", "Seg_UNET_CFD_actual_v2"))
        self.combo_device.setCurrentText(config.get("device", "cuda"))
        
        # Threshold
        thresh = int(config.get("confidence_threshold", 0.5) * 100)
        self.slider_thresh.setValue(thresh)
        self.lbl_thresh.setText(f"Default Confidence Threshold: {thresh / 100:.2f}")

        # Alpha
        alpha = int(config.get("overlay_alpha", 0.4) * 100)
        self.slider_alpha.setValue(alpha)
        self.lbl_alpha.setText(f"Overlay Transparency (Alpha): {alpha / 100:.2f}")

        # Colors
        overlay_color = config.get("overlay_color", [255, 0, 0])
        box_color = config.get("box_color", [0, 255, 0])
        contour_color = config.get("contour_color", [0, 0, 255])
        
        self.combo_color_overlay.setCurrentText(self.rgb_to_color_name(overlay_color))
        self.combo_color_box.setCurrentText(self.rgb_to_color_name(box_color))
        self.combo_color_contour.setCurrentText(self.rgb_to_color_name(contour_color))

        # Reports directory
        reports_dir = config.get("default_reports_dir", self.hm.reports_dir)
        self.lbl_reports_dir.setText(f"Reports Directory: {reports_dir}")
        self.lbl_reports_dir.setToolTip(reports_dir)

    def save_settings(self):
        new_config = {
            "model_variant": self.combo_model.currentText(),
            "device": self.combo_device.currentText(),
            "confidence_threshold": self.slider_thresh.value() / 100.0,
            "overlay_alpha": self.slider_alpha.value() / 100.0,
            "overlay_color": self.color_to_rgb(self.combo_color_overlay.currentText()),
            "box_color": self.color_to_rgb(self.combo_color_box.currentText()),
            "contour_color": self.color_to_rgb(self.combo_color_contour.currentText()),
            "default_reports_dir": self.lbl_reports_dir.toolTip()
        }
        
        success = self.hm.save_config(new_config)
        if success:
            QMessageBox.information(self, "Settings Saved", "System configurations have been updated successfully.")
            self.settings_saved.emit()
        else:
            QMessageBox.warning(self, "Error", "Failed to write settings to disk.")
