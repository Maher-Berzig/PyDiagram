# interface_item.py
"""
The UML "Interface" symbol (manual 6.1.1.29) - "lollipop" notation: a
small circle at the end of a short stub line.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for


class InterfaceItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 70, 40),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#FFFFFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

    def _circle_rect(self):
        r = self._rect
        d = min(r.width(), r.height()) * 0.6

        return QRectF(
            r.left() + (r.width() - d) / 2 * 0.4,
            r.top() + (r.height() - d) / 2,
            d, d
        )

    def boundingRect(self):
        extra = self.border_width / 2 + 4
        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        r = self._rect

        return [
            r.topLeft(),
            QPointF(r.center().x(), r.top()),
            r.topRight(),
            QPointF(r.left(), r.center().y()),
            r.center(),
            QPointF(r.right(), r.center().y()),
            r.bottomLeft(),
            QPointF(r.center().x(), r.bottom()),
            r.bottomRight(),
        ]

    def paint(self, painter, option, widget=None):
        r = self._rect
        circle = self._circle_rect()

        painter.setPen(QPen(self.border_color, self.border_width))
        painter.setBrush(brush_for(self.fill_color))
        painter.drawEllipse(circle)
        painter.drawLine(
            QPointF(circle.right(), circle.center().y()),
            QPointF(r.right(), circle.center().y())
        )

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r)

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
