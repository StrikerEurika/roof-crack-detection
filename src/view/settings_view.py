""" Context:
+ What: 
    - The SettingsView class is a QWidget that provides a user interface for modifying system configurations and managing the inspection database.
    - It allows users to set default model parameters, visualization styles, and directories for saving reports. 
    - Additionally, it provides functionality to clear the inspection history and cached data.
+ Path: src/view/settings_view.py
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, Signal, Slot

from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, SubtitleLabel, TitleLabel,
    ComboBox, Slider, PushButton, PrimaryPushButton, MessageBox, FluentIcon as FIF,
    InfoBar, InfoBarPosition, SingleDirectionScrollArea
)

from src.view_model import SettingsViewModel
from src.services.inference_service import get_available_model_variants, resolve_model_variant

class SettingsView(QWidget):
    """View widget for modifying system configurations and database utility via SettingsViewModel."""
    
    settings_saved = Signal()

    def __init__(self, view_model: SettingsViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(20)

        # Title (Fixed at the top)
        title = TitleLabel("System Settings", self)
        self.main_layout.addWidget(title)

        # Scroll Area for settings content
        self.scroll_area = SingleDirectionScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_container = QWidget()
        self.scroll_container.setStyleSheet("QWidget { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_container)
        self.scroll_layout.setContentsMargins(0, 0, 24, 0)
        self.scroll_layout.setSpacing(16)
        
        self.scroll_area.setWidget(self.scroll_container)
        self.main_layout.addWidget(self.scroll_area)

        # 1. Model Defaults Group
        self.setup_model_defaults()

        # 2. Theme Settings Group
        self.setup_theme_settings()

        # 3. Visualization Style Group
        self.setup_visualization_styles()

        # 4. Directories & Data Group
        self.setup_data_settings()

        # Bottom save buttons
        self.setup_save_actions()

        # Bind ViewModel Signals
        self.connect_view_model()

    def setup_model_defaults(self):
        self.group_model = SimpleCardWidget(self)
        layout = QVBoxLayout(self.group_model)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = SubtitleLabel("Model & Inference Defaults", self.group_model)
        layout.addWidget(title)
        
        # Model variant
        layout.addWidget(BodyLabel("Default Model Zoo Variant:", self.group_model))
        self.combo_model = ComboBox(self.group_model)
        # Add models with decorated UI
        self.rebuild_model_combo()
        self.combo_model.setFixedWidth(350)
        layout.addWidget(self.combo_model)
        self.combo_model.currentIndexChanged.connect(self.on_model_selection_changed)

        # Compute device
        layout.addWidget(BodyLabel("Default Compute Device:", self.group_model))
        self.combo_device = ComboBox(self.group_model)
        self.combo_device.addItems(["cuda", "cpu"])
        self.combo_device.setFixedWidth(150)
        layout.addWidget(self.combo_device)

        # Confidence slider
        self.lbl_thresh = BodyLabel("Default Confidence Threshold: 0.50", self.group_model)
        layout.addWidget(self.lbl_thresh)
        
        slider_layout = QHBoxLayout()
        self.slider_thresh = Slider(Qt.Orientation.Horizontal, self.group_model)
        self.slider_thresh.setRange(10, 90)
        self.slider_thresh.valueChanged.connect(self.on_thresh_changed)
        slider_layout.addWidget(self.slider_thresh)
        slider_layout.addStretch()
        layout.addLayout(slider_layout)

        self.scroll_layout.addWidget(self.group_model)

    def setup_theme_settings(self):
        self.group_theme = SimpleCardWidget(self)
        layout = QVBoxLayout(self.group_theme)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("Application Theme Mode", self.group_theme)
        layout.addWidget(title)

        layout.addWidget(BodyLabel("Select GUI Theme:", self.group_theme))
        self.combo_theme = ComboBox(self.group_theme)
        self.combo_theme.addItems(["Light Mode", "Dark Mode"])
        self.combo_theme.setFixedWidth(200)
        self.combo_theme.currentIndexChanged.connect(self.on_theme_selection_changed)
        layout.addWidget(self.combo_theme)

        self.scroll_layout.addWidget(self.group_theme)

    @Slot(int)
    def on_theme_selection_changed(self, idx: int):
        from qfluentwidgets import setTheme, Theme
        mode = "dark" if idx == 1 else "light"
        setTheme(Theme.DARK if mode == "dark" else Theme.LIGHT)
        main_win = self.window()
        if hasattr(main_win, "notify_theme_changed"):
            main_win.notify_theme_changed()

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
                self.combo_model.addItem(label, icon, userData=entry)
            else:
                self.combo_model.addItem(label, userData=entry)
            idx = self.combo_model.count() - 1
            if entry["status"] == "unavailable":
                self.combo_model.setItemEnabled(idx, False)

    # Handler to trigger download if needed
    @Slot(int)
    def on_model_selection_changed(self, idx):
        item = self.combo_model.itemData(idx)
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

    def setup_visualization_styles(self):
        self.group_vis = SimpleCardWidget(self)
        layout = QVBoxLayout(self.group_vis)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("Visualization Overlay Customization", self.group_vis)
        layout.addWidget(title)

        # Overlay transparency
        self.lbl_alpha = BodyLabel("Overlay Transparency (Alpha): 0.40", self.group_vis)
        layout.addWidget(self.lbl_alpha)
        
        slider_layout = QHBoxLayout()
        self.slider_alpha = Slider(Qt.Orientation.Horizontal, self.group_vis)
        self.slider_alpha.setRange(10, 90)
        self.slider_alpha.valueChanged.connect(self.on_alpha_changed)
        slider_layout.addWidget(self.slider_alpha)
        slider_layout.addStretch()
        layout.addLayout(slider_layout)

        # Color configurations
        colors_layout = QHBoxLayout()
        colors_layout.setSpacing(20)
        
        # 1. Overlay color
        col1 = QVBoxLayout()
        col1.addWidget(BodyLabel("Overlay Color:", self.group_vis))
        self.combo_color_overlay = ComboBox(self.group_vis)
        self.combo_color_overlay.addItems(["Red", "Blue", "Green", "Yellow"])
        self.combo_color_overlay.setFixedWidth(150)
        col1.addWidget(self.combo_color_overlay)
        colors_layout.addLayout(col1)

        # 2. Box color
        col2 = QVBoxLayout()
        col2.addWidget(BodyLabel("Bounding Box Color:", self.group_vis))
        self.combo_color_box = ComboBox(self.group_vis)
        self.combo_color_box.addItems(["Green", "Red", "Blue", "Yellow"])
        self.combo_color_box.setFixedWidth(150)
        col2.addWidget(self.combo_color_box)
        colors_layout.addLayout(col2)

        # 3. Contour color
        col3 = QVBoxLayout()
        col3.addWidget(BodyLabel("Contour Outline Color:", self.group_vis))
        self.combo_color_contour = ComboBox(self.group_vis)
        self.combo_color_contour.addItems(["Blue", "Red", "Green", "Yellow"])
        self.combo_color_contour.setFixedWidth(150)
        col3.addWidget(self.combo_color_contour)
        colors_layout.addLayout(col3)

        colors_layout.addStretch()
        layout.addLayout(colors_layout)
        self.scroll_layout.addWidget(self.group_vis)

    def setup_data_settings(self):
        self.group_data = SimpleCardWidget(self)
        layout = QVBoxLayout(self.group_data)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("Directories & History Maintenance", self.group_data)
        layout.addWidget(title)

        # Default Reports directory selection
        dir_layout = QHBoxLayout()
        self.lbl_reports_dir = BodyLabel("Reports Directory: ", self.group_data)
        self.lbl_reports_dir.setWordWrap(True)
        dir_layout.addWidget(self.lbl_reports_dir, stretch=4)

        self.btn_select_reports = PushButton(FIF.FOLDER, "Change...", self.group_data)
        self.btn_select_reports.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_reports.clicked.connect(self.select_reports_dir)
        dir_layout.addWidget(self.btn_select_reports, stretch=1)
        layout.addLayout(dir_layout)

        # Database cleaner
        db_layout = QHBoxLayout()
        lbl_db_info = BodyLabel("Delete all local inspection records and output asset cache permanently:", self.group_data)
        db_layout.addWidget(lbl_db_info, stretch=4)
        
        self.btn_clear_db = PushButton(FIF.DELETE, "Clear History", self.group_data)
        self.btn_clear_db.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_db.clicked.connect(self.clear_inspection_db)
        db_layout.addWidget(self.btn_clear_db, stretch=1)
        layout.addLayout(db_layout)

        self.scroll_layout.addWidget(self.group_data)

    def setup_save_actions(self):
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        self.btn_save = PrimaryPushButton("Save Configurations", self)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_settings)
        actions_layout.addWidget(self.btn_save)

        self.scroll_layout.addLayout(actions_layout)
        self.scroll_layout.addStretch()

    def connect_view_model(self):
        self.view_model.settings_loaded.connect(self.on_settings_loaded)
        self.view_model.settings_saved.connect(self.on_settings_saved)
        self.view_model.history_cleared.connect(self.on_history_cleared)
        self.view_model.error_occurred.connect(self.on_error)

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
        dialog = MessageBox(
            "Clear Inspection Database?",
            "Are you sure you want to permanently clear all inspection records and delete cached result visualizations?\n\nThis action cannot be undone.",
            self.window()
        )
        if dialog.exec():
            self.view_model.clear_history()

    def color_to_rgb(self, name: str) -> list:
        return self.view_model.color_to_rgb(name)

    def rgb_to_color_name(self, rgb: list) -> str:
        return self.view_model.rgb_to_color_name(rgb)

    @Slot(dict)
    def on_settings_loaded(self, config):
        # Model & device
        variant_key = resolve_model_variant(config.get("model_variant"))
        found_idx = 0
        for i in range(self.combo_model.count()):
            data = self.combo_model.itemData(i)
            if isinstance(data, dict) and data.get("key") == variant_key:
                found_idx = i
                break
        self.combo_model.setCurrentIndex(found_idx)
        self.combo_device.setCurrentText(config.get("device", "cpu"))
        
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

        # Theme mode
        theme_mode = config.get("theme_mode", "light")
        self.combo_theme.setCurrentIndex(1 if theme_mode == "dark" else 0)

        # Reports directory
        reports_dir = config.get("default_reports_dir", self.view_model.get_reports_dir())
        self.lbl_reports_dir.setText(f"Reports Directory: {reports_dir}")
        self.lbl_reports_dir.setToolTip(reports_dir)

    def save_settings(self):
        model_data = self.combo_model.currentData()
        model_variant = model_data.get("key") if isinstance(model_data, dict) else self.combo_model.currentText()
        new_config = {
            "model_variant": model_variant,
            "device": self.combo_device.currentText(),
            "confidence_threshold": self.slider_thresh.value() / 100.0,
            "overlay_alpha": self.slider_alpha.value() / 100.0,
            "overlay_color": self.color_to_rgb(self.combo_color_overlay.currentText()),
            "box_color": self.color_to_rgb(self.combo_color_box.currentText()),
            "contour_color": self.color_to_rgb(self.combo_color_contour.currentText()),
            "theme_mode": "dark" if self.combo_theme.currentIndex() == 1 else "light",
            "default_reports_dir": self.lbl_reports_dir.toolTip()
        }
        self.view_model.save_settings(new_config)

    @Slot(dict)
    def on_settings_saved(self, config):
        InfoBar.success(
            title="Settings Saved",
            content="System configurations have been updated successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.settings_saved.emit()

    @Slot()
    def on_history_cleared(self):
        InfoBar.success(
            title="History Cleared",
            content="Inspection history and database cache cleared successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.settings_saved.emit()

    @Slot(str)
    def on_error(self, message):
        InfoBar.error(
            title="Error",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )
