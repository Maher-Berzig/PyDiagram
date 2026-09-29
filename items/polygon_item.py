# polygon_item.py
"""
Manual 5.1.4, "Polygon": "any closed shape made up of straight lines.
The polygon tool allows the user to draw any shape with all straight
lines."

The manual doesn't describe Polygon's own interaction model in
detail (unlike Zigzagline/Polyline, which get worked examples with a
right-click menu). This implementation gives it the same right-click
"Add Point"/"Delete Point" pattern those two use for segments, since
a polygon has the same underlying need - changing its vertex count
after the fact - and it keeps the interaction language consistent
across every multi-vertex shape in the app.
"""

from PyQt5.QtCore import QLineF, QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem, QMenu

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .drag_handle_mixin import DraggableHandleMixin
from .line_item import build_dashed_pen

DEFAULT_POINTS = [QPointF(50, 0), QPointF(100, 80), QPointF(0, 80)]


class PolygonVertexHandle(DraggableHandleMixin, QGraphicsRectItem):

    SIZE = 8

    def __init__(self, owner, index):
        super().__init__(
            -self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner
        )

        self.owner = owner
        self.index = index

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(10)

        self.setBrush(QBrush(QColor("#2ea043")))
        self.setPen(QPen(QColor("#202020"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.owner._vertex_dragged(self.index)

        return super().itemChange(change, value)


class PolygonItem(DiagramItem):

    MIN_VERTICES = 3

    def __init__(self, points=None, parent=None):
        super().__init__(parent)

        if not points or len(points) < self.MIN_VERTICES:
            points = DEFAULT_POINTS

        self._points = [QPointF(p) for p in points]

        self.fill_color = QColor("#DCEBFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

        # Manual 5.1.11.3: border style/dash-length, same options as a
        # Line's.
        self.line_style = "solid"
        self.dash_length = 10.0

        self._vertex_handles = []
        self._create_vertex_handles()

    def _build_border_pen(self):
        return build_dashed_pen(
            self.border_color, self.border_width, self.line_style, self.dash_length
        )

    # -- geometry -----------------------------------------------------

    def boundingRect(self):
        extra = self.border_width + PolygonVertexHandle.SIZE

        return QPolygonF(self._points).boundingRect().adjusted(
            -extra, -extra, extra, extra
        )

    def connection_points(self):
        """
        Every vertex, plus the centroid - so a line can connect to
        either a corner or the shape's middle, matching how Rectangle/
        Ellipse expose both their corners and their center.
        """

        if not self._points:
            return []

        cx = sum(p.x() for p in self._points) / len(self._points)
        cy = sum(p.y() for p in self._points) / len(self._points)

        return list(self._points) + [QPointF(cx, cy)]

    def paint(self, painter, option, widget=None):
        painter.setPen(self._build_border_pen())
        painter.setBrush(brush_for(self.fill_color))
        painter.drawPolygon(QPolygonF(self._points))

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(QPolygonF(self._points))

        self._paint_connection_points(painter)


    # -- vertex handles (replace the base class's 4 corner handles) ---

    def _create_vertex_handles(self):
        for i in range(len(self._points)):
            handle = PolygonVertexHandle(self, i)

            # Appended before setPos(): setPos() fires itemChange
            # synchronously, which calls back into _vertex_dragged(i) -
            # if the handle weren't in the list yet, that lookup would
            # be an IndexError on the very first handle created.
            self._vertex_handles.append(handle)

            handle.setPos(self._points[i])
            handle.hide()

    def _create_handles(self):
        for handle in self._vertex_handles:
            handle.show()

    def _remove_handles(self):
        for handle in self._vertex_handles:
            handle.hide()

    def _update_handles(self):
        for i, handle in enumerate(self._vertex_handles):
            handle.setPos(self._points[i])

    def _vertex_dragged(self, index):
        if index >= len(self._vertex_handles) or index >= len(self._points):
            return

        self.prepareGeometryChange()
        self._points[index] = self._vertex_handles[index].pos()
        self.notify_connections()
        self.update()

    # -- add / delete vertex (right-click menu) ------------------------

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_action = menu.addAction("Add Point")
        delete_action = (
            menu.addAction("Delete Point")
            if len(self._points) > self.MIN_VERTICES else None
        )

        chosen = menu.exec_(event.screenPos())

        if chosen is add_action:
            self._add_point_near(event.pos())
        elif delete_action is not None and chosen is delete_action:
            self._delete_point_near(event.pos())

        event.accept()

    def _add_point_near(self, local_pos):
        """Inserts a new vertex into whichever edge is closest to the click."""

        n = len(self._points)
        best_i, best_dist = 0, None

        for i in range(n):
            a, b = self._points[i], self._points[(i + 1) % n]
            dist = _point_to_segment_dist(local_pos, a, b)

            if best_dist is None or dist < best_dist:
                best_dist, best_i = dist, i

        self.prepareGeometryChange()
        self._points.insert(best_i + 1, QPointF(local_pos))
        self._rebuild_vertex_handles()
        self.notify_connections()
        self.update()

    def _delete_point_near(self, local_pos):
        if len(self._points) <= self.MIN_VERTICES:
            return

        idx = min(
            range(len(self._points)),
            key=lambda i: QLineF(local_pos, self._points[i]).length()
        )

        self.prepareGeometryChange()
        del self._points[idx]
        self._rebuild_vertex_handles()
        self.notify_connections()
        self.update()

    def _rebuild_vertex_handles(self):
        for handle in self._vertex_handles:
            if handle.scene() is not None:
                handle.scene().removeItem(handle)

        self._vertex_handles = []
        self._create_vertex_handles()

        if self.isSelected():
            for handle in self._vertex_handles:
                handle.show()


def _point_to_segment_dist(p, a, b):
    length_sq = (b.x() - a.x()) ** 2 + (b.y() - a.y()) ** 2

    if length_sq == 0:
        return QLineF(p, a).length()

    t = max(0.0, min(1.0, (
        (p.x() - a.x()) * (b.x() - a.x())
        + (p.y() - a.y()) * (b.y() - a.y())
    ) / length_sq))

    proj = QPointF(a.x() + t * (b.x() - a.x()), a.y() + t * (b.y() - a.y()))

    return QLineF(p, proj).length()
