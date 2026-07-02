from collections import defaultdict
from datetime import datetime
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtCore import Qt

class InspectionChart(QWidget):
    """Custom chart widget. Show 7-day inspection trends."""
    DAYS = 7
    COLOR_INSPECTED = "#3b82f6"
    COLOR_CRACKS = "#f43f5e"
    CHART_TITLE = "7-Day Inspection Analytics"
    MIN_TICKS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart = QChart()
        # Theme/styling
        self.chart.setBackgroundRoundness(4)
        self.chart.setBackgroundBrush(Qt.BrushStyle.NoBrush)
        self.chart.setTitleBrush(QColor("#333333"))
        self.chart.setTitle("7-Day Inspection Analytics")
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.chart.setTitleFont(title_font)
        
        # Legend styling
        legend = self.chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignBottom)
        legend.setLabelColor(QColor("#444444"))
        legend.setFont(QFont("Segoe UI", 8))
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.chart_view)

    def update_data(self, history: list) -> None:
        self.chart.removeAllSeries()
        days = self._get_last_days()
        inspected_counts, cracked_counts = self._tally_history(history, days)
        set_inspected = QBarSet("Inspected")
        set_inspected.setColor(QColor(self.COLOR_INSPECTED))
        set_cracks = QBarSet("Cracks Detected")
        set_cracks.setColor(QColor(self.COLOR_CRACKS))
        for day in days:
            set_inspected.append(inspected_counts[day])
            set_cracks.append(cracked_counts[day])
        series = QBarSeries()
        series.append(set_inspected)
        series.append(set_cracks)
        self.chart.addSeries(series)
        axis_x = QBarCategoryAxis()
        axis_x.append(days)
        axis_x.setLabelsColor(QColor("#000000"))
        axis_x.setLinePenColor(QColor("#808080"))
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#000000"))
        axis_y.setLinePenColor(QColor("#808080"))
        axis_y.setGridLineColor(QColor("#e2e8f0"))
        max_val = max([inspected_counts[d] for d in days] + [self.MIN_TICKS])
        axis_y.setRange(0, max_val + 1)
        axis_y.setLabelFormat("%d")
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

    @staticmethod
    def _get_last_days() -> list:
        from datetime import timedelta
        return [
            (datetime.now() - timedelta(days=i)).strftime("%m/%d")
            for i in range(InspectionChart.DAYS - 1, -1, -1)
        ]

    @staticmethod
    def _tally_history(history: list, days: list) -> tuple:
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
        return inspected_counts, cracked_counts

