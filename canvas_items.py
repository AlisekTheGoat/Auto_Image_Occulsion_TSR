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
    SIZE = 10.0
    def __init__(self, parent: QGraphicsItem, position: str) -> None:
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE, parent)
        self.position = position
        self.setBrush(QBrush(QColor("white")))
        self.setPen(QPen(QColor("blue"), 1.0))
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        self.hide() # Skryté, dokud není rodič vybrán
        
        cursors = {
            'topleft': Qt.CursorShape.SizeFDiagCursor, 'topright': Qt.CursorShape.SizeBDiagCursor,
            'bottomleft': Qt.CursorShape.SizeBDiagCursor, 'bottomright': Qt.CursorShape.SizeFDiagCursor
        }
        self.setCursor(cursors.get(position, Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event: Any) -> None:
        # Uložení počátečního bodu pro výpočet delty
        self.last_mouse_pos = event.scenePos()
        event.accept()

    def mouseMoveEvent(self, event: Any) -> None:
        parent = self.parentItem()
        if not parent: return
        
        curr_mouse_pos = event.scenePos()
        delta = curr_mouse_pos - self.last_mouse_pos
        self.last_mouse_pos = curr_mouse_pos
        
        rect = parent.rect()
        pos = parent.pos()
        
        # Výpočet nových rozměrů na základě pozice handle
        # Používáme delta posun pro plynulost
        if self.position == 'topleft':
            pos += delta
            rect.setWidth(rect.width() - delta.x())
            rect.setHeight(rect.height() - delta.y())
        elif self.position == 'topright':
            pos.setY(pos.y() + delta.y())
            rect.setWidth(rect.width() + delta.x())
            rect.setHeight(rect.height() - delta.y())
        elif self.position == 'bottomleft':
            pos.setX(pos.x() + delta.x())
            rect.setWidth(rect.width() - delta.x())
            rect.setHeight(rect.height() + delta.y())
        elif self.position == 'bottomright':
            rect.setWidth(rect.width() + delta.x())
            rect.setHeight(rect.height() + delta.y())
        
        # Boundary Guard (Minimální velikost 5x5)
        if rect.width() > 5 and rect.height() > 5:
            parent.setPos(pos)
            parent.setRect(0, 0, rect.width(), rect.height())
            parent.update_handles()
        
        event.accept()

class BaseOcclusionItem:
    """Mixin pro společnou logiku masek."""
    def init_occlusion(self, data: MaskData, has_handles: bool = True):
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

        # Inicializace handles pouze pokud jsou vyžadovány
        if has_handles:
            self.handles = {
                'topleft': ResizeHandle(self, 'topleft'),
                'topright': ResizeHandle(self, 'topright'),
                'bottomleft': ResizeHandle(self, 'bottomleft'),
                'bottomright': ResizeHandle(self, 'bottomright')
            }
            self.update_handles()

    def update_style(self):
        selected = self.isSelected()
        if selected:
            self.setBrush(self.selected_brush)
        elif self.data.group_id:
            self.setBrush(self.grouped_brush)
        else:
            self.setBrush(self.default_brush)
        
        # Zobrazení/skrytí handles
        if hasattr(self, 'handles'):
            for h in self.handles.values():
                h.setVisible(selected)

    def update_handles(self):
        if not hasattr(self, 'handles'): return
        # Pro Rect a Ellipse používáme rect(), pro ostatní boundingRect()
        r = self.rect() if hasattr(self, 'rect') else self.boundingRect()
        self.handles['topleft'].setPos(r.topLeft())
        self.handles['topright'].setPos(r.topRight())
        self.handles['bottomleft'].setPos(r.bottomLeft())
        self.handles['bottomright'].setPos(r.bottomRight())
        
        # Sync dat
        self.data.x, self.data.y = self.x(), self.y()
        self.data.w, self.data.h = r.width(), r.height()

    def apply_boundary_guard(self, new_pos: QPointF) -> QPointF:
        """Zamezí masekám opustit plátno (velikost obrázku)."""
        scene = self.scene()
        if not scene: return new_pos
        
        s_rect = scene.sceneRect()
        item_rect = self.boundingRect()
        
        x = max(s_rect.left(), min(new_pos.x(), s_rect.right() - item_rect.width()))
        y = max(s_rect.top(), min(new_pos.y(), s_rect.bottom() - item_rect.height()))
        
        return QPointF(x, y)

class OcclusionRect(QGraphicsRectItem, BaseOcclusionItem):
    def __init__(self, data: MaskData) -> None:
        super().__init__(0, 0, data.w, data.h)
        self.setPos(data.x, data.y)
        self.init_occlusion(data)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 2.2 Boundary Guard při posunu
            return self.apply_boundary_guard(value)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
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
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return self.apply_boundary_guard(value)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.data.x, self.data.y = self.x(), self.y()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_style()
        return super().itemChange(change, value)

class OcclusionPath(QGraphicsPathItem, BaseOcclusionItem):
    """Pro Lasso tool (Volná ruka)."""
    def __init__(self, data: MaskData, path: QPainterPath) -> None:
        super().__init__(path)
        self.init_occlusion(data, has_handles=False)
        self._path = path
        
    def setPath(self, path: QPainterPath) -> None:
        super().setPath(path)
        self._path = path
        # Aktualizace bounding boxu v datech
        rect = path.boundingRect()
        self.data.x, self.data.y = rect.x(), rect.y()
        self.data.w, self.data.h = rect.width(), rect.height()

    def path(self) -> QPainterPath:
        return self._path

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return self.apply_boundary_guard(value)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.data.x, self.data.y = self.x(), self.y()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_style()
        return super().itemChange(change, value)
