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
        if tool == "Výběr":
            # Pokud klikneme na prázdné místo, zahájíme Rubber Band
            item = self.scene.itemAt(event.scenePos(), self.view.transform())
            # Kontrola zda jsme klikli na pozadí (pixmap) nebo nic
            is_background = not item or (isinstance(item, QGraphicsRectItem) and not hasattr(item, 'data'))
            
            if is_background:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.origin = event.screenPos()
                    if not self.rubber_band:
                        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.view)
                    self.rubber_band.setGeometry(QRect(self.view.mapFromGlobal(self.origin.toPoint()), QSize()))
                    self.rubber_band.show()
                    # Zrušit předchozí výběr
                    self.scene.clearSelection()
                    event.accept()
                    return

            QGraphicsScene.mousePressEvent(self.scene, event)
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
            self.rubber_band.setGeometry(QRect(self.view.mapFromGlobal(self.origin.toPoint()), event.screenPos()).normalized())
            event.accept()
            return

        if not self.drawing_item:
            QGraphicsScene.mouseMoveEvent(self.scene, event)
            return

        curr = event.scenePos()
        
        # 2.2 Boundary Guard - Omezení kreslení na hranice obrázku
        s_rect = self.scene.sceneRect()
        curr.setX(max(s_rect.left(), min(curr.x(), s_rect.right())))
        curr.setY(max(s_rect.top(), min(curr.y(), s_rect.bottom())))
        
        tool = self.tool_selector.currentText()
        
        if tool in ("Obdélník", "Elipsa"):
            rect = QRectF(self.start_point, curr).normalized()
            self.drawing_item.setPos(rect.topLeft())
            self.drawing_item.setRect(0, 0, rect.width(), rect.height())
            if hasattr(self.drawing_item, 'update_handles'):
                self.drawing_item.update_handles()
        elif tool == "Lasso (Volná ruka)" and self.lasso_path:
            self.lasso_path.lineTo(curr)
            self.drawing_item.setPath(self.lasso_path)
        event.accept()

    def scene_mouse_release(self, event: Any) -> None:
        if self.rubber_band and self.rubber_band.isVisible():
            self.rubber_band.hide()
            # Výběr prvků v obdélníku
            rect = self.view.mapToScene(self.rubber_band.geometry()).boundingRect()
            for item in self.scene.items(rect):
                if hasattr(item, 'data'):
                    item.setSelected(True)
            event.accept()
            return

        if self.drawing_item:
            if self.tool_selector.currentText() == "Lasso (Volná ruka)":
                self.lasso_path.closeSubpath()
                self.drawing_item.setPath(self.lasso_path)
            
            # Odstranění příliš malých prvků
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
            
        masks = [i for i in self.scene.items() if hasattr(i, 'data')]
        if not masks:
            QMessageBox.warning(self, "Uložit", "Nejsou definovány žádné masky.")
            return

        if not ANKI_AVAILABLE or not self.anki:
            QMessageBox.information(self, "Export", "Standalone režim: Export do Anki není dostupný.")
            return

        try:
            exporter = SVGExporter(self.scene.width(), self.scene.height())
            
            # Generování OM SVG (Všechny masky)
            om_svg = exporter.generate_om(masks)
            
            # Generování Q a A pro každou masku
            q_svgs = []
            a_svgs = []
            for i in range(len(masks)):
                q_svgs.append(exporter.generate_q(masks, i))
                a_svgs.append(exporter.generate_a(masks, i))
            
            # Uložení do Anki
            count = self.anki.save_assets_and_notes(
                self.current_image_path, om_svg, q_svgs, a_svgs, masks
            )
            
            QMessageBox.information(self, "Hotovo", f"Úspěšně vytvořeno {count} karet v Anki.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se uložit karty: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
