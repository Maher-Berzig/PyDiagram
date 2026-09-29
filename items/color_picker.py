# color_picker.py
"""
App addition (not in the manual): "color, gradient, or pattern"
picking and rendering, shared by every fill/border color button in
the app - property_dialog.py's per-shape _color_button, and
main_window.py's default-fill/default-border swatches.

A color value in this app is now a plain QColor (as it always was),
a QLinearGradient between two colors at a chosen direction, or a
PatternFill - a repeating hatch/dot/image tile (see pattern_fill.py)
- both new. Anywhere a QColor used to be assumed outright
(QColor(value), value.name(), value.alphaF(), QBrush(value)) needs to
go through the helpers here instead, since those raise on a QGradient
or a PatternFill.
"""

import math

from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QGradient,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .pattern_fill import PatternFill, PATTERNS, PATTERN_LABELS


def is_gradient(value):
    return isinstance(value, QGradient)


def is_radial_gradient(value):
    return isinstance(value, QRadialGradient)


def is_pattern(value):
    return isinstance(value, PatternFill)


def copy_color_value(value):
    """An independent copy of `value` - a QColor, a QGradient, or a
    PatternFill - safe to use in place of a bare QColor(value) call,
    which raises on the other two."""

    if is_radial_gradient(value):
        return QRadialGradient(value)

    if is_gradient(value):
        return QLinearGradient(value)

    if is_pattern(value):
        return value.copy()

    return QColor(value)


def representative_color(value):
    """A single, plain QColor standing in for `value`: itself if it's
    already one, a gradient's first stop's color, or a pattern's
    primary color otherwise - for code that can only ever use one
    flat color (serialization fallback, TikZ export's color registry,
    a QColorDialog's own starting selection)."""

    if is_gradient(value):
        stops = value.stops()
        return QColor(stops[0][1]) if stops else QColor("#000000")

    if is_pattern(value):
        return QColor(value.color_a)

    return QColor(value)


def brush_for(value):
    """The QBrush to actually paint `value` with - a plain QBrush for
    a QColor or QGradient (both are valid QBrush constructor
    arguments), or the tiled/rotated brush a PatternFill resolves
    itself into. Every paint() method should build its fill/border
    brush through this rather than a bare QBrush(self.fill_color),
    which raises on a PatternFill."""

    if is_pattern(value):
        return value.to_brush()

    return QBrush(value)


def gradient_colors(value):
    """(start, end) QColors of a gradient - representative_color()
    plus the last stop. Only meaningful when is_gradient(value)."""

    stops = value.stops()

    if not stops:
        return QColor("#000000"), QColor("#000000")

    return QColor(stops[0][1]), QColor(stops[-1][1])


def gradient_angle(value):
    """The gradient's own direction in degrees (0 = left-to-right, 90
    = top-to-bottom, matching make_gradient's convention below) -
    recovered from its actual start()/finalStop() points, so
    reopening an existing gradient in the editor shows the direction
    it was actually set to rather than resetting to 0. Meaningless
    for a radial gradient (no start()/finalStop() to read)."""

    if not is_gradient(value) or is_radial_gradient(value):
        return 0

    start, end = value.start(), value.finalStop()
    dx, dy = end.x() - start.x(), end.y() - start.y()

    if dx == 0 and dy == 0:
        return 0

    return math.degrees(math.atan2(dy, dx)) % 360


def gradient_center(value):
    """A radial gradient's own control point, as an (x, y) fraction
    of the shape's bounding box (0.5, 0.5 = dead center) - recovered
    from its actual center() so reopening an existing radial gradient
    shows the point where it was actually left, rather than resetting
    to the middle."""

    if not is_radial_gradient(value):
        return 0.5, 0.5

    center = value.center()
    return center.x(), center.y()


def make_gradient(color_a, color_b, angle_deg=0):
    """
    A two-stop QLinearGradient between the two colors, running at
    `angle_deg` (0 = left-to-right, 90 = top-to-bottom, increasing
    clockwise - screen/Qt convention, y grows downward) and sized to
    whatever shape it ends up filling/stroking: ObjectBoundingMode
    maps its points onto that shape's own bounding box, whatever size
    it is, rather than a fixed pixel span.

    The gradient line is sized with the same formula CSS's own
    linear-gradient(angle, ...) uses, so it always runs exactly
    corner-to-corner of the (normalized, 1x1) bounding box regardless
    of angle - not just for the horizontal/vertical cases.
    """

    rad = math.radians(angle_deg)
    half = 0.5 * (abs(math.sin(rad)) + abs(math.cos(rad)))
    dx, dy = math.cos(rad) * half, math.sin(rad) * half

    gradient = QLinearGradient(0.5 - dx, 0.5 - dy, 0.5 + dx, 0.5 + dy)
    gradient.setCoordinateMode(QGradient.ObjectBoundingMode)
    gradient.setColorAt(0.0, QColor(color_a))
    gradient.setColorAt(1.0, QColor(color_b))

    return gradient


def make_radial_gradient(color_a, color_b, center=(0.5, 0.5)):
    """
    A two-stop QRadialGradient between the two colors, centered on
    `center` (an (x, y) fraction of the shape's bounding box - (0.5,
    0.5) is dead center) and sized to whatever shape it ends up
    filling, the same ObjectBoundingMode approach as make_gradient()
    above.

    The radius always reaches the box's farthest corner from the
    control point, so the gradient covers the whole shape rather than
    fading to the end color partway across it - wherever the point
    is dragged to.
    """

    cx = min(max(center[0], 0.0), 1.0)
    cy = min(max(center[1], 0.0), 1.0)

    radius = max(
        math.hypot(cx - corner_x, cy - corner_y)
        for corner_x, corner_y in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0))
    ) or 0.0001

    gradient = QRadialGradient(cx, cy, radius, cx, cy)
    gradient.setCoordinateMode(QGradient.ObjectBoundingMode)
    gradient.setColorAt(0.0, QColor(color_a))
    gradient.setColorAt(1.0, QColor(color_b))

    return gradient


def paint_swatch(color, width=48, height=18):
    """A small QIcon preview of `color` - a flat fill for a QColor,
    or the actual gradient/pattern otherwise, via brush_for()."""

    pixmap = QPixmap(width, height)

    if is_gradient(color) or is_pattern(color):
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), brush_for(color))
        painter.end()
    else:
        pixmap.fill(color)

    return QIcon(pixmap)


_DIRECTION_PRESETS = (
    ("\u2192", 0), ("\u2198", 45), ("\u2193", 90), ("\u2199", 135),
    ("\u2190", 180), ("\u2196", 225), ("\u2191", 270), ("\u2197", 315),
)


class _GradientPreview(QLabel):
    """The live gradient swatch, doubling as the radial mode's control
    surface: while radial is active, clicking or dragging anywhere on
    it moves the gradient's center point there and redraws it."""

    def __init__(self, dialog):
        super().__init__()
        self._dialog = dialog

    def mousePressEvent(self, event):
        self._dialog._move_center_to(event.pos())

    def mouseMoveEvent(self, event):
        self._dialog._move_center_to(event.pos())


class _GradientDialog(QDialog):
    """
    One dialog for the whole gradient: start color, end color, and
    either a direction (any angle, including diagonal - not just
    horizontal) for a linear gradient, or a draggable center point for
    a radial one - with a live preview, rather than the previous
    "pick a start color, then separately pick an end color" pair of
    plain QColorDialogs and no way to set direction at all.
    """

    def __init__(self, parent, title, start_color, end_color, angle_deg,
                 is_radial=False, center=(0.5, 0.5)):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.start_color = QColor(start_color)
        self.end_color = QColor(end_color)
        self._center = (center[0], center[1])

        layout = QVBoxLayout(self)

        self._preview = _GradientPreview(self)
        self._preview.setFixedHeight(60)
        self._preview.setMinimumWidth(260)
        layout.addWidget(self._preview)

        form = QFormLayout()

        self._start_btn = QPushButton()
        self._start_btn.setIconSize(QSize(48, 18))
        self._start_btn.clicked.connect(self._pick_start)
        form.addRow("Start Color:", self._start_btn)

        self._end_btn = QPushButton()
        self._end_btn.setIconSize(QSize(48, 18))
        self._end_btn.clicked.connect(self._pick_end)
        form.addRow("End Color:", self._end_btn)

        type_row = QHBoxLayout()
        self._linear_btn = QPushButton("Linear")
        self._linear_btn.setCheckable(True)
        self._radial_btn = QPushButton("Radial")
        self._radial_btn.setCheckable(True)
        self._type_group = QButtonGroup(self)
        self._type_group.setExclusive(True)
        self._type_group.addButton(self._linear_btn)
        self._type_group.addButton(self._radial_btn)
        self._linear_btn.setChecked(not is_radial)
        self._radial_btn.setChecked(is_radial)
        self._radial_btn.toggled.connect(self._on_mode_changed)
        type_row.addWidget(self._linear_btn)
        type_row.addWidget(self._radial_btn)
        form.addRow("Type:", type_row)

        self._angle_spin = QSpinBox()
        self._angle_spin.setRange(0, 359)
        self._angle_spin.setSuffix("\u00b0")
        self._angle_spin.setValue(int(round(angle_deg)) % 360)
        self._angle_spin.valueChanged.connect(self._update_preview)
        form.addRow("Direction:", self._angle_spin)

        layout.addLayout(form)

        self._presets_widget = QWidget()
        presets = QHBoxLayout(self._presets_widget)
        presets.setContentsMargins(0, 0, 0, 0)

        for label, deg in _DIRECTION_PRESETS:
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(f"{deg}\u00b0")
            btn.clicked.connect(lambda _checked, d=deg: self._angle_spin.setValue(d))
            presets.addWidget(btn)

        layout.addWidget(self._presets_widget)

        hint = QLabel("Drag the point on the preview to move the gradient's center.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._radial_hint = hint

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_swatches()
        self._on_mode_changed()

    def _move_center_to(self, pos):
        if not self._radial_btn.isChecked():
            return

        width = max(self._preview.width(), 1)
        height = max(self._preview.height(), 1)

        self._center = (
            min(max(pos.x() / width, 0.0), 1.0),
            min(max(pos.y() / height, 0.0), 1.0),
        )
        self._update_preview()

    def _on_mode_changed(self):
        is_radial = self._radial_btn.isChecked()
        self._angle_spin.setEnabled(not is_radial)
        self._presets_widget.setEnabled(not is_radial)
        self._radial_hint.setVisible(is_radial)
        self._update_preview()

    def _pick_start(self):
        chosen = QColorDialog.getColor(
            self.start_color, self, "Choose Start Color",
            QColorDialog.ShowAlphaChannel
        )

        if chosen.isValid():
            self.start_color = chosen
            self._update_swatches()
            self._update_preview()

    def _pick_end(self):
        chosen = QColorDialog.getColor(
            self.end_color, self, "Choose End Color",
            QColorDialog.ShowAlphaChannel
        )

        if chosen.isValid():
            self.end_color = chosen
            self._update_swatches()
            self._update_preview()

    def _update_swatches(self):
        self._start_btn.setIcon(paint_swatch(self.start_color))
        self._end_btn.setIcon(paint_swatch(self.end_color))

    def _update_preview(self):
        gradient = self.result_gradient()

        width = max(self._preview.width(), 260)
        height = self._preview.height()

        pixmap = QPixmap(width, height)
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), QBrush(gradient))

        if self._radial_btn.isChecked():
            point = QPointF(self._center[0] * width, self._center[1] * height)
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.white)
            painter.drawEllipse(point, 5, 5)

        painter.end()

        self._preview.setPixmap(pixmap)

    def result_gradient(self):
        if self._radial_btn.isChecked():
            return make_radial_gradient(self.start_color, self.end_color, self._center)

        return make_gradient(self.start_color, self.end_color, self._angle_spin.value())


class _PatternDialog(QDialog):
    """
    One dialog for the whole pattern fill: which built-in hatch/dot
    pattern (or an image file used as a repeating tile instead), its
    two colors, tile size, line width, and angle - all with a live
    preview.
    """

    def __init__(self, parent, title, initial):
        super().__init__(parent)

        self.setWindowTitle(title)

        self._value = (
            initial.copy() if is_pattern(initial) else PatternFill()
        )

        layout = QVBoxLayout(self)

        self._preview = QLabel()
        self._preview.setFixedHeight(60)
        self._preview.setMinimumWidth(260)
        layout.addWidget(self._preview)

        form = QFormLayout()

        self._type_combo = QComboBox()
        for name in PATTERNS:
            self._type_combo.addItem(PATTERN_LABELS[name], name)
        self._type_combo.addItem("Image...", "image")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Pattern:", self._type_combo)

        # -- built-in pattern controls --
        self._pattern_group = QWidget()
        pattern_form = QFormLayout(self._pattern_group)
        pattern_form.setContentsMargins(0, 0, 0, 0)

        self._color_a_btn = QPushButton()
        self._color_a_btn.setIconSize(QSize(48, 18))
        self._color_a_btn.clicked.connect(self._pick_color_a)
        pattern_form.addRow("Pattern Color:", self._color_a_btn)

        self._color_b_btn = QPushButton()
        self._color_b_btn.setIconSize(QSize(48, 18))
        self._color_b_btn.clicked.connect(self._pick_color_b)
        pattern_form.addRow("Background Color:", self._color_b_btn)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(4, 200)
        self._size_spin.valueChanged.connect(self._update_preview)
        pattern_form.addRow("Pattern Size:", self._size_spin)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 20)
        self._width_spin.valueChanged.connect(self._update_preview)
        pattern_form.addRow("Line Width:", self._width_spin)

        layout.addWidget(self._pattern_group)

        # -- image controls --
        self._image_group = QWidget()
        image_form = QFormLayout(self._image_group)
        image_form.setContentsMargins(0, 0, 0, 0)

        image_row = QHBoxLayout()
        self._image_label = QLabel("(no file selected)")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_image)
        image_row.addWidget(self._image_label, 1)
        image_row.addWidget(browse_btn)
        image_form.addRow("Image File:", image_row)

        self._image_w_spin = QSpinBox()
        self._image_w_spin.setRange(4, 1000)
        self._image_w_spin.valueChanged.connect(self._update_preview)
        image_form.addRow("Tile Width:", self._image_w_spin)

        self._image_h_spin = QSpinBox()
        self._image_h_spin.setRange(4, 1000)
        self._image_h_spin.valueChanged.connect(self._update_preview)
        image_form.addRow("Tile Height:", self._image_h_spin)

        layout.addWidget(self._image_group)

        # -- shared: angle --
        self._angle_spin = QSpinBox()
        self._angle_spin.setRange(0, 359)
        self._angle_spin.setSuffix("\u00b0")
        self._angle_spin.valueChanged.connect(self._update_preview)
        form.addRow("Pattern Angle:", self._angle_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_value(self._value)

    def _load_value(self, value):
        index = self._type_combo.findData(
            "image" if value.image_path else value.pattern
        )
        self._type_combo.setCurrentIndex(max(0, index))

        self._color_a_btn.setIcon(paint_swatch(value.color_a))
        self._color_b_btn.setIcon(paint_swatch(value.color_b))
        self._size_spin.setValue(int(value.size))
        self._width_spin.setValue(int(value.line_width))
        self._angle_spin.setValue(int(value.angle) % 360)

        self._image_label.setText(value.image_path or "(no file selected)")
        self._image_w_spin.setValue(int(value.image_width))
        self._image_h_spin.setValue(int(value.image_height))

        self._on_type_changed()

    def _on_type_changed(self):
        is_image = self._type_combo.currentData() == "image"
        self._pattern_group.setVisible(not is_image)
        self._image_group.setVisible(is_image)
        self._update_preview()

    def _pick_color_a(self):
        chosen = QColorDialog.getColor(
            self._value.color_a, self, "Choose Pattern Color",
            QColorDialog.ShowAlphaChannel
        )

        if chosen.isValid():
            self._value.color_a = chosen
            self._color_a_btn.setIcon(paint_swatch(chosen))
            self._update_preview()

    def _pick_color_b(self):
        chosen = QColorDialog.getColor(
            self._value.color_b, self, "Choose Background Color",
            QColorDialog.ShowAlphaChannel
        )

        if chosen.isValid():
            self._value.color_b = chosen
            self._color_b_btn.setIcon(paint_swatch(chosen))
            self._update_preview()

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Pattern Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )

        if path:
            self._value.image_path = path
            self._image_label.setText(path)
            self._update_preview()

    def _update_preview(self):
        result = self.result_pattern()

        pixmap = QPixmap(max(self._preview.width(), 260), self._preview.height())
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), result.to_brush())
        painter.end()

        self._preview.setPixmap(pixmap)

    def result_pattern(self):
        is_image = self._type_combo.currentData() == "image"

        self._value.pattern = (
            self._value.pattern if is_image else self._type_combo.currentData()
        )
        self._value.image_path = self._value.image_path if is_image else None
        self._value.size = self._size_spin.value()
        self._value.line_width = self._width_spin.value()
        self._value.angle = self._angle_spin.value()
        self._value.image_width = self._image_w_spin.value()
        self._value.image_height = self._image_h_spin.value()

        return self._value.copy()


def pick_color_or_gradient(parent, title, initial):
    """
    Offers a solid color (the same QColorDialog as always, alpha
    channel included), a two-color gradient - linear (start color, end
    color, and direction) or radial (start/end color and a draggable
    center point) - see _GradientDialog, or a repeating pattern fill
    (a built-in hatch/dot tile or an image file - see _PatternDialog).
    Returns a QColor, a QLinearGradient, a QRadialGradient, a
    PatternFill, or None if cancelled at any point.
    """

    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText("Use a solid color, a two-color gradient, or a pattern?")
    solid_btn = box.addButton("Solid Color", QMessageBox.AcceptRole)
    gradient_btn = box.addButton("Gradient...", QMessageBox.AcceptRole)
    pattern_btn = box.addButton("Pattern...", QMessageBox.AcceptRole)
    box.addButton(QMessageBox.Cancel)
    box.exec_()

    clicked = box.clickedButton()

    if clicked is solid_btn:
        chosen = QColorDialog.getColor(
            representative_color(initial), parent, title,
            QColorDialog.ShowAlphaChannel
        )

        return chosen if chosen.isValid() else None

    if clicked is gradient_btn:
        if is_gradient(initial):
            start_default, end_default = gradient_colors(initial)
            angle_default = gradient_angle(initial)
            radial_default = is_radial_gradient(initial)
            center_default = gradient_center(initial)
        else:
            start_default = end_default = representative_color(initial)
            angle_default = 0
            radial_default = False
            center_default = (0.5, 0.5)

        dialog = _GradientDialog(
            parent, title, start_default, end_default, angle_default,
            radial_default, center_default
        )

        if dialog.exec_() == QDialog.Accepted:
            return dialog.result_gradient()

        return None

    if clicked is pattern_btn:
        dialog = _PatternDialog(parent, title, initial)

        if dialog.exec_() == QDialog.Accepted:
            return dialog.result_pattern()

        return None

    return None


