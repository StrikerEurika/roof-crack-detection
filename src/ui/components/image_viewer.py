import numpy as np
from typing import Optional
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QPainter, QImage
from PySide6.QtCore import Qt, Signal

class ImageViewer(QGraphicsView):
    """Interactive image viewer widget. Zoom, pan, drag-and-drop."""
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')
    ZOOM_FACTOR = 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 15.0

    image_dropped = Signal(str)

    def __init__(self, parent: Optional[QGraphicsView] = None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        # Configure viewer behavior
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set drag & drop
        self.setAcceptDrops(True)
        
        # Zoom parameters
        self.zoom_factor = self.ZOOM_FACTOR
        self.current_zoom = 1.0
        self.min_zoom = self.MIN_ZOOM
        self.max_zoom = self.MAX_ZOOM

    def set_image(self, pixmap: QPixmap) -> None:
        """Display QPixmap, fit to screen."""
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.fit_in_view()

    def set_ndarray_image(self, ndarray_img: np.ndarray) -> None:
        """Loads a NumPy array (RGB, RGBA, Grayscale, Binary) into viewer."""
        q_img = self._ndarray_to_qimage(ndarray_img)
        self.set_image(QPixmap.fromImage(q_img))

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
        """Fits the pixmap to the viewport bounds."""
        rect = self.pixmap_item.boundingRect()
        if not rect.isEmpty():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.current_zoom = 1.0

    def wheelEvent(self, event) -> None:
        """Mouse wheel zoom."""
        if self.pixmap_item.pixmap().isNull():
            return
        angle = event.angleDelta().y()
        if angle > 0:
            factor = self.zoom_factor
            if self.current_zoom * factor <= self.max_zoom:
                self.scale(factor, factor)
                self.current_zoom *= factor
        else:
            factor = 1.0 / self.zoom_factor
            if self.current_zoom * factor >= self.min_zoom:
                self.scale(factor, factor)
                self.current_zoom *= factor

    def resizeEvent(self, event) -> None:
        """Viewport resize, refit if no zoom."""
        super().resizeEvent(event)
        if self.current_zoom == 1.0:
            self.fit_in_view()

    # Drag and Drop handlers
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(self.IMAGE_EXTENSIONS):
                    self.image_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)
