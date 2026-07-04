""" Context:
+ Path: src/view/components/crack_table.py
+ Description: Dedicated table widget for displaying detected cracks with severity coloring.
"""

from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QTableWidget, 
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from qfluentwidgets import TableWidget

class CrackTableWidget(TableWidget):
    """Table to display detected cracks with severity info"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()
        
    def _setup_table(self):
        """table appearence and behaviours"""
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels([
            "Index", 
            "Bounding Box (X1, Y1, X2, Y2)", 
            "Size / Length Rating"
        ])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMaximumHeight(150)
        
        # column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
    def populate(self, boxes: List[Tuple[int, int, int, int]]):
        """Update the table with new crack data"""
        self.setRowCount(0)
        self.setRowCount(len(boxes))
        
        # populate each row with box data
        
        
    def _add_row(self, index: int, box_corners: Tuple[int, int, int, int]):
        """Add a row to the table"""
        
        # index column
        index_item = QTableWidgetItem(str(index + 1))
        index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(index, 0, index_item)

        # bounding box column
        coordinates = f"({box_corners[0]}, {box_corners[1]}, {box_corners[2]}, {box_corners[3]})"
        coordinates_item = QTableWidgetItem(coordinates)
        coordinates_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(index, 1, coordinates_item)
