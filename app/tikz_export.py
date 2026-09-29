# tikz_export.py
"""
App addition (not in the manual): exports the diagram as TikZ/PGF
code - a toolbar button and File > Export as Tikz... both call
export_tikz() and show the result (see MainWindow.export_tikz /
show_tikz_dialog in app/main_window.py).

Unlike export_png/export_svg in document_io.py, which hand the whole
job to Qt (QImage/QSvgGenerator both know how to turn arbitrary
painter calls into their target format), there's no built-in "paint
to TikZ" backend - so this module re-derives each shape's geometry
from its own stored attributes (the same attributes document_io's
_serialize_item() reads for saving) and re-expresses them as literal
TikZ drawing commands.

Every coordinate is obtained via item.mapToScene(...) rather than by
hand-rolling the position/rotation/flip/group-nesting algebra: Qt's
own (already-exercised) transform stack already composes an item's
own rotation+flip with its position and with every ancestor's
transform (a group's own position/rotation/flip, recursively), so
mapping each shape's defining local points through it is both less
code and more correct than trying to reconstruct that composition
here. Ellipses/circles are the one shape whose outline isn't just a
handful of literal points - see _local_frame() for how a rotation
angle is recovered purely by comparing mapped points, which stays
correct even under nested/rotated/flipped groups without this module
ever computing that composition explicitly.

Coverage is deliberately uneven: Rectangle/Square/Ellipse/Circle/
Diamond/the Assorted triangles+cross/Polygon/Polyline/Zigzagline/
Line/Arc/Bezierline/Beziergon/Text/Class/Group are reproduced
faithfully (mirroring Dia's manual, this is most of what a diagram is
made of). Actor/Interface/Cylinder are simplified approximations of
their icons (noted inline). The twelve Flowchart/UML shapes of
items/stencil_items.py (Data, Predefined Process, Preparation,
Document, Delay, Summing Junction, Package, Component, Node, Note,
Lifeline, Required Interface) are exported exactly: see
_export_stencil() below. Image references the original file via
\\includegraphics rather than embedding it - same one-way,
references-not-copies approach the manual describes for Dia's own
Image object (5.1.12).
"""

import math

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainterPath

from items.color_picker import representative_color
from items.plot_math import compile_function, sample, FunctionError
from items.mask_item import MaskItem
from items.assorted_item import CircleSectionItem
from items.stencil_items import StencilItem


PX_PER_CM = 20.0  # matches the app's 20px grid == Dia's own 1cm default grid


def _cm(px):
    return px / PX_PER_CM


# TeX pt per cm (1in = 2.54cm = 72.27pt), used only for the couple of
# font-relative quantities below (letter spacing, outline/contour
# halo) that are naturally expressed in points rather than the cm
# coordinate space everything else in this module uses.
PT_PER_CM = 72.27 / 2.54


def _px_to_pt(px):
    return _cm(px) * PT_PER_CM


def _fmt(value):
    """Renders a number to 3 decimal places, trimmed of trailing
    zeros/the decimal point itself, and never bare '-' or '-0'."""

    value = round(value, 3)

    if value == 0:
        value = 0.0

    text = f"{value:.3f}".rstrip("0").rstrip(".")

    return text if text not in ("", "-") else "0"


def _pt(scene_point):
    """Scene point (Qt, y-down, pixels) -> 'x,y' TikZ coordinate
    string (cm, y-up)."""

    return f"{_fmt(_cm(scene_point.x()))},{_fmt(_cm(-scene_point.y()))}"


def _escape_latex(text):
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


def _local_frame(item, origin):
    """
    Maps the item's own local +x axis at `origin` into TikZ space via
    item.mapToScene(), returning (scene_origin, angle_degrees) -
    `angle_degrees` is the CCW rotation (TikZ's own convention) that
    axis ends up at. Callers that only need to place a shape whose
    appearance doesn't change under reflection (an ellipse/circle is
    identical to its own mirror image) can use this angle alone,
    without separately tracking flip state.

    Reading item.rotation_angle directly would only capture this
    item's rotation relative to its immediate parent - wrong the
    moment it (or an ancestor) sits inside a rotated group. Deriving
    it from mapped points instead is correct at any nesting depth,
    since it measures what actually happens to the axis rather than
    replaying the matrix math by hand.
    """

    o = item.mapToScene(origin)
    ex_p = item.mapToScene(origin + QPointF(1, 0))

    # Scene delta, converted to TikZ's y-up sense.
    dx = ex_p.x() - o.x()
    dy = -(ex_p.y() - o.y())

    return o, math.degrees(math.atan2(dy, dx))


_DASH_STYLE = {
    "solid": None,
    "dashed": "dashed",
    "dash-dot": "dashdotted",
    "dash-dot-dot": "dashdotdotted",
    "dotted": "dotted",
}

# arrows.meta tip names. Not a perfect match for every style this app
# offers (there's no built-in square/diamond-tip pair in the base
# library under those exact silhouettes) but a reasonable stand-in
# for each - see the header comment on \\usetikzlibrary{arrows.meta}.
_ARROW_TIP = {
    "none": None,
    "line_arrow": "Straight Barb",
    "filled_triangle": "Triangle",
    "hollow_triangle": "Triangle[open]",
    "filled_diamond": "Diamond",
    "hollow_diamond": "Diamond[open]",
    "filled_circle": "Circle",
    "hollow_circle": "Circle[open]",
    "filled_square": "Turned Square",
    "hollow_square": "Turned Square[open]",
    "half_head": "Straight Barb[harpoon]",
}


class _ColorRegistry:
    """
    Collects every distinct QColor used across the export and hands
    back one TikZ-safe name per color, defined once via \\definecolor
    up front - so e.g. a dozen shapes sharing the same fill reference
    one name instead of repeating a raw RGB triple at every use site.
    """

    def __init__(self):
        self._names = {}

    def name(self, qcolor):
        key = qcolor.name()

        if key not in self._names:
            self._names[key] = f"pydiaC{key[1:].upper()}"

        return self._names[key]

    def definitions(self):
        return [
            f"\\definecolor{{{name}}}{{HTML}}{{{hexval[1:].upper()}}}"
            for hexval, name in self._names.items()
        ]


class _Exporter:

    def __init__(self):
        self.colors = _ColorRegistry()
        self.lines = []
        # Set by _text_node() below whenever a Text shape actually
        # uses outline/letter-spacing, so export_tikz() only adds the
        # packages that feature needs to the preamble.
        self.uses_contour = False
        self.uses_letterspacing = False

    # -- small helpers --------------------------------------------------

    def emit(self, line):
        self.lines.append(line)

    def _pen_options(self, color, width_px, line_style="solid"):
        # Gradients (app addition) approximate to their first stop
        # color here - proper \shade-based gradient export would need
        # per-shape-type work this export doesn't do yet.
        color = representative_color(color)

        opts = [
            f"draw={self.colors.name(color)}",
            f"line width={_fmt(_cm(width_px))}cm",
        ]

        if color.alphaF() < 0.999:
            # Alpha-channel border colors (property dialogs' color
            # pickers all support ShowAlphaChannel) become a separate
            # `draw opacity` - TikZ's `fill=`/`draw=` color names carry
            # RGB only, opacity is its own option.
            opts.append(f"draw opacity={_fmt(color.alphaF())}")

        dash = _DASH_STYLE.get(line_style)

        if dash:
            opts.append(dash)

        return opts

    def _fill_option(self, color, draw_background=True):
        if not draw_background:
            return []

        color = representative_color(color)

        opts = [f"fill={self.colors.name(color)}"]

        if color.alphaF() < 0.999:
            opts.append(f"fill opacity={_fmt(color.alphaF())}")

        return opts

    def _arrow_option(self, start_arrow, end_arrow):
        tip_start = _ARROW_TIP.get(start_arrow)
        tip_end = _ARROW_TIP.get(end_arrow)

        if not tip_start and not tip_end:
            return []

        return [f"{tip_start or ''}-{tip_end or ''}"]

    def _polygon(self, item, local_points, options, close=True):
        pts = " -- ".join(
            f"({_pt(item.mapToScene(p))})" for p in local_points
        )

        self.emit(
            f"\\draw[{', '.join(options)}] {pts}{' -- cycle' if close else ''};"
        )

    def _polyline_open(self, item, local_points, options):
        self._polygon(item, local_points, options, close=False)

    def _ellipse(self, item, local_rect, options):
        origin = local_rect.center()
        o, angle = _local_frame(item, origin)

        rx = _cm(local_rect.width() / 2)
        ry = _cm(local_rect.height() / 2)

        # Item scale (Objects -> Scale): measure how far one local unit
        # along each axis really travels in the scene.
        p0 = item.mapToScene(origin)
        px_ = item.mapToScene(origin + QPointF(1, 0))
        py_ = item.mapToScene(origin + QPointF(0, 1))
        rx *= math.hypot(px_.x() - p0.x(), px_.y() - p0.y())
        ry *= math.hypot(py_.x() - p0.x(), py_.y() - p0.y())

        rotate = f"rotate around={{{_fmt(angle)}:({_pt(o)})}}"

        self.emit(
            f"\\draw[{rotate}, {', '.join(options)}] "
            f"({_pt(o)}) ellipse ({_fmt(rx)}cm and {_fmt(ry)}cm);"
        )

    def _cubic_path(self, item, nodes, closed):
        """
        nodes: list of {"anchor","control_in","control_out"} dicts in
        the item's local coordinates (see bezier_utils.build_bezier_path,
        which this mirrors exactly, one segment per pair of
        consecutive anchors: (prev anchor) .. controls (prev's
        control_out) and (cur's control_in) .. (cur anchor)).
        """

        pts = [f"({_pt(item.mapToScene(nodes[0]['anchor']))})"]

        def segment(prev, cur):
            c1 = item.mapToScene(prev["control_out"])
            c2 = item.mapToScene(cur["control_in"])
            anchor = item.mapToScene(cur["anchor"])
            pts.append(f".. controls ({_pt(c1)}) and ({_pt(c2)}) .. ({_pt(anchor)})")

        for prev, cur in zip(nodes, nodes[1:]):
            segment(prev, cur)

        if closed and len(nodes) > 1:
            segment(nodes[-1], nodes[0])

        return pts

    def _text_node(self, item, local_pos, text, color, font_size,
                    bold=False, italic=False, align="left", options=None,
                    letter_spacing=0.0, outline_enabled=False,
                    outline_color=None, outline_width=0.0):
        if not text:
            return

        # A gradient/pattern text color approximates to its
        # first/primary color, same as _pen_options()/_fill_option().
        color = representative_color(color)

        # microtype's \textls[<permille>]{...} tracks by a fraction of
        # the current font's em (1000ths), so the app's absolute px
        # spacing is re-expressed relative to this text's own point
        # size rather than carried over as a raw length.
        permille = round(_px_to_pt(letter_spacing) / font_size * 1000) if (
            letter_spacing and font_size
        ) else 0

        if permille:
            self.uses_letterspacing = True

        contour_length = None

        if outline_enabled:
            self.uses_contour = True
            outline_color_name = self.colors.name(
                representative_color(outline_color)
            )
            # contour's \contourlength is a halo radius added on every
            # side of each glyph, matching how the app's own
            # outline_width (a QPen stroke width, split evenly across
            # the glyph edge - see _EditableTextChild.paint()) is
            # already halved wherever its geometric extent is used.
            contour_length = _fmt(_px_to_pt(outline_width / 2.0))

        def _style_line(escaped_line):
            # \textls must be the innermost wrapper - it needs to see
            # the raw glyphs to track them; \contour then replicates
            # whatever it's given (already-tracked or not) to build
            # the halo. Applied per explicit line, not to the whole
            # multi-line body at once, since both commands build a
            # single box internally and don't understand a bare "\\"
            # paragraph break inside their argument.
            result = escaped_line

            if permille:
                result = f"\\textls[{permille}]{{{result}}}"

            if outline_enabled:
                result = f"\\contour{{{outline_color_name}}}{{{result}}}"

            return result

        text_lines = text.splitlines() or [""]
        body = " \\\\ ".join(_style_line(_escape_latex(line)) for line in text_lines)

        style = []

        if bold:
            style.append(r"\bfseries")

        if italic:
            style.append(r"\itshape")

        style_prefix = "".join(style)

        opts = [
            f"text={self.colors.name(color)}",
            "align=" + (align if align in ("left", "right", "center") else "left"),
        ]

        if options:
            opts.extend(options)

        o = item.mapToScene(local_pos)

        node_line = (
            f"\\node[{', '.join(opts)}] at ({_pt(o)}) "
            f"{{{style_prefix}{body}}};"
        )

        if outline_enabled:
            # Scoped so each outlined Text shape can carry its own
            # outline_width without one \contourlength assignment
            # leaking into the next.
            self.emit(f"\\begingroup\\contourlength{{{contour_length}pt}}")
            self.emit(node_line)
            self.emit("\\endgroup")
        else:
            self.emit(node_line)


    # -- dispatch ---------------------------------------------------

    def export_item(self, item, item_classes):
        (RectangleItem, EllipseItem, DiamondItem, CylinderItem,
         ActorItem, InterfaceItem, ClassItem,
         TextItem, LineItem, GroupItem, ArcItem, PolygonItem,
         PolylineItem, ZigzaglineItem, ImageItem, BezierlineItem,
         BeziergonItem, SquareItem, CircleItem, IsoscelesTriangleItem,
         RightTriangleItem, CrossItem, RegularPolygonItem, StarItem, SpiralItem, PlotItem) = item_classes

        try:
            if isinstance(item, GroupItem):
                self._export_group(item, item_classes)
            elif isinstance(item, StencilItem):
                self._export_stencil(item)
            elif isinstance(item, PlotItem):
                self._export_plot(item)
            elif isinstance(item, ClassItem):
                self._export_class(item)
            elif isinstance(item, TextItem):
                self._export_text(item)
            elif isinstance(item, ArcItem):
                self._export_arc(item)
            elif isinstance(item, (PolylineItem, ZigzaglineItem)):
                self._export_polyline(item)
            elif isinstance(item, LineItem):
                self._export_line(item)
            elif isinstance(item, PolygonItem):
                self._export_polygon(item)
            elif isinstance(item, MaskItem):
                self._export_mask(item)
            elif isinstance(item, BeziergonItem):
                self._export_beziergon(item)
            elif isinstance(item, BezierlineItem):
                self._export_bezierline(item)
            elif isinstance(item, (CircleItem, )):
                self._export_circle(item)
            elif isinstance(item, EllipseItem):
                self._export_ellipse(item)
            elif isinstance(item, DiamondItem):
                self._export_polygon_points(item, item._vertices(), item)
            elif isinstance(item, (SquareItem, IsoscelesTriangleItem,
                                    RightTriangleItem, CrossItem)):
                self._export_polygon_points(
                    item, item._shape_path_points(), item
                )
            elif isinstance(item, RegularPolygonItem):
                self._export_regular_polygon(item)
            elif isinstance(item, StarItem):
                self._export_star(item)
            elif isinstance(item, CircleSectionItem):
                self._export_circle_section(item)
            elif isinstance(item, SpiralItem):
                self._export_spiral(item)
            elif isinstance(item, ActorItem):
                self._export_actor(item)
            elif isinstance(item, InterfaceItem):
                self._export_interface(item)
            elif isinstance(item, CylinderItem):
                self._export_cylinder(item)
            elif isinstance(item, ImageItem):
                self._export_image(item)
            elif isinstance(item, RectangleItem):
                self._export_rectangle(item)
            else:
                self._export_fallback(item)
        except Exception as exc:  # pragma: no cover - export must never crash
            self.emit(f"% (skipped {type(item).__name__}: {exc})")

    # -- per-type exporters -------------------------------------------

    def _export_plot(self, item):
        """
        Export the Plot shape, including its current axis/tick settings.

        The plot functions and fill are sampled in the same data space as
        PlotItem.paint().  Axis rendering is reproduced from PlotItem's
        settings, including custom tick-label templates.  In a template,
        ``{value}`` is replaced by the numerical tick value before the
        result is escaped for use as ordinary TikZ text.
        """

        try:
            f1 = compile_function(item.f1_expr)
            f2 = compile_function(item.f2_expr)
        except FunctionError:
            self._export_fallback(item)
            return

        xs, ys1 = sample(
            f1, item.x_min, item.x_max, item.num_points, (item.x1, item.x2)
        )
        _, ys2 = sample(
            f2, item.x_min, item.x_max, item.num_points, (item.x1, item.x2)
        )

        top_pts, bottom_pts = [], []
        x_left = min(item.x1, item.x2)
        x_right = max(item.x1, item.x2)

        for x, y1, y2 in zip(xs, ys1, ys2):
            if not (x_left <= x <= x_right):
                continue

            if y1 != y1 or y2 != y2:
                continue

            top_pts.append(item.to_px(x, y1))
            bottom_pts.append(item.to_px(x, y2))

        if len(top_pts) >= 2:
            fill_opts = ["draw=none"] + self._fill_option(item.fill_color, True)
            self._polygon(
                item, top_pts + list(reversed(bottom_pts)), fill_opts, close=True
            )

        # The two vertical fill-boundary markers use exactly the same
        # colors and line styles as the on-canvas Plot item.
        if item.show_bounds_lines:
            for x, color in (
                (item.x1, item.x1_line_color),
                (item.x2, item.x2_line_color),
            ):
                if item.x_min <= x <= item.x_max:
                    bounds_opts = self._pen_options(
                        color, item.bounds_line_width, item.bounds_line_style
                    )
                    self._polyline_open(
                        item,
                        [item.to_px(x, item.y_min), item.to_px(x, item.y_max)],
                        bounds_opts,
                    )

        def curve_runs(ys):
            runs, run = [], []

            for x, y in zip(xs, ys):
                if y != y:
                    if len(run) >= 2:
                        runs.append(run)
                    run = []
                    continue

                run.append(item.to_px(x, y))

            if len(run) >= 2:
                runs.append(run)

            return runs

        f1_opts = self._pen_options(item.f1_color, item.curve_width)
        for run in curve_runs(ys1):
            self._polyline_open(item, run, f1_opts)

        f2_opts = self._pen_options(item.f2_color, item.curve_width)
        for run in curve_runs(ys2):
            self._polyline_open(item, run, f2_opts)

        axis_opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )

        if item.axis_type == "boxed":
            r = item._rect
            corners = [
                r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()
            ]
            self._polygon(item, corners, axis_opts, close=True)

            # Boxed axes have tick marks on all four sides, but labels only
            # on the conventional bottom/left sides.
            self._export_plot_ticks(
                item, bottom=True, left=True, top=True, right=True,
                bottom_labels=item.show_xtick_labels,
                left_labels=item.show_ytick_labels,
                top_labels=False,
                right_labels=False,
            )

        elif item.axis_type == "framed":
            # Framed = bottom + left axes only, with arrows, no top/right.
            r = item._rect
            bottom = [QPointF(r.left(), r.bottom()), QPointF(r.right(), r.bottom())]
            left = [QPointF(r.left(), r.bottom()), QPointF(r.left(), r.top())]

            framed_opts = list(axis_opts)
            framed_opts += ["-{Straight Barb}"]
            self._polyline_open(item, bottom, framed_opts)
            self._polyline_open(item, left, framed_opts)

            self._export_plot_ticks(
                item, bottom=True, left=True,
                bottom_labels=item.show_xtick_labels,
                left_labels=item.show_ytick_labels,
            )

        elif item.axis_type == "normal":
            y0 = 0.0 if item.y_min <= 0 <= item.y_max else item.y_min
            x0 = 0.0 if item.x_min <= 0 <= item.x_max else item.x_min

            normal_opts = list(axis_opts) + ["-{Straight Barb}"]
            self._polyline_open(
                item,
                [item.to_px(item.x_min, y0), item.to_px(item.x_max, y0)],
                normal_opts,
            )
            self._polyline_open(
                item,
                [item.to_px(x0, item.y_min), item.to_px(x0, item.y_max)],
                normal_opts,
            )

            self._export_plot_ticks(
                item,
                normal=True,
                y0=y0,
                x0=x0,
                bottom_labels=item.show_xtick_labels,
                left_labels=item.show_ytick_labels,
            )

    @staticmethod
    def _plot_tick_label(value, template):
        """Return PlotItem's custom tick label in export-safe plain text."""
        base = f"{value:g}"
        if base == "-0":
            base = "0"
        template = template or "{value}"
        return template.replace("{value}", base)

    def _plot_node(self, item, local_point, text, anchor):
        """Emit a tick-label node at a Plot-local point."""
        scene_point = item.mapToScene(local_point)
        opts = [f"anchor={anchor}"]
        self.emit(
            f"\\node[{', '.join(opts)}] at ({_pt(scene_point)}) "
            f"{{{_escape_latex(text)}}};"
        )

    def _export_plot_ticks(
        self, item, bottom=False, left=False, top=False, right=False,
        bottom_labels=True, left_labels=True, top_labels=False,
        right_labels=False, normal=False, y0=None, x0=None
    ):
        """Export Plot tick marks and the user-customized tick labels."""
        r = item._rect

        for x in item._tick_xs():
            if normal:
                p = item.to_px(x, y0)
                if bottom:
                    self._polyline_open(
                        item,
                        [QPointF(p.x(), p.y() - 3), QPointF(p.x(), p.y() + 3)],
                        self._pen_options(item.border_color, 1),
                    )
                if bottom_labels:
                    self._plot_node(
                        item,
                        QPointF(p.x(), p.y() + 16),
                        self._plot_tick_label(x, item.x_tick_label_format),
                        "north",
                    )
                continue

            if bottom:
                p = item.to_px(x, item.y_min)
                self._polyline_open(
                    item,
                    [QPointF(p.x(), r.bottom()),
                     QPointF(p.x(), r.bottom() - 5)],
                    self._pen_options(item.border_color, 1),
                )
                if bottom_labels:
                    self._plot_node(
                        item,
                        QPointF(p.x(), r.bottom() + 16),
                        self._plot_tick_label(x, item.x_tick_label_format),
                        "north",
                    )

            if top:
                p = item.to_px(x, item.y_max)
                self._polyline_open(
                    item,
                    [QPointF(p.x(), r.top()),
                     QPointF(p.x(), r.top() + 5)],
                    self._pen_options(item.border_color, 1),
                )
                if top_labels:
                    self._plot_node(
                        item,
                        QPointF(p.x(), r.top() - 16),
                        self._plot_tick_label(x, item.x_tick_label_format),
                        "south",
                    )

        for y in item._tick_ys():
            if normal:
                p = item.to_px(x0, y)
                if left:
                    self._polyline_open(
                        item,
                        [QPointF(p.x() - 3, p.y()), QPointF(p.x() + 3, p.y())],
                        self._pen_options(item.border_color, 1),
                    )
                if left_labels:
                    self._plot_node(
                        item,
                        QPointF(p.x() - 26, p.y() + 4),
                        self._plot_tick_label(y, item.y_tick_label_format),
                        "east",
                    )
                continue

            if left:
                p = item.to_px(item.x_min, y)
                self._polyline_open(
                    item,
                    [QPointF(r.left(), p.y()),
                     QPointF(r.left() + 5, p.y())],
                    self._pen_options(item.border_color, 1),
                )
                if left_labels:
                    self._plot_node(
                        item,
                        QPointF(r.left() - 30, p.y() + 4),
                        self._plot_tick_label(y, item.y_tick_label_format),
                        "east",
                    )

            if right:
                p = item.to_px(item.x_max, y)
                self._polyline_open(
                    item,
                    [QPointF(r.right(), p.y()),
                     QPointF(r.right() - 5, p.y())],
                    self._pen_options(item.border_color, 1),
                )
                if right_labels:
                    self._plot_node(
                        item,
                        QPointF(r.right() + 30, p.y() + 4),
                        self._plot_tick_label(y, item.y_tick_label_format),
                        "west",
                    )

    def _export_rectangle(self, item):
        r = item._rect
        corners = [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]

        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, item.draw_background)

        radii = item.corner_radii

        if len(set(radii)) == 1:
            # All four corners equal: TikZ's own key is enough.
            if radii[0] > 0:
                opts.append(f"rounded corners={_fmt(_cm(radii[0]))}cm")

            self._polygon(item, corners, opts)
            return

        # Different radius per corner: emit the exact outline (lines
        # and cubic arcs) mapped through the item's transform.
        path = item._corner_path()
        els = [path.elementAt(i) for i in range(path.elementCount())]
        parts = []
        i = 0

        def pt(e):
            return f"({_pt(item.mapToScene(QPointF(e.x, e.y)))})"

        while i < len(els):
            e = els[i]

            if e.type == QPainterPath.MoveToElement:
                parts.append(pt(e))
            elif e.type == QPainterPath.LineToElement:
                parts.append(f"-- {pt(e)}")
            elif e.type == QPainterPath.CurveToElement and i + 2 < len(els):
                parts.append(
                    f".. controls {pt(e)} and {pt(els[i + 1])} .. "
                    f"{pt(els[i + 2])}"
                )
                i += 2

            i += 1

        self.emit(f"\\draw[{', '.join(opts)}] {' '.join(parts)} -- cycle;")

    def _export_ellipse(self, item):
        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, True)
        self._ellipse(item, item._rect, opts)

    def _export_circle(self, item):
        self._export_ellipse(item)

    def _export_regular_polygon(self, item):
        """Export a regular polygon using TikZ's semantic shape when possible.

        This deliberately does not dump hundreds of sampled coordinates.  The
        number of sides, radius, centre and rotation are all retained as
        parameters in the generated TikZ.  A literal path is used only when
        the application's per-corner radius cannot be represented by the
        TikZ regular-polygon node.
        """
        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, getattr(item, "draw_background", True))

        center_local = item._rect.center()
        center_scene, angle = _local_frame(item, center_local)
        radius_cm = _cm(min(item._rect.width(), item._rect.height()) / 2)
        n = max(item.MIN_POINTS, int(item.num_points))

        if getattr(item, "corner_radius", 0.0) <= 0.0:
            node_opts = list(opts) + [
                "regular polygon",
                f"regular polygon sides={n}",
                f"minimum size={_fmt(2 * radius_cm)}cm",
                "inner sep=0pt",
                f"rotate={_fmt(angle)}",
            ]
            self.emit(
                f"\\node[{', '.join(node_opts)}] at ({_pt(center_scene)}) {{}};"
            )
            return

        # TikZ cannot assign a different corner radius to the semantic
        # regular-polygon node, so retain the exact application geometry for
        # this less-common case rather than silently changing its appearance.
        from items.assorted_item import _rounded_polygon_path
        pts = item._points()
        path = _rounded_polygon_path(pts, [item.corner_radius] * len(pts))
        poly = path.toFillPolygon()
        self._polygon(item, [QPointF(p) for p in poly], opts, close=True)

    def _export_star(self, item):
        """Export a star with TikZ's native star shape when unrounded.

        TikZ's `star`, `star points` and `star point ratio` correspond exactly
        to the model's point count and inner/outer radius ratio.  For rounded
        corners, where TikZ has no separate inner/outer corner-radius keys,
        the actual rounded Qt path is exported instead.
        """
        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, getattr(item, "draw_background", True))

        center_local = item._rect.center()
        center_scene, angle = _local_frame(item, center_local)
        radius_cm = _cm(min(item._rect.width(), item._rect.height()) / 2)
        n = max(item.MIN_POINTS, int(item.num_points))
        ratio = max(0.05, min(float(item.inner_radius_ratio), 0.95))

        if (getattr(item, "outer_corner_radius", 0.0) <= 0.0 and
                getattr(item, "inner_corner_radius", 0.0) <= 0.0):
            node_opts = list(opts) + [
                "star",
                f"star points={n}",
                f"star point ratio={_fmt(ratio)}",
                f"minimum size={_fmt(2 * radius_cm)}cm",
                "inner sep=0pt",
                f"rotate={_fmt(angle)}",
            ]
            self.emit(
                f"\\node[{', '.join(node_opts)}] at ({_pt(center_scene)}) {{}};"
            )
            return

        from items.assorted_item import _rounded_polygon_path
        pts = item._points()
        radii = [
            item.outer_corner_radius if i % 2 == 0 else item.inner_corner_radius
            for i in range(len(pts))
        ]
        path = _rounded_polygon_path(pts, radii)
        poly = path.toFillPolygon()
        self._polygon(item, [QPointF(p) for p in poly], opts, close=True)

    def _export_circle_section(self, item):
        """Export the circle section as the compact native TikZ arc path.

        The missing sector is measured counter-clockwise from 0 degrees to
        ``missing_angle``, exactly matching the requested construction.
        """
        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, getattr(item, "draw_background", True))

        center = item.mapToScene(item._rect.center())
        radius_cm = _cm(min(item._rect.width(), item._rect.height()) / 2.0)
        angle = max(item.MIN_MISSING_ANGLE, min(item.MAX_MISSING_ANGLE, float(item.missing_angle)))
        # Determine the item's actual local x-axis direction so the entire
        # construction remains correct inside rotated/flipped groups.
        _, rotation = _local_frame(item, item._rect.center())

        cx, cy = _pt(center).split(",")
        start_angle = angle + rotation
        end_angle = rotation
        node = f"({cx},{cy}) -- ({_fmt(start_angle)}:{_fmt(radius_cm)}cm) arc ({_fmt(start_angle)}:{_fmt(end_angle)}:{_fmt(radius_cm)}cm) -- cycle"
        self.emit(f"\\path[{', '.join(opts)}] {node};")

    def _export_spiral(self, item):
        """Export the spiral parametrically instead of as sampled vertices.

        The generated TikZ preserves the editable endpoint: its radial length
        and angular direction are derived from the actual centre/endpoint.
        The curve is therefore compact, readable and remains mathematically
        a spiral rather than a long list of line segments.
        """
        opts = self._pen_options(item.pen_color, item.pen_width, item.line_style)

        center_scene = item.mapToScene(item._center)
        endpoint_scene = item.mapToScene(item._endpoint)
        dx = endpoint_scene.x() - center_scene.x()
        dy = -(endpoint_scene.y() - center_scene.y())
        radius_cm = math.hypot(dx, dy) / PX_PER_CM
        end_angle = math.degrees(math.atan2(dy, dx))
        turns = max(float(item.MIN_TURNS), float(item.turns))

        if radius_cm <= 1e-9:
            self.emit(f"\\draw[{', '.join(opts)}] ({_pt(center_scene)}) -- ({_pt(endpoint_scene)});")
            return

        # The application's spiral starts at -90 degrees and finishes at the
        # endpoint angle after `turns` complete revolutions.  TikZ/PGF uses
        # degrees in cos()/sin(), so no coordinate sampling is necessary.
        span = turns * 360.0 + end_angle + 90.0
        plot_opts = list(opts) + [
            "variable=\\t",
            f"domain=0:{_fmt(span)}",
            "samples=160",
            "smooth",
        ]
        rate = radius_cm / span if abs(span) > 1e-9 else 0.0
        cx, cy = _pt(center_scene).split(",")
        self.emit(
            f"\\draw[shift={{({cx},{cy})}}, {', '.join(plot_opts)}] "
            f"plot[variable=\\t] ({{{rate:.9g}*\\t*cos(\\t-90)}}, "
            f"{{{rate:.9g}*\\t*sin(\\t-90)}})"
            f"; % endpoint angle={_fmt(end_angle)}\u00b0, radius={_fmt(radius_cm)}cm"
        )

    def _export_stencil(self, item):
        """
        Exports one of the Flowchart/UML shapes of items/stencil_items.py.

        The shape's layers() are the very geometry paint() draws - lines,
        cubic Beziers and ellipses - so this walks those and re-emits
        them one-to-one, instead of keeping a second, hand-maintained
        TikZ description per shape that could drift from the canvas.
        Filled layers get the shape's fill (unless Draw background is
        off); every layer gets the border colour/width/style, and a
        Lifeline's line is dashed even when the border style is solid
        (StencilItem.layer_line_style()).
        """

        for layer in item.layers():
            opts = self._pen_options(
                item.border_color, item.border_width,
                item.layer_line_style(layer)
            )

            if layer.filled:
                opts += self._fill_option(
                    item.fill_color, item.draw_background
                )

            if layer.ellipse is not None:
                self._ellipse(item, layer.ellipse, opts)
            else:
                self._stencil_path(item, layer.path, opts, close=layer.filled)

    def _stencil_path(self, item, path, options, close):
        """
        Re-emits a QPainterPath (MoveTo/LineTo/CurveTo elements only) as
        one TikZ \\draw. `close` (used for filled outlines) ends every
        sub-path with `-- cycle` so the outline joins up properly; Qt's
        own closing line back to the start point is dropped in favour
        of it.
        """

        def pt(element):
            return f"({_pt(item.mapToScene(QPointF(element.x, element.y)))})"

        subpaths = []
        current = None
        i = 0

        while i < path.elementCount():
            e = path.elementAt(i)

            if e.type == QPainterPath.MoveToElement:
                current = {"start": (e.x, e.y), "last": (e.x, e.y),
                           "pieces": [pt(e)]}
                subpaths.append(current)
                i += 1
            elif e.type == QPainterPath.LineToElement:
                current["pieces"].append(f"-- {pt(e)}")
                current["last"] = (e.x, e.y)
                i += 1
            elif e.type == QPainterPath.CurveToElement:
                c2 = path.elementAt(i + 1)
                end = path.elementAt(i + 2)
                current["pieces"].append(
                    f".. controls {pt(e)} and {pt(c2)} .. {pt(end)}"
                )
                current["last"] = (end.x, end.y)
                i += 3
            else:
                i += 1

        texts = []

        for sub in subpaths:
            pieces = sub["pieces"]

            if close:
                closes_on_start = (
                    abs(sub["last"][0] - sub["start"][0]) < 1e-6
                    and abs(sub["last"][1] - sub["start"][1]) < 1e-6
                )

                if (len(pieces) > 1 and closes_on_start
                        and pieces[-1].startswith("-- ")):
                    pieces = pieces[:-1]

                pieces = pieces + ["-- cycle"]

            texts.append(" ".join(pieces))

        self.emit(f"\\draw[{', '.join(options)}] {' '.join(texts)};")

    def _export_polygon_points(self, item, points, source):
        opts = self._pen_options(
            source.border_color, source.border_width,
            getattr(source, "line_style", "solid")
        )
        opts += self._fill_option(source.fill_color, True)
        self._polygon(item, points, opts)

    def _export_polygon(self, item):
        self._export_polygon_points(item, item._points, item)

    def _export_polyline(self, item):
        opts = self._pen_options(item.pen_color, item.pen_width, item.line_style)
        opts += self._arrow_option(item.start_arrow, item.end_arrow)

        if getattr(item, "corner_radius", 0) > 0:
            radius = (item.corner_radius / 10.0) * 20.0  # CORNER_RADIUS_MAX_PX
            opts.append(f"rounded corners={_fmt(_cm(radius))}cm")

        self._polyline_open(item, item._points, opts)

    def _export_line(self, item):
        opts = self._pen_options(item.pen_color, item.pen_width, item.line_style)
        opts += self._arrow_option(item.start_arrow, item.end_arrow)
        self._polyline_open(item, [item._p1, item._p2], opts)

    def _export_arc(self, item):
        opts = self._pen_options(item.pen_color, item.pen_width, item.line_style)
        opts += self._arrow_option(item.start_arrow, item.end_arrow)

        p1, p2 = item._p1, item._p2
        control = item._control_point()

        # Qt's quadTo(control, p2) as an equivalent cubic (the two
        # curves are mathematically identical), since TikZ's `..
        # controls A and B ..` path syntax is cubic-only.
        c1 = p1 + (control - p1) * (2 / 3)
        c2 = p2 + (control - p2) * (2 / 3)

        p1s, c1s, c2s, p2s = (
            item.mapToScene(p1), item.mapToScene(c1),
            item.mapToScene(c2), item.mapToScene(p2),
        )

        self.emit(
            f"\\draw[{', '.join(opts)}] ({_pt(p1s)}) "
            f".. controls ({_pt(c1s)}) and ({_pt(c2s)}) .. ({_pt(p2s)});"
        )

    def _export_mask(self, item):
        """Apply a Beziergon mask to everything exported below it.

        QGraphicsScene paints the mask after the objects underneath it.
        TikZ has the same effect by retrospectively wrapping the already
        emitted lower-z content in an even-odd clipping scope containing
        the export page plus the mask path. Objects above the mask are
        emitted after that scope and therefore remain unaffected.
        """
        scene = item.scene()
        page = scene.paper_rect() if scene is not None else QRectF(-1000, -1000, 2000, 2000)
        page_path = (
            f"({_pt(QPointF(page.left(), page.top()))}) -- "
            f"({_pt(QPointF(page.right(), page.top()))}) -- "
            f"({_pt(QPointF(page.right(), page.bottom()))}) -- "
            f"({_pt(QPointF(page.left(), page.bottom()))}) -- cycle"
        )
        mask_pts = self._cubic_path(item, item._nodes, closed=True)
        mask_path = " ".join(mask_pts) + " -- cycle"

        previous = list(self.lines)
        self.lines = [
            "\\begin{scope}[even odd rule]",
            f"\\clip {page_path} {mask_path};",
            *previous,
            "\\end{scope}",
        ]

    def _export_beziergon(self, item):
        opts = self._pen_options(
            item.border_color, item.border_width,
            getattr(item, "line_style", "solid")
        )
        opts += self._fill_option(item.fill_color, True)

        pts = self._cubic_path(item, item._nodes, closed=True)
        self.emit(f"\\draw[{', '.join(opts)}] {' '.join(pts)} -- cycle;")

    def _export_bezierline(self, item):
        opts = self._pen_options(item.pen_color, item.pen_width, item.line_style)
        opts += self._arrow_option(item.start_arrow, item.end_arrow)

        pts = self._cubic_path(item, item._nodes, closed=False)
        self.emit(f"\\draw[{', '.join(opts)}] {' '.join(pts)};")

    def _export_text(self, item):
        r = item._rect

        if item.draw_background:
            opts = ["draw=none"] + self._fill_option(item.fill_color, True)
            self._polygon(
                item, [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()],
                opts,
            )

        self._text_node(
            item, r.center(), item.text(), item.text_color, item.font_size,
            bold=item.font_weight in ("bold", "bold_italic"),
            italic=item.font_weight in ("italic", "bold_italic"),
            align=item.text_align,
            options=[f"text width={_fmt(_cm(r.width()))}cm"],
            letter_spacing=item.letter_spacing,
            outline_enabled=item.outline_enabled,
            outline_color=item.outline_color,
            outline_width=item.outline_width,
        )

    def _export_class(self, item):
        r = item._rect
        name_rect, attr_rect, op_rect = item._compartment_rects()

        opts = self._pen_options(item.border_color, item.border_width)
        opts += self._fill_option(item.fill_color, True)
        self._polygon(item, [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()], opts)

        line_opts = self._pen_options(item.border_color, max(item.border_width, 1))
        self._polyline_open(
            item,
            [QPointF(r.left(), name_rect.bottom()), QPointF(r.right(), name_rect.bottom())],
            line_opts,
        )
        self._polyline_open(
            item,
            [QPointF(r.left(), attr_rect.bottom()), QPointF(r.right(), attr_rect.bottom())],
            line_opts,
        )

        self._text_node(
            item, name_rect.center(), item.class_name, item.border_color, 11,
            bold=True, align="center",
            options=[f"text width={_fmt(_cm(name_rect.width()))}cm"],
        )
        self._text_node(
            item, QPointF(attr_rect.left() + 4, attr_rect.top() + 2),
            item.attributes, item.border_color, 9, align="left",
            options=[
                f"text width={_fmt(_cm(attr_rect.width() - 8))}cm",
                "anchor=north west",
            ],
        )
        self._text_node(
            item, QPointF(op_rect.left() + 4, op_rect.top() + 2),
            item.operations, item.border_color, 9, align="left",
            options=[
                f"text width={_fmt(_cm(op_rect.width() - 8))}cm",
                "anchor=north west",
            ],
        )

    def _export_actor(self, item):
        # Approximation of the stick-figure icon (head/torso/arms/
        # legs) - see items/actor_item.py's own paint() for the exact
        # proportions this mirrors.
        r = item._rect
        w, h = r.width(), r.height()
        cx = r.center().x()

        head_d = min(w * 0.5, h * 0.28)
        head_rect = QRectF(cx - head_d / 2, r.top(), head_d, head_d)

        neck_y = r.top() + head_d
        hip_y = r.top() + h * 0.62
        foot_y = r.bottom()
        arm_y = neck_y + (hip_y - neck_y) * 0.25

        opts = self._pen_options(item.border_color, item.border_width)
        opts += self._fill_option(item.fill_color, True)
        self._ellipse(item, head_rect, opts)

        line_opts = self._pen_options(item.border_color, item.border_width)
        for a, b in (
            (QPointF(cx, neck_y), QPointF(cx, hip_y)),
            (QPointF(r.left(), arm_y), QPointF(r.right(), arm_y)),
            (QPointF(cx, hip_y), QPointF(r.left(), foot_y)),
            (QPointF(cx, hip_y), QPointF(r.right(), foot_y)),
        ):
            self._polyline_open(item, [a, b], line_opts)

    def _export_interface(self, item):
        # Approximation of the "lollipop" icon (a small circle plus a
        # stub line) - see items/interface_item.py's own paint().
        r = item._rect
        circle = item._circle_rect()

        opts = self._pen_options(item.border_color, item.border_width)
        opts += self._fill_option(item.fill_color, True)
        self._ellipse(item, circle, opts)

        line_opts = self._pen_options(item.border_color, item.border_width)
        self._polyline_open(
            item,
            [QPointF(circle.right(), circle.center().y()), QPointF(r.right(), circle.center().y())],
            line_opts,
        )

    def _export_cylinder(self, item):
        # Approximation of the database-cylinder icon: a top ellipse
        # cap plus two straight sides plus a bottom ellipse cap (drawn
        # full rather than as a half-arc, then covered by the fill of
        # the shape above it - visually equivalent to the true
        # top-cap/sides/bottom-arc outline in items/cylinder_item.py).
        r = item._rect
        cap = item._cap_height()

        top_cap = QRectF(r.left(), r.top(), r.width(), cap * 2)
        bottom_cap = QRectF(r.left(), r.bottom() - cap * 2, r.width(), cap * 2)

        opts = self._pen_options(item.border_color, item.border_width)
        fill_opts = opts + self._fill_option(item.fill_color, True)

        body = [
            QPointF(r.left(), r.top() + cap),
            QPointF(r.left(), r.bottom() - cap),
            QPointF(r.right(), r.bottom() - cap),
            QPointF(r.right(), r.top() + cap),
        ]
        self._polygon(item, body, ["draw=none"] + self._fill_option(item.fill_color, True), close=True)

        self._ellipse(item, bottom_cap, fill_opts)
        self._ellipse(item, top_cap, fill_opts)

        line_opts = self._pen_options(item.border_color, item.border_width)
        self._polyline_open(
            item, [QPointF(r.left(), r.top() + cap), QPointF(r.left(), r.bottom() - cap)], line_opts
        )
        self._polyline_open(
            item, [QPointF(r.right(), r.top() + cap), QPointF(r.right(), r.bottom() - cap)], line_opts
        )

    def _export_image(self, item):
        r = item._rect
        origin = r.center()
        o, angle = _local_frame(item, origin)

        width_cm = _fmt(_cm(r.width()))
        height_cm = _fmt(_cm(r.height()))

        if getattr(item, "file_path", ""):
            path = item.file_path.replace("\\", "/")
            self.emit(
                f"\\node[rotate={_fmt(angle)}] at ({_pt(o)}) "
                f"{{\\includegraphics[width={width_cm}cm,height={height_cm}cm]{{{path}}}}};"
                "  % path is local to wherever the diagram was exported from"
            )
        else:
            opts = ["draw=black", "dashed"]
            corners = [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]
            self._polygon(item, corners, opts)
            self.emit(f"% Image has no file set (\"Broken Image\" placeholder)")

    def _export_group(self, item, item_classes):
        self.emit(f"% -- group: {len(item._children)} item(s) --")

        children = sorted(
            item._children,
            key=lambda c: getattr(c, "local_z", 0.0),
        )

        for child in children:
            self.export_item(child, item_classes)

    def _export_fallback(self, item):
        rect = item.boundingRect()
        corners = [
            item.mapToScene(rect.topLeft()),
            item.mapToScene(rect.topRight()),
            item.mapToScene(rect.bottomRight()),
            item.mapToScene(rect.bottomLeft()),
        ]

        pts = " -- ".join(f"({_pt(p)})" for p in corners)
        self.emit(f"% Unsupported item type: {type(item).__name__}")
        self.emit(f"\\draw[draw=black, dashed] {pts} -- cycle;")


def _item_classes():
    # Deferred import, same reasoning as document_io._item_classes():
    # avoids a load-order cycle with items/*.py.
    from items.rectangle_item import RectangleItem
    from items.ellipse_item import EllipseItem
    from items.diamond_item import DiamondItem
    from items.cylinder_item import CylinderItem
    from items.actor_item import ActorItem
    from items.interface_item import InterfaceItem
    from items.class_item import ClassItem
    from items.text_item import TextItem
    from items.line_item import LineItem
    from items.arc_item import ArcItem
    from items.polygon_item import PolygonItem
    from items.polyline_item import PolylineItem
    from items.zigzagline_item import ZigzaglineItem
    from items.image_item import ImageItem
    from items.bezierline_item import BezierlineItem
    from items.beziergon_item import BeziergonItem
    from items.group_item import GroupItem
    from items.assorted_item import (
        SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
        CrossItem, RegularPolygonItem, StarItem, SpiralItem, CircleSectionItem,
    )
    from items.plot_item import PlotItem

    return (
        RectangleItem, EllipseItem, DiamondItem, CylinderItem,
        ActorItem, InterfaceItem, ClassItem,
        TextItem, LineItem, GroupItem, ArcItem, PolygonItem,
        PolylineItem, ZigzaglineItem, ImageItem, BezierlineItem,
        BeziergonItem, SquareItem, CircleItem, IsoscelesTriangleItem,
        RightTriangleItem, CrossItem, RegularPolygonItem, StarItem, SpiralItem, PlotItem
    )


def export_tikz(scene):
    """
    Returns the diagram as a standalone \\begin{tikzpicture}...
    \\end{tikzpicture} block (plus a leading comment noting the
    preamble it needs), ready to paste into an existing LaTeX
    document - same "export for sharing, not for reopening here"
    spirit as export_png/export_svg (manual 8.2.3).
    """

    from items.diagram_item import DiagramItem
    from items.group_item import GroupItem

    item_classes = _item_classes()

    top_level = [
        i for i in scene.items()
        if isinstance(i, DiagramItem) and i.parentItem() is None
    ]

    top_level_set = set(top_level)
    # scene.items() is front-to-back; reverse for back-to-front
    # drawing order (see canvas/commands.py's own note on why
    # scene.items() rather than a raw zValue() sort is used to break
    # ties consistently).
    top_level = [i for i in reversed(scene.items()) if i in top_level_set]

    exporter = _Exporter()

    for item in top_level:
        exporter.export_item(item, item_classes)

    body = exporter.lines
    color_defs = exporter.colors.definitions()

    header = [
        "% Generated by PyDiagram - Export as TikZ.",
        "% Geometry is exported parametrically where TikZ has a native shape,",
        "% and as exact paths only where the application has extra geometry",
        "% (for example separate inner/outer star corner radii).",
        "\\documentclass[tikz,border=8pt]{standalone}",
        "",
        "\\usepackage{xcolor}",
        "\\usetikzlibrary{shapes.geometric,arrows.meta}",
    ]

    # Only pulled in when a Text shape actually uses that feature -
    # contour/microtype require pdflatex or lualatex, so a diagram
    # with no outlined/letter-spaced text stays compilable as before.
    if exporter.uses_contour:
        header.append("\\usepackage{contour}")

    if exporter.uses_letterspacing:
        header.append("\\usepackage{microtype}")

    header.append("")

    lines = header

    if color_defs:
        lines += color_defs + [""]

    lines.append("\\begin{document}")
    lines.append("")
    lines.append("\\begin{tikzpicture}")
    lines += [f"  {line}" for line in body]
    lines.append("\\end{tikzpicture}")
    lines.append("")
    lines.append("\\end{document}")

    return "\n".join(lines)
