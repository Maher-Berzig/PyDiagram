# save_shape_dialog.py
"""
App addition (not in the manual): Objects -> Save as New Shape...

Gathers a category (an existing user-shapes subfolder, or a new one
to create) and a name for a shape being saved from the current
selection. This dialog is UI-only - it doesn't touch the scene or the
filesystem itself, same division of labor as tikz_dialog.py; the
actual saving happens in MainWindow.save_selection_as_shape(), via
app/custom_shapes.py.
"""

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

NEW_CATEGORY_LABEL = "New Category..."


def prompt_save_shape(parent, categories):
    """
    Shows the Save-as-New-Shape dialog. `categories` is the list of
    existing custom-shape category names to offer in the dropdown.
    Returns (category_name, shape_name) on OK, or None if the user
    cancelled.
    """

    dialog = QDialog(parent)
    dialog.setWindowTitle("Save as New Shape")

    layout = QVBoxLayout(dialog)
    form = QFormLayout()
    layout.addLayout(form)

    category_combo = QComboBox()
    category_combo.addItems(categories)
    category_combo.addItem(NEW_CATEGORY_LABEL)

    new_category_edit = QLineEdit()
    new_category_edit.setPlaceholderText("Folder name for the new category")

    name_edit = QLineEdit()
    name_edit.setPlaceholderText("Shape name")

    form.addRow("Category:", category_combo)
    form.addRow("New category name:", new_category_edit)
    form.addRow("Shape name:", name_edit)

    if not categories:
        # Nothing to pick from yet - default straight to "create a
        # new category" instead of leaving the combo on a blank entry.
        category_combo.setCurrentText(NEW_CATEGORY_LABEL)

    def sync_new_category_field():
        new_category_edit.setVisible(
            category_combo.currentText() == NEW_CATEGORY_LABEL
        )
        form.labelForField(new_category_edit).setVisible(
            new_category_edit.isVisible()
        )

    category_combo.currentIndexChanged.connect(sync_new_category_field)
    sync_new_category_field()

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    ok_button = buttons.button(QDialogButtonBox.Ok)

    def validate():
        creating_category = category_combo.currentText() == NEW_CATEGORY_LABEL
        category_ok = (
            bool(new_category_edit.text().strip()) if creating_category else True
        )
        ok_button.setEnabled(category_ok and bool(name_edit.text().strip()))

    category_combo.currentIndexChanged.connect(validate)
    new_category_edit.textChanged.connect(validate)
    name_edit.textChanged.connect(validate)
    validate()

    name_edit.setFocus()

    if dialog.exec_() != QDialog.Accepted:
        return None

    if category_combo.currentText() == NEW_CATEGORY_LABEL:
        category_name = new_category_edit.text().strip()
    else:
        category_name = category_combo.currentText()

    shape_name = name_edit.text().strip()

    return category_name, shape_name
