# ellipse_item.py

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .line_item import build_dashed_pen


class EllipseItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 120, 80),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#DFF5E1")
        self.border_color = QColor("#202020")
        self.border_width = 2

        # Manual 5.1.11.3: border style/dash-length, same options as a
        # Line's.
        self.line_style = "solid"
        self.dash_length = 10.0

    def _build_border_pen(self):
        return build_dashed_pen(
            self.border_color, self.border_width, self.line_style, self.dash_length
        )

    def boundingRect(self):
        extra = self.border_width / 2 + 4

        return self._rect.adjusted(
            -extra,
            -extra,
            extra,
            extra
        )

    def connection_points(self):
        """
        Nine positions on the ellipse itself: the four cardinal points
        already sit on the curve (the bounding box's own edge
        midpoints), and the four "corner" ones now do too - the
        ellipse's own points at 45 degrees, rather than the bounding
        box's literal corners, which sit outside an ellipse's actual
        outline.
        """

        r = self._rect
        cx, cy = r.center().x(), r.center().y()
        rx, ry = r.width() / 2, r.height() / 2
        k = 0.7071067811865476  # cos(45deg) == sin(45deg)

        return [
            QPointF(cx - rx * k, cy - ry * k),
            QPointF(cx, cy - ry),
            QPointF(cx + rx * k, cy - ry * k),
            QPointF(cx - rx, cy),
            QPointF(cx, cy),
            QPointF(cx + rx, cy),
            QPointF(cx - rx * k, cy + ry * k),
            QPointF(cx, cy + ry),
            QPointF(cx + rx * k, cy + ry * k),
        ]

    def paint(
        self,
        painter,
        option,
        widget=None
    ):
        painter.setPen(self._build_border_pen())

        painter.setBrush(
            brush_for(self.fill_color)
        )

        painter.drawEllipse(self._rect)

        if self.isSelected():
            painter.setPen(
                QPen(
                    QColor("#1677ff"),
                    1,
                    Qt.DashLine
                )
            )

            painter.setBrush(Qt.NoBrush)

            painter.drawEllipse(self._rect)

        self._paint_connection_points(painter)

    def resize_from_handle(
        self,
        handle,
        delta,
        original
    ):
        rect = QRectF(original)

        if handle == "top_left":
            rect.setTopLeft(
                original.topLeft() + delta
            )

        elif handle == "top_right":
            rect.setTopRight(
                original.topRight() + delta
            )

        elif handle == "bottom_left":
            rect.setBottomLeft(
                original.bottomLeft() + delta
            )

        elif handle == "bottom_right":
            rect.setBottomRight(
                original.bottomRight() + delta
            )

        if rect.width() < self.MIN_WIDTH:
            rect.setWidth(self.MIN_WIDTH)

        if rect.height() < self.MIN_HEIGHT:
            rect.setHeight(self.MIN_HEIGHT)

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()