""" Context:
- What: DocumentationView widget displaying user manual loaded dynamically from Markdown file (docs/USER_MANUAL.md).
- Path: src/view/documentation_view.py
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser
from PySide6.QtCore import Qt, Slot

from qfluentwidgets import (
    LargeTitleLabel, BodyLabel, PushButton, FluentIcon as FIF,
    SingleDirectionScrollArea, CardWidget
)

class DocumentationView(QWidget):
    """View widget rendering user manual from Markdown documentation file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manual_path = self._resolve_manual_path()

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # 1. Header bar
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        title = LargeTitleLabel("User Manual & Documentation", self)
        subtitle = BodyLabel("Comprehensive guide for operating the Roof Surface Crack Inspection Suite", self)
        subtitle.setStyleSheet("color: #606060;")
        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.btn_reload = PushButton(FIF.SYNC, "Reload Manual", self)
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.clicked.connect(self.reload_manual)
        header_layout.addWidget(self.btn_reload)

        self.main_layout.addLayout(header_layout)

        # 2. Markdown Viewer Container Card
        self.card_container = CardWidget(self)
        card_layout = QVBoxLayout(self.card_container)
        card_layout.setContentsMargins(16, 16, 16, 16)

        self.text_browser = QTextBrowser(self.card_container)
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                background: transparent;
                color: #1f2937;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 14px;
            }
            QTextBrowser QWidget {
                color: #1f2937;
            }
        """)

        card_layout.addWidget(self.text_browser)
        self.main_layout.addWidget(self.card_container, stretch=1)

    def _resolve_manual_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "docs", "USER_MANUAL.md")

    @Slot()
    def reload_manual(self):
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        text_color = "#e2e8f0" if is_dark else "#1f2937"
        heading_color = "#f8fafc" if is_dark else "#0f172a"
        code_bg = "#334155" if is_dark else "#f1f5f9"
        code_color = "#f8fafc" if is_dark else "#0f172a"
        hr_color = "#475569" if is_dark else "#e2e8f0"

        if os.path.exists(self.manual_path):
            with open(self.manual_path, "r", encoding="utf-8") as f:
                md_text = f.read()
            self.text_browser.document().setDefaultStyleSheet(f"""
                body, p, li, td, span, div {{
                    color: {text_color};
                    font-size: 14px;
                    line-height: 1.6;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: {heading_color};
                    font-weight: bold;
                    margin-top: 14px;
                    margin-bottom: 8px;
                }}
                code, pre {{
                    background-color: {code_bg};
                    color: {code_color};
                    font-family: 'Consolas', monospace;
                }}
                hr {{
                    border: 1px solid {hr_color};
                }}
                a {{
                    color: #3b82f6;
                }}
            """)
            self.text_browser.setMarkdown(md_text)
        else:
            self.text_browser.setHtml(
                "<h3 style='color: #e81123;'>User Manual File Not Found</h3>"
                f"<p style='color: {text_color};'>Expected documentation at: <code>{self.manual_path}</code></p>"
            )
