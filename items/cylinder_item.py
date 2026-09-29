# cylinder_item.py
"""
The "Database" flowchart symbol (manual 6.1.1.14) - a cylinder: an
ellipse cap on top, straight sides, and a curved bottom. Resize and
connection-point behavior mirror RectangleItem/DiamondItem, operating
on the same bounding self._rect.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPainterPath, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for

# How tall the top/bottom ellipse caps are, as a fraction of the
# shape's own height (clamped so very short/wide cylinders still work).
CAP_RATIO = 0.25


class CylinderItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 120, 100),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#D9E8FF")
        self.border_color = QColor("#202020")
        self.border_width = 2

    def _cap_height(self):
        return min(self._rect.height() * CAP_RATIO, self._rect.width() / 2)

    def _build_path(self):
        r = self._rect
        cap = self._cap_height()

        path = QPainterPath()

        top_cap = QRectF(r.left(), r.top(), r.width(), cap * 2)
        bottom_cap = QRectF(r.left(), r.bottom() - cap * 2, r.width(), cap * 2)

        path.moveTo(r.left(), r.top() + cap)
        path.arcTo(top_cap, 180, -180)
        path.lineTo(r.right(), r.bottom() - cap)
        path.arcTo(bottom_cap, 0, -180)
        path.lineTo(r.left(), r.top() + cap)
        path.closeSubpath()

        return path

    def boundingRect(self):
        extra = self.border_width / 2 + 4

        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        r = self._rect
        cap = self._cap_height()

        return [
            QPointF(r.center().x(), r.top()),
            QPointF(r.left(), r.top() + cap),
            QPointF(r.right(), r.top() + cap),
            QPointF(r.left(), r.center().y()),
            r.center(),
            QPointF(r.right(), r.center().y()),
            QPointF(r.left(), r.bottom() - cap),
            QPointF(r.right(), r.bottom() - cap),
            QPointF(r.center().x(), r.bottom()),
        ]

    def paint(self, painter, option, widget=None):
        path = self._build_path()

        painter.setPen(QPen(self.border_color, self.border_width))
        painter.setBrush(brush_for(self.fill_color))
        painter.drawPath(path)

        # The seam where the top cap meets the body reads better with
        # a visible line, same as real cylinder-styled database icons.
        cap = self._cap_height()
        r = self._rect
        painter.drawArc(
            QRectF(r.left(), r.top(), r.width(), cap * 2), 0, -180 * 16
        )

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

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

        if rect.height() < max(self.MIN_HEIGHT, 40):
            rect.setHeight(max(self.MIN_HEIGHT, 40))

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()
