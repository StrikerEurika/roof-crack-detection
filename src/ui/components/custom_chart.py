from collections import defaultdict
from datetime import datetime
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtCore import Qt

class InspectionChart(QWidget):
    """Custom chart widget using PySide6.QtCharts to show 7-day inspection trends."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart = QChart()
        # Theme/styling
        self.chart.setBackgroundRoundness(8)
        self.chart.setBackgroundBrush(QColor("#1e293b")) # matches cardbg
        self.chart.setTitleBrush(QColor("#f8fafc")) # white text
        self.chart.setTitle("7-Day Inspection Analytics")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        self.chart.setTitleFont(title_font)
        
        # Legend styling
        legend = self.chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignBottom)
        legend.setLabelColor(QColor("#94a3b8"))
        legend.setFont(QFont("Segoe UI", 9))
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.chart_view)

    def update_data(self, history: list):
        """Processes the last 7 days of data from history and updates the chart."""
        self.chart.removeAllSeries()
        
        # Determine last 7 days keys
        days = []
        for i in range(6, -1, -1):
            # Calculate date strings
            from datetime import timedelta
            date_str = (datetime.now() - timedelta(days=i)).strftime("%m/%d")
            days.append(date_str)
            
        inspected_counts = defaultdict(int)
        cracked_counts = defaultdict(int)
        
        for record in history:
            timestamp_str = record.get("timestamp", "")
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    date_key = dt.strftime("%m/%d")
                    if date_key in days:
                        inspected_counts[date_key] += 1
                        if record.get("crack_detected", False):
                            cracked_counts[date_key] += 1
                except Exception:
                    pass
                    
        # Create bar sets
        set_inspected = QBarSet("Inspected")
        set_inspected.setColor(QColor("#3b82f6")) # Blue
        
        set_cracks = QBarSet("Cracks Detected")
        set_cracks.setColor(QColor("#f43f5e")) # Coral Red
        
        for day in days:
            set_inspected.append(inspected_counts[day])
            set_cracks.append(cracked_counts[day])
            
        series = QBarSeries()
        series.append(set_inspected)
        series.append(set_cracks)
        self.chart.addSeries(series)
        
        # X-Axis configuration
        axis_x = QBarCategoryAxis()
        axis_x.append(days)
        axis_x.setLabelsColor(QColor("#94a3b8"))
        axis_x.setLinePenColor(QColor("#334155"))
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        # Y-Axis configuration
        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#94a3b8"))
        axis_y.setLinePenColor(QColor("#334155"))
        axis_y.setGridLineColor(QColor("#334155"))
        # Dynamic range
        max_val = max([inspected_counts[d] for d in days] + [5]) # minimum 5 ticks
        axis_y.setRange(0, max_val + 1)
        axis_y.setLabelFormat("%d")
        
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
