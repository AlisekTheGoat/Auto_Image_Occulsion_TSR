import sys
import os
import uuid
from typing import Optional, List, Any, Dict
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QGraphicsView, QGraphicsScene, QFileDialog, QMessageBox, QComboBox, QToolButton,
    QRubberBand, QGraphicsRectItem
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF, QRect, QSize

try:
    from .ocr_handler import OCRHandler
    from .export_handler import SVGExporter
    from .anki_handler import AnkiHandler
    from .canvas_items import MaskData, OcclusionRect, OcclusionEllipse, OcclusionPath
except ImportError:
    from ocr_handler import OCRHandler
    from export_handler import SVGExporter
    from anki_handler import AnkiHandler
    from canvas_items import MaskData, OcclusionRect, OcclusionEllipse, OcclusionPath

try:
    import aqt
    from aqt import mw
    from aqt.utils import showInfo, QueryOp
    ANKI_AVAILABLE = True
except ImportError:
    mw = None
    ANKI_AVAILABLE = False

class OcclusionDialog(QDialog):
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion")
        self.resize(1280, 800)
        self.ocr = OCRHandler()
        self.anki = AnkiHandler() if ANKI_AVAILABLE else None
        self.current_image_path: Optional[str] = None
        self.drawing_item: Optional[Any] = None
        self.lasso_path: Optional[QPainterPath] = None
        self.rubber_band: Optional[QRubberBand] = None
        self.origin = QPointF()
        self.setup_ui()

    def setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.view)
        
        toolbar = QHBoxLayout()
        self.load_btn = QPushButton("Načíst")
        self.load_btn.clicked.connect(self.on_load_clicked)
        toolbar.addWidget(self.load_btn)

        self.tool_selector = QComboBox()
        self.tool_selector.addItems(["Výběr", "Obdélník", "Elipsa", "Lasso (Volná ruka)"])
        toolbar.addWidget(self.tool_selector)

        self.occlude_btn = QPushButton("Auto-OCR")
        self.occlude_btn.clicked.connect(self.run_ocr_auto)
        toolbar.addWidget(self.occlude_btn)

        self.group_btn = QPushButton("Seskupit")
        self.group_btn.clicked.connect(self.group_selected)
        toolbar.addWidget(self.group_btn)

        self.ungroup_btn = QPushButton("Rozdělit")
        self.ungroup_btn.clicked.connect(self.ungroup_selected)
        toolbar.addWidget(self.ungroup_btn)

        self.save_btn = QPushButton("Uložit do Anki")
        self.save_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.on_save_clicked)
        toolbar.addWidget(self.save_btn)
        
        self.layout.addLayout(toolbar)

        self.view.installEventFilter(self)
        self.scene.mousePressEvent = self.scene_mouse_press
        self.scene.mouseMoveEvent = self.scene_mouse_move
        self.scene.mouseReleaseEvent = self.scene_mouse_release

    def eventFilter(self, source: Any, event: Any) -> bool:
        if event.type() == event.Type.KeyPress and source is self.view:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                for item in self.scene.selectedItems():
                    self.scene.removeItem(item)
                return True
        return super().eventFilter(source, event)

    def group_selected(self) -> None:
        items = [i for i in self.scene.selectedItems() if hasattr(i, 'data')]
        if len(items) < 2: return
        gid = str(uuid.uuid4())[:8]
        for i in items:
            i.data.group_id = gid
            i.update_style()

    def ungroup_selected(self) -> None:
        for i in self.scene.selectedItems():
            if hasattr(i, 'data'):
                i.data.group_id = None
                i.update_style()

    def scene_mouse_press(self, event: Any) -> None:
        tool = self.tool_selector.currentText()
        
        # Pokud je vybrán nástroj "Výběr" nebo se klikne na prázdné místo
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        is_background = not item or (isinstance(item, QGraphicsRectItem) and not hasattr(item, 'data'))
        
        if tool == "Výběr" or (event.button() == Qt.MouseButton.LeftButton and is_background):
            if event.button() == Qt.MouseButton.LeftButton:
                # Zahájení výběrového rámečku (Rubber Band)
                self.origin = event.screenPos()
                if not self.rubber_band:
                    self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.view)
                
                # Bezpečný převod na QPoint (celá čísla)
                origin_point = self.origin.toPoint() if hasattr(self.origin, 'toPoint') else self.origin
                local_pos = self.view.mapFromGlobal(origin_point)
                
                self.rubber_band.setGeometry(QRect(local_pos, QSize()))
                self.rubber_band.show()
                
                # Pokud nedržíme Shift, zrušíme předchozí výběr
                if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.scene.clearSelection()
                
                event.accept()
                return

        if event.button() != Qt.MouseButton.LeftButton:
            QGraphicsScene.mousePressEvent(self.scene, event)
            return

        self.start_point = event.scenePos()
        if tool == "Obdélník":
            self.drawing_item = OcclusionRect(MaskData(self.start_point.x(), self.start_point.y(), 1, 1))
        elif tool == "Elipsa":
            self.drawing_item = OcclusionEllipse(MaskData(self.start_point.x(), self.start_point.y(), 1, 1))
        elif tool == "Lasso (Volná ruka)":
            self.lasso_path = QPainterPath(self.start_point)
            self.drawing_item = OcclusionPath(MaskData(self.start_point.x(), self.start_point.y(), 0, 0, "path"), self.lasso_path)
        
        if self.drawing_item:
            self.scene.addItem(self.drawing_item)
        event.accept()

    def scene_mouse_move(self, event: Any) -> None:
        if self.rubber_band and self.rubber_band.isVisible():
            # 1. Aktualizace geometrie výběrového rámečku
            current_screen_pos = event.screenPos()
            origin_point = self.origin.toPoint() if hasattr(self.origin, 'toPoint') else self.origin
            curr_point = current_screen_pos.toPoint() if hasattr(current_screen_pos, 'toPoint') else current_screen_pos
            
            rect = QRect(self.view.mapFromGlobal(origin_point), 
                         self.view.mapFromGlobal(curr_point)).normalized()
            self.rubber_band.setGeometry(rect)
            
            # 2. DYNAMICKÝ VÝBĚR (Interaktivní označování během tažení)
            selection_rect = self.view.mapToScene(rect).boundingRect()
            
            # Projdeme všechny položky s daty (masky)
            for item in self.scene.items():
                if hasattr(item, 'data'):
                    # Pokud je maska v rámečku, označíme ji, jinak odznačíme
                    is_in_rect = selection_rect.intersects(item.sceneBoundingRect())
                    item.setSelected(is_in_rect)
            
            event.accept()
            return

    def scene_mouse_release(self, event: Any) -> None:
        if self.rubber_band and self.rubber_band.isVisible():
            # Rámeček už vše označil v reálném čase během move, stačí ho jen skrýt
            self.rubber_band.hide()
            self.origin = QPointF()
            event.accept()
            return

        if self.drawing_item:
            # ... (zbytek logiky drawing_item zůstává stejný)
            if self.tool_selector.currentText() == "Lasso (Volná ruka)":
                self.lasso_path.closeSubpath()
                self.drawing_item.setPath(self.lasso_path)
            
            bounds = self.drawing_item.boundingRect()
            if bounds.width() < 5 and bounds.height() < 5:
                self.scene.removeItem(self.drawing_item)
            
            self.drawing_item = None
            self.lasso_path = None
        QGraphicsScene.mouseReleaseEvent(self.scene, event)

    def on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Obrázek", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.current_image_path = path
            pixmap = QPixmap(path)
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def run_ocr_auto(self) -> None:
        if not self.current_image_path: return
        
        if not ANKI_AVAILABLE:
            # Standalone mode - přímé volání
            boxes = self.ocr.get_text_boxes(self.current_image_path)
            self._handle_ocr_results(boxes)
            return

        # Anki mode - asynchronní QueryOp
        self.occlude_btn.setEnabled(False)
        self.occlude_btn.setText("Skenuji...")
        
        op = QueryOp(
            parent=self,
            op=lambda col: self.ocr.get_text_boxes(self.current_image_path),
            success=self._handle_ocr_results
        )
        op.with_progress("Probíhá OCR analýza...").run_in_background()

    def _handle_ocr_results(self, boxes: List[Dict[str, Any]]) -> None:
        if ANKI_AVAILABLE:
            self.occlude_btn.setEnabled(True)
            self.occlude_btn.setText("Auto-OCR")
            
        for b in boxes:
            self.scene.addItem(OcclusionRect(MaskData(
                float(b['x']), float(b['y']), float(b['w']), float(b['h']), 
                text=b['text']
            )))

    def on_save_clicked(self) -> None:
        if not self.current_image_path or not self.scene:
            return
            
        all_masks = [i for i in self.scene.items() if hasattr(i, 'data')]
        if not all_masks:
            QMessageBox.warning(self, "Uložit", "Nejsou definovány žádné masky.")
            return

        if not ANKI_AVAILABLE or not self.anki:
            QMessageBox.information(self, "Export", "Standalone režim: Export do Anki není dostupný.")
            return

        try:
            exporter = SVGExporter(self.scene.width(), self.scene.height())
            
            # Seskupení masek pro generování karet
            # key: group_id (nebo uuid pro neseskupené), value: list of indices in all_masks
            groups: Dict[str, List[int]] = {}
            for i, mask in enumerate(all_masks):
                gid = mask.data.group_id if mask.data.group_id else f"single-{uuid.uuid4().hex}"
                if gid not in groups:
                    groups[gid] = []
                groups[gid].append(i)
            
            # Seznam skupin (list of lists of indices)
            grouped_indices = list(groups.values())
            
            # Generování OM SVG (Všechny masky)
            om_svg = exporter.generate_om(all_masks)
            
            # Generování Q a A pro každou skupinu (kartu)
            q_svgs = []
            a_svgs = []
            # Připravíme data pro Remarks (spojíme texty ze všech masek ve skupině)
            card_data = []
            
            for indices in grouped_indices:
                q_svgs.append(exporter.generate_q(all_masks, indices))
                a_svgs.append(exporter.generate_a(all_masks, indices))
                
                # Spojení textů pro Remarks
                texts = [all_masks[idx].data.text for idx in indices if all_masks[idx].data.text]
                card_data.append(" | ".join(texts) if texts else "")
            
            # Uložení do Anki
            count = self.anki.save_assets_and_notes(
                self.current_image_path, om_svg, q_svgs, a_svgs, card_data
            )
            
            QMessageBox.information(self, "Hotovo", f"Úspěšně vytvořeno {count} karet v Anki.")
            self.accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se uložit karty: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
