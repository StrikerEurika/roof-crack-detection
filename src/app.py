import os
import sys
from dataclasses import dataclass

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

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
    import sys
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



def create_context(project_root: str | None = None) -> AppContext:
    root = project_root or get_project_root()
    history_manager = HistoryManager(root)
    inference_service = InferenceService()
    return AppContext(root, history_manager, inference_service)


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName("Roof Crack Inspection Suite")
    app.setOrganizationName("Material AI Labs")

    icon_path = os.path.join(get_project_root(), "assets", "icons", "icons-05.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(QPixmap(icon_path)))

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
