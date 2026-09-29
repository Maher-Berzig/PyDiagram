# polyline_item.py
"""
Manual 5.1.9, "Polyline": "multiple segments like a zigzagline, but
can have turns of any angle. A Polyline starts with one segment. You
add more segments by right-clicking and selecting Add segment from
the menu... Corner radius value between 0 and 10.00, where 0 = sharp
corners and 10.00 = maximally-rounded corners."

Connects at its two endpoints exactly like Line does (5.1.6/4.2.5) -
interior vertices are plain, non-connecting bend points. Rather than
re-implementing that connection machinery, this class reuses
LineItem's methods directly (class-level aliasing below): they only
touch self._p1/_p2, self._h1/_h2, self._start_conn/_end_conn, and
self._position_handles() - all of which this class also provides (the
first two as properties/aliases over the point list), so the exact
same tested code runs correctly here via ordinary Python duck typing.

Zigzagline (5.1.8, in zigzagline_item.py) is a subclass adding
autoroute and orthogonal-path computation.
"""

from PyQt5.QtCore import QLineF, QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainterPath, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem, QMenu

from .diagram_item import DiagramItem
from .line_item import ARROW_LENGTH, LineItem
from .drag_handle_mixin import DraggableHandleMixin

CORNER_RADIUS_MAX_PX = 20.0  # on-screen radius at corner_radius == 10.0


class MultiPointHandle(DraggableHandleMixin, QGraphicsRectItem):
    """
    One draggable vertex. Functionally identical to LineEndHandle for
    the two endpoints (green/red connection-state coloring); interior
    handles never call set_connected(True) since they don't connect.
    """

    SIZE = 8

    def __init__(self, owner, index):
        super().__init__(
            -self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner
        )

        self.owner = owner
        self.index = index
        self._detached = False

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(10)

        self.set_connected(False)

    def set_connected(self, connected):
        color = QColor("#d92626") if connected else QColor("#2ea043")
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#202020"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self._detached:
            self.owner._vertex_dragged(self.index)

        return super().itemChange(change, value)


class PolylineItem(DiagramItem):

    MIN_POINTS = 2

    def __init__(self, points=None, parent=None):
        super().__init__(parent)

        if not points or len(points) < self.MIN_POINTS:
            points = [QPointF(0, 0), QPointF(100, 0)]

        self._points = [QPointF(p) for p in points]

        self.pen_color = QColor("#202020")
        self.pen_width = 2
        self.line_style = "solid"
        self.dash_length = 10.0
        self.start_arrow = "none"
        self.end_arrow = "none"
        self.start_arrow_size = 1.0
        self.end_arrow_size = 1.0

        # Manual 5.1.8/5.1.9: 0 (sharp) to 10.00 (maximally rounded).
        self.corner_radius = 0.0

        self._start_conn = None
        self._end_conn = None

        # Guards against re-entrant _vertex_dragged calls while
        # _rebuild_vertex_handles() is (re)creating handle objects -
        # setPos() on a freshly-created handle fires itemChange just
        # like a real drag would, which would otherwise call back into
        # work (Zigzagline's _reroute() in particular) that itself
        # rebuilds handles, infinitely.
        self._rebuilding_handles = False

        self._vertex_handles = []
        self._create_vertex_handles()

    # -- endpoints as a 2-point-line-shaped view onto the point list --
    # (what LineItem's borrowed methods below actually read/write)

    @property
    def _p1(self):
        return self._points[0]

    @_p1.setter
    def _p1(self, value):
        self._points[0] = value

    @property
    def _p2(self):
        return self._points[-1]

    @_p2.setter
    def _p2(self, value):
        self._points[-1] = value

    # Same tested implementations as LineItem, applying here via
    # ordinary duck typing - see the module docstring.
    set_point = LineItem.set_point
    _try_connect = LineItem._try_connect
    _find_connection_target = LineItem._find_connection_target
    _find_snap_to_object_target = LineItem._find_snap_to_object_target
    _set_connection = LineItem._set_connection
    update_connection_endpoint = LineItem.update_connection_endpoint
    clear_connection = LineItem.clear_connection
    detach = LineItem.detach
    _build_pen = LineItem._build_pen
    _paint_arrow = LineItem._paint_arrow

    # -- geometry -----------------------------------------------------

    def boundingRect(self):
        extra = self.pen_width + MultiPointHandle.SIZE + ARROW_LENGTH * max(
            self.start_arrow_size, self.end_arrow_size, 1.0
        )

        return QPolygonF(self._points).boundingRect().adjusted(
            -extra, -extra, extra, extra
        )

    def connection_points(self):
        # A line isn't itself a connection target for other lines -
        # matches LineItem, which doesn't override this either.
        return []

    def _path(self):
        """
        The visible outline: straight segments, or - if corner_radius
        is set - each interior joint replaced with a rounded curve.
        Approximated by trimming back along each adjacent segment and
        joining with a quadratic curve, rather than true circular-arc
        corner math - simple, and looks right at every radius.
        """

        path = QPainterPath(self._points[0])
        n = len(self._points)

        if self.corner_radius <= 0 or n < 3:
            for p in self._points[1:]:
                path.lineTo(p)

            return path

        radius = (self.corner_radius / 10.0) * CORNER_RADIUS_MAX_PX

        for i in range(1, n - 1):
            prev_p, cur, next_p = (
                self._points[i - 1], self._points[i], self._points[i + 1]
            )

            in_len = QLineF(prev_p, cur).length()
            out_len = QLineF(cur, next_p).length()
            r_in = min(radius, in_len / 2)
            r_out = min(radius, out_len / 2)

            in_dir = _unit(cur - prev_p)
            out_dir = _unit(next_p - cur)

            enter = cur - in_dir * r_in
            leave = cur + out_dir * r_out

            path.lineTo(enter)
            path.quadTo(cur, leave)

        path.lineTo(self._points[-1])

        return path

    def paint(self, painter, option, widget=None):
        pen = self._build_pen()

        if self.isSelected():
            pen.setColor(QColor("#1677ff"))

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._path())

        arrow_color = pen.color()

        if len(self._points) >= 2 and self._points[0] != self._points[1]:
            self._paint_arrow(
                painter, self._points[0], self._points[0] - self._points[1],
                self.start_arrow, arrow_color, self.start_arrow_size
            )

        if len(self._points) >= 2 and self._points[-1] != self._points[-2]:
            self._paint_arrow(
                painter, self._points[-1], self._points[-1] - self._points[-2],
                self.end_arrow, arrow_color, self.end_arrow_size
            )


    # Permanent end/vertex handles, always visible - same convention
    # as LineItem, so the base class's selection-driven corner-resize
    # handles are switched off here too.
    def _create_handles(self):
        pass

    def _remove_handles(self):
        pass

    def _update_handles(self):
        pass

    def _position_handles(self):
        for i, handle in enumerate(self._vertex_handles):
            if i < len(self._points):
                handle.setPos(self._points[i])

    # -- vertices -------------------------------------------------------

    def _create_vertex_handles(self):
        for i in range(len(self._points)):
            handle = MultiPointHandle(self, i)

            # Appended before setPos(): see the polygon_item.py note -
            # setPos() fires itemChange synchronously, which calls
            # back into _vertex_dragged(i), and for the first/last
            # index that reaches _try_connect(), which needs _h1/_h2
            # already set - so these are kept valid on every iteration,
            # not just assigned once after the loop.
            self._vertex_handles.append(handle)

            if i == 0:
                self._h1 = handle

            self._h2 = handle

            handle.setPos(self._points[i])

    def _rebuild_vertex_handles(self):
        for handle in self._vertex_handles:
            # Marked stale before removal: a handle we're replacing
            # can still receive a delayed setPos() from code that was
            # already mid-iteration over the old self._vertex_handles
            # list when this rebuild started (see the module docstring
            # on re-entrancy) - without this flag, that delayed call
            # would report an index number that no longer means what
            # it used to against the new, possibly different-length,
            # point list.
            handle._detached = True

            if handle.scene() is not None:
                handle.scene().removeItem(handle)

        self._vertex_handles = []

        self._rebuilding_handles = True
        try:
            self._create_vertex_handles()
        finally:
            self._rebuilding_handles = False

        # New handle objects don't inherit the old ones' connected-
        # state coloring, so reapply it from the actual connections.
        self._h1.set_connected(self._start_conn is not None)
        self._h2.set_connected(self._end_conn is not None)

    def _vertex_dragged(self, index):
        if self._rebuilding_handles:
            return

        if index >= len(self._vertex_handles) or index >= len(self._points):
            return

        self.prepareGeometryChange()
        self._points[index] = self._vertex_handles[index].pos()

        n = len(self._points)

        if index == 0:
            self._try_connect("p1", self.mapToScene(self._points[0]))
        elif index == n - 1:
            self._try_connect("p2", self.mapToScene(self._points[-1]))

        self.notify_connections()
        self._position_handles()
        self.update()

    # -- add / delete segment (right-click menu) -----------------------

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_action = menu.addAction("Add segment")
        delete_action = (
            menu.addAction("Delete segment")
            if len(self._points) > 2 else None
        )

        chosen = menu.exec_(event.screenPos())

        if chosen is add_action:
            self._add_segment_near(event.pos())
        elif delete_action is not None and chosen is delete_action:
            self._delete_segment_near(event.pos())

        event.accept()

    def _add_segment_near(self, local_pos):
        n = len(self._points)
        best_i, best_dist = 0, None

        for i in range(n - 1):
            a, b = self._points[i], self._points[i + 1]
            dist = _point_to_segment_dist(local_pos, a, b)

            if best_dist is None or dist < best_dist:
                best_dist, best_i = dist, i

        self.prepareGeometryChange()
        self._points.insert(best_i + 1, QPointF(local_pos))
        self._rebuild_vertex_handles()
        self.update()

    def _delete_segment_near(self, local_pos):
        interior = list(range(1, len(self._points) - 1))

        if not interior:
            return

        idx = min(
            interior,
            key=lambda i: QLineF(local_pos, self._points[i]).length()
        )

        self.prepareGeometryChange()
        del self._points[idx]
        self._rebuild_vertex_handles()
        self.update()


def _unit(vector):
    length = (vector.x() ** 2 + vector.y() ** 2) ** 0.5

    if length == 0:
        return QPointF(0, 0)

    return QPointF(vector.x() / length, vector.y() / length)


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
