# assorted_item.py
"""
Manual 6.1.1.1, "Assorted": "Assorted Geometric Shapes. The purpose of
this sheet is to provide a selection of simple and convenient preset
shapes so that users need not spend time creating their own basic
shapes. The set includes shapes with constrained ratio such as
perfect Circles, Squares, various type of Triangle and Crosses. These
objects do not allow text to be entered inside the shape."

"No text inside" just means these behave like Rectangle/Ellipse (a
Properties dialog on double-click, not an editable text child) rather
than like Text or a UML Class - already the default for any shape
that isn't TextItem/ClassItem, so nothing extra is needed for that
part.

Square and Circle are the "constrained ratio" shapes the manual
calls out - their resize_from_handle forces width == height, unlike
every other resizable shape in the app. Triangle/Right Triangle/Cross
resize freely like an ordinary box.
"""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt, QLineF
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygonF, QPainterPath

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .line_item import build_dashed_pen
from .drag_handle_mixin import DraggableHandleMixin
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem


class AssortedShapeItem(DiagramItem):

    CONSTRAIN_SQUARE = False

    def __init__(self, rect=QRectF(0, 0, 80, 80), parent=None):
        super().__init__(parent)

        self._rect = QRectF(rect)

        self.fill_color = QColor("#DCEBFF")
        self.border_color = QColor("#202020")
        self.border_width = 2

        # Manual 5.1.11.3: border style/dash-length, same options as a
        # Line's. Shared here at the AssortedShapeItem base so every
        # concrete shape has it (paint()/_build_border_pen() below are
        # also shared), even though only Circle/Isosceles Triangle/
        # Right Triangle/Cross expose it in their Properties dialog -
        # it stays "solid" (i.e. unchanged) for Square unless code
        # sets it directly.
        self.line_style = "solid"
        self.dash_length = 10.0

    def _build_border_pen(self):
        return build_dashed_pen(
            self.border_color, self.border_width, self.line_style, self.dash_length
        )

    def boundingRect(self):
        extra = self.border_width + 4

        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        """Corners, edge midpoints, and center - same pattern as
        RectangleItem/EllipseItem, regardless of the shape actually
        painted inside that bounding box."""

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

    def _shape_path_points(self):
        """Overridden by each concrete shape to return the polygon
        points to draw, or None for shapes drawn some other way
        (Circle uses drawEllipse directly instead)."""

        raise NotImplementedError

    def paint(self, painter, option, widget=None):
        painter.setPen(self._build_border_pen())
        painter.setBrush(
            brush_for(self.fill_color) if getattr(self, "draw_background", True)
            else Qt.NoBrush
        )

        self._draw_shape(painter)

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            self._draw_shape(painter)

        self._paint_connection_points(painter)

    def _draw_shape(self, painter):
        points = self._shape_path_points()
        painter.drawPolygon(QPolygonF(points))

    def resize_from_handle(self, handle, delta, original):
        rect = QRectF(original)

        if handle == "top_left":
            rect.setTopLeft(original.topLeft() + delta)
        elif handle == "top_right":
            rect.setTopRight(original.topRight() + delta)
        elif handle == "bottom_left":
            rect.setBottomLeft(original.bottomLeft() + delta)
        elif handle == "bottom_right":
            rect.setBottomRight(original.bottomRight() + delta)

        if self.CONSTRAIN_SQUARE:
            size = max(
                abs(rect.width()), abs(rect.height()), self.MIN_WIDTH
            )

            if handle == "top_left":
                rect = QRectF(
                    original.bottomRight().x() - size,
                    original.bottomRight().y() - size,
                    size, size
                )
            elif handle == "top_right":
                rect = QRectF(
                    original.bottomLeft().x(),
                    original.bottomLeft().y() - size,
                    size, size
                )
            elif handle == "bottom_left":
                rect = QRectF(
                    original.topRight().x() - size,
                    original.topRight().y(),
                    size, size
                )
            elif handle == "bottom_right":
                rect = QRectF(
                    original.topLeft().x(),
                    original.topLeft().y(),
                    size, size
                )
        else:
            if rect.width() < self.MIN_WIDTH:
                rect.setWidth(self.MIN_WIDTH)

            if rect.height() < self.MIN_HEIGHT:
                rect.setHeight(self.MIN_HEIGHT)

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()


class SquareItem(AssortedShapeItem):
    """Manual 6.1.1.1: a "perfect Square"."""

    CONSTRAIN_SQUARE = True

    def _shape_path_points(self):
        r = self._rect
        return [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]


class CircleItem(AssortedShapeItem):
    """Manual 6.1.1.1: a "perfect Circle"."""

    CONSTRAIN_SQUARE = True

    def _draw_shape(self, painter):
        painter.drawEllipse(self._rect)

    def connection_points(self):
        """Same on-the-curve placement as EllipseItem, rather than the
        AssortedShapeItem default (which sits on the bounding box's
        corners - outside a circle's actual outline)."""

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



# ---------------------------------------------------------------------------
# Regular polygon / star / spiral additions


def _regular_points(center, radius, count, phase=-math.pi / 2):
    return [
        QPointF(
            center.x() + radius * math.cos(phase + 2 * math.pi * i / count),
            center.y() + radius * math.sin(phase + 2 * math.pi * i / count),
        )
        for i in range(count)
    ]


def _rounded_polygon_path(points, radii):
    """Build a closed QPainterPath with an independent radius per vertex."""
    if not points:
        return QPainterPath()
    n = len(points)
    starts, ends = [], []
    for i, p in enumerate(points):
        prev = points[(i - 1) % n]
        nxt = points[(i + 1) % n]
        rp = max(0.0, min(float(radii[i]), QLineF(p, prev).length() / 2,
                          QLineF(p, nxt).length() / 2))
        vin = QLineF(p, prev)
        vout = QLineF(p, nxt)
        starts.append(vin.pointAt(rp / max(vin.length(), 1e-9)))
        ends.append(vout.pointAt(rp / max(vout.length(), 1e-9)))

    path = QPainterPath()
    path.moveTo(ends[-1])
    for i in range(n):
        path.lineTo(starts[i])
        if radii[i] > 0:
            path.quadTo(points[i], ends[i])
        else:
            path.lineTo(points[i])
            path.lineTo(ends[i])
    path.closeSubpath()
    return path


class RegularPolygonItem(AssortedShapeItem):
    CONSTRAIN_SQUARE = True
    MIN_POINTS = 3
    DEFAULT_POINTS = 5

    def __init__(self, rect=QRectF(0, 0, 100, 100), parent=None):
        super().__init__(rect, parent)
        self.num_points = self.DEFAULT_POINTS
        self.corner_radius = 0.0
        self.draw_background = True

    def _points(self):
        r = self._rect
        radius = min(r.width(), r.height()) / 2
        return _regular_points(r.center(), radius, max(self.MIN_POINTS, int(self.num_points)))

    def _shape_path_points(self):
        return self._points()

    def _draw_shape(self, painter):
        points = self._points()
        if self.corner_radius > 0:
            path = _rounded_polygon_path(points, [self.corner_radius] * len(points))
            painter.drawPath(path)
        else:
            painter.drawPolygon(QPolygonF(points))

    def connection_points(self):
        pts = self._points()
        return pts + [self._rect.center()]


class StarRadiusHandle(DraggableHandleMixin, QGraphicsRectItem):
    SIZE = 9

    def __init__(self, owner, which):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner)
        self.owner = owner
        self.which = which
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(20)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#1677ff"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self.owner._updating_special_handles:
            self.owner._radius_handle_dragged(self.which)
        return super().itemChange(change, value)


class StarItem(AssortedShapeItem):
    CONSTRAIN_SQUARE = True
    MIN_POINTS = 2
    DEFAULT_POINTS = 5

    def __init__(self, rect=QRectF(0, 0, 100, 100), parent=None):
        super().__init__(rect, parent)
        self.num_points = self.DEFAULT_POINTS
        self.inner_radius_ratio = 0.45
        self.outer_corner_radius = 0.0
        self.inner_corner_radius = 0.0
        self.draw_background = True
        self._special_handles = [StarRadiusHandle(self, "inner"), StarRadiusHandle(self, "outer")]
        self._updating_special_handles = True
        self._update_special_handles()
        self._updating_special_handles = False

    def _radii(self):
        r = self._rect
        outer = min(r.width(), r.height()) / 2
        inner = outer * max(0.05, min(float(self.inner_radius_ratio), 0.95))
        return outer, inner

    def _points(self):
        center = self._rect.center()
        outer, inner = self._radii()
        count = max(self.MIN_POINTS, int(self.num_points))
        pts = []
        for i in range(count):
            a = -math.pi / 2 + 2 * math.pi * i / count
            pts.append(QPointF(center.x() + outer * math.cos(a), center.y() + outer * math.sin(a)))
            a2 = a + math.pi / count
            pts.append(QPointF(center.x() + inner * math.cos(a2), center.y() + inner * math.sin(a2)))
        return pts

    def _shape_path_points(self):
        return self._points()

    def _draw_shape(self, painter):
        pts = self._points()
        radii = []
        for i in range(len(pts)):
            radii.append(self.outer_corner_radius if i % 2 == 0 else self.inner_corner_radius)
        if any(r > 0 for r in radii):
            painter.drawPath(_rounded_polygon_path(pts, radii))
        else:
            painter.drawPolygon(QPolygonF(pts))

    def connection_points(self):
        return self._points() + [self._rect.center()]

    def _create_handles(self):
        for h in self._special_handles:
            h.show()
        self._update_special_handles()

    def _remove_handles(self):
        for h in self._special_handles:
            h.hide()

    def _update_handles(self):
        if hasattr(self, "_special_handles"):
            self._update_special_handles()

    def _update_special_handles(self):
        if not hasattr(self, "_special_handles"):
            return
        pts = self._points()
        if len(pts) < 2:
            return
        self._updating_special_handles = True
        self._special_handles[1].setPos(pts[0])
        self._special_handles[0].setPos(pts[1])
        self._updating_special_handles = False

    def _radius_handle_dragged(self, which):
        center = self._rect.center()
        handle = self._special_handles[0 if which == "inner" else 1]
        radius = QLineF(center, handle.pos()).length()
        outer, inner = self._radii()
        if which == "outer":
            radius = max(self.MIN_WIDTH / 2, radius)
            new_rect = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
            self.prepareGeometryChange()
            self._rect = new_rect
        else:
            radius = max(2.0, min(radius, outer * 0.95))
            self.inner_radius_ratio = radius / max(outer, 1e-9)
        self.prepareGeometryChange()
        self._update_special_handles()
        self.notify_connections()
        self.update()


class SpiralEndpointHandle(DraggableHandleMixin, QGraphicsRectItem):
    SIZE = 9

    def __init__(self, owner):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner)
        self.owner = owner
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(20)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#1677ff"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self.owner._updating_endpoint_handle:
            self.owner._endpoint_dragged()
        return super().itemChange(change, value)


class SpiralItem(DiagramItem):
    MIN_TURNS = 0.25

    def __init__(self, center=QPointF(0, 0), endpoint=QPointF(100, 0), parent=None):
        super().__init__(parent)
        self._center = QPointF(center)
        self._endpoint = QPointF(endpoint)
        self.turns = 3.0
        self.pen_color = QColor("#202020")
        self.pen_width = 2
        self.line_style = "solid"
        self.dash_length = 10.0
        self._endpoint_handle = SpiralEndpointHandle(self)
        self._updating_endpoint_handle = True
        self._endpoint_handle.setPos(self._endpoint)
        self._updating_endpoint_handle = False

    def boundingRect(self):
        extra = self.pen_width + SpiralEndpointHandle.SIZE
        pts = self._sample_points(96)
        if not pts:
            return QRectF(self._center, self._center).adjusted(-extra, -extra, extra, extra)
        rect = QPolygonF(pts).boundingRect()
        return rect.adjusted(-extra, -extra, extra, extra)

    def _sample_points(self, n=160):
        radius = QLineF(self._center, self._endpoint).length()
        if radius <= 0:
            return [QPointF(self._center)]
        end_angle = math.atan2(self._endpoint.y() - self._center.y(), self._endpoint.x() - self._center.x())
        pts = []
        steps = max(8, int(n))
        for i in range(steps):
            t = i / (steps - 1)
            a = -math.pi / 2 + t * (self.turns * 2 * math.pi + end_angle + math.pi / 2)
            rr = radius * t
            pts.append(QPointF(self._center.x() + rr * math.cos(a), self._center.y() + rr * math.sin(a)))
        pts[-1] = QPointF(self._endpoint)
        return pts

    def paint(self, painter, option, widget=None):
        painter.setPen(build_dashed_pen(self.pen_color, self.pen_width, self.line_style, self.dash_length))
        pts = self._sample_points()
        if len(pts) > 1:
            painter.drawPolyline(QPolygonF(pts))
        if self.isSelected():
            pen = QPen(QColor("#1677ff"), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF(pts))

    def connection_points(self):
        return [self._center, self._endpoint]

    def _create_handles(self):
        self._endpoint_handle.show()
        self._update_handles()

    def _remove_handles(self):
        self._endpoint_handle.hide()

    def _update_handles(self):
        self._updating_endpoint_handle = True
        self._endpoint_handle.setPos(self._endpoint)
        self._updating_endpoint_handle = False

    def _endpoint_dragged(self):
        self.prepareGeometryChange()
        self._endpoint = QPointF(self._endpoint_handle.pos())
        self.notify_connections()
        self.update()

    def resize_from_handle(self, handle, delta, original):
        # Spiral has a single endpoint handle; the normal rectangle resize
        # handles are intentionally not used.
        if handle == "endpoint":
            self._endpoint_handle.setPos(self._endpoint_handle.pos() + delta)





class CircleSectionAngleHandle(DraggableHandleMixin, QGraphicsRectItem):
    SIZE = 9

    def __init__(self, owner):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, owner)
        self.owner = owner
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(20)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#1677ff"), 1))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and not self.owner._updating_angle_handle:
            self.owner._angle_handle_dragged()
        return super().itemChange(change, value)


class CircleSectionItem(AssortedShapeItem):
    """A circular disk with an adjustable missing angular sector.

    The initial shape is a three-quarter circle (90 degree missing sector).
    The blue manipulation handle sits on the outer circle at the end of the
    missing sector and can be dragged around the circumference to change the
    missing angle.
    """

    CONSTRAIN_SQUARE = True
    DEFAULT_MISSING_ANGLE = 90.0
    MIN_MISSING_ANGLE = 1.0
    MAX_MISSING_ANGLE = 359.0

    def __init__(self, rect=QRectF(0, 0, 100, 100), parent=None):
        super().__init__(rect, parent)
        self.missing_angle = self.DEFAULT_MISSING_ANGLE
        self.draw_background = True
        self._angle_handle = CircleSectionAngleHandle(self)
        self._angle_handle.hide()
        self._updating_angle_handle = True
        self._update_angle_handle()
        self._updating_angle_handle = False

    def _radius(self):
        return min(self._rect.width(), self._rect.height()) / 2.0

    def _angle_point(self, angle):
        center = self._rect.center()
        radius = self._radius()
        a = math.radians(angle)
        # Mathematical/TikZ angle convention: 0 degrees points right and
        # positive angles go counter-clockwise. Qt's scene coordinates have
        # the opposite y direction, hence the minus sign.
        return QPointF(
            center.x() + radius * math.cos(a),
            center.y() - radius * math.sin(a),
        )

    def _path(self):
        center = self._rect.center()
        radius = self._radius()
        path = QPainterPath()
        path.moveTo(center)
        # Start at the end of the missing sector, then follow the major arc
        # back to angle 0. Sampling keeps the on-screen geometry independent
        # of Qt's pie-angle convention and matches the TikZ construction.
        start = max(self.MIN_MISSING_ANGLE, min(self.MAX_MISSING_ANGLE, float(self.missing_angle)))
        path.lineTo(self._angle_point(start))
        steps = max(24, int((360.0 - start) * radius / 8.0))
        for i in range(1, steps + 1):
            a = start + (360.0 - start) * i / steps
            path.lineTo(self._angle_point(a))
        path.lineTo(center)
        path.closeSubpath()
        return path

    def _draw_shape(self, painter):
        painter.drawPath(self._path())

    def connection_points(self):
        center = self._rect.center()
        return [
            self._angle_point(0),
            self._angle_point(self.missing_angle),
            center,
        ]

    def _create_handles(self):
        self._angle_handle.show()
        self._update_angle_handle()
        super()._create_handles()
        # The angle handle is deliberately separate from the four resize
        # handles; it controls only the missing sector.
        self._angle_handle.show()

    def _remove_handles(self):
        self._angle_handle.hide()
        super()._remove_handles()

    def _update_handles(self):
        super()._update_handles()
        self._update_angle_handle()

    def _update_angle_handle(self):
        if not hasattr(self, "_angle_handle"):
            return
        self._updating_angle_handle = True
        self._angle_handle.setPos(self._angle_point(self.missing_angle))
        self._updating_angle_handle = False

    def _angle_handle_dragged(self):
        center = self._rect.center()
        pos = self._angle_handle.pos()
        dx = pos.x() - center.x()
        dy = -(pos.y() - center.y())
        if abs(dx) + abs(dy) < 1e-9:
            return
        angle = math.degrees(math.atan2(dy, dx)) % 360.0
        angle = max(self.MIN_MISSING_ANGLE, min(self.MAX_MISSING_ANGLE, angle))
        self.missing_angle = angle
        self._update_angle_handle()
        self.notify_connections()
        self.update()


class IsoscelesTriangleItem(AssortedShapeItem):
    """Manual 6.1.1.1: one of the "various type of Triangle"."""

    def _shape_path_points(self):
        r = self._rect
        return [
            QPointF(r.center().x(), r.top()),
            r.bottomRight(),
            r.bottomLeft(),
        ]

    def connection_points(self):
        """Each vertex and edge midpoint, plus the centroid - same
        vertex-plus-midpoint-plus-center pattern DiamondItem uses,
        rather than the AssortedShapeItem default's bounding-box
        corners (two of which aren't on this triangle's outline at
        all)."""

        apex, bottom_right, bottom_left = self._shape_path_points()

        def midpoint(a, b):
            return QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)

        return [
            apex,
            midpoint(apex, bottom_right),
            bottom_right,
            midpoint(bottom_right, bottom_left),
            bottom_left,
            midpoint(bottom_left, apex),
            self._rect.center(),
        ]


class RightTriangleItem(AssortedShapeItem):
    """Manual 6.1.1.1: another of the "various type of Triangle"."""

    def _shape_path_points(self):
        r = self._rect
        return [r.topLeft(), r.bottomLeft(), r.bottomRight()]

    def connection_points(self):
        """See IsoscelesTriangleItem.connection_points - same
        vertex/edge-midpoint/centroid pattern, for this triangle's own
        (different) three vertices."""

        top_left, bottom_left, bottom_right = self._shape_path_points()

        def midpoint(a, b):
            return QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)

        return [
            top_left,
            midpoint(top_left, bottom_left),
            bottom_left,
            midpoint(bottom_left, bottom_right),
            bottom_right,
            midpoint(bottom_right, top_left),
            self._rect.center(),
        ]


class CrossItem(AssortedShapeItem):
    """Manual 6.1.1.1: "Crosses"."""

    def _shape_path_points(self):
        r = self._rect
        w, h = r.width(), r.height()
        tx, ty = w / 3, h / 3
        x0, y0 = r.left(), r.top()

        return [
            QPointF(x0 + tx, y0),
            QPointF(x0 + 2 * tx, y0),
            QPointF(x0 + 2 * tx, y0 + ty),
            QPointF(x0 + w, y0 + ty),
            QPointF(x0 + w, y0 + 2 * ty),
            QPointF(x0 + 2 * tx, y0 + 2 * ty),
            QPointF(x0 + 2 * tx, y0 + h),
            QPointF(x0 + tx, y0 + h),
            QPointF(x0 + tx, y0 + 2 * ty),
            QPointF(x0, y0 + 2 * ty),
            QPointF(x0, y0 + ty),
            QPointF(x0 + tx, y0 + ty),
        ]

    def connection_points(self):
        """Every one of the cross's own 12 vertices, plus the
        centroid - matching PolygonItem's "every vertex plus centroid"
        convention, rather than the AssortedShapeItem default's
        bounding-box corners (which sit in the cross's notches, well
        outside its actual outline)."""

        return self._shape_path_points() + [self._rect.center()]
