from collections import defaultdict
from datetime import datetime
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtCore import Qt, QMargins
from qfluentwidgets import SimpleCardWidget, isDarkTheme, qconfig

class InspectionChart(SimpleCardWidget):
    """Custom chart widget displaying 7-day inspection trends with Fluent styling."""
    DAYS = 7
    COLOR_INSPECTED = "#3b82f6"  # Fluent Blue
    COLOR_CRACKS = "#f43f5e"     # Rose/Red
    CHART_TITLE = "7-Day Inspection Analytics"
    MIN_TICKS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        
        self.chart = QChart()
        # Make the chart background transparent to let SimpleCardWidget styling shine through
        self.chart.setBackgroundRoundness(8)
        self.chart.setBackgroundBrush(Qt.BrushStyle.NoBrush)
        self.chart.setMargins(QMargins(8, 8, 8, 8))
        
        # Configure Title
        self.chart.setTitle(self.CHART_TITLE)
        title_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self.chart.setTitleFont(title_font)
        
        # Legend styling
        legend = self.chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignBottom)
        legend.setFont(QFont("Segoe UI", 9))
        
        # Chart View Container
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setBackgroundBrush(Qt.BrushStyle.NoBrush)
        self.layout.addWidget(self.chart_view)
        
        # Apply theme-aware colors initially
        self.apply_theme()
        
        # Dynamically respond to global theme changes
        qconfig.themeChanged.connect(self.apply_theme)

    def apply_theme(self, theme=None) -> None:
        """Adapts the chart visual colors depending on Light/Dark theme mode."""
        is_dark = isDarkTheme()
        
        if is_dark:
            title_color = "#ffffff"
            label_color = "#d0d0d0"
            grid_color = "#2d2d2d"
            axis_line_color = "#555555"
        else:
            title_color = "#202020"
            label_color = "#555555"
            grid_color = "#e2e8f0"
            axis_line_color = "#cccccc"
            
        self.chart.setTitleBrush(QColor(title_color))
        
        legend = self.chart.legend()
        legend.setLabelColor(QColor(label_color))
        
        for axis in self.chart.axes():
            axis.setLabelsColor(QColor(label_color))
            axis.setLabelsFont(QFont("Segoe UI", 9))
            axis.setLinePenColor(QColor(axis_line_color))
            if isinstance(axis, QValueAxis):
                axis.setGridLineColor(QColor(grid_color))

    def update_data(self, history: list) -> None:
        # Clear series and remove old axes to prevent stacking/double-draw
        self.chart.removeAllSeries()
        for axis in list(self.chart.axes()):
            self.chart.removeAxis(axis)
            
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
        
        # X-Axis
        axis_x = QBarCategoryAxis()
        axis_x.append(days)
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        # Y-Axis
        axis_y = QValueAxis()
        max_val = max([inspected_counts[d] for d in days] + [self.MIN_TICKS])
        axis_y.setRange(0, max_val + 1)
        axis_y.setLabelFormat("%d")
        
        # Ensure Y-axis gridlines tick at clean integer increments
        axis_y.setTickCount(int(min(max_val + 2, 6)))
        
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        # Style newly added axes based on current theme colors
        self.apply_theme()

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


