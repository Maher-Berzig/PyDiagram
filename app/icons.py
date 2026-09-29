# icons.py
"""
Small pictogram icons for the toolbar/toolbox, drawn with QPainter
instead of loaded from image files. Keeps the project self-contained
(no bundled/licensed icon assets) while giving the toolbox the same
"grid of little line-art icons" look as Dia's toolbox.
"""

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import (
    QBrush, QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPen,
    QPixmap, QPolygonF,
)

SIZE = 24


def _blank_pixmap():
    pixmap = QPixmap(SIZE, SIZE)
    pixmap.fill(Qt.transparent)
    return pixmap


def _icon(draw_fn):
    pixmap = _blank_pixmap()
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    draw_fn(painter)
    painter.end()
    return QIcon(pixmap)


def select_icon():
    def draw(p):
        arrow = QPolygonF([
            QPointF(4, 2), QPointF(4, 18), QPointF(8, 14),
            QPointF(11, 20), QPointF(14, 18.5), QPointF(11, 12.5),
            QPointF(17, 12.5),
        ])
        p.setPen(QPen(QColor("#202020"), 1))
        p.setBrush(QBrush(QColor("#404040")))
        p.drawPolygon(arrow)
    return _icon(draw)


def rotate_icon():
    """App addition (not in the manual): Objects -> Rotate."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(3, 3, 16, 16), 40 * 16, 260 * 16)
        # arrowhead at the open end of the arc
        p.setBrush(QBrush(QColor("#202020")))
        p.drawPolygon(QPolygonF([
            QPointF(16.0, 2.0), QPointF(20.5, 7.5), QPointF(13.0, 7.0),
        ]))
    return _icon(draw)


def flip_icon():
    """App addition (not in the manual): Objects -> Flip."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.drawLine(QPointF(12, 2), QPointF(12, 22))
        p.setPen(QPen(QColor("#202020"), 1))
        p.setBrush(QBrush(QColor("#404040")))
        p.drawPolygon(QPolygonF([
            QPointF(3, 6), QPointF(10, 6), QPointF(10, 18), QPointF(3, 18),
        ]))
        p.setBrush(QBrush(QColor("#a0a0a0")))
        p.drawPolygon(QPolygonF([
            QPointF(21, 6), QPointF(14, 6), QPointF(14, 18), QPointF(21, 18),
        ]))
    return _icon(draw)


def zoom_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(3, 3, 12, 12))
        p.drawLine(QPointF(13, 13), QPointF(20, 20))
    return _icon(draw)


def pan_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        cx, cy, r = 12, 12, 7
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            tip = QPointF(cx + dx * r, cy + dy * r)
            p.drawLine(QPointF(cx, cy), tip)
            # small arrowhead
            if dx == 0:
                p.drawLine(tip, QPointF(tip.x() - 3, tip.y() - 3 * dy))
                p.drawLine(tip, QPointF(tip.x() + 3, tip.y() - 3 * dy))
            else:
                p.drawLine(tip, QPointF(tip.x() - 3 * dx, tip.y() - 3))
                p.drawLine(tip, QPointF(tip.x() - 3 * dx, tip.y() + 3))
    return _icon(draw)


def text_icon():
    def draw(p):
        font = QFont("Sans Serif", 13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(QColor("#202020"), 1))
        p.drawText(QRectF(0, 0, SIZE, SIZE), Qt.AlignCenter, "A")
    return _icon(draw)


def anchor_icon():
    def draw(p):
        p.setRenderHint(p.Antialiasing, True)
        scale = SIZE / 32.0
        p.save()
        p.scale(scale, scale)
        # Polished modern palette & line caps for a cleaner aesthetic
        edge_pen = QPen(QColor("#263238"), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        arc_pen = QPen(QColor("#263238"), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        node_pen = QPen(QColor("#0288D1"), 1.4)
        node_brush = QBrush(QColor("#E1F5FE"))
        # Redesigned proportions with a proper anchor ring, stock (crossbar), and cleaner geometry
        ring_center = QPointF(16, 5)
        stock_left = QPointF(10, 10)
        stock_right = QPointF(22, 10)
        shaft_top = QPointF(16, 6.5)
        shaft_bottom = QPointF(16, 24)
        # Draw Anchor Ring
        p.setPen(edge_pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(ring_center, 2.5, 2.5)
        # Draw Stock (Crossbar)
        p.drawLine(stock_left, stock_right)
        # Draw Main Shaft
        p.drawLine(shaft_top, shaft_bottom)
        # Draw Smooth Curved Arms
        p.setPen(arc_pen)
        left_curve = QPainterPath()
        left_curve.moveTo(16, 23)
        left_curve.cubicTo(11, 23, 7, 20, 7, 15)
        p.drawPath(left_curve)
        right_curve = QPainterPath()
        right_curve.moveTo(16, 23)
        right_curve.cubicTo(21, 23, 25, 20, 25, 15)
        p.drawPath(right_curve)
        # Draw Sharp Anchor Flukes / Tips
        p.setPen(edge_pen)
        left_tip = QPointF(4, 12)
        left_barb = QPointF(8, 13.5)
        p.drawLine(QPointF(7, 15), left_tip)
        p.drawLine(left_tip, left_barb)
        right_tip = QPointF(28, 12)
        right_barb = QPointF(24, 13.5)
        p.drawLine(QPointF(25, 15), right_tip)
        p.drawLine(right_tip, right_barb)
        # Enhanced Tech Nodes (including stock center)
        p.setPen(node_pen)
        p.setBrush(node_brush)
        nodes = [
            ring_center,
            QPointF(16, 10),
            QPointF(7, 15),
            QPointF(25, 15),
            shaft_bottom,
        ]
        for point in nodes:
            p.drawEllipse(point, 2.2, 2.2)
        p.restore()
    return _icon(draw)


def tikz_icon():
    def draw(p):
        p.setRenderHint(p.Antialiasing, True)

        scale = SIZE / 32.0
        p.save()
        p.scale(scale, scale)

        edge_pen = QPen(QColor("#37474F"), 1.8)
        node_pen = QPen(QColor("#1565C0"), 1.4)
        node_brush = QBrush(QColor("#E3F2FD"))

        p.setPen(edge_pen)
        p.setBrush(Qt.NoBrush)

        edges = [
            (QPointF(8, 10), QPointF(20, 7)),
            (QPointF(8, 10), QPointF(13, 21)),
            (QPointF(20, 7), QPointF(27, 15)),
            (QPointF(13, 21), QPointF(27, 15)),
            (QPointF(27, 15), QPointF(23, 25)),
        ]

        for a, b in edges:
            p.drawLine(a, b)

        p.setPen(node_pen)
        p.setBrush(node_brush)

        for point in [
            QPointF(8, 10),
            QPointF(20, 7),
            QPointF(13, 21),
            QPointF(27, 15),
            QPointF(23, 25),
        ]:
            p.drawEllipse(point, 3, 3)

        p.restore()

    return _icon(draw)



def rectangle_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawRect(QRectF(3, 5, 18, 14))
    return _icon(draw)


def ellipse_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(QBrush(QColor("#DFF5E1")))
        p.drawEllipse(QRectF(2, 5, 20, 14))
    return _icon(draw)


def plot_icon():
    """App addition (not in the manual): the Plot shape - a tiny pair
    of axes with a curve, evoking f1(x)/f2(x) over a coordinate
    system."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.2))
        p.drawLine(QPointF(3, 20), QPointF(3, 3))
        p.drawLine(QPointF(3, 20), QPointF(21, 20))

        curve = QPainterPath(QPointF(4, 17))
        curve.cubicTo(QPointF(9, 6), QPointF(13, 22), QPointF(20, 7))
        p.setPen(QPen(QColor("#1565C0"), 1.5))
        p.drawPath(curve)
    return _icon(draw)


def line_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.drawLine(QPointF(3, 20), QPointF(20, 4))
        head = QPolygonF([
            QPointF(20, 4), QPointF(14, 6), QPointF(18, 10),
        ])
        p.setBrush(QBrush(QColor("#202020")))
        p.drawPolygon(head)
    return _icon(draw)


def polygon_icon():
    """Manual 5.1.4, "Polygon"."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawPolygon(QPolygonF([
            QPointF(12, 3), QPointF(21, 10), QPointF(17, 20),
            QPointF(7, 20), QPointF(3, 10),
        ]))
    return _icon(draw)


def star_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        import math
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = 9 if i % 2 == 0 else 4
            pts.append(QPointF(12 + r * math.cos(a), 12 + r * math.sin(a)))
        p.drawPolygon(QPolygonF(pts))
    return _icon(draw)


def spiral_icon():
    def draw(p):
        import math
        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(Qt.NoBrush)
        pts = []
        for i in range(45):
            t = i / 44.0
            a = t * 4 * math.pi
            r = 1 + 9 * t
            pts.append(QPointF(12 + r * math.cos(a), 12 + r * math.sin(a)))
        p.drawPolyline(QPolygonF(pts))
    return _icon(draw)


def arc_icon():
    """Manual 5.1.7, "Arc"."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        path_rect = QRectF(2, 2, 20, 20)
        p.drawArc(path_rect, 30 * 16, 120 * 16)
    return _icon(draw)


def polyline_icon():
    """Manual 5.1.9, "Polyline": arbitrary-angle bends."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        path = [QPointF(3, 20), QPointF(10, 6), QPointF(15, 16), QPointF(21, 4)]
        for a, b in zip(path, path[1:]):
            p.drawLine(a, b)
    return _icon(draw)


def zigzagline_icon():
    """Manual 5.1.8, "Zigzagline": strictly 90-degree bends."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        path = [QPointF(3, 5), QPointF(3, 14), QPointF(14, 14), QPointF(14, 21), QPointF(21, 21)]
        for a, b in zip(path, path[1:]):
            p.drawLine(a, b)
    return _icon(draw)


def image_icon():
    """Manual 5.1.12, "Image": a picture-frame glyph."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#f2f2f2")))
        p.drawRect(QRectF(2, 3, 20, 16))
        p.setBrush(QBrush(QColor("#DFF5E1")))
        p.drawEllipse(QRectF(4, 5, 5, 5))
        p.setBrush(QBrush(QColor("#8fbc8f")))
        p.drawPolygon(QPolygonF([
            QPointF(2, 17), QPointF(9, 9), QPointF(14, 14),
            QPointF(17, 11), QPointF(22, 17), QPointF(22, 19),
            QPointF(2, 19),
        ]))
    return _icon(draw)


def beziergon_icon():
    """Manual 5.1.5, "Beziergon": Polygon, but curved."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        path = QPainterPath(QPointF(12, 3))
        path.cubicTo(QPointF(22, 6), QPointF(20, 16), QPointF(15, 20))
        path.cubicTo(QPointF(10, 23), QPointF(2, 18), QPointF(3, 11))
        path.cubicTo(QPointF(4, 5), QPointF(7, 2), QPointF(12, 3))
        path.closeSubpath()
        p.drawPath(path)
    return _icon(draw)


def mask_icon():
    def draw(p):
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor("#202020"), 1.4))
        p.setBrush(QBrush(QColor("#eeeeee")))
        outer = QRectF(2, 2, 20, 20)
        p.drawRect(outer)
        hole = QPainterPath()
        hole.moveTo(QPointF(5, 12))
        hole.cubicTo(QPointF(6, 4), QPointF(16, 4), QPointF(19, 12))
        hole.cubicTo(QPointF(18, 20), QPointF(7, 20), QPointF(5, 12))
        hole.closeSubpath()
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        p.drawPath(hole)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#d62828"), 1.2, Qt.DashLine))
        p.drawPath(hole)
    return _icon(draw)


def bezierline_icon():
    """Manual 5.1.10, "Bezierline": Line, but curved."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 2))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath(QPointF(3, 20))
        path.cubicTo(QPointF(3, 4), QPointF(19, 20), QPointF(21, 4))
        p.drawPath(path)
    return _icon(draw)


def square_icon():
    """Manual 6.1.1.1, "Assorted": a perfect Square."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawRect(QRectF(3, 3, 18, 18))
    return _icon(draw)


def circle_icon():
    """Manual 6.1.1.1, "Assorted": a perfect Circle."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawEllipse(QRectF(3, 3, 18, 18))
    return _icon(draw)


def circle_section_icon():
    """Assorted: a circle with an adjustable missing sector."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        path = QPainterPath()
        path.moveTo(QPointF(12, 12))
        path.lineTo(QPointF(12, 3))
        path.arcTo(QRectF(3, 3, 18, 18), 90, 270)
        path.lineTo(QPointF(12, 12))
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(QBrush(QColor("#1677ff")))
        p.drawEllipse(QPointF(12, 3), 2.2, 2.2)
    return _icon(draw)


def isosceles_triangle_icon():
    """Manual 6.1.1.1, "Assorted": Triangle."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawPolygon(QPolygonF([
            QPointF(12, 3), QPointF(21, 21), QPointF(3, 21),
        ]))
    return _icon(draw)


def right_triangle_icon():
    """Manual 6.1.1.1, "Assorted": Triangle."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawPolygon(QPolygonF([
            QPointF(3, 3), QPointF(3, 21), QPointF(21, 21),
        ]))
    return _icon(draw)


def cross_icon():
    """Manual 6.1.1.1, "Assorted": Crosses."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#DCEBFF")))
        p.drawPolygon(QPolygonF([
            QPointF(9, 3), QPointF(15, 3), QPointF(15, 9),
            QPointF(21, 9), QPointF(21, 15), QPointF(15, 15),
            QPointF(15, 21), QPointF(9, 21), QPointF(9, 15),
            QPointF(3, 15), QPointF(3, 9), QPointF(9, 9),
        ]))
    return _icon(draw)


def _placeholder_icon(draw_shape_fn):
    """
    Shapes that aren't wired up to a real tool yet get a dashed
    outline and a washed-out fill, so the toolbox visually hints
    "not available" without needing a text label.
    """

    def draw(p):
        p.setPen(QPen(QColor("#9a9a9a"), 1.5, Qt.DashLine))
        p.setBrush(QBrush(QColor("#eeeeee")))
        draw_shape_fn(p)
    return _icon(draw)


def triangle_icon():
    def shape(p):
        p.drawPolygon(QPolygonF([
            QPointF(12, 3), QPointF(21, 20), QPointF(3, 20),
        ]))
    return _placeholder_icon(shape)


def diamond_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(QBrush(QColor("#FFE8B3")))
        p.drawPolygon(QPolygonF([
            QPointF(12, 3), QPointF(21, 12), QPointF(12, 21), QPointF(3, 12),
        ]))
    return _icon(draw)


def cylinder_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(QBrush(QColor("#D9E8FF")))
        body = QRectF(3, 6, 18, 13)
        p.drawRoundedRect(body, 0, 0)
        p.drawEllipse(QRectF(3, 3, 18, 6))
        p.drawLine(QPointF(3, 19), QPointF(3, 9))
        p.drawLine(QPointF(21, 19), QPointF(21, 9))
        p.drawArc(QRectF(3, 13, 18, 6), 0, -180 * 16)
    return _icon(draw)


def parallelogram_icon():
    def shape(p):
        p.drawPolygon(QPolygonF([
            QPointF(7, 5), QPointF(21, 5), QPointF(17, 19), QPointF(3, 19),
        ]))
    return _placeholder_icon(shape)


def class_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.2))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRect(QRectF(3, 3, 18, 18))
        p.drawLine(QPointF(3, 9), QPointF(21, 9))
        p.drawLine(QPointF(3, 15), QPointF(21, 15))
    return _icon(draw)


def actor_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(9, 2, 6, 6))
        p.drawLine(QPointF(12, 8), QPointF(12, 15))
        p.drawLine(QPointF(4, 11), QPointF(20, 11))
        p.drawLine(QPointF(12, 15), QPointF(5, 22))
        p.drawLine(QPointF(12, 15), QPointF(19, 22))
    return _icon(draw)


def interface_icon():
    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1.3))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(3, 9, 8, 8))
        p.drawLine(QPointF(11, 13), QPointF(21, 13))
    return _icon(draw)


def _stencil_icon(class_name, rect, **overrides):
    """
    Toolbox icon for one of the Flowchart/UML shapes in
    items/stencil_items.py, painted by the real shape itself
    (StencilItem.draw_layers) at icon size, so the button always shows
    exactly what the tool will draw. `overrides` shrinks the shape's own
    size parameters (tab height, fold size, ...) to suit a 24 px icon.
    """

    def draw(p):
        from items import stencil_items

        item = getattr(stencil_items, class_name)(QRectF(*rect))
        item.border_color = QColor("#202020")
        item.border_width = 1.4
        item.dash_length = 3.0

        for name, value in overrides.items():
            setattr(item, name, float(value))

        item.draw_layers(p)

    return _icon(draw)


def data_icon():
    return _stencil_icon("DataItem", (2.5, 5, 19, 14), slant=5)


def predefined_process_icon():
    return _stencil_icon("PredefinedProcessItem", (3, 5, 18, 14), bar_inset=3)


def preparation_icon():
    return _stencil_icon("PreparationItem", (2.5, 5, 19, 14), point_inset=5)


def document_icon():
    return _stencil_icon("DocumentItem", (3, 4, 18, 16), wave_height=3)


def delay_icon():
    return _stencil_icon("DelayItem", (3, 5, 18, 14))


def summing_junction_icon():
    return _stencil_icon("SummingJunctionItem", (3.5, 3.5, 17, 17))


def package_icon():
    return _stencil_icon("PackageItem", (3, 4, 18, 16), tab_width=8, tab_height=4)


def component_icon():
    return _stencil_icon(
        "ComponentItem", (2, 4, 20, 16), tab_width=7, tab_height=4
    )


def node_icon():
    return _stencil_icon("NodeItem", (3, 3, 18, 18), depth=5)


def note_icon():
    return _stencil_icon("NoteItem", (4, 3, 16, 18), fold_size=5)


def lifeline_icon():
    return _stencil_icon("LifelineItem", (4, 2, 16, 20), head_height=7)


def required_interface_icon():
    return _stencil_icon("RequiredInterfaceItem", (3, 5, 18, 14))


def arrow_reference_icon():
    return _stencil_icon("ArrowReferenceItem", (2, 5, 20, 14), corner_radius=2.5)


def paper_tape_icon():
    return _stencil_icon("PaperTapeItem", (2, 5, 20, 14), wave_height=3)


def data_storage_icon():
    return _stencil_icon("DataStorageItem", (2, 5, 20, 14), bow_depth=4)


def enumeration_icon():
    return _stencil_icon("EnumerationItem", (3, 4, 18, 16), header_height=5)


def artifact_icon():
    return _stencil_icon("ArtifactItem", (4, 3, 16, 18), fold_size=5)


def frame_icon():
    return _stencil_icon("FrameItem", (3, 4, 18, 16), tab_width=8, tab_height=4)


def crescent_icon():
    """Assorted: crescent, with its blue thickness control point."""

    def draw(p):
        from items.stencil_items import CrescentItem

        item = CrescentItem(QRectF(3, 3, 18, 18))
        item.thickness = 40.0
        item.border_color = QColor("#202020")
        item.border_width = 1.4
        item.draw_layers(p)

        p.setPen(QPen(QColor("#1677ff"), 1))
        p.setBrush(QBrush(QColor("#1677ff")))
        p.drawEllipse(item.handle_point(), 2.0, 2.0)

    return _icon(draw)


def spring_icon():
    return _stencil_icon("SpringItem", (6, 2, 12, 20), coils=3, end_length=3)


def l_shape_icon():
    # The L's box follows its four arm sizes, so give all four.
    return _stencil_icon(
        "LShapeItem", (4, 4, 16, 16),
        v_width=6, v_height=16, h_width=16, h_height=6,
    )


def anchor_cursor():
    """
    App addition (not in the manual): the mouse cursor shown over the
    canvas while the Anchor tool is active (MainWindow.activate_tool()),
    the same "⨉" glyph a click adds (draw_connection_marker() in
    items/diagram_item.py) - so the cursor previews exactly where the
    new connection point will land, with its hotspot (the pixel Qt/
    the OS treats as the actual click position) placed exactly on the
    glyph's centre.

    A real OS cursor is just a static bitmap composited by the window
    system, with no access to a QPainter composition mode - so unlike
    draw_connection_marker()'s on-canvas mark, this can't invert
    itself against whatever happens to be underneath. It uses the
    usual static-image alternative instead: the glyph redrawn white
    in a ring of one-pixel offsets (a cheap halo/outline) underneath a
    black copy on top, which keeps it legible over a light or dark -
    or colored - background alike.
    """

    size = 24
    center = QPointF(size / 2, size / 2)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    font = QFont()
    font.setPixelSize(16)
    font.setBold(True)
    painter.setFont(font)

    symbol_rect = painter.boundingRect(QRectF(0, 0, 0, 0), Qt.AlignCenter, "⨉")
    symbol_rect.moveCenter(center)

    painter.setPen(QColor("white"))
    for dx, dy in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                   (0, 1), (1, -1), (1, 0), (1, 1)):
        painter.drawText(symbol_rect.translated(dx, dy), Qt.AlignCenter, "⨉")

    painter.setPen(QColor("black"))
    painter.drawText(symbol_rect, Qt.AlignCenter, "⨉")

    painter.end()

    return QCursor(pixmap, int(center.x()), int(center.y()))


def line_width_icon(width):
    """
    Manual 4.1.7, Figure 4.10: "five lines of increasing width" in the
    Toolbox's default-line-width control.
    """

    def draw(p):
        p.setPen(QPen(QColor("#202020"), max(width, 1)))
        p.drawLine(QPointF(3, SIZE / 2), QPointF(SIZE - 3, SIZE / 2))
    return _icon(draw)


def restore_colors_icon():
    """Manual Figure 4.8: small black-over-white swatch button."""

    def draw(p):
        p.setPen(QPen(QColor("#202020"), 1))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRect(QRectF(8, 8, 12, 12))
        p.setBrush(QBrush(QColor("#202020")))
        p.drawRect(QRectF(4, 4, 12, 12))
    return _icon(draw)



def reverse_colors_icon():
    """Curved arrow for swapping foreground/background colors."""

    def draw(p):
        p.setRenderHint(p.Antialiasing, True)

        p.setPen(QPen(QColor("#202020"), 1.5))
        p.setBrush(Qt.NoBrush)

        # Curved arrow
        p.drawArc(
            QRectF(4, 4, 16, 16),
            20 * 16,
            200 * 16
        )

        # Arrowhead at the end of the arc
        tip = QPointF(5.87, 17.14)
        left = QPointF(2.26, 14.37)
        right = QPointF(5.96, 12.67)


        p.drawLine(tip, left)
        p.drawLine(tip, right)

    return _icon(draw)



ICON_SIZE = QSize(SIZE, SIZE)
