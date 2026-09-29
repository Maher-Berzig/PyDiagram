# diamond_item.py
"""
The "Decision" flowchart symbol (manual 6.1.1.14) - a rhombus. Its
geometry, resize, and connection-point behavior all mirror
RectangleItem exactly, operating on the same bounding self._rect;
only paint() and connection_points() differ, since the actual drawn
shape is a diamond inscribed in that rect rather than the rect itself.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen, QPolygonF

from .diagram_item import DiagramItem
from .color_picker import brush_for


class DiamondItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 140, 90),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#FFE8B3")
        self.border_color = QColor("#202020")
        self.border_width = 2

    def _vertices(self):
        r = self._rect

        return [
            QPointF(r.center().x(), r.top()),      # top
            QPointF(r.right(), r.center().y()),    # right
            QPointF(r.center().x(), r.bottom()),   # bottom
            QPointF(r.left(), r.center().y()),     # left
        ]

    def boundingRect(self):
        extra = self.border_width / 2 + 4

        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        top, right, bottom, left = self._vertices()
        r = self._rect

        def midpoint(a, b):
            return QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)

        return [
            top,
            midpoint(top, right),
            right,
            midpoint(right, bottom),
            bottom,
            midpoint(bottom, left),
            left,
            midpoint(left, top),
            r.center(),
        ]

    def paint(self, painter, option, widget=None):
        polygon = QPolygonF(self._vertices())

        painter.setPen(QPen(self.border_color, self.border_width))
        painter.setBrush(brush_for(self.fill_color))
        painter.drawPolygon(polygon)

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(polygon)

        self._paint_connection_points(painter)

    def resize_from_handle(self, handle, delta, original):
        rect = QRectF(original)

        if handle == "top_left":
            rect.setTopLeft(original.topLeft() + delta)
        elif handle == "top_right":
            rect.setTopRight(original.topRight() + delta)
        elif handle == "bottom_left":
            rect.setBottomLeft(original.bottomLeft() + delta)
        elif handle == "bottom_right":
            rect.setBottomRight(original.bottomRight() + delta)

        if rect.width() < self.MIN_WIDTH:
            rect.setWidth(self.MIN_WIDTH)

        if rect.height() < self.MIN_HEIGHT:
            rect.setHeight(self.MIN_HEIGHT)

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()
