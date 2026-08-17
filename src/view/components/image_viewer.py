import numpy as np
from typing import Optional
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor
from PySide6.QtCore import Qt, Signal, QTimer

class ImageViewer(QGraphicsView):
    """Interactive image viewer widget. Zoom, pan, drag-and-drop. Shows overlay feedback and exposes signals for parent tracking."""
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')
    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 15.0

    image_dropped = Signal(str)
    zoom_changed = Signal(float)  # Emits current_zoom value
    fitted = Signal()  # Emits when fit_in_view called

    def __init__(self, parent: Optional[QGraphicsView] = None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Configure background style
        self.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #cbd5e1;
                background-color: #e2e8f0;
                border-radius: 8px;
            }
        """)
        self.setBackgroundBrush(QColor("#e2e8f0"))
        self.scene.setBackgroundBrush(QColor("#e2e8f0"))

        # Configure viewer behavior
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Soft placeholder text label
        self.placeholder_label = QLabel("No image loaded", self)
        self.placeholder_label.setStyleSheet("color: #64748b; font-size: 14px; font-weight: 500; background: transparent;")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Set drag & drop
        self.setAcceptDrops(True)

        # Zoom parameters
        self.zoom_factor = self.ZOOM_FACTOR
        self.current_zoom = 1.0
        self.min_zoom = self.MIN_ZOOM
        self.max_zoom = self.MAX_ZOOM

        # Overlay QLabel for zoom/fit feedback
        self.feedback_label = QLabel(self)
        self.feedback_label.setStyleSheet("background: rgba(0, 0, 0, 160); color: white; border-radius: 6px; padding: 6px; font-size: 13px;")
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setVisible(False)
        self.feedback_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self._hide_feedback)

    def set_image(self, pixmap: QPixmap) -> None:
        """Display QPixmap, fit to screen."""
        self.pixmap_item.setPixmap(pixmap)
        if not pixmap.isNull():
            self.placeholder_label.setVisible(False)
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fit_in_view()
        else:
            self.placeholder_label.setVisible(True)
            self.scene.setSceneRect(0, 0, 0, 0)

    def set_ndarray_image(self, ndarray_img: np.ndarray) -> None:
        """Loads a NumPy array (RGB, RGBA, Grayscale, Binary) into viewer."""
        q_img = self._ndarray_to_qimage(ndarray_img)
        self.set_image(QPixmap.fromImage(q_img))

    def clear(self) -> None:
        """Clears displayed pixmap and resets viewer state."""
        self.pixmap_item.setPixmap(QPixmap())
        self.scene.setSceneRect(0, 0, 0, 0)
        self.current_zoom = 1.0
        self.placeholder_label.setVisible(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "placeholder_label"):
            self.placeholder_label.setGeometry(self.rect())

    @staticmethod
    def _ndarray_to_qimage(array: np.ndarray) -> QImage:
        arr = np.ascontiguousarray(array)
        if len(arr.shape) == 2:
            h, w = arr.shape
            c = 1
        elif len(arr.shape) == 3:
            h, w, c = arr.shape
        else:
            raise ValueError(f"Unsupported image shape: {arr.shape}")

        if c == 1:
            if len(arr.shape) == 3:
                arr = arr[:, :, 0]
            if arr.dtype == bool:
                arr = (arr * 255).astype("uint8")
            elif arr.dtype != np.uint8:
                arr = (arr * 255).astype("uint8") if arr.max() <= 1.0 else arr.astype("uint8")
            else:
                uniq = np.unique(arr)
                if len(uniq) <= 2 and all(val in (0, 1) for val in uniq):
                    arr = arr * 255
            bytes_per_line = w
            return QImage(arr.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
        elif c == 3:
            bytes_per_line = 3 * w
            return QImage(arr.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        elif c == 4:
            bytes_per_line = 4 * w
            return QImage(arr.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        else:
            raise ValueError(f"Unsupported number of channels: {c}")

    def fit_in_view(self):
        """Fits the pixmap to the viewport bounds and show feedback overlay. Emits fitted signal."""
        rect = self.pixmap_item.boundingRect()
        if not rect.isEmpty():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.current_zoom = 1.0
            self._show_feedback("Fitted")
            self.fitted.emit()

    def wheelEvent(self, event) -> None:
        """Mouse wheel zoom. Shows overlay with zoom percent. Emits zoom_changed signal."""
        if self.pixmap_item.pixmap().isNull():
            return
        angle = event.angleDelta().y()
        updated = False
        if angle > 0:
            factor = self.zoom_factor
            if self.current_zoom * factor <= self.max_zoom:
                self.scale(factor, factor)
                self.current_zoom *= factor
                updated = True
        else:
            factor = 1.0 / self.zoom_factor
            if self.current_zoom * factor >= self.min_zoom:
                self.scale(factor, factor)
                self.current_zoom *= factor
                updated = True
        if updated:
            self._show_feedback(f"Zoom: {self.current_zoom:.2f}x")
            self.zoom_changed.emit(self.current_zoom)

    def resizeEvent(self, event) -> None:
        """Viewport resize, refit if no zoom. Shows feedback overlay when fitted."""
        super().resizeEvent(event)
        if not hasattr(self, 'current_zoom') or not hasattr(self, 'feedback_label'):
            return
        if self.current_zoom == 1.0:
            self.fit_in_view()
            self._show_feedback("Fitted")
            self.fitted.emit()

    def dragEnterEvent(self, event) -> None:
        """Accept drag enter if files/images. Otherwise, defer to base."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        """Accept drag move if files/images. Otherwise, defer to base."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        """Handle file/image drop. Emit image_dropped, show overlay."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(self.IMAGE_EXTENSIONS):
                    self.image_dropped.emit(file_path)
                    self._show_feedback(f"Dropped: {file_path.split('/')[-1]}")
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def _show_feedback(self, text: str, ms: int = 1100) -> None:
        self.feedback_label.setText(text)
        self.feedback_label.adjustSize()
        label_w, label_h = self.feedback_label.width(), self.feedback_label.height()
        v_width, v_height = self.viewport().width(), self.viewport().height()
        x = (v_width - label_w) // 2
        y = v_height // 12
        self.feedback_label.move(x, y)
        self.feedback_label.setVisible(True)
        self.feedback_label.raise_()
        self.feedback_timer.start(ms)

    def _hide_feedback(self) -> None:
        self.feedback_label.setVisible(False)

# END OF FILE
