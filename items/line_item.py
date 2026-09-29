# line_item.py
"""
A Line object with two connectable endpoints, modeled on the Dia
manual's description (4.2.5, 5.1.6, 5.1.11):

- Each end has a small square handle: green while unconnected, red
  once snapped to another shape's connection point.
- Dragging an end handle near a shape's connection point snaps to it
  and connects; dragging it away disconnects.
- While connected, moving or resizing the other shape drags this
  line's endpoint along with it.
- Dragging the line's own body (not a handle) moves the whole line
  and disconnects both ends - matching the manual's "If you move the
  line, it will disconnect from both objects."
- Width, color, style, and arrows are all editable (5.1.11): style is
  one of the five options the manual's Figure 5.7 shows, and each end
  gets its own independent arrow style (5.1.11.4) out of the
  "large number of options" available, applied via _paint_arrow().
"""

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem

from .diagram_item import DiagramItem
from .drag_handle_mixin import DraggableHandleMixin
from .color_picker import brush_for

CONNECT_TOLERANCE = 12  # scene units; how close counts as "snap"

# Manual 5.1.11.3: "one of the five options shown above" (solid, plus
# four dash/dot variants). Qt.PenStyle only gives us four dash
# flavors, so DashDotDotLine stands in for the fifth ("dotted"-with-
# longer-gaps) rather than duplicating DotLine.
LINE_STYLES = ["solid", "dashed", "dash-dot", "dash-dot-dot", "dotted"]

_QT_PEN_STYLE = {
    "solid": Qt.SolidLine,
    "dashed": Qt.DashLine,
    "dash-dot": Qt.DashDotLine,
    "dash-dot-dot": Qt.DashDotDotLine,
    "dotted": Qt.DotLine,
}

LINE_STYLE_LABELS = {
    "solid": "Solid",
    "dashed": "Dashed",
    "dash-dot": "Dash-Dot",
    "dash-dot-dot": "Dash-Dot-Dot",
    "dotted": "Dotted",
}


def build_dashed_pen(color, width, line_style, dash_length):
    """
    Shared by every item that has a line_style/dash_length pair - the
    Line/Polyline/Zigzagline/Bezierline family (via LineItem._build_pen
    below) and, in the border-based shapes (Rectangle, Ellipse,
    Polygon, Beziergon, and Assorted's Circle/Isosceles Triangle/Right
    Triangle/Cross), each item's own _build_border_pen(). Factored out
    here rather than duplicated in every one of those, since the only
    difference between them is which pair of attributes (pen_color/
    pen_width vs border_color/border_width) feeds it.
    """

    pen = QPen(brush_for(color), width)
    pen.setStyle(_QT_PEN_STYLE.get(line_style, Qt.SolidLine))

    if line_style != "solid":
        # QPen's dash pattern is expressed in units of the pen's own
        # width, so this converts the manual's "dash length" (an
        # absolute distance) into that scale.
        w = max(width, 1)
        pen.setDashOffset(0)

        base_pattern = pen.dashPattern()
        factor = max(dash_length, 1.0) / (w * 2)

        if base_pattern:
            pen.setDashPattern([v * factor for v in base_pattern])

    return pen

# Manual 5.1.11.4: independent begin/end arrow styles, "a large number
# of options" in real Dia - this is a representative subset rather
# than the full list.
ARROW_STYLES = [
    "none", "line_arrow", "filled_triangle", "hollow_triangle",
    "filled_diamond", "hollow_diamond", "filled_circle", "hollow_circle",
    "filled_square", "hollow_square", "half_head",
]

ARROW_STYLE_LABELS = {
    "none": "None",
    "line_arrow": "Line Arrow",
    "filled_triangle": "Filled Triangle",
    "hollow_triangle": "Hollow Triangle",
    "filled_diamond": "Filled Diamond",
    "hollow_diamond": "Hollow Diamond",
    "filled_circle": "Filled Circle",
    "hollow_circle": "Hollow Circle",
    "filled_square": "Filled Square",
    "hollow_square": "Hollow Square",
    "half_head": "Half Head",
}

ARROW_LENGTH = 12
ARROW_WIDTH = 8


class LineEndHandle(DraggableHandleMixin, QGraphicsRectItem):

    SIZE = 8

    def __init__(self, owner, which):
        super().__init__(
            -self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner
        )

        self.owner = owner
        self.which = which

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(10)

        self.set_connected(False)

    def set_connected(self, connected):
        color = QColor("#d92626") if connected else QColor("#2ea043")
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#202020"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.owner._handle_dragged(self.which)

        return super().itemChange(change, value)


class LineItem(DiagramItem):

    def __init__(self, p1=QPointF(0, 0), p2=QPointF(100, 0), parent=None):
        super().__init__(parent)

        self._p1 = QPointF(p1)
        self._p2 = QPointF(p2)

        self.pen_color = QColor("#202020")
        self.pen_width = 2

        # Manual 5.1.11.3/5.1.11.4: style/dash-length are shared by the
        # whole line; each end has its own independent arrow style
        # and (own addition beyond the manual) its own size scale.
        self.line_style = "solid"
        self.dash_length = 10.0
        self.start_arrow = "none"
        self.end_arrow = "none"
        self.start_arrow_size = 1.0
        self.end_arrow_size = 1.0

        # (item, connection_point_index) or None, for each end
        self._start_conn = None
        self._end_conn = None

        self._h1 = LineEndHandle(self, "p1")
        self._h2 = LineEndHandle(self, "p2")
        self._position_handles()

    # -- geometry -----------------------------------------------------

    def boundingRect(self):
        extra = self.pen_width + LineEndHandle.SIZE + ARROW_LENGTH * max(
            self.start_arrow_size, self.end_arrow_size, 1.0
        )

        return QRectF(self._p1, self._p2).normalized().adjusted(
            -extra, -extra, extra, extra
        )

    def _build_pen(self):
        return build_dashed_pen(
            self.pen_color, self.pen_width, self.line_style, self.dash_length
        )

    def paint(self, painter, option, widget=None):
        pen = self._build_pen()

        if self.isSelected():
            pen.setColor(QColor("#1677ff"))

        painter.setPen(pen)
        painter.drawLine(self._p1, self._p2)

        arrow_color = pen.color()

        if self._p1 != self._p2:
            self._paint_arrow(
                painter, self._p1, self._p1 - self._p2,
                self.start_arrow, arrow_color, self.start_arrow_size
            )
            self._paint_arrow(
                painter, self._p2, self._p2 - self._p1,
                self.end_arrow, arrow_color, self.end_arrow_size
            )

    def _paint_arrow(self, painter, tip, direction, style, color, size=1.0):
        """
        Draws one end's arrow decoration, oriented along `direction`
        (pointing outward from the line, away from the other end) with
        its point at `tip`. Manual 5.1.11.4: "If you don't want any
        arrow, just select the plain line" - "none" draws nothing.

        The wings/base are placed BEHIND tip (back toward the rest of
        the line), not beyond it - the sharp point of an arrowhead
        belongs exactly at the connection point, with the shape
        flaring backward from there, not the other way around.

        `size` scales the whole decoration (both its length and
        width) - manual 5.1.11.4's arrow options apply per end, and so
        does this: it's set independently as start_arrow_size /
        end_arrow_size, not a single shared value.
        """

        if style == "none":
            return

        length = QLineF(QPointF(0, 0), direction).length()

        if length == 0:
            return

        # Unit vector back along the line, and its perpendicular.
        ux, uy = direction.x() / length, direction.y() / length
        px, py = -uy, ux

        arrow_length = ARROW_LENGTH * size
        arrow_width = ARROW_WIDTH * size

        base = QPointF(
            tip.x() - ux * arrow_length, tip.y() - uy * arrow_length
        )
        left = QPointF(
            base.x() + px * arrow_width / 2, base.y() + py * arrow_width / 2
        )
        right = QPointF(
            base.x() - px * arrow_width / 2, base.y() - py * arrow_width / 2
        )

        painter.save()
        pen = QPen(color, max(self.pen_width, 1))
        painter.setPen(pen)

        if style == "line_arrow":
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(tip, left)
            painter.drawLine(tip, right)

        elif style == "half_head":
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(tip, left)

        elif style == "filled_triangle":
            painter.setBrush(QBrush(color))
            painter.drawPolygon(QPolygonF([tip, left, right]))

        elif style == "hollow_triangle":
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawPolygon(QPolygonF([tip, left, right]))

        elif style == "filled_diamond":
            mid_back = QPointF(
                tip.x() - ux * arrow_length * 2, tip.y() - uy * arrow_length * 2
            )
            painter.setBrush(QBrush(color))
            painter.drawPolygon(QPolygonF([tip, left, mid_back, right]))

        elif style == "hollow_diamond":
            mid_back = QPointF(
                tip.x() - ux * arrow_length * 2, tip.y() - uy * arrow_length * 2
            )
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawPolygon(QPolygonF([tip, left, mid_back, right]))

        elif style == "filled_circle":
            center = QPointF(
                tip.x() - ux * arrow_width / 2, tip.y() - uy * arrow_width / 2
            )
            painter.setBrush(QBrush(color))
            painter.drawEllipse(center, arrow_width / 2, arrow_width / 2)

        elif style == "hollow_circle":
            center = QPointF(
                tip.x() - ux * arrow_width / 2, tip.y() - uy * arrow_width / 2
            )
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(center, arrow_width / 2, arrow_width / 2)

        elif style in ("filled_square", "hollow_square"):
            # near_left/near_right sit at the tip end (the connection
            # point); left/right (already computed above) sit at the
            # base end - together the four corners of a square/
            # rectangle spanning the same length x width as the other
            # styles' bounding box.
            near_left = QPointF(
                tip.x() + px * arrow_width / 2, tip.y() + py * arrow_width / 2
            )
            near_right = QPointF(
                tip.x() - px * arrow_width / 2, tip.y() - py * arrow_width / 2
            )
            painter.setBrush(
                QBrush(color if style == "filled_square" else QColor("#ffffff"))
            )
            painter.drawPolygon(
                QPolygonF([near_left, left, right, near_right])
            )

        painter.restore()

    def _position_handles(self):
        self._h1.setPos(self._p1)
        self._h2.setPos(self._p2)

    # Lines use their own permanent end-handles instead of the four
    # corner resize handles every other DiagramItem gets, so the base
    # class's selection-driven handle creation is switched off here.
    def _create_handles(self):
        pass

    def _remove_handles(self):
        pass

    def _update_handles(self):
        pass

    # -- endpoint dragging / connecting --------------------------------

    def set_point(self, which, scene_pos, try_connect=False):
        local = self.mapFromScene(scene_pos)

        self.prepareGeometryChange()

        if which == "p1":
            self._p1 = local
        else:
            self._p2 = local

        if try_connect:
            self._try_connect(which, scene_pos)

        self._position_handles()
        self.update()

    def _try_connect(self, which, scene_pos):
        handle = self._h1 if which == "p1" else self._h2
        old_conn = self._start_conn if which == "p1" else self._end_conn

        target = self._find_connection_target(scene_pos)

        if target:
            item, idx, snapped_scene_pos = target
            snapped_local = self.mapFromScene(snapped_scene_pos)

            if which == "p1":
                self._p1 = snapped_local
            else:
                self._p2 = snapped_local

            if not (old_conn and old_conn[0] is item and old_conn[1] == idx):
                self._set_connection(which, item, idx)

            handle.set_connected(True)
        else:
            if old_conn:
                self._set_connection(which, None, None)

            handle.set_connected(False)

    def _find_connection_target(self, scene_pos):
        if self.scene() is None:
            return None

        search_rect = QRectF(
            scene_pos.x() - CONNECT_TOLERANCE,
            scene_pos.y() - CONNECT_TOLERANCE,
            CONNECT_TOLERANCE * 2,
            CONNECT_TOLERANCE * 2,
        )

        best = None
        best_dist = CONNECT_TOLERANCE

        for candidate in self.scene().items(search_rect):
            if candidate is self or isinstance(candidate, LineItem):
                continue

            if not isinstance(candidate, DiagramItem):
                continue

            points = candidate.all_connection_points()

            for idx, point in enumerate(points):
                point_scene = candidate.mapToScene(point)
                dist = QLineF(scene_pos, point_scene).length()

                if dist <= best_dist:
                    best_dist = dist
                    best = (candidate, idx, point_scene)

        if best is None and getattr(self.scene(), "snap_to_objects", False):
            best = self._find_snap_to_object_target(scene_pos)

        return best

    def _find_snap_to_object_target(self, scene_pos):
        """
        Manual 3.6, "Snap To Objects": "lines can be connected to the
        middle connection point of an object by dragging the line end
        handle to any point inside the object" - so when this is on,
        landing anywhere inside a shape (not just near its center
        point) connects to that shape's middle connection point.
        """

        for candidate in self.scene().items(scene_pos):
            if candidate is self or isinstance(candidate, LineItem):
                continue

            if not isinstance(candidate, DiagramItem):
                continue

            points = candidate.all_connection_points()

            if not points:
                continue

            center_local = candidate.boundingRect().center()

            idx = min(
                range(len(points)),
                key=lambda i: QLineF(points[i], center_local).length()
            )

            return (candidate, idx, candidate.mapToScene(points[idx]))

        return None

    def _set_connection(self, which, item, idx):
        old = self._start_conn if which == "p1" else self._end_conn

        if old:
            old[0].unregister_connection(self, which)

        new_conn = (item, idx) if item is not None else None

        if item is not None:
            item.register_connection(self, which)

        if which == "p1":
            self._start_conn = new_conn
        else:
            self._end_conn = new_conn

    def _handle_dragged(self, which):
        handle = self._h1 if which == "p1" else self._h2
        self.set_point(which, handle.scenePos(), try_connect=True)

    def update_connection_endpoint(self, which):
        """
        Called by a connected DiagramItem after it moves or resizes.
        """

        conn = self._start_conn if which == "p1" else self._end_conn

        if not conn:
            return

        item, idx = conn
        points = item.all_connection_points()

        if idx >= len(points):
            return

        scene_pt = item.mapToScene(points[idx])
        local_pt = self.mapFromScene(scene_pt)

        self.prepareGeometryChange()

        if which == "p1":
            self._p1 = local_pt
        else:
            self._p2 = local_pt

        self._position_handles()
        self.update()

    def clear_connection(self, which):
        if which == "p1":
            self._start_conn = None
            self._h1.set_connected(False)
        else:
            self._end_conn = None
            self._h2.set_connected(False)

    def detach(self):
        """
        Called before this line itself is removed, so the shapes it
        was connected to don't keep a stale reference to it.
        """

        for which, conn in (("p1", self._start_conn), ("p2", self._end_conn)):
            if conn:
                conn[0].unregister_connection(self, which)

    # -- whole-line dragging -------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Dragging the line's body (not an end handle) moves the
            # whole item via its own .pos() - per the manual, this
            # disconnects both ends.
            if self._start_conn:
                self._set_connection("p1", None, None)
                self._h1.set_connected(False)

            if self._end_conn:
                self._set_connection("p2", None, None)
                self._h2.set_connected(False)

        return super().itemChange(change, value)
