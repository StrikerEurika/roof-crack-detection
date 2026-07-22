import os
import sys
from dataclasses import dataclass

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap

from src.model import HistoryManager
from src.services import InferenceService
from src.view.mainwindow import MainWindow


@dataclass
class AppContext:
    """Application-level dependencies shared across MVVM layers."""

    project_root: str
    history_manager: HistoryManager
    inference_service: InferenceService


def get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_context(project_root: str | None = None) -> AppContext:
    root = project_root or get_project_root()
    history_manager = HistoryManager(root)
    inference_service = InferenceService()
    return AppContext(root, history_manager, inference_service)


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    icon_path = os.path.join(get_project_root(), "assets/icons", "icon-05.png")
    app.setWindowIcon(QIcon(icon_path))

    app.setApplicationName("Roof Crack Inspection Suite")
    app.setOrganizationName("Material AI Labs")
    return app


def run() -> int:
    project_root = get_project_root()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.chdir(project_root)

    app = create_application(sys.argv)
    context = create_context(project_root)
    window = MainWindow(context)
    window.show()
    return app.exec()
