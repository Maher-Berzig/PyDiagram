# ruler.py
"""
Manual 3.3: "Rulers appear on the top and the left of the Dia canvas.
They show... how large your canvas is... Each ruler has an arrow that
moves along the ruler to show the exact coordinate of the mouse
pointer."

Ticks are drawn directly in scene units (this clone has no notion of
centimeters/DPI - manual 3.3's discussion of that mapping doesn't
apply to a from-scratch clone with its own arbitrary scene units).
"""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget

BREADTH = 22

# Ticks are spaced in scene units, at whatever one of these steps
# keeps labeled ticks comfortably far apart at the current zoom.
_STEP_CANDIDATES = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
_MIN_LABEL_SPACING_PX = 45


class RulerWidget(QWidget):

    def __init__(self, view, orientation, parent=None):
        super().__init__(parent)

        self.view = view
        self.orientation = orientation  # "horizontal" or "vertical"
        self.marker_scene_pos = None

        if orientation == "horizontal":
            self.setFixedHeight(BREADTH)
        else:
            self.setFixedWidth(BREADTH)

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def set_marker(self, scene_pos):
        self.marker_scene_pos = scene_pos
        self.update()

    def clear_marker(self):
        self.marker_scene_pos = None
        self.update()

    def _pick_step(self):
        # Distance (in scene units) that _MIN_LABEL_SPACING_PX screen
        # pixels currently corresponds to, given the view's zoom.
        zoom = getattr(self.view, "_zoom", 1.0) or 1.0
        min_scene_gap = _MIN_LABEL_SPACING_PX / zoom

        for step in _STEP_CANDIDATES:
            if step >= min_scene_gap:
                return step

        return _STEP_CANDIDATES[-1]

    def paintEvent(self, event):
        painter = QPainter(self)

        try:
            painter.fillRect(self.rect(), QColor("#f0f0f0"))
            painter.setPen(QPen(QColor("#888888"), 1))

            if self.orientation == "horizontal":
                painter.drawLine(0, BREADTH - 1, self.width(), BREADTH - 1)
            else:
                painter.drawLine(BREADTH - 1, 0, BREADTH - 1, self.height())

            top_left = self.view.mapToScene(0, 0)
            bottom_right = self.view.mapToScene(
                self.view.viewport().width(),
                self.view.viewport().height(),
            )

            step = self._pick_step()
            minor = step / 5

            if self.orientation == "horizontal":
                self._draw_horizontal(painter, top_left.x(), bottom_right.x(), step, minor)
            else:
                self._draw_vertical(painter, top_left.y(), bottom_right.y(), step, minor)

            self._draw_marker(painter)
        finally:
            painter.end()

    def _scene_x_to_widget(self, x):
        return self.view.mapFromScene(x, 0).x()

    def _scene_y_to_widget(self, y):
        return self.view.mapFromScene(0, y).y()

    def _draw_horizontal(self, painter, start, end, step, minor):
        painter.setPen(QPen(QColor("#aaaaaa"), 1))

        first_minor = int(start // minor) * minor

        x = first_minor
        while x <= end:
            px = self._scene_x_to_widget(x)
            painter.drawLine(int(px), BREADTH - 6, int(px), BREADTH - 1)
            x += minor

        painter.setPen(QPen(QColor("#404040"), 1))

        first_major = int(start // step) * step

        x = first_major
        while x <= end:
            px = self._scene_x_to_widget(x)
            painter.drawLine(int(px), 2, int(px), BREADTH - 1)
            painter.drawText(
                int(px) + 2, BREADTH - 12, str(int(x))
            )
            x += step

    def _draw_vertical(self, painter, start, end, step, minor):
        painter.setPen(QPen(QColor("#aaaaaa"), 1))

        first_minor = int(start // minor) * minor

        y = first_minor
        while y <= end:
            py = self._scene_y_to_widget(y)
            painter.drawLine(BREADTH - 6, int(py), BREADTH - 1, int(py))
            y += minor

        painter.setPen(QPen(QColor("#404040"), 1))

        first_major = int(start // step) * step

        y = first_major
        while y <= end:
            py = self._scene_y_to_widget(y)
            painter.drawLine(2, int(py), BREADTH - 1, int(py))

            painter.save()
            painter.translate(BREADTH - 12, int(py) - 2)
            painter.rotate(-90)
            painter.drawText(0, 0, str(int(y)))
            painter.restore()

            y += step

    def _draw_marker(self, painter):
        if self.marker_scene_pos is None:
            return

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#d92626"))

        if self.orientation == "horizontal":
            px = self._scene_x_to_widget(self.marker_scene_pos.x())
            triangle = [
                (px, BREADTH - 1),
                (px - 4, BREADTH - 8),
                (px + 4, BREADTH - 8),
            ]
        else:
            py = self._scene_y_to_widget(self.marker_scene_pos.y())
            triangle = [
                (BREADTH - 1, py),
                (BREADTH - 8, py - 4),
                (BREADTH - 8, py + 4),
            ]

        painter.drawPolygon(
            QPolygonF([QPointF(x, y) for x, y in triangle])
        )


class RulerCorner(QWidget):
    """The small blank square where the two rulers meet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BREADTH, BREADTH)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f0f0f0"))
        painter.end()
