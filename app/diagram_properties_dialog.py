# diagram_properties_dialog.py
"""
Diagram -> Properties (manual 3.1, Figure 3.1 "Diagram / Properties /
Grid"; 3.4 "Background Color"; 9.1.5 "Grid Lines"). Two tabs:

- Grid: visibility, snap-to-grid, independent X/Y spacing, and color.
  Real Dia also has "Dynamic grid" (grid follows zoom instead of
  scene units) and "Hex grid" - both skipped here, since this clone's
  grid is always a fixed-scene-unit rectangular grid.
- Colors: just Background (3.4). Real Dia's Colors tab also covers
  Grid Lines and Page Breaks colors; grid color is folded into the
  Grid tab above instead, and this clone has no page-break lines.

Applies its changes directly to the DiagramScene on OK - there's
nothing to undo/redo here, same as Dia's own Preferences-style dialogs.
"""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from items.property_dialog import _color_button
from canvas.diagram_scene import PAPER_SIZES_MM
from app import settings


def open_diagram_properties(scene, parent=None):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Paper Sizes")
    layout = QVBoxLayout(dialog)

    tabs = QTabWidget()
    layout.addWidget(tabs)

    # -- Paper Sizes tab ------------------------------------------------

    diagram_page = QWidget()
    diagram_form = QFormLayout(diagram_page)

    paper_combo = QComboBox()
    paper_combo.addItem("Best Fit", "Best Fit")
    for name, (width, height) in PAPER_SIZES_MM.items():
        paper_combo.addItem(f"{name} — {width} × {height} mm", name)
    paper_combo.addItem("Custom Size", "Custom Size")

    current_paper = getattr(scene, "paper_format", "A4")
    index = paper_combo.findData(current_paper)
    paper_combo.setCurrentIndex(index if index >= 0 else paper_combo.findData("A4"))

    orientation_combo = QComboBox()
    orientation_combo.addItem("portrait", "portrait")
    orientation_combo.addItem("landscape", "landscape")
    current_orientation = getattr(scene, "paper_orientation", "portrait")
    oi = orientation_combo.findData(current_orientation)
    orientation_combo.setCurrentIndex(oi if oi >= 0 else 0)

    custom_width = QSpinBox()
    custom_width.setRange(1, 10000)
    custom_width.setSuffix(" mm")
    custom_width.setValue(round(getattr(scene, "custom_width_mm", 210.0)))

    custom_height = QSpinBox()
    custom_height.setRange(1, 10000)
    custom_height.setSuffix(" mm")
    custom_height.setValue(round(getattr(scene, "custom_height_mm", 297.0)))

    diagram_form.addRow("Paper size:", paper_combo)
    diagram_form.addRow("Paper orientation:", orientation_combo)
    diagram_form.addRow("Custom width:", custom_width)
    diagram_form.addRow("Custom height:", custom_height)
    tabs.addTab(diagram_page, "Paper Sizes")

    def update_custom_enabled():
        enabled = paper_combo.currentData() == "Custom Size"
        custom_width.setEnabled(enabled)
        custom_height.setEnabled(enabled)

    paper_combo.currentIndexChanged.connect(update_custom_enabled)
    update_custom_enabled()

    # -- Grid tab ------------------------------------------------------

    grid_page = QWidget()
    grid_form = QFormLayout(grid_page)

    visible_check = QCheckBox()
    visible_check.setChecked(scene.show_grid)

    snap_check = QCheckBox()
    snap_check.setChecked(scene.snap_to_grid)

    x_size_spin = QSpinBox()
    x_size_spin.setRange(2, 500)
    x_size_spin.setValue(int(scene.grid_x_size))

    y_size_spin = QSpinBox()
    y_size_spin.setRange(2, 500)
    y_size_spin.setValue(int(scene.grid_y_size))

    grid_color_btn = _color_button(scene.grid_color)

    grid_form.addRow("Visible:", visible_check)
    grid_form.addRow("Snap to:", snap_check)
    grid_form.addRow("X Size:", x_size_spin)
    grid_form.addRow("Y Size:", y_size_spin)
    grid_form.addRow("Color:", grid_color_btn)

    tabs.addTab(grid_page, "Grid")

    # -- Colors tab ------------------------------------------------------

    colors_page = QWidget()
    colors_form = QFormLayout(colors_page)

    bg_btn = _color_button(scene.background_color)
    colors_form.addRow("Background:", bg_btn)

    tabs.addTab(colors_page, "Colors")

    buttons = QDialogButtonBox(
        QDialogButtonBox.Ok | QDialogButtonBox.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec_() != QDialog.Accepted:
        return

    scene.show_grid = visible_check.isChecked()
    scene.snap_to_grid = snap_check.isChecked()
    scene.grid_x_size = x_size_spin.value()
    scene.grid_y_size = y_size_spin.value()
    scene.grid_color = QColor(grid_color_btn.color)
    scene.background_color = QColor(bg_btn.color)

    paper_format = paper_combo.currentData()
    orientation = orientation_combo.currentData()
    custom_width_mm = custom_width.value()
    custom_height_mm = custom_height.value()
    scene.set_paper_settings(paper_format, orientation, custom_width_mm, custom_height_mm)
    settings.save_default_paper_settings(
        paper_format, orientation, custom_width_mm, custom_height_mm
    )
    scene.update()
