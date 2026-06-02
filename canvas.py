import sys
from typing import Optional, List, Dict, Any

try:
    from aqt import mw
except ImportError:
    # Podpora pro Standalone Mode (mimo Anki)
    mw = None

from PyQt6.QtWidgets import (
    QApplication,
    QDialog, 
    QVBoxLayout, 
    QPushButton, 
    QGraphicsView, 
    QGraphicsScene, 
    QFileDialog,
    QGraphicsRectItem
)
from PyQt6.QtGui import QPixmap, QColor, QPen
from PyQt6.QtCore import Qt

from ocr_handler import OCRHandler

class OcclusionDialog(QDialog):
    """Hlavní dialogové okno pro správu masek na obrázku."""
    
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion - Canvas")
        self.resize(1000, 700)
        
        self.ocr = OCRHandler()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Inicializace prvků uživatelského rozhraní."""
        self.layout = QVBoxLayout(self)
        
        # Inicializace Scény a View
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(Qt.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.layout.addWidget(self.view)
        
        # Ovládací prvky
        self.load_btn = QPushButton("Načíst obrázek a spustit OCR")
        self.load_btn.setFixedHeight(40)
        self.load_btn.clicked.connect(self.load_image)
        self.layout.addWidget(self.load_btn)

    def load_image(self) -> None:
        """Otevře dialog pro výběr obrázku a zahájí zpracování."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Vybrat obrázek", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.svg)"
        )
        
        if file_path:
            self.display_image(file_path)
            self.run_ocr_auto(file_path)

    def display_image(self, path: str) -> None:
        """Vykreslí vybraný obrázek na QGraphicsScene."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def run_ocr_auto(self, path: str) -> None:
        """Spustí OCR a vykreslí detekované bounding boxy."""
        boxes = self.ocr.get_text_boxes(path)
        
        for box in boxes:
            self.draw_debug_rect(box['x'], box['y'], box['w'], box['h'])

    def draw_debug_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Vykreslí poloprůhledný obdélník přes detekovaný text."""
        rect_item = QGraphicsRectItem(float(x), float(y), float(w), float(h))
        
        # Styl: červená barva, poloprůhledná výplň
        color = QColor(255, 0, 0, 80)
        rect_item.setBrush(color)
        rect_item.setPen(QPen(Qt.GlobalColor.red))
        
        self.scene.addItem(rect_item)

if __name__ == "__main__":
    # Spuštění v Standalone Mode
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
