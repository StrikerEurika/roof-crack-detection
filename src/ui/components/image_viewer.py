from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QPainter, QImage
from PySide6.QtCore import Qt, Signal

class ImageViewer(QGraphicsView):
    """An interactive image viewer widget supporting zooming, panning, and drag-and-drop notifications."""
    
    image_dropped = Signal(str)

    def __init__(self, parent=None):
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
        self.zoom_factor = 1.15
        self.current_zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 15.0

    def set_image(self, pixmap: QPixmap):
        """Loads and displays a QPixmap in the viewer, fitting it to the screen initially."""
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.fit_in_view()

    def set_ndarray_image(self, ndarray_img):
        """Loads a NumPy array (RGB) image into the viewer."""
        h, w, c = ndarray_img.shape
        bytes_per_line = c * w
        q_img = QImage(ndarray_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img)
        self.set_image(pix)

    def fit_in_view(self):
        """Fits the pixmap to the viewport bounds."""
        rect = self.pixmap_item.boundingRect()
        if not rect.isEmpty():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.current_zoom = 1.0

    def wheelEvent(self, event):
        """Handles zooming with mouse wheel."""
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

    def resizeEvent(self, event):
        """Adjusts zoom on viewport resize (keeps initial fit)."""
        super().resizeEvent(event)
        # Avoid refitting on every small window drag if user already zoomed, 
        # but fit initially when image is loaded and viewer resized.
        if self.current_zoom == 1.0:
            self.fit_in_view()

    # Drag and Drop handlers
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                # Check for image extensions
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')):
                    self.image_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)
