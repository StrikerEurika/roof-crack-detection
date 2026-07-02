import sys
import os

# Add project root to sys.path to resolve 'src' imports correctly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.controllers import HistoryManager
from src.ui import MainWindow

def main():
    # Set the working directory to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Initialize PySide6 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Roof Crack Inspection Suite")
    app.setOrganizationName("Material AI Labs")
    
    # Initialize history and configurations manager
    history_manager = HistoryManager(project_root)
    
    # Initialize and show main window
    window = MainWindow(history_manager)
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
