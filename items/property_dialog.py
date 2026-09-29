# property_dialog.py
"""
Manual 4.3 ("Object Properties") and 4.3.2.1: double-clicking a shape
(or right-click -> Properties) opens a dialog to edit its color and
line width. This is deliberately separate from TextItem's own
double-click behavior, which enters in-canvas text editing instead
(manual 4.1.2) - Rectangle/Ellipse/Line don't have that alternate
mode, so their double-click always means "edit properties".
"""

import os

from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QTextEdit,
    QWidget,
)

from app.translations import tr
from canvas.commands import ChangePropertiesCommand
from items.line_item import ARROW_STYLE_LABELS, ARROW_STYLES, LINE_STYLE_LABELS, LINE_STYLES
from items.color_picker import copy_color_value, paint_swatch, pick_color_or_gradient


def _arrow_size_spin(value):
    spin = QDoubleSpinBox()
    spin.setRange(0.2, 20.0)
    spin.setSingleStep(0.5)
    spin.setValue(value)
    return spin


class _PlainValueField:
    """
    App addition (not in the manual): a stand-in for the widgets
    edit_shape_properties() below otherwise expects in `fields` - used
    for ImageItem.latex_recipe (see the ImageItem branch further down),
    a plain dict that has no natural widget of its own to live in the
    way file_path already has path_edit. `.value` is read directly by
    a dedicated branch in edit_shape_properties()'s old/new diff loop,
    the same way that loop reads a QLineEdit's .text() or a QCheckBox's
    .isChecked().
    """

    def __init__(self, value):
        self.value = value


def _option_combo(options, labels, current):
    """
    A QComboBox whose visible text is `labels[value]` for each
    `value` in `options`, with the internal value stashed as the
    item's data - so edit_shape_properties can read back
    `widget.currentData()` regardless of what's displayed.
    """

    combo = QComboBox()

    for value in options:
        combo.addItem(labels.get(value, value), value)

    index = combo.findData(current)
    combo.setCurrentIndex(index if index >= 0 else 0)

    return combo


def _packed_row(layout, *pairs):
    """
    Adds one form row containing several (label, widget) pairs side
    by side, rather than the dialog's usual one-control-per-row
    layout - used for the Plot shape's Properties (a function
    alongside its curve color, a fill boundary alongside its own line
    color) so related settings read as pairs on shared lines instead
    of one long vertical list.
    """

    row = QWidget()
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)

    for label_text, widget in pairs:
        row_layout.addWidget(QLabel(label_text))
        row_layout.addWidget(widget)

    row_layout.addStretch(1)
    layout.addRow(row)


def _color_button(initial_color):
    """
    A small color-swatch button with alpha-channel support, and now
    gradient support: clicking it offers a choice between a solid
    color (the same QColorDialog as before) or a two-color gradient
    (see items/color_picker.py). button.color ends up holding
    whichever the user picked - a QColor or a QLinearGradient.
    """
    button = QPushButton()
    button.color = copy_color_value(initial_color)
    button.setIconSize(QSize(48, 18))
    def _update_swatch():
        button.setIcon(paint_swatch(button.color))
    def _pick():
        chosen = pick_color_or_gradient(
            None, tr.get("choose_color", "Choose Color"), button.color
        )
        if chosen is not None:
            button.color = chosen
            _update_swatch()
    button.clicked.connect(_pick)
    _update_swatch()
    return button


def _pdf_link_destination_combo(item):
    """Build the PDF-internal destination selector for an item.

    Destinations are the persistent document IDs of the other currently
    open tabs.  The user sees the normal tab/document name; the stored
    value is the ID, not a PDF page number.
    """
    combo = QComboBox()
    combo.addItem(tr.get("pdf_link_none", "None"), None)

    current_target = getattr(item, "pdf_link_target", None)
    seen_ids = set()
    current_document_id = None

    scene = item.scene()
    if scene is not None:
        current_document_id = getattr(scene, "document_id", None)
        views = scene.views()
        if views:
            window = views[0].window()
            tabs = getattr(window, "tabs", None)
            if tabs is not None:
                for index in range(tabs.count()):
                    container = tabs.widget(index)
                    document_id = getattr(container, "document_id", None)
                    if not document_id or document_id == current_document_id:
                        continue
                    seen_ids.add(document_id)

                    name = (
                        os.path.basename(container.file_path)
                        if getattr(container, "file_path", None)
                        else getattr(container, "default_name", None) or "Untitled"
                    )
                    combo.addItem(name, document_id)

    # Preserve a previously stored link even if its target document has
    # since been closed.  Reopening Properties must not silently erase it.
    if current_target and current_target not in seen_ids:
        combo.addItem(
            tr.get("pdf_link_unavailable", "Unavailable destination (document is closed)"),
            current_target,
        )

    index = combo.findData(current_target)
    combo.setCurrentIndex(index if index >= 0 else 0)
    return combo


def _build_dialog(item, parent=None):
    """
    Returns (dialog, fields) where fields maps the item's attribute
    name to the widget editing it, or (None, {}) if this item type
    has no editable properties.
    """

    from items.rectangle_item import RectangleItem
    from items.ellipse_item import EllipseItem
    from items.diamond_item import DiamondItem
    from items.cylinder_item import CylinderItem
    from items.actor_item import ActorItem
    from items.interface_item import InterfaceItem
    from items.class_item import ClassItem
    from items.line_item import LineItem
    from items.polygon_item import PolygonItem
    from items.polyline_item import PolylineItem
    from items.zigzagline_item import ZigzaglineItem
    from items.image_item import ImageItem, IMAGE_FILE_FILTER
    from items.bezierline_item import BezierlineItem
    from items.beziergon_item import BeziergonItem
    from items.text_item import (
        TextItem, FONT_WEIGHTS, FONT_WEIGHT_LABELS,
        TEXT_ALIGNMENTS, TEXT_ALIGNMENT_LABELS,
    )
    from items.assorted_item import (
        SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
        CrossItem, RegularPolygonItem, StarItem, SpiralItem, CircleSectionItem,
    )
    from items.plot_item import PlotItem, AXIS_TYPES, AXIS_TYPE_LABELS
    from items.stencil_items import StencilItem

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr.get("properties_dialog", "Properties"))
    if isinstance(item, PlotItem):
        dialog.setMinimumWidth(760)
        dialog.setMinimumHeight(430)
    layout = QFormLayout(dialog)

    fields = {}

    if isinstance(item, StencilItem):
        # The Flowchart/UML shapes of items/stencil_items.py: the usual
        # fill/line rows, then one row per size parameter that shape
        # declares in PARAMS (tab height, fold size, ...), so a new
        # parameter needs no change here.
        fields = {}

        if item.HAS_FILL:
            fill_btn = _color_button(item.fill_color)
            layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
            fields["fill_color"] = fill_btn

        border_btn = _color_button(item.border_color)

        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)

        fields.update({
            "border_color": border_btn,
            "border_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
        })

        for param in item.PARAMS:
            spin = QDoubleSpinBox()
            spin.setRange(param.minimum, param.maximum)
            spin.setDecimals(param.decimals)
            spin.setSingleStep(param.step)
            spin.setSuffix(param.unit)
            spin.setValue(getattr(item, param.name))
            layout.addRow(param.label, spin)
            fields[param.name] = spin

        if item.HAS_FILL:
            draw_bg_check = QCheckBox()
            draw_bg_check.setChecked(item.draw_background)
            layout.addRow(
                tr.get("prop_draw_background", "Draw background:"),
                draw_bg_check,
            )
            fields["draw_background"] = draw_bg_check

    elif isinstance(item, (RegularPolygonItem, StarItem)):
        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)

        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )
        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")
        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(style_combo.currentData() != "solid")
        )

        points_spin = QSpinBox()
        points_spin.setRange(item.MIN_POINTS, 100)
        points_spin.setValue(int(item.num_points))

        radius1_spin = QDoubleSpinBox()
        radius1_spin.setRange(0.0, 50.0)
        radius1_spin.setValue(
            float(item.outer_corner_radius if isinstance(item, StarItem) else item.corner_radius)
        )

        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(
            tr.get("prop_num_points", "Number of points:"), points_spin
        )

        fields = {
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "num_points": points_spin,
        }

        if isinstance(item, StarItem):
            inner_ratio_spin = QDoubleSpinBox()
            inner_ratio_spin.setRange(5.0, 95.0)
            inner_ratio_spin.setDecimals(1)
            inner_ratio_spin.setSuffix(" %")
            inner_ratio_spin.setValue(item.inner_radius_ratio * 100.0)

            inner_corner_spin = QDoubleSpinBox()
            inner_corner_spin.setRange(0.0, 50.0)
            inner_corner_spin.setValue(float(item.inner_corner_radius))

            draw_bg_check = QCheckBox()
            draw_bg_check.setChecked(item.draw_background)

            layout.addRow(
                tr.get("prop_outer_corner_radius", "Outer Corner Radius:"),
                radius1_spin,
            )
            layout.addRow(
                tr.get("prop_inner_corner_radius", "Inner Corner Radius:"),
                inner_corner_spin,
            )
            layout.addRow(
                tr.get("prop_inner_radius", "Inner Radius:"),
                inner_ratio_spin,
            )
            layout.addRow(
                tr.get("prop_draw_background", "Draw background:"),
                draw_bg_check,
            )
            fields.update({
                "outer_corner_radius": radius1_spin,
                "inner_corner_radius": inner_corner_spin,
                "inner_radius_ratio": inner_ratio_spin,
                "draw_background": draw_bg_check,
            })
        else:
            draw_bg_check = QCheckBox()
            draw_bg_check.setChecked(item.draw_background)
            layout.addRow(
                tr.get("prop_corner_radius", "Corner Radius:"), radius1_spin
            )
            layout.addRow(
                tr.get("prop_draw_background", "Draw background:"),
                draw_bg_check,
            )
            fields.update({
                "corner_radius": radius1_spin,
                "draw_background": draw_bg_check,
            })

    elif isinstance(item, CircleSectionItem):
        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)
        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))
        style_combo = _option_combo(LINE_STYLES, LINE_STYLE_LABELS, item.line_style)
        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")
        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(style_combo.currentData() != "solid")
        )
        angle_spin = QDoubleSpinBox()
        angle_spin.setRange(item.MIN_MISSING_ANGLE, item.MAX_MISSING_ANGLE)
        angle_spin.setDecimals(1)
        angle_spin.setSuffix(" °")
        angle_spin.setValue(item.missing_angle)
        draw_bg_check = QCheckBox()
        draw_bg_check.setChecked(item.draw_background)

        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(
            tr.get("prop_missing_angle", "Missing angle:"), angle_spin
        )
        layout.addRow(
            tr.get("prop_draw_background", "Draw background:"), draw_bg_check
        )
        fields = {
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "missing_angle": angle_spin,
            "draw_background": draw_bg_check,
        }

    elif isinstance(item, SpiralItem):
        color_btn = _color_button(item.pen_color)
        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(int(item.pen_width))
        style_combo = _option_combo(LINE_STYLES, LINE_STYLE_LABELS, item.line_style)
        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")
        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(style_combo.currentData() != "solid")
        )
        turns_spin = QDoubleSpinBox()
        turns_spin.setRange(0.25, 100.0)
        turns_spin.setDecimals(2)
        turns_spin.setSingleStep(0.25)
        turns_spin.setValue(item.turns)

        layout.addRow(tr.get("prop_line_color", "Line color:"), color_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(tr.get("prop_turns", "Turns:"), turns_spin)
        fields = {
            "pen_color": color_btn,
            "pen_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "turns": turns_spin,
        }

    elif isinstance(item, ClassItem):
        name_edit = QLineEdit(item.class_name)

        attrs_edit = QTextEdit(item.attributes)
        attrs_edit.setFixedHeight(70)

        ops_edit = QTextEdit(item.operations)
        ops_edit.setFixedHeight(70)

        fill_btn = _color_button(item.fill_color)

        layout.addRow(tr.get("prop_class_name", "Class name:"), name_edit)
        layout.addRow(tr.get("prop_attributes", "Attributes:"), attrs_edit)
        layout.addRow(tr.get("prop_operations", "Operations:"), ops_edit)
        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)

        fields = {
            "class_name": name_edit,
            "attributes": attrs_edit,
            "operations": ops_edit,
            "fill_color": fill_btn,
        }

    elif isinstance(item, RectangleItem):
        # Manual 5.1.2, "Box": Corner Rounding and Draw Background are
        # Box-specific, on top of the fill/border/width/style every
        # simple shape shares - so RectangleItem gets its own branch
        # instead of folding into the group below.
        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)

        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        # One radius per corner, clockwise from the top-left.
        radius_spins = []

        corner_tips = [
            ("top-left",     "prop_corner_tip_tl"),
            ("top-right",    "prop_corner_tip_tr"),
            ("bottom-right", "prop_corner_tip_br"),
            ("bottom-left",  "prop_corner_tip_bl"),
        ]

        for n, (tip, tip_key) in enumerate(corner_tips, 1):
            spin = QSpinBox()
            spin.setRange(0, 50)
            spin.setValue(int(getattr(item, f"corner_radius_{n}")))
            spin.setToolTip(
                tr.get("prop_corner_n_tooltip", "Corner {n} ({tip})").format(
                    n=n, tip=tr.get(tip_key, tip)
                )
            )
            radius_spins.append(spin)

        draw_bg_check = QCheckBox()
        draw_bg_check.setChecked(item.draw_background)

        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)

        for n, spin in enumerate(radius_spins, 1):
            layout.addRow(
                tr.get("prop_corner_n_radius", "Corner {n} radius:").format(n=n),
                spin,
            )

        layout.addRow(
            tr.get("prop_draw_background", "Draw background:"), draw_bg_check
        )

        fields = {
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "corner_radius_1": radius_spins[0],
            "corner_radius_2": radius_spins[1],
            "corner_radius_3": radius_spins[2],
            "corner_radius_4": radius_spins[3],
            "draw_background": draw_bg_check,
        }

    elif isinstance(
        item,
        (EllipseItem, PolygonItem, BeziergonItem, CircleItem,
         IsoscelesTriangleItem, RightTriangleItem, CrossItem)
    ):
        # Same fill/border/width every simple shape has, plus the
        # Line/Rectangle-style border-style/dash-length pair.
        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)

        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)

        fields = {
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
        }

    elif isinstance(
        item,
        (DiamondItem, CylinderItem, ActorItem, InterfaceItem, SquareItem)
    ):
        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)

        width_spin = QSpinBox()
        width_spin.setRange(0, 20)
        width_spin.setValue(int(item.border_width))

        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_btn)
        layout.addRow(tr.get("prop_line_color", "Line color:"), border_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)

        fields = {
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": width_spin,
        }

    elif isinstance(item, LineItem):
        color_btn = _color_button(item.pen_color)

        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(int(item.pen_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        start_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.start_arrow
        )
        end_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.end_arrow
        )

        start_size_spin = _arrow_size_spin(item.start_arrow_size)
        end_size_spin = _arrow_size_spin(item.end_arrow_size)

        layout.addRow(tr.get("prop_line_color", "Line color:"), color_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(tr.get("prop_start_arrow", "Start arrow:"), start_combo)
        layout.addRow(
            tr.get("prop_start_arrow_size", "Start arrow size:"),
            start_size_spin,
        )
        layout.addRow(tr.get("prop_end_arrow", "End arrow:"), end_combo)
        layout.addRow(
            tr.get("prop_end_arrow_size", "End arrow size:"), end_size_spin
        )

        fields = {
            "pen_color": color_btn,
            "pen_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "start_arrow": start_combo,
            "start_arrow_size": start_size_spin,
            "end_arrow": end_combo,
            "end_arrow_size": end_size_spin,
        }

    elif isinstance(item, ZigzaglineItem):
        # Checked before the plain PolylineItem branch below, since
        # Zigzagline is a Polyline subclass and would otherwise match
        # there first, losing its Autoroute checkbox.
        color_btn = _color_button(item.pen_color)

        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(int(item.pen_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        start_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.start_arrow
        )
        end_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.end_arrow
        )

        start_size_spin = _arrow_size_spin(item.start_arrow_size)
        end_size_spin = _arrow_size_spin(item.end_arrow_size)

        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.0, 10.0)
        radius_spin.setSingleStep(0.5)
        radius_spin.setValue(item.corner_radius)

        autoroute_check = QCheckBox()
        autoroute_check.setChecked(item.autoroute)

        layout.addRow(tr.get("prop_line_color", "Line color:"), color_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(tr.get("prop_start_arrow", "Start arrow:"), start_combo)
        layout.addRow(
            tr.get("prop_start_arrow_size", "Start arrow size:"),
            start_size_spin,
        )
        layout.addRow(tr.get("prop_end_arrow", "End arrow:"), end_combo)
        layout.addRow(
            tr.get("prop_end_arrow_size", "End arrow size:"), end_size_spin
        )
        layout.addRow(
            tr.get("prop_corner_radius", "Corner Radius:"), radius_spin
        )
        layout.addRow(tr.get("prop_autoroute", "Autoroute:"), autoroute_check)

        fields = {
            "pen_color": color_btn,
            "pen_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "start_arrow": start_combo,
            "start_arrow_size": start_size_spin,
            "end_arrow": end_combo,
            "end_arrow_size": end_size_spin,
            "corner_radius": radius_spin,
            "autoroute": autoroute_check,
        }

    elif isinstance(item, PolylineItem):
        color_btn = _color_button(item.pen_color)

        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(int(item.pen_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        start_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.start_arrow
        )
        end_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.end_arrow
        )

        start_size_spin = _arrow_size_spin(item.start_arrow_size)
        end_size_spin = _arrow_size_spin(item.end_arrow_size)

        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.0, 10.0)
        radius_spin.setSingleStep(0.5)
        radius_spin.setValue(item.corner_radius)

        layout.addRow(tr.get("prop_line_color", "Line color:"), color_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(tr.get("prop_start_arrow", "Start arrow:"), start_combo)
        layout.addRow(
            tr.get("prop_start_arrow_size", "Start arrow size:"),
            start_size_spin,
        )
        layout.addRow(tr.get("prop_end_arrow", "End arrow:"), end_combo)
        layout.addRow(
            tr.get("prop_end_arrow_size", "End arrow size:"), end_size_spin
        )
        layout.addRow(
            tr.get("prop_corner_radius", "Corner Radius:"), radius_spin
        )

        fields = {
            "pen_color": color_btn,
            "pen_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "start_arrow": start_combo,
            "start_arrow_size": start_size_spin,
            "end_arrow": end_combo,
            "end_arrow_size": end_size_spin,
            "corner_radius": radius_spin,
        }

    elif isinstance(item, BezierlineItem):
        # No corner_radius field here - a Bezierline's curvature comes
        # from its control points (dragged directly on the canvas),
        # not a single overall radius the way Polyline/Zigzagline have.
        color_btn = _color_button(item.pen_color)

        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(int(item.pen_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)
        dash_spin.setEnabled(item.line_style != "solid")

        style_combo.currentIndexChanged.connect(
            lambda _i: dash_spin.setEnabled(
                style_combo.currentData() != "solid"
            )
        )

        start_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.start_arrow
        )
        end_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, item.end_arrow
        )

        start_size_spin = _arrow_size_spin(item.start_arrow_size)
        end_size_spin = _arrow_size_spin(item.end_arrow_size)

        layout.addRow(tr.get("prop_line_color", "Line color:"), color_btn)
        layout.addRow(tr.get("prop_line_width", "Line width:"), width_spin)
        layout.addRow(tr.get("prop_line_style", "Line style:"), style_combo)
        layout.addRow(tr.get("prop_dash_length", "Dash length:"), dash_spin)
        layout.addRow(tr.get("prop_start_arrow", "Start arrow:"), start_combo)
        layout.addRow(
            tr.get("prop_start_arrow_size", "Start arrow size:"),
            start_size_spin,
        )
        layout.addRow(tr.get("prop_end_arrow", "End arrow:"), end_combo)
        layout.addRow(
            tr.get("prop_end_arrow_size", "End arrow size:"), end_size_spin
        )

        fields = {
            "pen_color": color_btn,
            "pen_width": width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
            "start_arrow": start_combo,
            "start_arrow_size": start_size_spin,
            "end_arrow": end_combo,
            "end_arrow_size": end_size_spin,
        }

    elif isinstance(item, ImageItem):
        path_edit = QLineEdit(item.file_path)
        path_edit.setReadOnly(True)

        # App addition (not in the manual): carried alongside
        # file_path so a LaTeX-rendered image's recipe (equation,
        # colors, padding, DPI) is saved with the diagram too - see
        # ImageItem.latex_recipe and app/latex_render.py's module
        # docstring for why that matters (Diagram -> Clean Up LaTeX
        # Image Cache...).
        latex_recipe_field = _PlainValueField(item.latex_recipe)

        browse_btn = QPushButton(tr.get("browse", "Browse..."))

        def _browse():
            path, _ = QFileDialog.getOpenFileName(
                None, tr.get("select_image", "Select Image"),
                item.file_path or "", IMAGE_FILE_FILTER
            )

            if path:
                path_edit.setText(path)
                # A manually browsed-to file isn't a LaTeX render (or
                # isn't necessarily still the one latex_recipe would
                # reproduce), so it no longer carries one.
                latex_recipe_field.value = None

        browse_btn.clicked.connect(_browse)

        # App addition (not in the manual): renders a LaTeX equation
        # to a PNG (app/latex_render.py, app/latex_image_dialog.py)
        # and inserts it exactly the way Browse... above does - both
        # just set path_edit's text, so the generic QLineEdit handling
        # already in edit_shape_properties() (below) is what actually
        # applies either one to item.file_path.
        latex_btn = QPushButton(
            tr.get("create_from_latex", "Create from LaTeX...")
        )

        def _create_from_latex():
            from app.latex_image_dialog import prompt_latex_image

            result = prompt_latex_image(
                dialog, path_edit.text(), latex_recipe_field.value
            )

            if result:
                new_path, recipe = result
                path_edit.setText(new_path)
                latex_recipe_field.value = recipe

        latex_btn.clicked.connect(_create_from_latex)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(path_edit)
        row_layout.addWidget(browse_btn)
        row_layout.addWidget(latex_btn)

        layout.addRow(tr.get("prop_image_file", "Image file:"), row)

        # fields["file_path"] points at the QLineEdit itself, not the
        # wrapper row - edit_shape_properties reads it generically via
        # the QLineEdit branch below, same as any other text field.
        fields = {
            "file_path": path_edit,
            "latex_recipe": latex_recipe_field,
        }

    elif isinstance(item, TextItem):
        text_edit = QTextEdit()
        text_edit.setPlainText(item.text_content)
        text_edit.setMaximumHeight(80)

        font_combo = QFontComboBox()
        font_combo.setCurrentFont(QFont(item.font_family))

        weight_combo = _option_combo(
            FONT_WEIGHTS, FONT_WEIGHT_LABELS, item.font_weight
        )

        font_row = QWidget()
        font_row_layout = QHBoxLayout(font_row)
        font_row_layout.setContentsMargins(0, 0, 0, 0)
        font_row_layout.addWidget(font_combo)
        font_row_layout.addWidget(weight_combo)

        align_combo = _option_combo(
            TEXT_ALIGNMENTS, TEXT_ALIGNMENT_LABELS, item.text_align
        )

        size_spin = QSpinBox()
        size_spin.setRange(6, 96)
        size_spin.setValue(item.font_size)

        spacing_spin = QDoubleSpinBox()
        spacing_spin.setRange(-10.0, 50.0)
        spacing_spin.setSingleStep(0.5)
        spacing_spin.setSuffix(" px")
        spacing_spin.setValue(item.letter_spacing)

        text_color_btn = _color_button(item.text_color)
        fill_color_btn = _color_button(item.fill_color)

        draw_bg_check = QCheckBox()
        draw_bg_check.setChecked(item.draw_background)

        outline_check = QCheckBox()
        outline_check.setChecked(item.outline_enabled)

        outline_color_btn = _color_button(item.outline_color)

        outline_width_spin = QDoubleSpinBox()
        outline_width_spin.setRange(0.5, 40.0)
        outline_width_spin.setSingleStep(0.5)
        outline_width_spin.setValue(item.outline_width)

        layout.addRow(tr.get("prop_text", "Text:"), text_edit)
        layout.addRow(tr.get("prop_font", "Font:"), font_row)
        layout.addRow(tr.get("prop_alignment", "Alignment:"), align_combo)
        layout.addRow(tr.get("prop_font_size", "Font size:"), size_spin)
        layout.addRow(
            tr.get("prop_letter_spacing", "Letter spacing:"), spacing_spin
        )
        layout.addRow(tr.get("prop_text_color", "Text color:"), text_color_btn)
        layout.addRow(tr.get("prop_fill_color", "Fill color:"), fill_color_btn)
        layout.addRow(
            tr.get("prop_draw_background", "Draw background:"), draw_bg_check
        )
        layout.addRow(tr.get("prop_outline", "Outline:"), outline_check)
        layout.addRow(
            tr.get("prop_outline_color", "Outline color:"), outline_color_btn
        )
        layout.addRow(
            tr.get("prop_outline_width", "Outline width:"), outline_width_spin
        )

        fields = {
            "text_content": text_edit,
            "font_family": font_combo,
            "font_weight": weight_combo,
            "text_align": align_combo,
            "font_size": size_spin,
            "letter_spacing": spacing_spin,
            "text_color": text_color_btn,
            "fill_color": fill_color_btn,
            "draw_background": draw_bg_check,
            "outline_enabled": outline_check,
            "outline_color": outline_color_btn,
            "outline_width": outline_width_spin,
        }

    elif isinstance(item, PlotItem):
        # Plot properties are deliberately organized into three tabs:
        # Functions & Range, Axes & Ticks, and Lines & Fill.  A Plot has
        # substantially more parameters than ordinary shapes, so putting
        # everything into one long form makes related options hard to find.
        tabs = QTabWidget()
        layout.addRow(tabs)

        # ---- Functions & range --------------------------------------
        functions_page = QWidget()
        functions_form = QFormLayout(functions_page)

        f1_edit = QLineEdit(item.f1_expr)
        f2_edit = QLineEdit(item.f2_expr)

        def _range_spin(value):
            spin = QDoubleSpinBox()
            spin.setRange(-1e6, 1e6)
            spin.setDecimals(3)
            spin.setValue(value)
            return spin

        x_min_spin = _range_spin(item.x_min)
        x_max_spin = _range_spin(item.x_max)
        x1_spin = _range_spin(item.x1)
        x2_spin = _range_spin(item.x2)
        y_min_spin = _range_spin(item.y_min)
        y_max_spin = _range_spin(item.y_max)

        f1_color_btn = _color_button(item.f1_color)
        f2_color_btn = _color_button(item.f2_color)

        num_points_spin = QSpinBox()
        num_points_spin.setRange(10, 5000)
        num_points_spin.setValue(item.num_points)

        _packed_row(
            functions_form,
            (tr.get("prop_f1", "f1(x):"), f1_edit),
            (tr.get("prop_color", "Color:"), f1_color_btn),
        )
        _packed_row(
            functions_form,
            (tr.get("prop_f2", "f2(x):"), f2_edit),
            (tr.get("prop_color", "Color:"), f2_color_btn),
        )
        _packed_row(
            functions_form,
            (tr.get("prop_x_minimum", "X minimum:"), x_min_spin),
            (tr.get("prop_x_maximum", "X maximum:"), x_max_spin),
        )
        _packed_row(
            functions_form,
            (tr.get("prop_fill_x1", "Fill x1:"), x1_spin),
            (tr.get("prop_fill_x2", "Fill x2:"), x2_spin),
        )
        _packed_row(
            functions_form,
            (tr.get("prop_y_minimum", "Y minimum:"), y_min_spin),
            (tr.get("prop_y_maximum", "Y maximum:"), y_max_spin),
        )
        functions_form.addRow(
            tr.get("prop_sample_points", "Sample points:"), num_points_spin
        )

        tabs.addTab(
            functions_page, tr.get("functions_range", "Functions & Range")
        )

        # ---- Axes & ticks -------------------------------------------
        axes_page = QWidget()
        axes_form = QFormLayout(axes_page)

        axis_combo = _option_combo(AXIS_TYPES, AXIS_TYPE_LABELS, item.axis_type)

        show_grid_check = QCheckBox()
        show_grid_check.setChecked(item.show_grid)

        show_xtick_check = QCheckBox()
        show_xtick_check.setChecked(item.show_xtick_labels)

        show_ytick_check = QCheckBox()
        show_ytick_check.setChecked(item.show_ytick_labels)

        xtick_interval_spin = QDoubleSpinBox()
        xtick_interval_spin.setRange(0, 1e6)
        xtick_interval_spin.setDecimals(3)
        xtick_interval_spin.setSpecialValueText(
            tr.get("prop_axis_type", "Auto") if False else "Auto"
        )
        xtick_interval_spin.setValue(item.xtick_interval)

        ytick_interval_spin = QDoubleSpinBox()
        ytick_interval_spin.setRange(0, 1e6)
        ytick_interval_spin.setDecimals(3)
        ytick_interval_spin.setSpecialValueText("Auto")
        ytick_interval_spin.setValue(item.ytick_interval)

        x_tick_format_edit = QLineEdit(item.x_tick_label_format)
        x_tick_format_edit.setPlaceholderText(
            tr.get("prop_x_tick_placeholder", "e.g. x={value}")
        )
        x_tick_format_edit.setToolTip(
            tr.get(
                "prop_tick_tooltip",
                "Use {value} for the numeric tick value; surrounding text is preserved.",
            )
        )

        y_tick_format_edit = QLineEdit(item.y_tick_label_format)
        y_tick_format_edit.setPlaceholderText(
            tr.get("prop_y_tick_placeholder", "e.g. y={value}")
        )
        y_tick_format_edit.setToolTip(
            tr.get(
                "prop_tick_tooltip",
                "Use {value} for the numeric tick value; surrounding text is preserved.",
            )
        )

        axes_form.addRow(tr.get("prop_axis_type", "Axis type:"), axis_combo)
        axes_form.addRow(tr.get("prop_show_grid", "Show grid:"), show_grid_check)
        _packed_row(
            axes_form,
            (tr.get("prop_x_tick_interval", "X tick interval:"), xtick_interval_spin),
            (tr.get("prop_show_x_labels", "Show X labels:"), show_xtick_check),
        )
        axes_form.addRow(
            tr.get("prop_x_tick_label_format", "X tick label format:"),
            x_tick_format_edit,
        )
        _packed_row(
            axes_form,
            (tr.get("prop_y_tick_interval", "Y tick interval:"), ytick_interval_spin),
            (tr.get("prop_show_y_labels", "Show Y labels:"), show_ytick_check),
        )
        axes_form.addRow(
            tr.get("prop_y_tick_label_format", "Y tick label format:"),
            y_tick_format_edit,
        )

        hint = QLabel(
            tr.get(
                "prop_tick_hint",
                "Use {value} as the tick value. Examples:  x={value}   or   {value} cm",
            )
        )
        hint.setWordWrap(True)
        axes_form.addRow(tr.get("prop_label_help", "Label help:"), hint)

        tabs.addTab(axes_page, tr.get("axes_ticks", "Axes & Ticks"))

        # ---- Lines & fill -------------------------------------------
        style_page = QWidget()
        style_form = QFormLayout(style_page)

        curve_width_spin = QSpinBox()
        curve_width_spin.setRange(1, 20)
        curve_width_spin.setValue(int(item.curve_width))

        show_bounds_check = QCheckBox()
        show_bounds_check.setChecked(item.show_bounds_lines)

        x1_color_btn = _color_button(item.x1_line_color)
        x2_color_btn = _color_button(item.x2_line_color)

        bounds_width_spin = QSpinBox()
        bounds_width_spin.setRange(0, 20)
        bounds_width_spin.setValue(int(item.bounds_line_width))

        bounds_style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.bounds_line_style
        )

        fill_btn = _color_button(item.fill_color)
        border_btn = _color_button(item.border_color)

        border_width_spin = QSpinBox()
        border_width_spin.setRange(0, 20)
        border_width_spin.setValue(int(item.border_width))

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, item.line_style
        )

        dash_spin = QDoubleSpinBox()
        dash_spin.setRange(1.0, 100.0)
        dash_spin.setValue(item.dash_length)

        def _update_dash_state():
            dash_spin.setEnabled(
                style_combo.currentData() != "solid"
                or bounds_style_combo.currentData() != "solid"
            )

        style_combo.currentIndexChanged.connect(lambda _i: _update_dash_state())
        bounds_style_combo.currentIndexChanged.connect(
            lambda _i: _update_dash_state()
        )
        _update_dash_state()

        style_form.addRow(
            tr.get("prop_curve_width", "Curve width:"), curve_width_spin
        )

        boundary_box = QGroupBox(
            tr.get("prop_boundary_box", "x1 / x2 boundary lines")
        )
        boundary_form = QFormLayout(boundary_box)
        _packed_row(
            boundary_form,
            (tr.get("prop_x1_color", "x1 color:"), x1_color_btn),
            (tr.get("prop_x2_color", "x2 color:"), x2_color_btn),
        )
        _packed_row(
            boundary_form,
            (tr.get("prop_width", "Width:"), bounds_width_spin),
            (tr.get("prop_style", "Style:"), bounds_style_combo),
        )
        boundary_form.addRow(
            tr.get("prop_dash_length", "Dash length:"), dash_spin
        )
        boundary_form.addRow(
            tr.get("prop_show_boundary_lines", "Show boundary lines:"),
            show_bounds_check,
        )
        style_form.addRow(boundary_box)

        curve_box = QGroupBox(
            tr.get("prop_curves_fill_box", "Curves and fill")
        )
        curve_form = QFormLayout(curve_box)
        _packed_row(
            curve_form,
            (tr.get("prop_fill", "Fill:"), fill_btn),
            (tr.get("prop_axis_border", "Axis/border:"), border_btn),
        )
        _packed_row(
            curve_form,
            (tr.get("prop_axis_border_width", "Axis/border width:"), border_width_spin),
            (tr.get("prop_axis_border_style", "Axis/border style:"), style_combo),
        )
        curve_form.addRow(
            tr.get("note", "Note:"),
            QLabel(
                tr.get(
                    "curve_colors_note",
                    "Curve colors are set on the Functions & Range tab.",
                )
            ),
        )
        style_form.addRow(curve_box)

        tabs.addTab(style_page, tr.get("lines_fill", "Lines & Fill"))

        fields = {
            "f1_expr": f1_edit,
            "f2_expr": f2_edit,
            "x_min": x_min_spin,
            "x_max": x_max_spin,
            "x1": x1_spin,
            "x2": x2_spin,
            "y_min": y_min_spin,
            "y_max": y_max_spin,
            "axis_type": axis_combo,
            "show_grid": show_grid_check,
            "show_bounds_lines": show_bounds_check,
            "show_xtick_labels": show_xtick_check,
            "show_ytick_labels": show_ytick_check,
            "xtick_interval": xtick_interval_spin,
            "ytick_interval": ytick_interval_spin,
            "x_tick_label_format": x_tick_format_edit,
            "y_tick_label_format": y_tick_format_edit,
            "num_points": num_points_spin,
            "f1_color": f1_color_btn,
            "f2_color": f2_color_btn,
            "x1_line_color": x1_color_btn,
            "x2_line_color": x2_color_btn,
            "curve_width": curve_width_spin,
            "bounds_line_width": bounds_width_spin,
            "bounds_line_style": bounds_style_combo,
            "fill_color": fill_btn,
            "border_color": border_btn,
            "border_width": border_width_spin,
            "line_style": style_combo,
            "dash_length": dash_spin,
        }

    else:
        return None, {}

    # App addition (not in the manual): every shape's Properties
    # dialog gets a Rotation field, added here once rather than
    # duplicated into every branch above - see DiagramItem.rotation_angle.
    rotation_spin = QDoubleSpinBox()
    rotation_spin.setRange(0.0, 360.0)
    rotation_spin.setSingleStep(1.0)
    rotation_spin.setDecimals(1)
    rotation_spin.setSuffix("\u00b0")
    rotation_spin.setValue(item.rotation_angle % 360)
    layout.addRow(tr.get("prop_rotation", "Rotation:"), rotation_spin)
    fields["rotation_angle"] = rotation_spin

    # App addition (not in the manual): Flip, same reasoning as
    # Rotation above - added once here rather than in every branch.
    flip_h_check = QCheckBox()
    flip_h_check.setChecked(item.flip_horizontal)
    layout.addRow(
        tr.get("prop_flip_horizontal", "Flip horizontal:"), flip_h_check
    )
    fields["flip_horizontal"] = flip_h_check

    flip_v_check = QCheckBox()
    flip_v_check.setChecked(item.flip_vertical)
    layout.addRow(
        tr.get("prop_flip_vertical", "Flip vertical:"), flip_v_check
    )
    fields["flip_vertical"] = flip_v_check

    # App addition (not in the manual): an optional internal PDF page
    # link is available to every DiagramItem, including TextItem.  The
    # selector stores a persistent destination document ID; the exporter
    # resolves that ID to the actual PDF page after the user's export
    # order is known.
    pdf_link_combo = _pdf_link_destination_combo(item)
    layout.addRow(
        tr.get("pdf_link", "PDF Link:"),
        pdf_link_combo,
    )
    fields["pdf_link_target"] = pdf_link_combo

    buttons = QDialogButtonBox(
        QDialogButtonBox.Ok | QDialogButtonBox.Cancel
    )

    if isinstance(item, PlotItem):
        def _validate_and_accept():
            from items.plot_math import compile_function, FunctionError

            try:
                compile_function(f1_edit.text())
                compile_function(f2_edit.text())
            except FunctionError as exc:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    dialog,
                    tr.get("invalid_function", "Invalid Function"),
                    str(exc),
                )
                return

            dialog.accept()

        buttons.accepted.connect(_validate_and_accept)
    else:
        buttons.accepted.connect(dialog.accept)

    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)

    return dialog, fields


def open_shape_properties(item, scene):
    """
    Opens `item`'s Properties dialog on the next event-loop iteration
    rather than immediately - every caller of this is a
    mouseDoubleClickEvent override, and opening a modal QDialog
    synchronously from inside a mouse event handler leaves Qt still
    treating the mouse button as down when the dialog appears, so the
    very first click on one of the dialog's own buttons (OK/Cancel)
    gets swallowed as that phantom release instead of registering as
    a real click - hence needing two or three clicks before anything
    happens. Deferring via QTimer.singleShot(0, ...) lets the double-
    click finish being processed (and that mouse grab released)
    before the dialog opens, so its buttons respond normally on the
    first click.
    """

    QTimer.singleShot(0, lambda: edit_shape_properties(item, scene))


def edit_shape_properties(item, scene, exec_dialog=None):
    """
    exec_dialog(dialog, fields) -> QDialog.DialogCode defaults to a
    real modal dialog.exec_(); tests can pass a stand-in that fills
    in the fields programmatically and returns Accepted/Rejected
    without blocking on real user input.
    """

    parent = None

    if scene is not None:
        views = scene.views()

        if views:
            # The actual top-level window (MainWindow), not just the
            # canvas view itself - a dialog needs a real top-level
            # parent to be correctly activated/focused by the window
            # manager (on Windows in particular, a parentless dialog
            # can need an extra click just to give it focus before a
            # click on OK/Cancel actually registers).
            parent = views[0].window()

    dialog, fields = _build_dialog(item, parent)

    if dialog is None:
        return

    if exec_dialog is None:
        result = dialog.exec_()
    else:
        result = exec_dialog(dialog, fields)

    if result != QDialog.Accepted:
        return

    old_props = {}
    new_props = {}

    for name, widget in fields.items():
        old_value = getattr(item, name)

        if isinstance(widget, _PlainValueField):
            new_value = widget.value
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            new_value = widget.value()
        elif isinstance(widget, QFontComboBox):
            # Checked before the plain QComboBox branch below, since
            # QFontComboBox is a QComboBox subclass - .currentData()
            # doesn't hold a font family the way _option_combo's
            # combos store their value.
            new_value = widget.currentFont().family()
        elif isinstance(widget, QComboBox):
            new_value = widget.currentData()
        elif isinstance(widget, QCheckBox):
            new_value = widget.isChecked()
        elif isinstance(widget, QLineEdit):
            new_value = widget.text()
        elif isinstance(widget, QTextEdit):
            new_value = widget.toPlainText()
        else:
            new_value = copy_color_value(widget.color)

        if name == "inner_radius_ratio":
            new_value = new_value / 100.0

        changed = type(new_value) is not type(old_value) or new_value != old_value

        if changed:
            old_props[name] = old_value
            new_props[name] = new_value

    if not new_props:
        return

    if scene is not None and hasattr(scene, "undo_stack"):
        scene.undo_stack.push(
            ChangePropertiesCommand(item, old_props, new_props, "Edit Properties")
        )
    else:
        for name, value in new_props.items():
            setattr(item, name, value)

        item.update()