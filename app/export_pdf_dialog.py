# export_pdf_dialog.py
"""
App addition (not in the manual): File -> Export to PDF...

Lists every .pydia document currently open in a tab, each with a
checkbox. [Move Up] / [Move Down] set the page order, [Export] asks for
the PDF's file name and closes the dialog with Accepted; the caller
(MainWindow.export_pdf) then reads selected_containers()/output_path
and writes one page per checked document, in list order.
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class ExportPdfDialog(QDialog):

    def __init__(self, entries, parent=None, current=None):
        """
        entries: [(container, display_name, tooltip)] in tab order.
        current: the container whose row starts out highlighted.
        """

        super().__init__(parent)

        self.setWindowTitle("Export to PDF")
        self.resize(460, 360)

        self.output_path = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Check the files to export, one PDF page each, "
                   "in the order listed:")
        )

        body = QHBoxLayout()
        layout.addLayout(body, 1)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        body.addWidget(self.list_widget, 1)

        for container, name, tooltip in entries:
            item = QListWidgetItem(name)
            item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            item.setCheckState(Qt.Checked)
            item.setToolTip(tooltip)
            item.setData(Qt.UserRole, container)
            self.list_widget.addItem(item)

        side = QVBoxLayout()
        body.addLayout(side)

        self.up_button = QPushButton("Move Up")
        self.down_button = QPushButton("Move Down")
        side.addWidget(self.up_button)
        side.addWidget(self.down_button)
        side.addStretch(1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        layout.addLayout(bottom)

        self.export_button = QPushButton("Export")
        self.export_button.setDefault(True)
        cancel_button = QPushButton("Cancel")
        bottom.addWidget(self.export_button)
        bottom.addWidget(cancel_button)

        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button.clicked.connect(lambda: self._move(1))
        self.export_button.clicked.connect(self._export)
        cancel_button.clicked.connect(self.reject)
        self.list_widget.currentRowChanged.connect(self._update_buttons)
        self.list_widget.itemChanged.connect(self._update_buttons)

        row = 0

        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(Qt.UserRole) is current:
                row = i

        self.list_widget.setCurrentRow(row)
        self._update_buttons()

    def selected_containers(self):
        """Checked documents, in the order shown in the list."""

        result = []

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)

            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole))

        return result

    def _move(self, step):
        row = self.list_widget.currentRow()
        target = row + step

        if row < 0 or not 0 <= target < self.list_widget.count():
            return

        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(target, item)
        self.list_widget.setCurrentRow(target)

    def _update_buttons(self, *_args):
        row = self.list_widget.currentRow()
        count = self.list_widget.count()

        self.up_button.setEnabled(row > 0)
        self.down_button.setEnabled(0 <= row < count - 1)
        self.export_button.setEnabled(bool(self.selected_containers()))

    def _export(self):
        containers = self.selected_containers()

        if not containers:
            return

        first = containers[0].file_path
        directory = os.path.dirname(first) if first else ""
        stem = (
            os.path.splitext(os.path.basename(first))[0]
            if first and len(containers) == 1 else "diagrams"
        )

        path, _ = QFileDialog.getSaveFileName(
            self, "Export to PDF", os.path.join(directory, stem + ".pdf"),
            "PDF Files (*.pdf)"
        )

        if not path:
            return

        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        self.output_path = path
        self.accept()
