# plot_item.py
"""
App addition (not in the manual): the "Plot" shape - two functions
f1(x)/f2(x) plotted over a wide [x_min, x_max] domain, with the area
between them filled solid/gradient/pattern over a narrower [x1, x2]
sub-range (marked by its own two vertical boundary lines), and a
choice of axis styles. Adapted from a reference matplotlib
fill_between()-based script; reimplemented here as a QGraphicsItem so
it behaves like any other shape (resizable, movable, connectable,
undoable, saved/loaded, TikZ-exportable) rather than a one-off static
picture.

Geometry-wise this is a resizable rectangle (same _rect/resize-handle
contract as RectangleItem) whose interior is entirely computed at
paint time from its data-space settings (f1_expr, f2_expr, the x/y
ranges) rather than drawn from stored points, the way Text's own
content is computed from its string rather than stored as a path.

The fill polygon is built by walking f1 forward across [x1, x2] then
f2 backward (the standard fill_between construction) and drawn with
Qt's OddEvenFill rule set explicitly - which is what makes it render
correctly even when f1 and f2 cross one another inside [x1, x2] (each
crossing splits the polygon into a self-intersecting "bowtie", and
OddEvenFill is exactly the rule that fills such a shape the way
someone would expect "the area between the two curves" to look,
regardless of which curve is on top at any given x). The vertical
x1/x2 boundary lines are cosmetic markers laid on top of this, not
inputs to the fill shape itself.
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPainterPath, QPen

from .diagram_item import DiagramItem
from .color_picker import brush_for
from .line_item import build_dashed_pen
from .plot_math import compile_function, sample, FunctionError

import math


AXIS_TYPES = ["none", "normal", "framed", "boxed"]

AXIS_TYPE_LABELS = {
    "none": "None",
    "normal": "Normal",
    "framed": "Framed",
    "boxed": "Boxed",
}


class PlotItem(DiagramItem):

    MIN_WIDTH = 120
    MIN_HEIGHT = 100

    def __init__(self, rect=QRectF(0, 0, 320, 220), parent=None):
        super().__init__(parent)

        self._rect = QRectF(rect)

        # f1(x)/f2(x) are plotted over the wide [x_min, x_max] domain
        # (and [y_min, y_max] vertically); the colored area between
        # them is bounded horizontally by the narrower [x1, x2] -
        # marked on the plot by its own two vertical boundary lines,
        # each independently colored (x1_line_color/x2_line_color)
        # with a shared width/style (bounds_line_width/_style).
        self.f1_expr = "sin(x) + 3"
        self.f2_expr = "cos(x) + 1"
        self.x_min = -5.0
        self.x_max = 10.0
        self.x1 = 0.0
        self.x2 = 5.0
        self.y_min = -2.0
        self.y_max = 6.0

        self.axis_type = "normal"
        self.show_grid = False
        self.show_bounds_lines = True
        self.num_points = 200

        # 0 means "automatic" (ticks at the domain ends, and at 0 if
        # it's within range) - a positive value places ticks every
        # that many units instead.
        self.xtick_interval = 0.0
        self.ytick_interval = 0.0
        self.show_xtick_labels = True
        self.show_ytick_labels = True
        # Tick-label templates.  The literal ``{value}`` is replaced by
        # the formatted numeric tick value; surrounding text is preserved.
        # Examples: ``x={value}``, ``t={value}``, ``{value} cm``.
        self.x_tick_label_format = "{value}"
        self.y_tick_label_format = "{value}"

        self.f1_color = QColor("#1565C0")
        self.f2_color = QColor("#C62828")
        self.curve_width = 2

        self.x1_line_color = QColor("#607D8B")
        self.x2_line_color = QColor("#607D8B")
        self.bounds_line_width = 1
        self.bounds_line_style = "dashed"

        self.fill_color = QColor(128, 0, 200, 90)

        self.border_color = QColor("#202020")
        self.border_width = 1
        self.line_style = "solid"
        self.dash_length = 10.0

    # -- geometry (same contract as RectangleItem) ---------------------

    def _build_border_pen(self):
        return build_dashed_pen(
            self.border_color, self.border_width, self.line_style, self.dash_length
        )

    def boundingRect(self):
        extra = self.border_width / 2 + 4
        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        """Corners, edge midpoints, and center - same as
        RectangleItem's, since a Plot's own outline is its rectangle
        regardless of axis style or what's plotted inside it."""

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

        if rect.width() < self.MIN_WIDTH:
            rect.setWidth(self.MIN_WIDTH)

        if rect.height() < self.MIN_HEIGHT:
            rect.setHeight(self.MIN_HEIGHT)

        self.prepareGeometryChange()
        self._rect = rect
        self._update_handles()
        self.notify_connections()
        self.update()

    def mouseDoubleClickEvent(self, event):
        from .property_dialog import open_shape_properties
        open_shape_properties(self, self.scene())
        super().mouseDoubleClickEvent(event)

    # -- data-space <-> pixel-space mapping ----------------------------

    def _span(self):
        dx = self.x_max - self.x_min
        dy = self.y_max - self.y_min
        return (dx if dx != 0 else 1.0), (dy if dy != 0 else 1.0)

    def to_px(self, x, y):
        r = self._rect
        dx, dy = self._span()

        px = r.left() + (x - self.x_min) / dx * r.width()
        py = r.bottom() - (y - self.y_min) / dy * r.height()

        return QPointF(px, py)

    def _curve_path(self, xs, ys):
        path = None

        for x, y in zip(xs, ys):
            if y != y or y in (float("inf"), float("-inf")):  # NaN/inf check
                path = None
                continue

            point = self.to_px(x, y)

            if path is None:
                path = QPainterPath(point)
            else:
                path.lineTo(point)

        return path

    def _build_bounds_pen(self, color):
        return build_dashed_pen(
            color, self.bounds_line_width, self.bounds_line_style, self.dash_length
        )

    # -- painting -------------------------------------------------------

    def paint(self, painter, option, widget=None):
        r = self._rect

        try:
            f1 = compile_function(self.f1_expr)
            f2 = compile_function(self.f2_expr)
        except FunctionError:
            # An invalid expression still draws the frame/axes and a
            # notice, rather than raising out of paint() and taking
            # the whole canvas down with it.
            painter.setPen(self._build_border_pen())
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r)
            painter.drawText(r, Qt.AlignCenter, "Invalid f1(x)/f2(x)")
            self._paint_connection_points(painter)
            return

        xs, ys1 = sample(
            f1, self.x_min, self.x_max, self.num_points, (self.x1, self.x2)
        )
        _, ys2 = sample(
            f2, self.x_min, self.x_max, self.num_points, (self.x1, self.x2)
        )

        painter.save()
        painter.setClipRect(r)

        if self.show_grid and self.axis_type != "none":
            self._paint_grid(painter)

        self._paint_fill(painter, xs, ys1, ys2)

        if self.show_bounds_lines:
            self._paint_bounds_lines(painter)

        f1_path = self._curve_path(xs, ys1)
        f2_path = self._curve_path(xs, ys2)

        if f1_path is not None:
            painter.setPen(QPen(brush_for(self.f1_color), self.curve_width))
            painter.drawPath(f1_path)

        if f2_path is not None:
            painter.setPen(QPen(brush_for(self.f2_color), self.curve_width))
            painter.drawPath(f2_path)

        painter.restore()

        if self.axis_type != "none":
            self._paint_axes(painter)

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r)

        self._paint_connection_points(painter)

    def _paint_fill(self, painter, xs, ys1, ys2):
        """
        Fill the region between f1 and f2 only on x1 <= x <= x2.

        The fill is explicitly clipped to the vertical strip [x1, x2].
        This is important because the two curves may cross, in which
        case a single self-intersecting QPainterPath can otherwise produce
        unwanted regions outside the intended fill.

        The path itself is constructed by following f1 from x1 to x2
        and f2 backwards from x2 to x1.  The clipping rectangle guarantees
        that the horizontal boundaries of the colored region are exactly
        x1 and x2.
        """

        x_left = min(self.x1, self.x2)
        x_right = max(self.x1, self.x2)

        points_f1 = []
        points_f2 = []

        for x, y1, y2 in zip(xs, ys1, ys2):
            if x < x_left or x > x_right:
                continue

            if (
                y1 != y1 or y2 != y2 or
                y1 in (float("inf"), float("-inf")) or
                y2 in (float("inf"), float("-inf"))
            ):
                continue

            points_f1.append(self.to_px(x, y1))
            points_f2.append(self.to_px(x, y2))

        if len(points_f1) < 2 or len(points_f2) < 2:
            return

        # Pixel coordinates of the two vertical limits.
        px1 = self.to_px(x_left, self.y_min).x()
        px2 = self.to_px(x_right, self.y_min).x()

        left = min(px1, px2)
        right = max(px1, px2)

        # Restrict the painter to the requested x-interval.
        painter.save()

        fill_clip = QRectF(
            left,
            self._rect.top(),
            right - left,
            self._rect.height()
        )

        painter.setClipRect(fill_clip, Qt.IntersectClip)

        # Build the closed region:
        #
        #       f1
        #    -------->
        #   |         |
        #   |         |
        #    <--------
        #       f2
        #
        path = QPainterPath(points_f1[0])

        for point in points_f1[1:]:
            path.lineTo(point)

        for point in reversed(points_f2):
            path.lineTo(point)

        path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(brush_for(self.fill_color))

        # WindingFill is preferable here because the x-clip already
        # enforces the horizontal limits.
        path.setFillRule(Qt.WindingFill)

        painter.drawPath(path)

        painter.restore()

    def _paint_bounds_lines(self, painter):
        """The two vertical lines marking [x1, x2], the fill's own
        horizontal bounds - each independently colored, sharing one
        width/style (bounds_line_width/bounds_line_style). Purely a
        visual marker laid on top of the fill - it plays no part in
        the fill polygon's own shape (see _paint_fill)."""

        for x, color in ((self.x1, self.x1_line_color), (self.x2, self.x2_line_color)):
            if self.x_min <= x <= self.x_max:
                painter.setPen(self._build_bounds_pen(color))
                top = self.to_px(x, self.y_max)
                bottom = self.to_px(x, self.y_min)
                painter.drawLine(top, bottom)

    def _ticks(self, lo, hi, interval):
        if interval and interval > 0:
            ticks = []
            n = math.ceil((lo - 1e-9) / interval)
            x = n * interval

            while x <= hi + 1e-9:
                if x >= lo - 1e-9:
                    ticks.append(round(x, 10))
                x += interval

            return ticks if ticks else [lo, hi]

        ticks = {lo, hi}

        if lo <= 0 <= hi:
            ticks.add(0.0)

        return sorted(ticks)

    def _tick_xs(self):
        return self._ticks(self.x_min, self.x_max, self.xtick_interval)

    def _tick_ys(self):
        return self._ticks(self.y_min, self.y_max, self.ytick_interval)

    def _paint_grid(self, painter):
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        painter.setPen(pen)

        for x in self._tick_xs():
            top = self.to_px(x, self.y_max)
            bottom = self.to_px(x, self.y_min)
            painter.drawLine(top, bottom)

        for y in self._tick_ys():
            left = self.to_px(self.x_min, y)
            right = self.to_px(self.x_max, y)
            painter.drawLine(left, right)

    @staticmethod
    def _fmt(value):
        text = f"{value:g}"
        return text if text != "-0" else "0"

    @classmethod
    def _fmt_tick_label(cls, value, template):
        """Apply a user-defined tick-label template.

        ``{value}`` is the only special token.  Keeping the replacement
        deliberately simple means ordinary braces in a label do not turn
        into Python format-string errors.
        """
        base = cls._fmt(value)
        template = template or "{value}"
        return template.replace("{value}", base)

    def _paint_axes(self, painter):
        """
        Axis style is one of AXIS_TYPES:
        - none: nothing (handled by the caller, this is never reached)
        - normal: classroom-style x/y axis lines through y=0/x=0 (or
          the nearest edge, if 0 isn't in range), with small arrowheads
          and tick labels (each togglable independently via
          show_xtick_labels/show_ytick_labels) at each tick.
        - framed: a plain rectangular border around the whole plot,
          with tick marks (no arrows) along the bottom and left edges.
        - boxed: the same border as framed, with tick marks mirrored
          onto the top and right edges too (labels stay on the
          bottom/left, matching a typical fully-boxed scientific plot).

        All positioned across the wide [x_min, x_max]/[y_min, y_max]
        domain the functions are actually plotted over - not the
        narrower [x1, x2] fill bounds, which get their own separate
        vertical lines (_paint_bounds_lines) instead.
        """

        r = self._rect
        painter.setPen(self._build_border_pen())

        if self.axis_type == "boxed":
            # A fully enclosed scientific-style frame.
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r)
            self._paint_ticks(painter, bottom=True, left=True)
            self._paint_ticks(painter, top=True, right=True, labels=False)
            return

        if self.axis_type == "framed":
            # Framed is deliberately different from Boxed: only the
            # bottom and left axes are drawn, exactly on the plot edges,
            # and both carry outward arrowheads.
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self._build_border_pen())

            bottom_start = QPointF(r.left(), r.bottom())
            bottom_end = QPointF(r.right(), r.bottom())
            left_start = QPointF(r.left(), r.bottom())
            left_end = QPointF(r.left(), r.top())

            painter.drawLine(bottom_start, bottom_end)
            self._draw_arrowhead(painter, bottom_start, bottom_end)
            painter.drawLine(left_start, left_end)
            self._draw_arrowhead(painter, left_start, left_end)

            self._paint_ticks(
                painter, bottom=True, left=True,
                bottom_labels=self.show_xtick_labels,
                left_labels=self.show_ytick_labels,
            )
            return

        # "normal"
        axis_pen = QPen(QColor("#000000"), 1)
        painter.setPen(axis_pen)

        y0 = 0.0 if self.y_min <= 0 <= self.y_max else self.y_min
        x0 = 0.0 if self.x_min <= 0 <= self.x_max else self.x_min

        x_axis_start = self.to_px(self.x_min, y0)
        x_axis_end = self.to_px(self.x_max, y0)
        painter.drawLine(x_axis_start, x_axis_end)
        self._draw_arrowhead(painter, x_axis_start, x_axis_end)

        y_axis_start = self.to_px(x0, self.y_min)
        y_axis_end = self.to_px(x0, self.y_max)
        painter.drawLine(y_axis_start, y_axis_end)
        self._draw_arrowhead(painter, y_axis_start, y_axis_end)

        for x in self._tick_xs():
            p = self.to_px(x, y0)
            painter.drawLine(QPointF(p.x(), p.y() - 3), QPointF(p.x(), p.y() + 3))
            if self.show_xtick_labels:
                painter.drawText(
                    QPointF(p.x() - 10, p.y() + 16),
                    self._fmt_tick_label(x, self.x_tick_label_format),
                )

        for y in self._tick_ys():
            p = self.to_px(x0, y)
            painter.drawLine(QPointF(p.x() - 3, p.y()), QPointF(p.x() + 3, p.y()))
            if self.show_ytick_labels:
                painter.drawText(
                    QPointF(p.x() - 26, p.y() + 4),
                    self._fmt_tick_label(y, self.y_tick_label_format),
                )

    def _draw_arrowhead(self, painter, start, end):
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        size = 8
        spread = math.radians(25)

        for sign in (1, -1):
            wing_angle = angle + math.pi - sign * spread
            wing = QPointF(
                end.x() + size * math.cos(wing_angle),
                end.y() + size * math.sin(wing_angle),
            )
            painter.drawLine(end, wing)

    def _paint_ticks(
        self, painter, bottom=False, top=False, left=False, right=False,
        labels=True, bottom_labels=None, left_labels=None
    ):
        r = self._rect
        draw_bottom_labels = (
            labels and self.show_xtick_labels
            if bottom_labels is None else bottom_labels
        )
        draw_left_labels = (
            labels and self.show_ytick_labels
            if left_labels is None else left_labels
        )

        for x in self._tick_xs():
            if bottom:
                p = self.to_px(x, self.y_min)
                painter.drawLine(
                    QPointF(p.x(), r.bottom()),
                    QPointF(p.x(), r.bottom() - 5),
                )
                if draw_bottom_labels:
                    painter.drawText(
                        QPointF(p.x() - 10, r.bottom() + 16),
                        self._fmt_tick_label(x, self.x_tick_label_format),
                    )
            if top:
                p = self.to_px(x, self.y_max)
                painter.drawLine(
                    QPointF(p.x(), r.top()),
                    QPointF(p.x(), r.top() + 5),
                )

        for y in self._tick_ys():
            if left:
                p = self.to_px(self.x_min, y)
                painter.drawLine(
                    QPointF(r.left(), p.y()),
                    QPointF(r.left() + 5, p.y()),
                )
                if draw_left_labels:
                    painter.drawText(
                        QPointF(r.left() - 30, p.y() + 4),
                        self._fmt_tick_label(y, self.y_tick_label_format),
                    )
            if right:
                p = self.to_px(self.x_max, y)
                painter.drawLine(
                    QPointF(r.right(), p.y()),
                    QPointF(r.right() - 5, p.y()),
                )
