# position_dialog.py
"""
Objects -> Position (app addition, not in the manual). Shows a
selected shape's current position relative to the rulers' (0,0)
origin (manual 3.3 - the rulers are drawn directly in scene units,
see canvas/ruler.py, so "relative to the rulers" is just the scene
position) in two editable fields, and lets the user type in a new
one.

Same shape as diagram_properties_dialog.open_diagram_properties:
a plain function that builds the dialog, runs it modally, and
returns the values the user entered (or None on Cancel) - it doesn't
touch the item/scene itself. The caller (MainWindow.
edit_position_selection) owns turning that into an undoable move,
the same way Rotate... (MainWindow.rotate_selection) owns turning
its angle into an undoable transform.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
)

_COORD_RANGE = 1_000_000.0


def _coord_spin(value):
    spin = QDoubleSpinBox()
    spin.setRange(-_COORD_RANGE, _COORD_RANGE)
    spin.setDecimals(2)
    spin.setValue(value)
    return spin


def open_position_dialog(x, y, parent=None):
    """
    `x`/`y`: the shape's current position, relative to the rulers'
    (0,0). Returns the new (x, y) the user entered, or None if they
    cancelled.
    """

    dialog = QDialog(parent)
    dialog.setWindowTitle("Position")
    layout = QVBoxLayout(dialog)

    form = QFormLayout()
    layout.addLayout(form)

    x_spin = _coord_spin(x)
    y_spin = _coord_spin(y)

    form.addRow("Horizontal:", x_spin)
    form.addRow("Vertical:", y_spin)

    buttons = QDialogButtonBox(
        QDialogButtonBox.Ok | QDialogButtonBox.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    x_spin.setFocus()
    x_spin.selectAll()

    if dialog.exec_() != QDialog.Accepted:
        return None

    return (x_spin.value(), y_spin.value())
