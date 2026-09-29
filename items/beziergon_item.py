# beziergon_item.py
"""
Manual 5.1.5, "Beziergon": "similar to the polygon as the user
defines the shape. However, it differs in that it allows curves to
exist in the shape."

Closed loop of the same anchor/control-point nodes Bezierline uses
(5.1.10, in bezier_utils.py) - every node has both a control_in and
control_out (there's no "first"/"last" node missing one, since the
shape wraps around) - filled and bordered like Polygon rather than
connecting to other shapes like a line.
"""

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QMenu

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .line_item import build_dashed_pen
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


class BeziergonItem(DiagramItem):

    MIN_VERTICES = 3

    def __init__(self, points=None, parent=None):
        super().__init__(parent)

        if not points or len(points) < self.MIN_VERTICES:
            points = [QPointF(50, 0), QPointF(100, 80), QPointF(0, 80)]

        self._nodes = [default_node(p) for p in points]

        self.fill_color = QColor("#DCEBFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

        # Manual 5.1.11.3: border style/dash-length, same options as a
        # Line's.
        self.line_style = "solid"
        self.dash_length = 10.0

        self._rebuilding_handles = False
        self._anchor_handles = []
        self._control_handle_map = {}
        self._create_handles_internal()

    def _build_border_pen(self):
        return build_dashed_pen(
            self.border_color, self.border_width, self.line_style, self.dash_length
        )

    # -- geometry -----------------------------------------------------

    def boundingRect(self):
        extra = self.border_width + BezierAnchorHandle.SIZE

        xs = [n["anchor"].x() for n in self._nodes]
        xs += [n["control_in"].x() for n in self._nodes]
        xs += [n["control_out"].x() for n in self._nodes]
        ys = [n["anchor"].y() for n in self._nodes]
        ys += [n["control_in"].y() for n in self._nodes]
        ys += [n["control_out"].y() for n in self._nodes]

        rect = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

        return rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        """Every anchor, plus the centroid - same pattern as Polygon."""

        if not self._nodes:
            return []

        anchors = [n["anchor"] for n in self._nodes]
        cx = sum(p.x() for p in anchors) / len(anchors)
        cy = sum(p.y() for p in anchors) / len(anchors)

        return anchors + [QPointF(cx, cy)]

    def _path(self):
        return build_bezier_path(self._nodes, closed=True)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._build_border_pen())
        painter.setBrush(brush_for(self.fill_color))
        painter.drawPath(self._path())

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self._path())

        self._paint_connection_points(painter)


    # -- handles (replace the base class's 4 corner handles) -----------

    def _create_handles(self):
        self._apply_handle_visibility()

    def _remove_handles(self):
        for handle in self._anchor_handles + list(self._control_handle_map.values()):
            handle.hide()

    def _update_handles(self):
        self._position_handles()

    def _apply_handle_visibility(self):
        """
        Anchor handles are always shown once the shape's handles are
        visible at all - a node's control handles are hidden exactly
        when it's Sharp, since a Sharp node's controls are always
        pinned exactly on top of the anchor (see apply_node_mode).
        Showing an unmovable orange dot stacked there was what ended
        up stealing the drag instead of the anchor's own green square
        underneath it, which is the actual point you can move.
        """

        for handle in self._anchor_handles:
            handle.show()

        for (index, _which), handle in self._control_handle_map.items():
            if index < len(self._nodes) and self._nodes[index]["mode"] == "sharp":
                handle.hide()
            else:
                handle.show()

    def _position_handles(self):
        for i, handle in enumerate(self._anchor_handles):
            if i < len(self._nodes):
                handle.setPos(self._nodes[i]["anchor"])

        for (i, which), handle in self._control_handle_map.items():
            if i < len(self._nodes):
                handle.setPos(self._nodes[i][f"control_{which}"])

        if self.isSelected():
            self._apply_handle_visibility()

    def _create_handles_internal(self):
        for i, node in enumerate(self._nodes):
            handle = BezierAnchorHandle(self, i)
            self._anchor_handles.append(handle)
            handle.hide()
            handle.setPos(node["anchor"])

        for i, node in enumerate(self._nodes):
            for which in ("in", "out"):
                handle = BezierControlHandle(self, i, which)
                self._control_handle_map[(i, which)] = handle
                handle.hide()
                handle.setPos(node[f"control_{which}"])

    def _rebuild_handles(self):
        was_selected = self.isSelected()

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

        if was_selected:
            self._apply_handle_visibility()

    # -- dragging -----------------------------------------------------

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
        node["control_in"] = node["control_in"] + delta
        node["control_out"] = node["control_out"] + delta

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
        node[f"control_{other_which}"] = constrain_partner_control(
            node["anchor"], new_pos, other, node["mode"]
        )

        self.prepareGeometryChange()
        self._position_handles()
        self.update()

    # -- add / delete point, and per-node mode (right-click menu) ------

    def contextMenuEvent(self, event):
        menu = QMenu()
        add_action = menu.addAction("Add Point")
        delete_action = (
            menu.addAction("Delete Point")
            if len(self._nodes) > self.MIN_VERTICES else None
        )

        nearest = min(
            range(len(self._nodes)),
            key=lambda i: QLineF(
                event.pos(), self._nodes[i]["anchor"]
            ).length()
        )

        menu.addSeparator()
        mode_actions = {}

        for mode in BEZIER_MODES:
            action = menu.addAction(BEZIER_MODE_LABELS[mode])
            action.setCheckable(True)
            action.setChecked(self._nodes[nearest]["mode"] == mode)
            mode_actions[action] = mode

        chosen = menu.exec_(event.screenPos())

        if chosen is add_action:
            self._add_point_near(event.pos())
        elif delete_action is not None and chosen is delete_action:
            self._delete_point_near(event.pos())
        elif chosen in mode_actions:
            self.prepareGeometryChange()
            apply_node_mode(self._nodes[nearest], mode_actions[chosen])
            self._position_handles()
            self.update()

        event.accept()

    def _add_point_near(self, local_pos):
        n = len(self._nodes)
        best_i, best_dist = 0, None

        for i in range(n):
            a = self._nodes[i]["anchor"]
            b = self._nodes[(i + 1) % n]["anchor"]
            dist = _point_to_segment_dist(local_pos, a, b)

            if best_dist is None or dist < best_dist:
                best_dist, best_i = dist, i

        self.prepareGeometryChange()
        self._nodes.insert(best_i + 1, default_node(local_pos))
        self._rebuild_handles()
        self.update()

    def _delete_point_near(self, local_pos):
        if len(self._nodes) <= self.MIN_VERTICES:
            return

        idx = min(
            range(len(self._nodes)),
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
