# bezier_utils.py
"""
Shared node/control-point model for Bezierline (5.1.10) and
Beziergon (5.1.5): "the green dots customize the size while the
orange dots customize the angles at which the line curves... Symmetric
control causes any dragging action on the added segment to be
symmetrical around this point. Smooth control allows you to pull away
from the middle point independently but rotations around the middle
point are symmetrical. Cusp control allows you to drag each handle
independently."

A curve is a list of nodes, each a dict:
    {"anchor": QPointF, "control_in": QPointF or None,
     "control_out": QPointF or None, "mode": one of BEZIER_MODES}

control_in is the incoming segment's control point (None for a node
with no incoming segment - the first node of an open Bezierline);
control_out is the outgoing segment's (None for the last node of an
open Bezierline). Both are always present on every node of a closed
Beziergon.
"""

import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem

from .drag_handle_mixin import DraggableHandleMixin

BEZIER_MODES = ["symmetric", "smooth", "cusp", "sharp"]

BEZIER_MODE_LABELS = {
    "symmetric": "Symmetric",
    "smooth": "Smooth",
    "cusp": "Cusp",
    "sharp": "Sharp",
}


def constrain_partner_control(anchor, moved_control, other_control, mode):
    """
    Given that `moved_control` just moved, returns the new position
    for the *other* control point of the same node under `mode`:

    - cusp: unaffected - each handle is fully independent.
    - smooth: kept collinear through the anchor (opposite side), but
      at its own existing distance - "rotations... are symmetrical"
      but you can still "pull away... independently".
    - symmetric: mirrored exactly - same distance, opposite side.
    - sharp: pinned to the anchor - a sharp mode node has no
      curvature at all, so there's no "other side" to mirror onto.
    """

    if mode == "sharp":
        return QPointF(anchor)

    if mode == "cusp" or other_control is None:
        return QPointF(other_control) if other_control is not None else None

    vec = moved_control - anchor
    length = math.hypot(vec.x(), vec.y())

    if length == 0:
        return QPointF(other_control)

    direction = QPointF(-vec.x() / length, -vec.y() / length)

    if mode == "symmetric":
        other_length = length
    else:
        other_vec = other_control - anchor
        other_length = math.hypot(other_vec.x(), other_vec.y())

    return QPointF(
        anchor.x() + direction.x() * other_length,
        anchor.y() + direction.y() * other_length,
    )


def apply_node_mode(node, mode):
    """
    Switches `node` to `mode` and immediately reconciles its two
    control points to fit it, rather than just relabeling the mode
    and leaving the actual curve untouched until the next time a
    handle gets dragged (which is what the right-click "Symmetric/
    Smooth/Cusp" menu used to do - since a freshly-added node's
    handles both start out zero-length anyway, switching modes on one
    looked like it was doing nothing at all).

    Whichever of the two handles currently has the larger offset from
    the anchor is treated as the reference the other is reconciled
    against, so switching modes preserves whatever curvature is
    already visible rather than always collapsing toward whichever
    side happens to be shorter. Sharp is the exception - it has no
    reference handle, since neither side keeps any offset at all.
    """

    node["mode"] = mode

    if mode == "sharp":
        node["control_in"] = QPointF(node["anchor"])
        node["control_out"] = QPointF(node["anchor"])
        return

    control_in = node.get("control_in")
    control_out = node.get("control_out")

    if control_in is None or control_out is None:
        # Bezierline's open ends only ever have a control point on
        # one side - nothing to reconcile it against.
        return

    anchor = node["anchor"]
    len_in = math.hypot(control_in.x() - anchor.x(), control_in.y() - anchor.y())
    len_out = math.hypot(control_out.x() - anchor.x(), control_out.y() - anchor.y())

    if len_out >= len_in:
        node["control_in"] = constrain_partner_control(
            anchor, control_out, control_in, mode
        )
    else:
        node["control_out"] = constrain_partner_control(
            anchor, control_in, control_out, mode
        )


def build_bezier_path(nodes, closed):
    """
    Builds the visible QPainterPath: a cubic segment between every
    consecutive pair of nodes, plus (for a closed Beziergon) one more
    curving back from the last node to the first.
    """

    path = QPainterPath(nodes[0]["anchor"])

    for prev, cur in zip(nodes, nodes[1:]):
        path.cubicTo(prev["control_out"], cur["control_in"], cur["anchor"])

    if closed and len(nodes) > 1:
        path.cubicTo(
            nodes[-1]["control_out"], nodes[0]["control_in"],
            nodes[0]["anchor"]
        )
        path.closeSubpath()

    return path


def default_node(anchor, mode="symmetric"):
    """A freshly-added node: degenerate (zero-length) control points,
    which renders as a sharp corner until the user drags them out."""

    return {
        "anchor": QPointF(anchor),
        "control_in": QPointF(anchor),
        "control_out": QPointF(anchor),
        "mode": mode,
    }


class BezierAnchorHandle(DraggableHandleMixin, QGraphicsRectItem):
    """
    A "green dot" (manual 5.1.10): the on-curve point at a node.
    Shared by Bezierline and Beziergon - both implement
    _anchor_dragged(index) on themselves, which this calls back into.
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
            self.owner._anchor_dragged(self.index)

        return super().itemChange(change, value)


class BezierControlHandle(DraggableHandleMixin, QGraphicsEllipseItem):
    """
    An "orange dot" (manual 5.1.10): a control point governing curve
    angle, linked to its node's Symmetric/Smooth/Cusp mode.
    """

    SIZE = 7

    def __init__(self, owner, index, which):
        super().__init__(
            -self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner
        )

        self.owner = owner
        self.index = index
        self.which = which  # "in" or "out"
        self._detached = False

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(10)

        self.setBrush(QBrush(QColor("#ff8c00")))
        self.setPen(QPen(QColor("#202020"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self._detached:
            self.owner._control_dragged(self.index, self.which)

        return super().itemChange(change, value)
