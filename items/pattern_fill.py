# pattern_fill.py
"""
App addition (not in the manual): "Pattern" fills/borders - a
repeating hatch/dot tile in two colors, or a repeating image tile -
as a third option alongside a solid color or a two-color gradient
(see color_picker.py). The tile-drawing code itself is adapted from a
reference create_pattern_brush()/create_image_brush() pair; folded
into one PatternFill value type here so a shape's fill_color/
border_color can hold "pattern" the same way it already holds
"gradient" - a small, re-editable Python object rather than a bare
Qt brush, so reopening the Properties dialog can show its actual
settings (pattern type, colors, size, line width, angle, or the
image file) back, the same way a QGradient's own stops can.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap, QTransform


PATTERNS = [
    "horizontal", "vertical", "cross",
    "backward_diagonal", "forward_diagonal", "diagonal_cross",
    "dense1", "dense2", "dense3", "dense4", "dense5", "dense6", "dense7",
]

PATTERN_LABELS = {
    "horizontal": "Horizontal Lines",
    "vertical": "Vertical Lines",
    "cross": "Cross",
    "backward_diagonal": "Backward Diagonal",
    "forward_diagonal": "Forward Diagonal",
    "diagonal_cross": "Diagonal Cross",
    "dense1": "Dense 1 (sparsest)",
    "dense2": "Dense 2",
    "dense3": "Dense 3",
    "dense4": "Dense 4",
    "dense5": "Dense 5",
    "dense6": "Dense 6",
    "dense7": "Dense 7 (densest)",
}

_DENSITY = {
    "dense1": 1, "dense2": 2, "dense3": 3, "dense4": 4,
    "dense5": 5, "dense6": 6, "dense7": 7,
}


def _draw_tile(pattern, size, color_a, color_b, line_width):
    size = max(4, int(size))
    line_width = max(1, int(line_width))

    pixmap = QPixmap(size, size)
    pixmap.fill(color_b)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(color_a, line_width))

    if pattern == "horizontal":
        painter.drawLine(0, size // 2, size, size // 2)
    elif pattern == "vertical":
        painter.drawLine(size // 2, 0, size // 2, size)
    elif pattern == "cross":
        painter.drawLine(0, size // 2, size, size // 2)
        painter.drawLine(size // 2, 0, size // 2, size)
    elif pattern == "backward_diagonal":
        painter.drawLine(0, size, size, 0)
        painter.drawLine(-size, size, 0, 0)
        painter.drawLine(size, size, 2 * size, 0)
    elif pattern == "forward_diagonal":
        painter.drawLine(0, 0, size, size)
        painter.drawLine(-size, 0, 0, size)
        painter.drawLine(size, 0, 2 * size, size)
    elif pattern == "diagonal_cross":
        painter.drawLine(0, 0, size, size)
        painter.drawLine(0, size, size, 0)
    elif pattern in _DENSITY:
        density = _DENSITY[pattern]
        step = max(2, size // (density + 2))

        for y in range(step // 2, size, step):
            for x in range(step // 2, size, step):
                painter.drawPoint(x, y)

    painter.end()

    return pixmap


class PatternFill:
    """
    Either a built-in hatch/dot pattern (`pattern` is one of the
    PATTERNS names, tiled in `color_a`-on-`color_b` at `size`/
    `line_width`) or a repeating image tile (`image_path` set instead)
    - `angle` rotates either kind. Resolved into an actual QBrush only
    when actually painted (to_brush()), via color_picker.brush_for().
    """

    def __init__(
        self, pattern="cross", color_a=None, color_b=None,
        size=24, line_width=2, angle=0,
        image_path=None, image_width=70, image_height=70,
    ):
        self.pattern = pattern
        self.color_a = QColor(color_a) if color_a is not None else QColor("#1565C0")
        self.color_b = QColor(color_b) if color_b is not None else QColor("#E3F2FD")
        self.size = size
        self.line_width = line_width
        self.angle = angle % 360
        self.image_path = image_path
        self.image_width = image_width
        self.image_height = image_height

    def copy(self):
        return PatternFill(
            self.pattern, QColor(self.color_a), QColor(self.color_b),
            self.size, self.line_width, self.angle,
            self.image_path, self.image_width, self.image_height,
        )

    def __eq__(self, other):
        if not isinstance(other, PatternFill):
            return False

        return (
            self.pattern == other.pattern
            and self.color_a == other.color_a
            and self.color_b == other.color_b
            and self.size == other.size
            and self.line_width == other.line_width
            and self.angle == other.angle
            and self.image_path == other.image_path
            and self.image_width == other.image_width
            and self.image_height == other.image_height
        )

    def to_pixmap(self):
        if self.image_path:
            pixmap = QPixmap(self.image_path)

            if not pixmap.isNull():
                return pixmap.scaled(
                    max(4, int(self.image_width)), max(4, int(self.image_height)),
                    Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
                )

            # Missing/unreadable file - falls back to a plain hatch
            # rather than an all-black/blank tile, so a shape using it
            # still looks like "a pattern" instead of silently broken.

        return _draw_tile(
            self.pattern, self.size, self.color_a, self.color_b, self.line_width
        )

    def to_brush(self):
        brush = QBrush(self.to_pixmap())

        if self.angle:
            transform = QTransform()
            transform.rotate(self.angle)
            brush.setTransform(transform)

        return brush
