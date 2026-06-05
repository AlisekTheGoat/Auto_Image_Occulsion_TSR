import sys
import os
import uuid
from typing import Optional, List, Any
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QGraphicsView, QGraphicsScene, QFileDialog, QMessageBox, QComboBox, QToolButton
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF

from ocr_handler import OCRHandler
from export_handler import SVGExporter
from canvas_items import MaskData, OcclusionRect, OcclusionEllipse, OcclusionPath

class OcclusionDialog(QDialog):
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Image Occlusion - Lead Architect Edition")
        self.resize(1100, 800)
        self.ocr = OCRHandler()
        self.current_image_path: Optional[str] = None
        self.drawing_item: Optional[Any] = None
        self.lasso_path: Optional[QPainterPath] = None
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
        if tool == "Výběr" or event.button() != Qt.MouseButton.LeftButton:
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
        if not self.drawing_item:
            QGraphicsScene.mouseMoveEvent(self.scene, event)
            return

        curr = event.scenePos()
        tool = self.tool_selector.currentText()
        
        if tool in ("Obdélník", "Elipsa"):
            rect = QRectF(self.start_point, curr).normalized()
            self.drawing_item.setPos(rect.topLeft())
            self.drawing_item.setRect(0, 0, rect.width(), rect.height())
        elif tool == "Lasso (Volná ruka)" and self.lasso_path:
            self.lasso_path.lineTo(curr)
            self.drawing_item.setPath(self.lasso_path)
        event.accept()

    def scene_mouse_release(self, event: Any) -> None:
        if self.drawing_item:
            if tool := self.tool_selector.currentText() == "Lasso (Volná ruka)":
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
        boxes = self.ocr.get_text_boxes(self.current_image_path)
        for b in boxes:
            self.scene.addItem(OcclusionRect(MaskData(float(b['x']), float(b['y']), float(b['w']), float(b['h']), text=b['text'])))

    def on_save_clicked(self) -> None:
        items = [i for i in self.scene.items() if hasattr(i, 'data')]
        if not items: return
        exporter = SVGExporter(self.scene.width(), self.scene.height())
        print(exporter.generate(items))
        QMessageBox.information(self, "Export", "SVG vypsáno do konzole.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OcclusionDialog()
    window.show()
    sys.exit(app.exec())
