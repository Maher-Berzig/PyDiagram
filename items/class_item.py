# class_item.py
"""
The UML "Class" symbol (manual 6.1.1.29): a box divided into name,
attributes, and operations compartments - simplified from Dia's own
multi-tab Class Properties dialog (Figure 6.11) down to three plain
text fields, but the same three compartments.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QFont, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for

NAME_COMPARTMENT_HEIGHT = 30


class ClassItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 180, 140),
        class_name="ClassName",
        attributes="",
        operations="",
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#FFFFFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

        self.class_name = class_name
        self.attributes = attributes
        self.operations = operations

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

    def _compartment_rects(self):
        r = self._rect

        name_h = min(NAME_COMPARTMENT_HEIGHT, r.height() * 0.34)
        remaining = r.height() - name_h

        attr_lines = self.attributes.splitlines() or [""]
        op_lines = self.operations.splitlines() or [""]
        total_lines = max(len(attr_lines) + len(op_lines), 1)

        attr_h = remaining * (len(attr_lines) / total_lines)
        op_h = remaining - attr_h

        name_rect = QRectF(r.left(), r.top(), r.width(), name_h)
        attr_rect = QRectF(r.left(), name_rect.bottom(), r.width(), attr_h)
        op_rect = QRectF(r.left(), attr_rect.bottom(), r.width(), op_h)

        return name_rect, attr_rect, op_rect

    def paint(self, painter, option, widget=None):
        r = self._rect
        name_rect, attr_rect, op_rect = self._compartment_rects()

        painter.setPen(QPen(self.border_color, self.border_width))
        painter.setBrush(brush_for(self.fill_color))
        painter.drawRect(r)

        painter.drawLine(
            QPointF(r.left(), name_rect.bottom()),
            QPointF(r.right(), name_rect.bottom())
        )
        painter.drawLine(
            QPointF(r.left(), attr_rect.bottom()),
            QPointF(r.right(), attr_rect.bottom())
        )

        name_font = QFont("Sans Serif", 11)
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.setPen(QPen(QColor("#202020")))
        painter.drawText(name_rect, Qt.AlignCenter, self.class_name)

        body_font = QFont("Sans Serif", 9)
        painter.setFont(body_font)
        painter.drawText(
            attr_rect.adjusted(6, 2, -4, -2),
            Qt.AlignLeft | Qt.AlignTop,
            self.attributes
        )
        painter.drawText(
            op_rect.adjusted(6, 2, -4, -2),
            Qt.AlignLeft | Qt.AlignTop,
            self.operations
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

        if rect.height() < max(self.MIN_HEIGHT, 60):
            rect.setHeight(max(self.MIN_HEIGHT, 60))

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()
