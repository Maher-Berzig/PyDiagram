import math

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


# ----------------------------------------------------------------------
# Shared style
# ----------------------------------------------------------------------

OUTLINE = QColor("#263238")
PRIMARY = QColor("#1976D2")
PRIMARY_DARK = QColor("#0D47A1")
SECONDARY = QColor("#90A4AE")
LIGHT_BLUE = QColor("#E3F2FD")
PAPER = QColor("#FFFFFF")
GRAY = QColor("#ECEFF1")
YELLOW = QColor("#FFC107")
YELLOW_LIGHT = QColor("#FFD95A")

ICON_SIZE = 28


def _pen(color=OUTLINE, width=1.6):
    pen = QPen(color, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _icon(draw_function):
    """
    Create a 32x32 antialiased icon.

    The drawing functions use a 24x24 coordinate system and are
    automatically scaled to the larger icon canvas.
    """

    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    painter.scale(ICON_SIZE / 24.0, ICON_SIZE / 24.0)
    draw_function(painter)

    painter.end()

    return QIcon(pixmap)


def _paper(painter, x=5, y=2, width=12, height=19):
    painter.setPen(_pen(OUTLINE, 1.5))
    painter.setBrush(QBrush(PAPER))
    painter.drawRoundedRect(
        QRectF(x, y, width, height),
        1.5,
        1.5,
    )


def _down_arrow(painter, x, y1, y2, color=PRIMARY):
    painter.setPen(_pen(color, 2.1))
    painter.drawLine(QPointF(x, y1), QPointF(x, y2))
    painter.drawLine(QPointF(x, y2), QPointF(x - 3, y2 - 3))
    painter.drawLine(QPointF(x, y2), QPointF(x + 3, y2 - 3))


def _up_arrow(painter, x, y1, y2, color=PRIMARY):
    painter.setPen(_pen(color, 2.1))
    painter.drawLine(QPointF(x, y1), QPointF(x, y2))
    painter.drawLine(QPointF(x, y1), QPointF(x - 3, y1 + 3))
    painter.drawLine(QPointF(x, y1), QPointF(x + 3, y1 + 3))


# ----------------------------------------------------------------------
# File icons
# ----------------------------------------------------------------------

def new_icon():
    """File -> New."""

    def draw(p):
        _paper(p)

        # Folded corner
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawPolygon(QPolygonF([
            QPointF(13, 2),
            QPointF(17, 6),
            QPointF(13, 6),
        ]))

        # Plus sign
        p.setPen(_pen(PRIMARY, 2.2))
        p.drawLine(QPointF(12, 10), QPointF(12, 18))
        p.drawLine(QPointF(8, 14), QPointF(16, 14))

    return _icon(draw)


def open_icon():
    """File -> Open."""

    def draw(p):
        p.setPen(_pen(OUTLINE, 1.5))
        p.setBrush(QBrush(YELLOW))
        p.drawPolygon(QPolygonF([
            QPointF(3, 7),
            QPointF(9, 7),
            QPointF(11, 9),
            QPointF(21, 9),
            QPointF(19, 20),
            QPointF(4, 20),
        ]))

        p.setPen(_pen(QColor("#D68B00"), 1))
        p.setBrush(QBrush(YELLOW_LIGHT))
        p.drawPolygon(QPolygonF([
            QPointF(3, 9),
            QPointF(21, 9),
            QPointF(19, 18),
            QPointF(4, 18),
        ]))

    return _icon(draw)


def save_icon():
    """File -> Save."""

    def draw(p):
        # Main disk
        p.setPen(_pen(OUTLINE, 1.4))
        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(4, 3, 16, 16), 2, 2)

        # Top label
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(PAPER))
        p.drawRect(QRectF(7, 4, 9, 5))

        # Bottom label
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(8, 12, 8, 6), 1, 1)

        p.setPen(_pen(PRIMARY_DARK, 1))
        p.drawLine(QPointF(9, 14), QPointF(15, 14))
        p.drawLine(QPointF(9, 16), QPointF(15, 16))

    return _icon(draw)



def recent_files_icon():
    """File -> Recent Files."""

    def draw(p):
        _paper(p, 3, 2, 13, 18)

        p.setPen(_pen(SECONDARY, 1.2))
        p.drawLine(QPointF(6, 7), QPointF(13, 7))
        p.drawLine(QPointF(6, 10), QPointF(13, 10))
        p.drawLine(QPointF(6, 13), QPointF(13, 13))

        # Clock
        p.setPen(_pen(PRIMARY, 1.8))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawEllipse(QRectF(12, 12, 9, 9))

        p.drawLine(QPointF(16.5, 14.5), QPointF(16.5, 16.5))
        p.drawLine(QPointF(16.5, 16.5), QPointF(18.3, 17.5))

    return _icon(draw)


def export_icon():
    """File -> Export."""

    def draw(p):
        _paper(p, 4, 2, 14, 18)

        p.setPen(_pen(SECONDARY, 1.1))
        p.drawLine(QPointF(7, 7), QPointF(15, 7))
        p.drawLine(QPointF(7, 10), QPointF(15, 10))

        # Export arrow
        p.setPen(_pen(PRIMARY, 2.1))
        p.drawLine(QPointF(12, 13), QPointF(12, 21))
        p.drawLine(QPointF(12, 21), QPointF(9, 18))
        p.drawLine(QPointF(12, 21), QPointF(15, 18))

    return _icon(draw)


# ----------------------------------------------------------------------
# Layer-order icons
# ----------------------------------------------------------------------

def send_to_back_icon():
    """Objects -> Send To Back."""

    def draw(p):
        # Three layers: top and middle are gray, bottom is primary
        p.setPen(_pen(OUTLINE, 1.3))
        p.setBrush(QBrush(GRAY))
        p.drawRoundedRect(QRectF(3, 3, 11, 3), 1, 1)
        p.drawRoundedRect(QRectF(3, 9, 11, 3), 1, 1)

        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(3, 15, 13, 3), 1, 1)

        # Long arrow pointing to the absolute bottom
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(20, 3), QPointF(20, 17))
        p.drawLine(QPointF(20, 17), QPointF(18, 15))
        p.drawLine(QPointF(20, 17), QPointF(22, 15))

    return _icon(draw)


def bring_to_front_icon():
    """Objects -> Bring To Front."""

    def draw(p):
        # Three layers: top is primary, middle and bottom are gray
        p.setPen(_pen(OUTLINE, 1.3))
        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(3, 3, 13, 3), 1, 1)

        p.setBrush(QBrush(GRAY))
        p.drawRoundedRect(QRectF(3, 9, 11, 3), 1, 1)
        p.drawRoundedRect(QRectF(3, 15, 11, 3), 1, 1)

        # Long arrow pointing to the absolute top
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(20, 17), QPointF(20, 3))
        p.drawLine(QPointF(20, 3), QPointF(18, 5))
        p.drawLine(QPointF(20, 3), QPointF(22, 5))

    return _icon(draw)


def send_backwards_icon():
    """Objects -> Send Backwards."""

    def draw(p):
        # Three layers: top is gray, middle is primary, bottom is gray
        p.setPen(_pen(OUTLINE, 1.3))
        p.setBrush(QBrush(GRAY))
        p.drawRoundedRect(QRectF(3, 3, 11, 3), 1, 1)
        p.drawRoundedRect(QRectF(3, 15, 11, 3), 1, 1)

        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(3, 9, 13, 3), 1, 1)

        # Short arrow pointing down one level (to the bottom gray layer)
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(20, 3), QPointF(20, 13))
        p.drawLine(QPointF(20, 13), QPointF(18, 11))
        p.drawLine(QPointF(20, 13), QPointF(22, 11))

    return _icon(draw)


def bring_forwards_icon():
    """Objects -> Bring Forwards."""

    def draw(p):
        # Three layers: top is gray, middle is primary, bottom is gray
        p.setPen(_pen(OUTLINE, 1.3))
        p.setBrush(QBrush(GRAY))
        p.drawRoundedRect(QRectF(3, 3, 11, 3), 1, 1)
        p.drawRoundedRect(QRectF(3, 15, 11, 3), 1, 1)

        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(3, 9, 13, 3), 1, 1)

        # Short arrow pointing up one level (to the top gray layer)
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(20, 18), QPointF(20, 8))
        p.drawLine(QPointF(20, 8), QPointF(18, 10))
        p.drawLine(QPointF(20, 8), QPointF(22, 10))

    return _icon(draw)


def move_forward_backward_icon():
    """Objects -> Move forwards or backwards."""

    def draw(p):
        # Three layers: top is gray, middle is primary, bottom is gray
        p.setPen(_pen(OUTLINE, 1.3))
        p.setBrush(QBrush(GRAY))
        p.drawRoundedRect(QRectF(10, 3, 11, 3), 1, 1)
        p.drawRoundedRect(QRectF(10, 15, 11, 3), 1, 1)

        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(8, 9, 13, 3), 1, 1)

        # Two arrows from the center: one up and one down
        p.setPen(_pen(PRIMARY_DARK, 1.8))

        # Up arrow
        p.drawLine(QPointF(4, 9), QPointF(4, 2))
        p.drawLine(QPointF(4, 2), QPointF(2, 4))
        p.drawLine(QPointF(4, 2), QPointF(6, 4))

        # Down arrow
        p.drawLine(QPointF(4, 13), QPointF(4, 20))
        p.drawLine(QPointF(4, 20), QPointF(2, 18))
        p.drawLine(QPointF(4, 20), QPointF(6, 18))

    return _icon(draw)


# ----------------------------------------------------------------------
# Object manipulation icons
# ----------------------------------------------------------------------

def group_icon():
    """Objects -> Group."""

    def draw(p):
        # Selection frame
        p.setPen(QPen(PRIMARY, 1.2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(2, 2, 20, 20), 2, 2)

        # Three objects
        p.setPen(_pen(OUTLINE, 1.2))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(4, 5, 7, 7), 1, 1)
        p.drawRoundedRect(QRectF(13, 5, 7, 7), 1, 1)
        p.drawRoundedRect(QRectF(8.5, 13, 7, 7), 1, 1)

    return _icon(draw)


def ungroup_icon():
    """Objects -> Ungroup."""

    def draw(p):
        p.setPen(_pen(OUTLINE, 1.2))
        p.setBrush(QBrush(LIGHT_BLUE))

        p.drawRoundedRect(QRectF(2, 4, 7, 7), 1, 1)
        p.drawRoundedRect(QRectF(15, 4, 7, 7), 1, 1)
        p.drawRoundedRect(QRectF(8.5, 15, 7, 7), 1, 1)

        # Separation marks
        p.setPen(QPen(PRIMARY, 1.2, Qt.DashLine))
        p.drawLine(QPointF(1, 13), QPointF(23, 13))
        #p.drawLine(QPointF(17, 14), QPointF(19, 14))
        p.drawLine(QPointF(12, 2), QPointF(12, 13))

    return _icon(draw)


def align_icon():
    """Objects -> Align."""

    def draw(p):
        # Alignment guide
        p.setPen(_pen(PRIMARY_DARK, 2))
        p.drawLine(QPointF(5, 3), QPointF(5, 21))

        # Objects aligned to the left edge
        p.setPen(_pen(PRIMARY, 2.2))
        p.drawLine(QPointF(5, 6), QPointF(18, 6))
        p.drawLine(QPointF(5, 11), QPointF(14, 11))
        p.drawLine(QPointF(5, 16), QPointF(19, 16))

    return _icon(draw)


def properties_icon():
    """Objects -> Properties."""

    def draw(p):
        # Window
        p.setPen(_pen(OUTLINE, 1.4))
        p.setBrush(QBrush(PAPER))
        p.drawRoundedRect(QRectF(3, 3, 18, 18), 2, 2)

        # Title bar
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(PRIMARY))
        p.drawRoundedRect(QRectF(4, 4, 16, 4), 1, 1)

        # Sliders
        p.setPen(_pen(SECONDARY, 1.5))
        p.drawLine(QPointF(7, 11), QPointF(17, 11))
        p.drawLine(QPointF(7, 15), QPointF(17, 15))
        p.drawLine(QPointF(7, 18), QPointF(17, 18))

        p.setPen(_pen(PRIMARY_DARK, 2))
        p.drawLine(QPointF(11, 9), QPointF(11, 13))
        p.drawLine(QPointF(14, 13), QPointF(14, 17))
        p.drawLine(QPointF(9, 16), QPointF(9, 20))

    return _icon(draw)


# ----------------------------------------------------------------------
# Optional flip icon from the original example
# ----------------------------------------------------------------------

def flip_icon():
    """Objects -> Flip."""

    def draw(p):
        p.setPen(_pen(OUTLINE, 2))
        p.drawLine(QPointF(12, 2), QPointF(12, 22))

        p.setPen(_pen(OUTLINE, 1))
        p.setBrush(QBrush(QColor("#455A64")))
        p.drawPolygon(QPolygonF([
            QPointF(3, 6),
            QPointF(10, 6),
            QPointF(10, 18),
            QPointF(3, 18),
        ]))

        p.setBrush(QBrush(QColor("#B0BEC5")))
        p.drawPolygon(QPolygonF([
            QPointF(21, 6),
            QPointF(14, 6),
            QPointF(14, 18),
            QPointF(21, 18),
        ]))

    return _icon(draw)


# ----------------------------------------------------------------------
# Position icon
# ----------------------------------------------------------------------

def position_icon():
    """
    Objects -> Position (app addition, not in the manual). Echoes the
    ruler corner (canvas/ruler.py): an L-shaped pair of axes with
    their origin at the top-left, dashed guide lines running from a
    point back to each axis, and the point itself.
    """

    def draw(p):
        p.setPen(_pen(OUTLINE, 1.6))
        p.drawLine(QPointF(3, 3), QPointF(21, 3))
        p.drawLine(QPointF(3, 3), QPointF(3, 21))

        dash_pen = QPen(SECONDARY, 1.2, Qt.DashLine)
        p.setPen(dash_pen)
        p.drawLine(QPointF(15, 3), QPointF(15, 15))
        p.drawLine(QPointF(3, 15), QPointF(15, 15))

        p.setPen(_pen(PRIMARY_DARK, 1))
        p.setBrush(QBrush(PRIMARY))
        p.drawEllipse(QPointF(15, 15), 2.6, 2.6)

    return _icon(draw)

# ----------------------------------------------------------------------
# Clean (Diagram -> Clean Up LaTeX Image Cache...) icon
# ----------------------------------------------------------------------

def save_shape_icon():
    """
    Objects -> Save as New Shape... (app addition) - a small shape
    (rounded square + circle) with a green "+" badge, i.e. "add this
    to the shape library".
    """

    def draw(p):
        # Square.
        p.setPen(_pen(OUTLINE, 1.5))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(3, 8, 10, 10), 1.5, 1.5)

        # Circle, overlapping the square's corner.
        p.setBrush(QBrush(PRIMARY))
        p.drawEllipse(QRectF(9, 12, 10, 10))

        # "+" badge, top right.
        green = QColor("#2E7D32")
        p.setPen(_pen(OUTLINE, 1.2))
        p.setBrush(QBrush(green))
        p.drawEllipse(QRectF(13.5, 1.5, 8, 8))
        p.setPen(_pen(PAPER, 1.6))
        p.drawLine(QPointF(17.5, 3.6), QPointF(17.5, 7.4))
        p.drawLine(QPointF(15.6, 5.5), QPointF(19.4, 5.5))

    return _icon(draw)


def clean_icon():
    """
    Diagram -> Clean Up LaTeX Image Cache... (app addition, not in the
    manual) - a plain trash-can, the universal "empty this out"
    symbol, since what the command actually empties (a cache folder)
    has no shape of its own worth drawing.
    """

    def draw(p):
        p.setPen(_pen(OUTLINE, 1.5))

        # Lid + handle.
        p.drawLine(QPointF(4.5, 6.5), QPointF(19.5, 6.5))
        p.drawLine(QPointF(9.5, 6.5), QPointF(10.3, 4))
        p.drawLine(QPointF(14.5, 6.5), QPointF(13.7, 4))
        p.drawLine(QPointF(10.3, 4), QPointF(13.7, 4))

        # Body - tapered, filled, matches the lid's own outline color.
        body = QPolygonF([
            QPointF(6, 6.5),
            QPointF(18, 6.5),
            QPointF(16.8, 21),
            QPointF(7.2, 21),
        ])
        p.setBrush(QBrush(GRAY))
        p.drawPolygon(body)

        # Ridge lines.
        p.setPen(_pen(SECONDARY, 1.3))
        p.drawLine(QPointF(9.5, 9.5), QPointF(9.7, 18.5))
        p.drawLine(QPointF(12, 9.5), QPointF(12, 18.5))
        p.drawLine(QPointF(14.5, 9.5), QPointF(14.3, 18.5))

    return _icon(draw)



# ----------------------------------------------------------------------
# Rotate icon (32 px rendering of the existing app/icons.py rotate_icon)
# ----------------------------------------------------------------------

def rotate_icon():
    """
    Objects -> Rotate. Vertical axis with an incomplete 
    ellipse and arrow indicating rotation.
    """

    def draw(p):
        # Vertical Axis
        p.setPen(_pen(OUTLINE, 1.8))
        p.drawLine(QPointF(12, 3), QPointF(12, 21))

        # Incomplete Ellipse (representing a 3D rotation path)
        # RectF(x, y, width, height) -> width 14, height 10 to create the perspective ellipse
        p.setPen(_pen(PRIMARY, 1.5))
        p.setBrush(Qt.NoBrush)
        # We draw an arc from 30 to 330 degrees to leave a gap for the arrowhead
        p.drawArc(QRectF(5, 8, 14, 8), 30 * 16, 300 * 16)

        # Arrowhead at the end of the ellipse
        p.setPen(_pen(PRIMARY_DARK, 1.5))
        p.setBrush(QBrush(PRIMARY_DARK))
        p.drawLine(QPointF(14, 13), QPointF(18, 14))
        p.drawLine(QPointF(16, 18), QPointF(18, 14))

    return _icon(draw)


# ----------------------------------------------------------------------
# Scale icon
# ----------------------------------------------------------------------

def _arrow_head(p, tip, direction, size=2.2, color=PRIMARY_DARK):
    length = math.hypot(direction.x(), direction.y())
    if length < 0.001:
        return

    ux = direction.x() / length
    uy = direction.y() / length
    px = -uy
    py = ux

    p.setPen(_pen(color, 1.35))

    # Narrower arrowhead
    spread = 0.42

    left = QPointF(
        tip.x() - ux * size + px * size * spread,
        tip.y() - uy * size + py * size * spread,
    )
    right = QPointF(
        tip.x() - ux * size - px * size * spread,
        tip.y() - uy * size - py * size * spread,
    )

    p.drawLine(tip, left)
    p.drawLine(tip, right)


def _draw_scale(p):
    """Parallelogram with horizontal and diagonal double-headed arrows."""

    p.save()

    # Scaled object
    shape = QPolygonF([
        QPointF(6.0, 19.5),
        QPointF(15.8, 19.5),
        QPointF(19.5, 9.5),
        QPointF(9.7, 9.5),
    ])

    p.setPen(_pen(PRIMARY_DARK, 1.5))
    p.setBrush(QBrush(LIGHT_BLUE))
    p.drawPolygon(shape)

    # Subtle interior edge
    p.setPen(_pen(PRIMARY, 1.0))
    p.drawLine(QPointF(7.3, 18.2), QPointF(15.0, 18.2))
    p.drawLine(QPointF(17.9, 10.8), QPointF(14.8, 18.2))

    # Horizontal dimension arrow.
    # Moved upward, farther from the shape.
    h_start = QPointF(9.5, 5.5)
    h_end = QPointF(20.5, 5.5)

    p.setPen(_pen(PRIMARY_DARK, 1.5))
    p.drawLine(h_start, h_end)
    _arrow_head(p, h_start, h_start - h_end, size=2.2)
    _arrow_head(p, h_end, h_end - h_start, size=2.2)

    # Diagonal dimension arrow.
    # Moved farther left of the shape.
    d_start = QPointF(1.8, 20.5)
    d_end = QPointF(5.3, 10.5)

    p.setPen(_pen(PRIMARY_DARK, 1.5))
    p.drawLine(d_start, d_end)
    _arrow_head(p, d_start, d_start - d_end, size=2.2)
    _arrow_head(p, d_end, d_end - d_start, size=2.2)

    p.restore()


def scale_icon():
    return _icon(_draw_scale)


# ----------------------------------------------------------------------
# Edit / View / panel-visibility toolbar icons
# ----------------------------------------------------------------------
# App addition (not in the manual): icons for the Edit, Duplicate,
# Select, Undo, Redo, Zoom, Best Fit, Rules, Shapes, Layers, Diagram
# Tree, Show Grid, Snap to Grid, Snap to Objects, Show Connections
# and Help toolbar buttons added alongside the original File/Objects
# row (see _create_toolbar()). Kept as their own section, with their
# own NEW_PRIMARY/ACCENT/WARNING/WHITE palette, so nothing above this
# comment changes appearance - reusing the module's own PRIMARY/GRAY
# names here would have silently recolored every icon above once the
# module finished loading (whichever assignment to a shared global
# runs last wins for every closure that reads it).

NEW_PRIMARY = QColor("#1565C0")
ACCENT = QColor("#43A047")
WARNING = QColor("#F57C00")
WHITE = QColor("#FFFFFF")


def _arrow(p, start, end, color=NEW_PRIMARY, width=2.2, head=4):
    """Draw an arrow from start to end. The arrowhead is oriented
    along the actual line direction (works for any angle)."""
    p.setPen(_pen(color, width))
    p.drawLine(start, end)

    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = (dx * dx + dy * dy) ** 0.5
    if length < 0.001:
        return

    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # perpendicular unit vector

    wing = head
    spread = 0.55
    p1 = QPointF(
        end.x() - ux * wing + px * wing * spread,
        end.y() - uy * wing + py * wing * spread,
    )
    p2 = QPointF(
        end.x() - ux * wing - px * wing * spread,
        end.y() - uy * wing - py * wing * spread,
    )
    p.drawLine(end, p1)
    p.drawLine(end, p2)


def _draw_magnet(p, y_offset=-3.0):
    """
    Clean upside-down horseshoe magnet.

    y_offset moves the magnet vertically. Negative values move it upward.
    """
    p.save()
    p.translate(0, y_offset)

    magnet = QPainterPath()
    magnet.moveTo(7.0, 19.0)
    magnet.lineTo(7.0, 12.5)
    magnet.cubicTo(7.0, 9.6, 9.2, 8.0, 12.0, 8.0)
    magnet.cubicTo(14.8, 8.0, 17.0, 9.6, 17.0, 12.5)
    magnet.lineTo(17.0, 19.0)

    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(PRIMARY_DARK, 2.25))
    p.drawPath(magnet)

    # Magnetic tips
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(YELLOW))
    p.drawRoundedRect(QRectF(5.6, 16.5, 2.8, 3.8), 0.8, 0.8)
    p.drawRoundedRect(QRectF(15.6, 16.5, 2.8, 3.8), 0.8, 0.8)

    p.restore()


def edit_icon():
    """Edit (drop-down: Copy / Cut / Paste)."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(5, 4, 12, 16), 1.5, 1.5)

        p.setBrush(QBrush(WHITE))
        p.drawRoundedRect(QRectF(8, 3, 7, 4), 1, 1)

        p.setPen(_pen(PRIMARY_DARK, 1.6))
        p.drawLine(QPointF(8, 10), QPointF(14, 10))
        p.drawLine(QPointF(8, 13), QPointF(14, 13))
        p.drawLine(QPointF(8, 16), QPointF(12, 16))

        _arrow(p, QPointF(15, 18), QPointF(21, 12), WARNING, 2.2, 3)

    return _icon(draw)


def duplicate_icon():
    """Edit -> Duplicate."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(4, 7, 11, 11), 1, 1)
        p.drawRoundedRect(QRectF(9, 4, 11, 11), 1, 1)

        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(12, 10), QPointF(17, 10))
        p.drawLine(QPointF(14.5, 7.5), QPointF(14.5, 12.5))

    return _icon(draw)


def select_icon():
    """Select (drop-down: All / None / Invert / Same Type / Transitive
    / Connected) - a dashed marquee around a triangle and a circle."""

    def draw(p):
        pen = QPen(NEW_PRIMARY, 1.5, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(4, 2, 16, 16))

        # Triangle (top-left)
        p.setPen(_pen(NEW_PRIMARY, 1.5))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawPolygon(QPolygonF([
            QPointF(7, 11),
            QPointF(9.5, 6),
            QPointF(12, 11),
        ]))

        # Circle (bottom-right)
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawEllipse(QRectF(12.5, 11.5, 5.5, 5.5))

    return _icon(draw)

def undo_icon():
    """Edit -> Undo."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2.5))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(5, 6, 14, 12), 0 * 16, 180 * 16)
        p.drawLine(QPointF(5, 12), QPointF(3, 8))
        p.drawLine(QPointF(5, 12), QPointF(9, 10))

    return _icon(draw)


def redo_icon():
    """Edit -> Redo."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2.5))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(5, 6, 14, 12), 180 * 16, -180 * 16)
        p.drawLine(QPointF(19, 12), QPointF(14, 9))
        p.drawLine(QPointF(19, 12), QPointF(20, 7))

    return _icon(draw)


def zoom_icon():
    """View -> Zoom (drop-down of presets)."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(4, 2.5, 12, 12))
        p.drawLine(QPointF(14.5, 13.5), QPointF(20.5, 19.5))

        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawLine(QPointF(7, 8.5), QPointF(13, 8.5))
        p.drawLine(QPointF(10, 5.5), QPointF(10, 11.5))

    return _icon(draw)



def best_fit_icon():
    """View -> Best Fit - arrows pointing inward toward the center."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2.2))
        _arrow(p, QPointF(4, 4), QPointF(9, 9))
        _arrow(p, QPointF(20, 4), QPointF(15, 9))
        _arrow(p, QPointF(4, 20), QPointF(9, 15))
        _arrow(p, QPointF(20, 20), QPointF(15, 15))

    return _icon(draw)


def refresh_icon():
    """View -> Refresh - two curved arrows chasing each other in a loop."""

    def draw(p):
        cx, cy, r = 12, 12.3, 7.3

        p.setPen(_pen(NEW_PRIMARY, 2.3))
        p.setBrush(Qt.NoBrush)

        # Two ~145-degree arcs, leaving a gap at each end for an
        # arrowhead - together they read as a circular "loop".
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 25 * 16, 145 * 16)
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 205 * 16, 145 * 16)

        def point_on_circle(deg):
            rad = math.radians(deg)
            return QPointF(cx + r * math.cos(rad), cy - r * math.sin(rad))

        def tangent_dir(deg):
            # Tangent to the circle at `deg`, pointing the same way the
            # arc above was swept (increasing angle = clockwise on
            # screen, since y grows downward).
            rad = math.radians(deg)
            return QPointF(math.sin(rad), math.cos(rad))

        _arrow_head(p, point_on_circle(25), tangent_dir(25), size=4.5, color=NEW_PRIMARY)
        _arrow_head(p, point_on_circle(205), tangent_dir(205), size=4.5, color=NEW_PRIMARY)

    return _icon(draw)


def rules_icon():
    """View -> Show Rulers - an L-shaped ruler with tick marks."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 1.6))
        p.setBrush(QBrush(LIGHT_BLUE))

        p.drawPolygon(QPolygonF([
            QPointF(3, 3),
            QPointF(21, 3),
            QPointF(21, 7),
            QPointF(7, 7),
            QPointF(7, 21),
            QPointF(3, 21),
        ]))

        p.setPen(_pen(PRIMARY_DARK, 1.4))
        for x in (7, 11, 15, 19):
            p.drawLine(QPointF(x, 3), QPointF(x, 5.5))
        for x in (9, 13, 17):
            p.drawLine(QPointF(x, 3), QPointF(x, 4.5))

        for y in (11, 15, 19):
            p.drawLine(QPointF(3, y), QPointF(5.5, y))
        for y in (9, 13, 17):
            p.drawLine(QPointF(3, y), QPointF(4.5, y))

    return _icon(draw)


def shapes_icon():
    """View -> Shapes (panel visibility)."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 1.9))
        p.setBrush(QBrush(LIGHT_BLUE))

        p.drawRect(QRectF(3, 4, 7, 7))
        p.drawEllipse(QRectF(14, 4, 7, 7))
        p.drawPolygon(QPolygonF([
            QPointF(3, 20),
            QPointF(7, 13),
            QPointF(11, 20),
        ]))
        p.drawRoundedRect(QRectF(14, 14, 7, 6), 1, 1)

    return _icon(draw)


def layers_icon():
    """View -> Layers (panel visibility)."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2))
        p.setBrush(QBrush(LIGHT_BLUE))

        p.drawPolygon(QPolygonF([
            QPointF(12, 3),
            QPointF(21, 8),
            QPointF(12, 13),
            QPointF(3, 8),
        ]))

        p.drawPolygon(QPolygonF([
            QPointF(12, 9),
            QPointF(21, 14),
            QPointF(12, 19),
            QPointF(3, 14),
        ]))

    return _icon(draw)


def diagram_tree_icon():
    """View -> Diagram Tree (panel visibility)."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2))
        p.setBrush(QBrush(LIGHT_BLUE))

        p.drawRoundedRect(QRectF(9, 3, 6, 5), 1, 1)
        p.drawRoundedRect(QRectF(3, 16, 6, 5), 1, 1)
        p.drawRoundedRect(QRectF(15, 16, 6, 5), 1, 1)

        p.drawLine(QPointF(12, 8), QPointF(12, 12))
        p.drawLine(QPointF(6, 12), QPointF(18, 12))
        p.drawLine(QPointF(6, 12), QPointF(6, 16))
        p.drawLine(QPointF(18, 12), QPointF(18, 16))

    return _icon(draw)


def show_grid_icon():
    """View -> Show Grid."""

    def draw(p):
        p.save()

        # Grid background
        p.setPen(_pen(PRIMARY, 1.35))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 1.2, 1.2)

        # Grid lines
        p.setPen(_pen(PRIMARY, 1.15))

        for x in (9.3, 14.7):
            p.drawLine(QPointF(x, 4.5), QPointF(x, 19.5))

        for y in (9.3, 14.7):
            p.drawLine(QPointF(4.5, y), QPointF(19.5, y))

        # Outer frame drawn last for a crisp silhouette
        p.setBrush(Qt.NoBrush)
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 1.2, 1.2)

        p.restore()

    return _icon(draw)
        

def snap_to_grid_icon():
    """View -> Snap To Grid."""

    def draw(p):
        p.save()

        # Move the magnet upward
        _draw_magnet(p, y_offset=-3.0)

        # Grid beneath the magnet
        p.setPen(_pen(PRIMARY, 1.25))

        for x in (7.0, 12.0, 17.0):
            p.drawLine(QPointF(x, 17.5), QPointF(x, 21.5))

        for y in (17.5, 19.5, 21.5):
            p.drawLine(QPointF(5.0, y), QPointF(19.0, y))

        p.setPen(_pen(PRIMARY_DARK, 1.5))
        p.drawLine(QPointF(5, 22), QPointF(19, 22))

        p.restore()

    return _icon(draw)


def snap_to_objects_icon():
    """View -> Snap To Objects."""

    def draw(p):
        p.save()

        # Move the magnet upward
        _draw_magnet(p, y_offset=-3.0)

        # Connection guides
        p.setPen(_pen(PRIMARY, 1.35))
        p.drawLine(QPointF(8.8, 20.5), QPointF(4.5, 22.0))
        p.drawLine(QPointF(15.2, 20.5), QPointF(19.5, 22.0))

        # Guide endpoints
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(PRIMARY))
        p.drawEllipse(QPointF(4.2, 21.7), 1.05, 1.05)
        p.drawEllipse(QPointF(19.8, 21.7), 1.05, 1.05)

        # Object node
        p.setPen(_pen(PRIMARY_DARK, 1.8))
        p.setBrush(QBrush(PAPER))
        p.drawEllipse(QPointF(12, 19.2), 3.4, 3.4)

        # Node center
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(PRIMARY))
        p.drawEllipse(QPointF(12, 19.2), 1.35, 1.35)

        p.restore()

    return _icon(draw)



def show_connections_icon():
    """View -> Show Connection Points - square with corner markers."""

    def draw(p):
        p.setRenderHint(p.Antialiasing, True)

        # Center square
        square = QRectF(6, 6, 12, 12)

        p.setPen(_pen(NEW_PRIMARY, 1.8))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawRect(square)

        # Black × markers at the four corners
        p.setPen(_pen(QColor("#202020"), 1.3))
        p.setBrush(Qt.NoBrush)

        corners = [
            QPointF(6, 6),    # top-left
            QPointF(18, 6),   # top-right
            QPointF(6, 18),   # bottom-left
            QPointF(18, 18),  # bottom-right
        ]

        size = 1.8

        for corner in corners:
            x = corner.x()
            y = corner.y()

            p.drawLine(
                QPointF(x - size, y - size),
                QPointF(x + size, y + size)
            )
            p.drawLine(
                QPointF(x - size, y + size),
                QPointF(x + size, y - size)
            )

    return _icon(draw)



def help_icon():
    """Help -> Help."""

    def draw(p):
        p.setPen(_pen(NEW_PRIMARY, 2.2))
        p.setBrush(QBrush(LIGHT_BLUE))
        p.drawEllipse(QRectF(3, 3, 18, 18))

        p.setPen(_pen(PRIMARY_DARK, 2.2))
        p.setBrush(Qt.NoBrush)

        # "?" head
        p.drawArc(QRectF(8.5, 6.5, 7, 7), 200 * 16, -180 * 16)
        p.drawLine(QPointF(15.3, 8.8), QPointF(12, 12.5))
        p.drawLine(QPointF(12, 12.5), QPointF(12, 15))

        # Dot
        p.setBrush(QBrush(PRIMARY_DARK))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(12, 18), 1.2, 1.2)

    return _icon(draw)
    


def language_icon():
    """Icon for switching the application language."""

    def draw(p):
        p.setRenderHint(p.Antialiasing, True)

        dark = QColor("#202020")
        blue = QColor("#1976D2")

        # Globe
        globe = QRectF(3, 3, 15, 15)

        p.setPen(QPen(blue, 1.5))
        p.setBrush(QBrush(QColor("#E3F2FD")))
        p.drawEllipse(globe)

        # Longitude
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(7, 3, 7, 15))

        # Latitude
        p.drawArc(globe, 0, 180 * 16)
        p.drawArc(globe, 180 * 16, 180 * 16)

        # Horizontal middle arc
        middle_latitude = QRectF(3, 6, 15, 7)
        #p.drawArc(middle_latitude, 0, 180 * 16)
        p.drawArc(middle_latitude, 180 * 16, 180 * 16)

    return _icon(draw)
    
