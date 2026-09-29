# bezierline_item.py
"""
Manual 5.1.10, "Bezierline": "a line which has curves in it. The
Bezierline's shape is edited by clicking and dragging the green and
orange dots. The green dots customize the size while the orange dots
customize the angles at which the line curves. With a right-click
menu, you can add or delete segments. If you add one or more
segments, three additional properties are available" - Symmetric,
Smooth, and Cusp (see bezier_utils.py).

Connects at its first/last anchor exactly like Line does, via the
same duck-typed reuse of LineItem's methods that Polyline uses (see
polyline_item.py's module docstring for why that works).
"""

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMenu

from .diagram_item import DiagramItem
from .line_item import ARROW_LENGTH, LineItem
from .bezier_utils import (
    BEZIER_MODES,
    BEZIER_MODE_LABELS,
    BezierAnchorHandle,
    BezierControlHandle,
    apply_node_mode,
    build_bezier_path,
    constrain_partner_control,
    default_node,
)


class BezierlineItem(DiagramItem):

    MIN_NODES = 2

    def __init__(self, points=None, parent=None):
        super().__init__(parent)

        if not points or len(points) < self.MIN_NODES:
            points = [QPointF(0, 0), QPointF(100, 0)]

        self._nodes = self._nodes_from_anchors(points)

        self.pen_color = QColor("#202020")
        self.pen_width = 2
        self.line_style = "solid"
        self.dash_length = 10.0
        self.start_arrow = "none"
        self.end_arrow = "none"
        self.start_arrow_size = 1.0
        self.end_arrow_size = 1.0

        self._start_conn = None
        self._end_conn = None

        self._rebuilding_handles = False
        self._anchor_handles = []
        self._control_handle_map = {}
        self._create_handles_internal()

    @staticmethod
    def _nodes_from_anchors(points):
        """
        Builds a fresh, essentially-straight node list from a plain
        anchor list - control points start collapsed onto their
        anchor (a degenerate, zero-length handle), same as any newly
        added node (see bezier_utils.default_node).
        """

        nodes = [default_node(p) for p in points]
        nodes[0]["control_in"] = None
        nodes[-1]["control_out"] = None

        return nodes

    # -- endpoints as a 2-point-line-shaped view, for LineItem's --
    # borrowed connection methods (see polyline_item.py)

    @property
    def _p1(self):
        return self._nodes[0]["anchor"]

    @_p1.setter
    def _p1(self, value):
        self._nodes[0]["anchor"] = value

    @property
    def _p2(self):
        return self._nodes[-1]["anchor"]

    @_p2.setter
    def _p2(self, value):
        self._nodes[-1]["anchor"] = value

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
        extra = self.pen_width + BezierAnchorHandle.SIZE + ARROW_LENGTH * max(
            self.start_arrow_size, self.end_arrow_size, 1.0
        )

        xs, ys = [], []

        for node in self._nodes:
            for key in ("anchor", "control_in", "control_out"):
                p = node[key]

                if p is not None:
                    xs.append(p.x())
                    ys.append(p.y())

        rect = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

        return rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        return []  # a line isn't itself a connection target (see LineItem)

    def _path(self):
        return build_bezier_path(self._nodes, closed=False)

    def paint(self, painter, option, widget=None):
        pen = self._build_pen()

        if self.isSelected():
            pen.setColor(QColor("#1677ff"))

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._path())

        arrow_color = pen.color()
        first, last = self._nodes[0], self._nodes[-1]

        if first["control_out"] != first["anchor"]:
            self._paint_arrow(
                painter, first["anchor"],
                first["anchor"] - first["control_out"],
                self.start_arrow, arrow_color, self.start_arrow_size
            )

        if last["control_in"] != last["anchor"]:
            self._paint_arrow(
                painter, last["anchor"],
                last["anchor"] - last["control_in"],
                self.end_arrow, arrow_color, self.end_arrow_size
            )


    # Permanent handles, always visible - same convention as Line/
    # Polyline, so the base class's selection-driven handles are off.
    def _create_handles(self):
        pass

    def _remove_handles(self):
        pass

    def _update_handles(self):
        pass

    def _position_handles(self):
        for i, handle in enumerate(self._anchor_handles):
            if i < len(self._nodes):
                handle.setPos(self._nodes[i]["anchor"])

        for (i, which), handle in self._control_handle_map.items():
            if i < len(self._nodes):
                node = self._nodes[i]
                point = node[f"control_{which}"]

                if point is not None:
                    handle.setPos(point)
                    # A Sharp node's controls are always pinned exactly
                    # on top of the anchor (see apply_node_mode) -
                    # hidden rather than shown stacked there, since an
                    # unmovable orange dot sitting on top of the
                    # anchor's own green square was what ended up
                    # stealing the drag instead of the anchor itself.
                    handle.setVisible(node["mode"] != "sharp")

    # -- handle construction --------------------------------------------

    def _create_handles_internal(self):
        for i, node in enumerate(self._nodes):
            handle = BezierAnchorHandle(self, i)
            self._anchor_handles.append(handle)

            if i == 0:
                self._h1 = handle

            self._h2 = handle

            handle.setPos(node["anchor"])

        for i, node in enumerate(self._nodes):
            for which in ("in", "out"):
                point = node[f"control_{which}"]

                if point is not None:
                    handle = BezierControlHandle(self, i, which)
                    self._control_handle_map[(i, which)] = handle
                    handle.setPos(point)
                    handle.setVisible(node["mode"] != "sharp")

    def _rebuild_handles(self):
        for handle in list(self._anchor_handles) + list(
            self._control_handle_map.values()
        ):
            handle._detached = True

            if handle.scene() is not None:
                handle.scene().removeItem(handle)

        self._anchor_handles = []
        self._control_handle_map = {}

        self._rebuilding_handles = True
        try:
            self._create_handles_internal()
        finally:
            self._rebuilding_handles = False

        self._h1.set_connected(self._start_conn is not None)
        self._h2.set_connected(self._end_conn is not None)

    # -- dragging ---------------------------------------------------------

    def _anchor_dragged(self, index):
        if self._rebuilding_handles:
            return

        if index >= len(self._anchor_handles) or index >= len(self._nodes):
            return

        node = self._nodes[index]
        new_pos = self._anchor_handles[index].pos()
        delta = new_pos - node["anchor"]

        self.prepareGeometryChange()
        node["anchor"] = QPointF(new_pos)

        if node["control_in"] is not None:
            node["control_in"] = node["control_in"] + delta

        if node["control_out"] is not None:
            node["control_out"] = node["control_out"] + delta

        n = len(self._nodes)

        if index == 0:
            self._try_connect("p1", self.mapToScene(node["anchor"]))
        elif index == n - 1:
            self._try_connect("p2", self.mapToScene(node["anchor"]))

        self.notify_connections()
        self._position_handles()
        self.update()

    def _control_dragged(self, index, which):
        if self._rebuilding_handles:
            return

        if index >= len(self._nodes):
            return

        node = self._nodes[index]
        handle = self._control_handle_map.get((index, which))

        if handle is None:
            return

        if node["mode"] == "sharp":
            # A sharp node has no curvature at all - dragging either
            # handle just snaps it straight back to the anchor.
            node["control_in"] = QPointF(node["anchor"])
            node["control_out"] = QPointF(node["anchor"])
            self.prepareGeometryChange()
            self._position_handles()
            self.update()
            return

        new_pos = handle.pos()
        node[f"control_{which}"] = QPointF(new_pos)

        other_which = "in" if which == "out" else "out"
        other = node[f"control_{other_which}"]

        if other is not None:
            node[f"control_{other_which}"] = constrain_partner_control(
                node["anchor"], new_pos, other, node["mode"]
            )

        self.prepareGeometryChange()
        self._position_handles()
        self.update()

    # -- add / delete segment, and per-node mode (right-click menu) ----

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_action = menu.addAction("Add segment")
        delete_action = (
            menu.addAction("Delete segment")
            if len(self._nodes) > 2 else None
        )

        interior = list(range(1, len(self._nodes) - 1))
        nearest_interior = None
        mode_actions = {}

        if interior:
            nearest_interior = min(
                interior,
                key=lambda i: QLineF(
                    event.pos(), self._nodes[i]["anchor"]
                ).length()
            )

            menu.addSeparator()

            for mode in BEZIER_MODES:
                action = menu.addAction(BEZIER_MODE_LABELS[mode])
                action.setCheckable(True)
                action.setChecked(self._nodes[nearest_interior]["mode"] == mode)
                mode_actions[action] = mode

        chosen = menu.exec_(event.screenPos())

        if chosen is add_action:
            self._add_segment_near(event.pos())
        elif delete_action is not None and chosen is delete_action:
            self._delete_segment_near(event.pos())
        elif chosen in mode_actions:
            self.prepareGeometryChange()
            apply_node_mode(self._nodes[nearest_interior], mode_actions[chosen])
            self._position_handles()
            self.update()

        event.accept()

    def _add_segment_near(self, local_pos):
        n = len(self._nodes)
        best_i, best_dist = 0, None

        for i in range(n - 1):
            a, b = self._nodes[i]["anchor"], self._nodes[i + 1]["anchor"]
            dist = _point_to_segment_dist(local_pos, a, b)

            if best_dist is None or dist < best_dist:
                best_dist, best_i = dist, i

        self.prepareGeometryChange()
        self._nodes.insert(best_i + 1, default_node(local_pos))
        self._rebuild_handles()
        self.update()

    def _delete_segment_near(self, local_pos):
        interior = list(range(1, len(self._nodes) - 1))

        if not interior:
            return

        idx = min(
            interior,
            key=lambda i: QLineF(local_pos, self._nodes[i]["anchor"]).length()
        )

        self.prepareGeometryChange()
        del self._nodes[idx]
        self._rebuild_handles()
        self.update()


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
