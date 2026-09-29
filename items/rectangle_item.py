# rectangle_item.py
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen, QPainterPath
from PyQt5.QtWidgets import QGraphicsItem

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .line_item import build_dashed_pen


class RectangleItem(DiagramItem):

    def __init__(
        self,
        rect=QRectF(0, 0, 120, 80),
        parent=None
    ):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#DCEBFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

        # Manual 5.1.11.3: border style/dash-length, same options as a
        # Line's (LINE_STYLES in line_item.py) - "solid" behaves
        # exactly as before, so this doesn't change any existing
        # diagram's appearance.
        self.line_style = "solid"
        self.dash_length = 10.0

        # Manual 5.1.2, "Box": Corner Rounding (0 = square corners) and
        # Draw Background (fill the interior, or leave it transparent).
        # Corner radii, clockwise from the top-left: 1 = top-left,
        # 2 = top-right, 3 = bottom-right, 4 = bottom-left (0 = square).
        self._corner_radii = [0, 0, 0, 0]
        self.draw_background = True

    # -- per-corner radii ------------------------------------------------

    def _set_corner_radius(self, index, value):
        self._corner_radii[index] = max(0, int(round(float(value))))
        self.update()

    @property
    def corner_radius_1(self):
        return self._corner_radii[0]

    @corner_radius_1.setter
    def corner_radius_1(self, value):
        self._set_corner_radius(0, value)

    @property
    def corner_radius_2(self):
        return self._corner_radii[1]

    @corner_radius_2.setter
    def corner_radius_2(self, value):
        self._set_corner_radius(1, value)

    @property
    def corner_radius_3(self):
        return self._corner_radii[2]

    @corner_radius_3.setter
    def corner_radius_3(self, value):
        self._set_corner_radius(2, value)

    @property
    def corner_radius_4(self):
        return self._corner_radii[3]

    @corner_radius_4.setter
    def corner_radius_4(self, value):
        self._set_corner_radius(3, value)

    @property
    def corner_radii(self):
        return list(self._corner_radii)

    @corner_radii.setter
    def corner_radii(self, values):
        values = list(values)[:4]
        values += [0] * (4 - len(values))
        self._corner_radii = [max(0, int(round(float(v)))) for v in values]
        self.update()

    @property
    def corner_radius(self):
        """Legacy single radius: reads the largest corner, and setting
        it rounds all four corners equally (old files/snapshots)."""

        return max(self._corner_radii)

    @corner_radius.setter
    def corner_radius(self, value):
        self.corner_radii = [value] * 4

    def _corner_path(self):
        """Closed outline with a separate circular radius per corner."""

        r = self._rect
        limit = min(r.width(), r.height()) / 2.0
        tl, tr, br, bl = [
            max(0.0, min(float(v), limit)) for v in self._corner_radii
        ]

        path = QPainterPath()
        path.moveTo(r.left() + tl, r.top())
        path.lineTo(r.right() - tr, r.top())

        if tr:
            path.arcTo(QRectF(r.right() - 2 * tr, r.top(), 2 * tr, 2 * tr), 90, -90)

        path.lineTo(r.right(), r.bottom() - br)

        if br:
            path.arcTo(
                QRectF(r.right() - 2 * br, r.bottom() - 2 * br, 2 * br, 2 * br),
                0, -90,
            )

        path.lineTo(r.left() + bl, r.bottom())

        if bl:
            path.arcTo(QRectF(r.left(), r.bottom() - 2 * bl, 2 * bl, 2 * bl), 270, -90)

        path.lineTo(r.left(), r.top() + tl)

        if tl:
            path.arcTo(QRectF(r.left(), r.top(), 2 * tl, 2 * tl), 180, -90)

        path.closeSubpath()

        return path

    def _draw_outline(self, painter):
        if any(self._corner_radii):
            painter.drawPath(self._corner_path())
        else:
            painter.drawRect(self._rect)

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
        Corners, edge midpoints, and center - matching the Dia manual's
        illustration of a shape's connection "x" marks (4.2.5).
        """

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

    def paint(
        self,
        painter,
        option,
        widget=None
    ):
        painter.setPen(self._build_border_pen())

        painter.setBrush(
            brush_for(self.fill_color) if self.draw_background else Qt.NoBrush
        )

        self._draw_outline(painter)

        if self.isSelected():
            painter.setPen(
                QPen(
                    QColor("#1677ff"),
                    1,
                    Qt.DashLine
                )
            )

            painter.setBrush(Qt.NoBrush)

            self._draw_outline(painter)

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
                original.topRight() +
                delta
            )

        elif handle == "bottom_left":
            rect.setBottomLeft(
                original.bottomLeft() +
                delta
            )

        elif handle == "bottom_right":
            rect.setBottomRight(
                original.bottomRight() +
                delta
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