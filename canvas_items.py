from typing import Any, Dict, Optional, List
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItem
from PyQt6.QtGui import QBrush, QColor, QPen, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF
from dataclasses import dataclass

@dataclass
class MaskData:
    """Datový model pro jednu masku."""
    x: float
    y: float
    w: float
    h: float
    shape_type: str = "rect" # rect, ellipse, path
    path_data: Optional[str] = None # Pro Lasso/Path v SVG formátu
    group_id: Optional[str] = None
    text: str = ""

class ResizeHandle(QGraphicsRectItem):
    SIZE = 14.0
    def __init__(self, parent: QGraphicsItem, position: str) -> None:
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE, parent)
        self.position = position
        self.setBrush(QBrush(Qt.GlobalColor.white))
        self.setPen(QPen(Qt.GlobalColor.blue, 1.5))
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        
        cursors = {
            'topleft': Qt.CursorShape.SizeFDiagCursor, 'topright': Qt.CursorShape.SizeBDiagCursor,
            'bottomleft': Qt.CursorShape.SizeBDiagCursor, 'bottomright': Qt.CursorShape.SizeFDiagCursor
        }
        self.setCursor(cursors.get(position, Qt.CursorShape.ArrowCursor))

class BaseOcclusionItem:
    """Mixin pro společnou logiku masek."""
    def init_occlusion(self, data: MaskData):
        self.data = data
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.default_brush = QBrush(QColor(255, 255, 0, 100))
        self.selected_brush = QBrush(QColor(255, 0, 0, 150))
        self.grouped_brush = QBrush(QColor(0, 255, 255, 100))
        self.setBrush(self.default_brush)
        self.setPen(QPen(Qt.GlobalColor.black, 1))

    def update_style(self):
        if self.isSelected():
            self.setBrush(self.selected_brush)
        elif self.data.group_id:
            self.setBrush(self.grouped_brush)
        else:
            self.setBrush(self.default_brush)

class OcclusionRect(QGraphicsRectItem, BaseOcclusionItem):
    def __init__(self, data: MaskData) -> None:
        super().__init__(0, 0, data.w, data.h)
        self.setPos(data.x, data.y)
        self.init_occlusion(data)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.data.x, self.data.y = self.x(), self.y()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_style()
        return super().itemChange(change, value)

class OcclusionEllipse(QGraphicsEllipseItem, BaseOcclusionItem):
    def __init__(self, data: MaskData) -> None:
        super().__init__(0, 0, data.w, data.h)
        self.setPos(data.x, data.y)
        self.init_occlusion(data)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.data.x, self.data.y = self.x(), self.y()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_style()
        return super().itemChange(change, value)

class OcclusionPath(QGraphicsPathItem, BaseOcclusionItem):
    """Pro Lasso tool."""
    def __init__(self, data: MaskData, path: QPainterPath) -> None:
        super().__init__(path)
        self.init_occlusion(data)
        
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_style()
        return super().itemChange(change, value)
