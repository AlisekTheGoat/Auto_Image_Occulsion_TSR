import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    from aqt import mw
except ImportError:
    # Podpora pro Standalone Mode (mimo Anki)
    mw = None

from PyQt6.QtWidgets import (
    QApplication,
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton, 
    QGraphicsView, 
    QGraphicsScene, 
    QFileDialog,
    QGraphicsRectItem,
    QMessageBox
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QPainter
from PyQt6.QtCore import Qt

from ocr_handler import OCRHandler

@dataclass
class MaskData:
    """Datový model pro jednu masku (occlusion)."""
    x: float
    y: float
    w: float
    h: float
    text: str = ""

class OcclusionRect(QGraphicsRectItem):
    """Interaktivní obdélník (maska) na plátně."""
    
    def __init__(self, data: MaskData) -> None:
        super().__init__(data.x, data.y, data.w, data.h)
        self.data = data
        
        # Nastavení interaktivity
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        # Styl: Žlutá poloprůhledná výplň (podobně jako v Image Occlusion Enhanced)
        self.default_brush = QBrush(QColor(255, 255, 0, 100))
        self.selected_brush = QBrush(QColor(255, 0, 0, 100))
        self.setBrush(self.default_brush)
        self.setPen(QPen(Qt.GlobalColor.black, 1))

    def itemChange(self, change: QGraphicsRectItem.GraphicsItemChange, value: Any) -> Any:
        """Sleduje změny pozice a aktualizuje datový model."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            # V reálné aplikaci by zde proběhla aktualizace self.data
            pass
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedChange:
            self.setBrush(self.selected_brush if value else self.default_brush)
        
        return super().itemChange(change, value)

class OcclusionDialog(QDialog):
    """Hlavní dialogové okno pro správu masek na obrázku."""
    
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion - Canvas")
        self.resize(1000, 750)
        
        self.ocr = OCRHandler()
        self.current_image_path: Optional[str] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Inicializace prvků uživatelského rozhraní."""
        self.layout = QVBoxLayout(self)
        
        # Inicializace Scény a View
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.view)
        
        # Ovládací panel
        self.controls_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Načíst obrázek")
        self.load_btn.setFixedHeight(40)
        self.load_btn.clicked.connect(self.on_load_clicked)
        self.controls_layout.addWidget(self.load_btn)
        
        self.occlude_btn = QPushButton("Auto-Occlude (OCR)")
        self.occlude_btn.setFixedHeight(40)
        self.occlude_btn.setEnabled(False)
        self.occlude_btn.clicked.connect(self.run_ocr_auto)
        self.controls_layout.addWidget(self.occlude_btn)
        
        self.layout.addLayout(self.controls_layout)

    def on_load_clicked(self) -> None:
        """Otevře dialog pro výběr obrázku."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Vybrat obrázek", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.svg)"
        )
        
        if file_path:
            self.current_image_path = file_path
            self.display_image(file_path)
            self.occlude_btn.setEnabled(True)

    def display_image(self, path: str) -> None:
        """Vykreslí vybraný obrázek na QGraphicsScene."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        else:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se načíst obrázek: {path}")

    def run_ocr_auto(self) -> None:
        """Spustí OCR a vytvoří interaktivní masky."""
        if not self.current_image_path:
            return

        # Vypnutí tlačítek během OCR
        self.occlude_btn.setEnabled(False)
        self.occlude_btn.setText("Zpracovávám...")
        QApplication.processEvents()

        try:
            boxes = self.ocr.get_text_boxes(self.current_image_path)
            
            for box in boxes:
                data = MaskData(
                    x=float(box['x']), 
                    y=float(box['y']), 
                    w=float(box['w']), 
                    h=float(box['h']),
                    text=box['text']
                )
                mask_item = OcclusionRect(data)
                self.scene.addItem(mask_item)

        finally:
            self.occlude_btn.setEnabled(True)
            self.occlude_btn.setText("Auto-Occlude (OCR)")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
