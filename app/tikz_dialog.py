# tikz_dialog.py
"""
App addition (not in the manual): the popup shown by the toolbar's
Tikz button and by File > Export as Tikz... (see tikz_export.py for
how the code itself is generated). Just a read-only view of the
generated code plus Copy-to-clipboard and Save-to-file - there's
nothing to accept/apply, so unlike diagram_properties_dialog.py this
has no OK/Cancel semantics, only Close.
"""

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


def show_tikz_dialog(tikz_code, parent=None):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Tikz Code")
    dialog.resize(700, 500)

    layout = QVBoxLayout(dialog)

    text_view = QPlainTextEdit()
    text_view.setPlainText(tikz_code)
    text_view.setReadOnly(True)
    text_view.setLineWrapMode(QPlainTextEdit.NoWrap)
    text_view.setStyleSheet("font-family: monospace;")
    layout.addWidget(text_view)

    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    copy_button = QPushButton("Copy to Clipboard")
    save_button = QPushButton("Save As...")
    buttons.addButton(copy_button, QDialogButtonBox.ActionRole)
    buttons.addButton(save_button, QDialogButtonBox.ActionRole)
    buttons.rejected.connect(dialog.reject)
    buttons.button(QDialogButtonBox.Close).clicked.connect(dialog.accept)
    layout.addWidget(buttons)

    def copy_to_clipboard():
        QApplication.clipboard().setText(text_view.toPlainText())

    def save_as():
        path, _ = QFileDialog.getSaveFileName(
            dialog, "Save Tikz Code", "diagram.tex", "TeX Files (*.tex);;All Files (*)"
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text_view.toPlainText())
        except OSError as exc:
            QMessageBox.warning(dialog, "Save Tikz Code", f"Could not save file:\n{exc}")

    copy_button.clicked.connect(copy_to_clipboard)
    save_button.clicked.connect(save_as)

    dialog.exec_()
