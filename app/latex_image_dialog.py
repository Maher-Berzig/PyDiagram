# latex_image_dialog.py
"""
App addition (not in the manual): Image shape's Properties dialog ->
"Create from LaTeX..." (see items/property_dialog.py's ImageItem
branch) - a small LaTeX editor (an optional Preamble field plus the
LaTeX content itself - anything from a bare equation to a full
theorem environment) with a live preview, next to the existing
Browse... file picker, for inserting the rendered result as the
shape's image instead of picking an existing file.
Compiling happens on a background thread (app/latex_render.py:
LatexRenderWorker) so the dialog stays responsive while pdflatex/
pdftocairo run - adapted from the same reference implementation that
module's docstring credits, turned from a standalone main window into
a modal dialog that hands its result back to the Properties dialog
that opened it, the same way that dialog's own Browse... button does.
"""

from PyQt5.QtCore import QSize, QThread, Qt
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from app import latex_render
from items.color_picker import paint_swatch

DEFAULT_PREAMBLE = ""

# Self-delimited now that the LaTeX field's content is inserted into
# the document verbatim (see LatexRenderWorker._render()) rather than
# always being wrapped in "$\displaystyle ... $" - a plain equation
# needs to supply its own math delimiters, same as any other LaTeX
# field content would.
DEFAULT_LATEX = """\\[
\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a},\\alpha,\\beta,\\pi,\\Delta,D'
\\]
"""



class _LatexErrorDialog(QDialog):
    """
    A scrollable stand-in for QMessageBox.critical(): the error text
    here is often a multi-thousand-character pdflatex log tail (see
    LatexRenderWorker._render()'s log_text[-6000:]), which a plain
    QMessageBox has no scrollbar for and just wraps in place, growing
    the window to fit (or, past a platform-specific point, clipping
    it) - a fixed-size dialog around a read-only QPlainTextEdit gives
    that text an actual scrollbar, and NoWrap keeps pdflatex's own
    long lines (file paths, "! " error lines) scannable rather than
    re-wrapped mid-line.
    """

    def __init__(self, parent, message):
        super().__init__(parent)

        self.setWindowTitle("LaTeX Error")
        self.resize(700, 480)
        self.setMinimumSize(400, 250)

        text_view = QPlainTextEdit()
        text_view.setReadOnly(True)
        text_view.setPlainText(message)
        text_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        text_view.setFont(QFont("Monospace"))

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("LaTeX compilation failed:"))
        layout.addWidget(text_view, 1)
        layout.addWidget(button_box)


class LatexImageDialog(QDialog):

    def __init__(self, parent=None, recipe=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

        self.setWindowTitle("Create Image from LaTeX")
        self.resize(640, 480)

        # Set once a render succeeds - what prompt_latex_image() below
        # returns to the caller. Stays None (and Insert stays
        # disabled - see _on_render_finished()/_on_render_error())
        # until then, so Insert can never hand back a stale or
        # never-rendered path.
        self.result_path = None
        self.result_recipe = None
        self.preview_pixmap = None
        self.worker_thread = None
        self.worker = None

        recipe = recipe or {}
        self.text_color = QColor(f'#{recipe.get("text_color", "000000")}')
        self.background_color = QColor(
            f'#{recipe.get("background_color", "FFFFFF")}'
        )

        self._build_ui(recipe)
        self._update_color_button_styles()
        self.render_preview()

    # -- ui ----------------------------------------------------------

    def _build_ui(self, recipe):
        self.preamble_edit = QPlainTextEdit()
        self.preamble_edit.setPlaceholderText(
            r"Extra preamble, e.g. \usepackage{amsthm}"
            "\n" r"\newtheorem{theorem}{Theorem}"
        )
        self.preamble_edit.setPlainText(recipe.get("preamble", DEFAULT_PREAMBLE))
        self.preamble_edit.setMaximumHeight(60)

        self.equation_edit = QPlainTextEdit()
        self.equation_edit.setPlaceholderText(
            r"Enter LaTeX, e.g. $\frac{-b \pm \sqrt{b^2-4ac}}{2a}$ or a full "
            r"\begin{theorem}...\end{theorem} using the preamble above"
        )
        # "equation" is the pre-existing recipe key (still read here so
        # reopening an image rendered before this field existed still
        # prefills correctly) - current_recipe() below writes "latex"
        # going forward, since the field is no longer equation-only.
        self.equation_edit.setPlainText(
            recipe.get("latex") or recipe.get("equation") or DEFAULT_LATEX
        )
        self.equation_edit.setMaximumHeight(70)

        self.text_color_button = QPushButton("Text Color")
        self.text_color_button.setIconSize(QSize(48, 18))
        self.background_color_button = QPushButton("Background Color")
        self.background_color_button.setIconSize(QSize(48, 18))

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setSuffix(" pt")
        self.padding_spin.setValue(
            recipe.get("padding", latex_render.DEFAULT_PADDING)
        )

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setSuffix(" dpi")
        self.dpi_spin.setValue(recipe.get("dpi", latex_render.DEFAULT_DPI))

        self.render_button = QPushButton("Render Preview")

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(300, 180)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setStyleSheet(
            "QLabel { border: 1px solid #888888; background-color: #ffffff; }"
        )

        options_row = QHBoxLayout()
        options_row.addWidget(self.text_color_button)
        options_row.addWidget(self.background_color_button)
        options_row.addWidget(QLabel("Padding:"))
        options_row.addWidget(self.padding_spin)
        options_row.addWidget(QLabel("DPI:"))
        options_row.addWidget(self.dpi_spin)
        options_row.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.insert_button = self.button_box.button(QDialogButtonBox.Ok)
        self.insert_button.setText("Insert")
        self.insert_button.setEnabled(False)
        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Preamble:"))
        layout.addWidget(self.preamble_edit)
        layout.addWidget(QLabel("LaTeX:"))
        layout.addWidget(self.equation_edit)
        layout.addLayout(options_row)
        layout.addWidget(self.render_button)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.button_box)

        self.text_color_button.clicked.connect(self._pick_text_color)
        self.background_color_button.clicked.connect(self._pick_background_color)
        self.render_button.clicked.connect(self.render_preview)

    def _update_color_button_styles(self):
        """
        Same swatch-icon convention every fill/border color button in
        the app uses (items/color_picker.py: paint_swatch(), also
        behind property_dialog.py's _color_button) - a small flat-color
        icon on the button rather than recoloring the button itself.
        Solid colors only (no gradient/pattern option, unlike
        _color_button): text_color/background_color here become a
        LaTeX \\definecolor{...}{HTML}{...} each, which has no way to
        express either.
        """

        self.text_color_button.setIcon(paint_swatch(self.text_color))
        self.background_color_button.setIcon(paint_swatch(self.background_color))

    def _pick_text_color(self):
        # No QColorDialog.ShowAlphaChannel here, unlike the app's other
        # color pickers: alpha has no equivalent in the HTML color
        # model \definecolor{...}{HTML}{...} renders with.
        color = QColorDialog.getColor(self.text_color, self, "Select Text Color")

        if color.isValid():
            self.text_color = color
            self._update_color_button_styles()

    def _pick_background_color(self):
        color = QColorDialog.getColor(
            self.background_color, self, "Select Background Color"
        )

        if color.isValid():
            self.background_color = color
            self._update_color_button_styles()

    # -- rendering -----------------------------------------------------

    def current_recipe(self):
        return {
            "preamble": self.preamble_edit.toPlainText().strip(),
            "latex": self.equation_edit.toPlainText().strip(),
            "text_color": self.text_color.name().lstrip("#").upper(),
            "background_color": self.background_color.name().lstrip("#").upper(),
            "padding": self.padding_spin.value(),
            "dpi": self.dpi_spin.value(),
        }

    def render_preview(self):
        recipe = self.current_recipe()
        self._pending_recipe = recipe

        if not recipe["latex"]:
            QMessageBox.warning(
                self, "Empty LaTeX", "Please enter some LaTeX to render."
            )
            return

        # Guards against a second overlapping render: this - and the
        # matching re-enable in _on_thread_finished() - is the only
        # place either button's enabled state is touched outside of
        # __init__, so a click can never land while a thread is
        # already running.
        self.render_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.insert_button.setEnabled(False)

        self.preview.clear()
        self.preview.setText("Rendering...")

        self.worker_thread = QThread(self)
        self.worker = latex_render.LatexRenderWorker(recipe)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.compile_latex)
        self.worker.finished.connect(self._on_render_finished)
        self.worker.error.connect(self._on_render_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_thread_finished)

        self.worker_thread.start()

    def _on_render_finished(self, png_path):
        pixmap = QPixmap(png_path)

        if pixmap.isNull():
            self._on_render_error(
                f"Qt could not load the rendered PNG:\n\n{png_path}"
            )
            return

        self.result_path = png_path
        self.result_recipe = self._pending_recipe
        self.preview_pixmap = pixmap
        self._update_preview_pixmap()
        self.insert_button.setEnabled(True)

    def _on_render_error(self, message):
        self.result_path = None
        self.result_recipe = None
        self.preview_pixmap = None
        self.preview.clear()
        self.preview.setText("Rendering failed")
        _LatexErrorDialog(self, message).exec_()

    def _on_thread_finished(self):
        self.render_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.worker_thread = None
        self.worker = None

    def _update_preview_pixmap(self):
        if self.preview_pixmap is None:
            return

        target = self.preview.size() - self.preview.size().__class__(8, 8)

        if target.width() <= 0 or target.height() <= 0:
            return

        scaled = self.preview_pixmap.scaled(
            target, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview_pixmap()

    def _on_accept(self):
        if self.result_path is None:
            return

        self.accept()


def prompt_latex_image(parent, current_path="", current_recipe=None):
    """
    Shows the "Create from LaTeX..." dialog, prefilled from
    `current_recipe` if the Image shape already has one saved
    (ImageItem.latex_recipe - see items/image_item.py), falling back
    to current_path's cache sidecar (app/latex_render.py:
    load_recipe()) for an Image shape saved before that attribute
    existed. Returns (new_path, recipe) - the newly rendered (or
    cache-reused) PNG's path and the exact recipe that produced it,
    ready to be saved back onto the shape as its new latex_recipe -
    or None if canceled.
    """

    recipe = current_recipe or latex_render.load_recipe(current_path)
    dialog = LatexImageDialog(parent, recipe)

    if dialog.exec_() == QDialog.Accepted:
        return dialog.result_path, dialog.result_recipe

    return None
