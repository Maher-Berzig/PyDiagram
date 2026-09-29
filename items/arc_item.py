# arc_item.py
"""
Manual 5.1.7, "Arc": "a line which has been bent to create a
semi-circle shape. Drag the orange handle in the middle to alter the
curve of the arc."

Implemented as a LineItem subclass rather than from scratch: an Arc
is a Line in every other respect (5.1.11 - "All lines share the
following properties: width, color, style, and arrows"; it connects
the same way, drags the same way, disconnects the same way) with one
addition - a third, non-connecting handle that bows the line into a
quadratic curve. Reusing LineItem means all of that shared behavior,
its property dialog, and its "same type" grouping all apply to Arc
for free.
"""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem

from .line_item import ARROW_LENGTH, LineEndHandle, LineItem
from .drag_handle_mixin import DraggableHandleMixin


class ArcBowHandle(DraggableHandleMixin, QGraphicsRectItem):
    """
    The manual's "orange handle in the middle". Free-dragging is
    allowed, but only the component of the drag perpendicular to the
    p1-p2 line actually changes the curve (see ArcItem._update_bow) -
    dragging along the line does nothing, rather than fighting the
    user for an ambiguous result.
    """

    SIZE = 8

    def __init__(self, owner):
        super().__init__(
            -self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner
        )

        self.owner = owner

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.SizeAllCursor)
        self.setZValue(10)

        self.setBrush(QBrush(QColor("#ff8c00")))
        self.setPen(QPen(QColor("#202020"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.owner._handle_dragged("bow")

        return super().itemChange(change, value)


class ArcItem(LineItem):

    def __init__(self, p1=QPointF(0, 0), p2=QPointF(100, 0), parent=None):
        # Read by _position_handles(), which LineItem.__init__ below
        # calls before self._h3 exists yet - see the hasattr guard.
        self._bow = 30.0

        super().__init__(p1, p2, parent)

        self._h3 = ArcBowHandle(self)
        self._position_handles()

    def _control_point(self):
        mid = QPointF(
            (self._p1.x() + self._p2.x()) / 2,
            (self._p1.y() + self._p2.y()) / 2,
        )

        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.hypot(dx, dy)

        if length == 0:
            return mid

        # Unit vector perpendicular to p1->p2.
        px, py = -dy / length, dx / length

        return QPointF(
            mid.x() + px * self._bow, mid.y() + py * self._bow
        )

    def boundingRect(self):
        extra = self.pen_width + LineEndHandle.SIZE + ARROW_LENGTH * max(
            self.start_arrow_size, self.end_arrow_size, 1.0
        )

        rect = QRectF(self._p1, self._p2).normalized()
        control = self._control_point()
        rect = rect.united(QRectF(control, control))

        return rect.adjusted(-extra, -extra, extra, extra)

    def paint(self, painter, option, widget=None):
        pen = self._build_pen()

        if self.isSelected():
            pen.setColor(QColor("#1677ff"))

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        control = self._control_point()

        path = QPainterPath(self._p1)
        path.quadTo(control, self._p2)
        painter.drawPath(path)

        arrow_color = pen.color()

        if self._p1 != self._p2:
            # Arrows follow the curve's tangent at each end, not the
            # straight p1-p2 direction - so they still point along
            # the arc even when it's bowed sharply.
            self._paint_arrow(
                painter, self._p1, self._p1 - control,
                self.start_arrow, arrow_color, self.start_arrow_size
            )
            self._paint_arrow(
                painter, self._p2, self._p2 - control,
                self.end_arrow, arrow_color, self.end_arrow_size
            )

    def _position_handles(self):
        self._h1.setPos(self._p1)
        self._h2.setPos(self._p2)

        # Guarded: LineItem.__init__ calls this once (via set_point-
        # adjacent setup) before self._h3 exists - see __init__ above.
        if hasattr(self, "_h3"):
            self._h3.setPos(self._control_point())

    def _handle_dragged(self, which):
        if which == "bow":
            self._update_bow()
            return

        super()._handle_dragged(which)

    def _update_bow(self):
        local = self.mapFromScene(self._h3.scenePos())

        mid = QPointF(
            (self._p1.x() + self._p2.x()) / 2,
            (self._p1.y() + self._p2.y()) / 2,
        )

        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = math.hypot(dx, dy)

        if length == 0:
            self._bow = 0.0
        else:
            px, py = -dy / length, dx / length
            self._bow = (
                (local.x() - mid.x()) * px + (local.y() - mid.y()) * py
            )

        self.prepareGeometryChange()
        self._position_handles()
        self.update()
