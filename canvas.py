import sys
import os
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
    QMessageBox,
    QGraphicsItem
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QPainter, QCursor
from PyQt6.QtCore import Qt, QRectF, QPointF

from ocr_handler import OCRHandler
from export_handler import SVGExporter

@dataclass
class MaskData:
    """Datový model pro jednu masku (occlusion)."""
    x: float
    y: float
    w: float
    h: float
    text: str = ""

class ResizeHandle(QGraphicsRectItem):
    """Malý čtvereček v rohu masky pro identifikaci úchytu."""
    SIZE = 14.0

    def __init__(self, parent: 'OcclusionRect', position: str) -> None:
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE, parent)
        self.parent_item = parent
        self.position = position # 'topleft', 'topright', 'bottomleft', 'bottomright'
        
        self.setBrush(QBrush(Qt.GlobalColor.white))
        self.setPen(QPen(Qt.GlobalColor.blue, 1.5))
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        
        # Nastavení kurzoru podle pozice
        cursors = {
            'topleft': Qt.CursorShape.SizeFDiagCursor,
            'topright': Qt.CursorShape.SizeBDiagCursor,
            'bottomleft': Qt.CursorShape.SizeBDiagCursor,
            'bottomright': Qt.CursorShape.SizeFDiagCursor
        }
        self.setCursor(cursors.get(position, Qt.CursorShape.ArrowCursor))

class OcclusionRect(QGraphicsRectItem):
    """Interaktivní obdélník (maska) na plátně s podporou změny velikosti."""
    
    def __init__(self, data: MaskData) -> None:
        # Použijeme lokální souřadnice (0,0) pro vnitřek itemu
        super().__init__(0, 0, data.w, data.h)
        self.setPos(data.x, data.y)
        self.data = data
        
        self.active_handle = None
        
        # Nastavení interaktivity
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        # Styl
        self.default_brush = QBrush(QColor(255, 255, 0, 100))
        self.selected_brush = QBrush(QColor(255, 0, 0, 100))
        self.setBrush(self.default_brush)
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Vytvoření úchytů (handles)
        self.handles = {
            'topleft': ResizeHandle(self, 'topleft'),
            'topright': ResizeHandle(self, 'topright'),
            'bottomleft': ResizeHandle(self, 'bottomleft'),
            'bottomright': ResizeHandle(self, 'bottomright')
        }
        self.update_handles_pos()
        self.set_handles_visible(False)

    def set_handles_visible(self, visible: bool) -> None:
        """Zobrazí nebo skryje úchyty pro změnu velikosti."""
        for handle in self.handles.values():
            handle.setVisible(visible)

    def update_handles_pos(self) -> None:
        """Aktualizuje pozici úchytů podle aktuální velikosti obdélníku."""
        r = self.rect()
        self.handles['topleft'].setPos(r.left(), r.top())
        self.handles['topright'].setPos(r.right(), r.top())
        self.handles['bottomleft'].setPos(r.left(), r.bottom())
        self.handles['bottomright'].setPos(r.right(), r.bottom())

    def mousePressEvent(self, event: Any) -> None:
        """Detekuje, zda uživatel klikl na úchyt nebo na tělo masky."""
        self.active_handle = None
        
        # Nejprve zkontrolujeme úchyty
        for handle in self.handles.values():
            if not handle.isVisible():
                continue
                
            # Zvětšíme virtuální oblast pro kliknutí na úchyt o 6px pro lepší stabilitu
            handle_click_rect = handle.rect().adjusted(-6, -6, 6, 6)
            if handle_click_rect.contains(handle.mapFromScene(event.scenePos())):
                self.active_handle = handle.position
                break
        
        if self.active_handle:
            # Důležité: Nastavíme event jako přijatý, aby se nepropagoval do scény (prevence unselectu)
            event.accept()
            
            # Definice protilehlého (fixního) rohu
            opposites = {
                'topleft': self.rect().bottomRight(),
                'topright': self.rect().bottomLeft(),
                'bottomleft': self.rect().topRight(),
                'bottomright': self.rect().topLeft()
            }
            self.fixed_scene_pos = self.mapToScene(opposites[self.active_handle])
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Provádí resize fixací protilehlého rohu ve scéně."""
        if self.active_handle:
            curr = event.scenePos()
            fixed = self.fixed_scene_pos
            
            # Omezení minimální velikosti (10px) při zachování směru
            if abs(curr.x() - fixed.x()) < 10:
                curr.setX(fixed.x() + (10 if curr.x() > fixed.x() else -10))
            if abs(curr.y() - fixed.y()) < 10:
                curr.setY(fixed.y() + (10 if curr.y() > fixed.y() else -10))
            
            # Vytvoření nového obdélníku ve scéně mezi myší a fixním bodem
            new_scene_rect = QRectF(curr, fixed).normalized()
            
            # Aktualizace pozice a velikosti itemu
            self.setPos(new_scene_rect.topLeft())
            self.setRect(0, 0, new_scene_rect.width(), new_scene_rect.height())
            self.update_handles_pos()
            
            # Synchronizace s datovým modelem
            self.data.x, self.data.y = self.x(), self.y()
            self.data.w, self.data.h = self.rect().width(), self.rect().height()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Ukončí režim resizingu."""
        self.active_handle = None
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        super().mouseReleaseEvent(event)

    def itemChange(self, change: QGraphicsRectItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            # Synchronizace pozice do datového modelu při běžném posunu (drag)
            if not getattr(self, 'active_handle', None):
                self.data.x = value.x()
                self.data.y = value.y()
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedChange:
            self.setBrush(self.selected_brush if value else self.default_brush)
            self.set_handles_visible(value)
        
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

        self.save_btn = QPushButton("Uložit do Anki")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.controls_layout.addWidget(self.save_btn)
        
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
            self.save_btn.setEnabled(True)

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

    def on_save_clicked(self) -> None:
        """Vygeneruje SVG a připraví data pro Anki."""
        if not self.current_image_path:
            return

        # Získání všech masek ze scény
        mask_items = [item for item in self.scene.items() if isinstance(item, OcclusionRect)]
        
        if not mask_items:
            QMessageBox.warning(self, "Varování", "Na obrázku nejsou žádné masky k uložení.")
            return

        # Generování SVG
        exporter = SVGExporter(self.scene.width(), self.scene.height())
        svg_content = exporter.generate(mask_items)
        image_name = os.path.basename(self.current_image_path)

        if mw:
            # TODO: Skutečný zápis do Anki Note v dalším kroku
            QMessageBox.information(self, "Anki Mode", "SVG vygenerováno! Připraveno pro zápis do Anki DB.")
        else:
            # Standalone Mode - výpis do konzole
            print(f"--- GENERATED SVG FOR {image_name} ---")
            print(svg_content)
            QMessageBox.information(self, "Standalone Mode", "SVG bylo vypsáno do konzole.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
