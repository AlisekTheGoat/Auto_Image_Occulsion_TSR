from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QPushButton, 
    QGraphicsView, 
    QGraphicsScene, 
    QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class OcclusionDialog(QDialog):
    """Hlavní dialogové okno pro správu masek na obrázku."""
    
    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion - Canvas")
        self.resize(1000, 700)
        
        self.setup_ui()

    def setup_ui(self) -> None:
        """Inicializace prvků uživatelského rozhraní."""
        self.layout = QVBoxLayout(self)
        
        # Inicializace Scény a View (Základ pro SVG Canvas)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(Qt.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.layout.addWidget(self.view)
        
        # Ovládací prvky
        self.load_btn = QPushButton("Načíst obrázek")
        self.load_btn.setFixedHeight(40)
        self.load_btn.clicked.connect(self.load_image)
        self.layout.addWidget(self.load_btn)

    def load_image(self) -> None:
        """Otevře dialog pro výběr obrázku a vykreslí jej na scénu."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Vybrat obrázek", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.svg)"
        )
        
        if file_path:
            self.display_image(file_path)

    def display_image(self, path: str) -> None:
        """Vykreslí vybraný obrázek na QGraphicsScene."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
