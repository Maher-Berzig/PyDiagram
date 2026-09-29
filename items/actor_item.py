# actor_item.py
"""
The UML "Actor" symbol (manual 6.1.1.29) - a stick figure. Geometry
is derived proportionally from the bounding self._rect, same resize/
connection-point pattern as the other simple shapes.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for


class ActorItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 60, 110),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#FFFFFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

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
        w = r.width()
        h = r.height()
        cx = r.center().x()

        head_d = min(w * 0.5, h * 0.28)
        head_rect = QRectF(cx - head_d / 2, r.top(), head_d, head_d)

        neck_y = r.top() + head_d
        hip_y = r.top() + h * 0.62
        foot_y = r.bottom()
        arm_y = neck_y + (hip_y - neck_y) * 0.25

        pen = QPen(self.border_color, self.border_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(brush_for(self.fill_color))

        painter.drawEllipse(head_rect)

        painter.drawLine(QPointF(cx, neck_y), QPointF(cx, hip_y))
        painter.drawLine(QPointF(r.left(), arm_y), QPointF(r.right(), arm_y))
        painter.drawLine(QPointF(cx, hip_y), QPointF(r.left(), foot_y))
        painter.drawLine(QPointF(cx, hip_y), QPointF(r.right(), foot_y))

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
