# image_item.py
"""
Manual 5.1.12, "Image": "A diagram can contain images as well as
shapes. To add an image, click on the Image icon and click on the
canvas. An object that says 'Broken Image' will appear. Double-click
it to open the properties dialog. Then click on 'Browse' and select
your file. Click 'OK' and then the image will display on the diagram.
You can resize the image as desired using the object handles."

Geometry-wise this is just a resizable rectangle (same _rect/
resize_from_handle contract as RectangleItem, so it uses the base
class's ordinary corner-resize handles), but what it paints is either
the loaded picture or the manual's own "Broken Image" placeholder -
which doubles as the missing/unreadable-file indicator, since the
image is reloaded from disk on every paint rather than embedded in
the saved diagram (matching how the manual describes Dia referencing
an external file, not embedding it).

App addition (not in the manual): if the shape was inserted via
"Create from LaTeX..." (app/latex_image_dialog.py), latex_recipe
below travels with the diagram (app/document_io.py) even though the
rendered file itself doesn't - so a missing file (most notably right
after Diagram -> Clean Up LaTeX Image Cache...) is regenerated
on the spot rather than staying "Broken Image" forever; see
_load_pixmap()/_recover_from_latex_recipe() below.
"""

import os

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPixmap

from .diagram_item import DiagramItem

# Manual 5.1.12: "The following image [formats] are usually
# supported... BMP, JPEG, PNG, SVG, XPM" - SVG isn't in this list
# since QPixmap can't load it directly without QtSvg; GIF is added as
# another common QImageReader-supported raster format.
IMAGE_FILE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.bmp *.xpm *.gif);;All Files (*)"
)


class ImageItem(DiagramItem):

    def __init__(self, rect=QRectF(0, 0, 120, 90), parent=None):
        super().__init__(parent)

        self._rect = QRectF(rect)
        self.file_path = ""

        # App addition (not in the manual): the LaTeX recipe (equation,
        # preamble, colors, padding, DPI) that rendered file_path, if
        # it was produced via "Create from LaTeX..." (app/
        # latex_image_dialog.py) - None for a plain Browse...'d image.
        # Saved with the diagram (app/document_io.py) so the rendered
        # file itself is disposable: see _load_pixmap()'s self-healing
        # reload below and app/latex_render.py's module docstring.
        self.latex_recipe = None

        # Not persisted - which file_path a recovery attempt has
        # already been tried (and, implicitly by still being that
        # value, failed) for, so a still-missing/still-unrenderable
        # file doesn't retry pdflatex on every single repaint. Reset
        # by _load_pixmap() itself whenever file_path moves on to
        # some other path worth a fresh attempt.
        self._latex_recovery_attempted_for = None

    def _load_pixmap(self):
        if self.file_path and os.path.isfile(self.file_path):
            pixmap = QPixmap(self.file_path)

            if not pixmap.isNull():
                return pixmap
        elif (
            self.latex_recipe
            and self._latex_recovery_attempted_for != self.file_path
        ):
            self._latex_recovery_attempted_for = self.file_path
            self._recover_from_latex_recipe()

            if self.file_path and os.path.isfile(self.file_path):
                pixmap = QPixmap(self.file_path)

                if not pixmap.isNull():
                    return pixmap

        return None

    def _recover_from_latex_recipe(self):
        """
        App addition (not in the manual): re-renders file_path from
        latex_recipe when the file itself is missing (or unreadable) -
        most notably right after Diagram -> Clean Up LaTeX Image
        Cache... (app/latex_render.py: clear_cache()), but this covers
        any other way the cached file could have gone missing too.
        Deferred import, same as items/property_dialog.py's own
        "Create from LaTeX..." wiring, to avoid items/ importing from
        app/ at module load time.
        """

        from app import latex_render

        try:
            png_path = latex_render.render_recipe(self.latex_recipe)
        except Exception:
            # Left as "Broken Image" - most commonly pdflatex/
            # pdftocairo not being installed on this machine. Not
            # retried again until file_path changes (see the
            # _latex_recovery_attempted_for guard above), so a slow,
            # doomed-to-fail subprocess pair isn't relaunched on every
            # repaint.
            return

        self.file_path = png_path

    def boundingRect(self):
        extra = 4

        return self._rect.adjusted(-extra, -extra, extra, extra)

    def connection_points(self):
        """
        Corners, edge midpoints, and center - same pattern as
        RectangleItem (4.2.5).
        """

        r = self._rect

        return [
            r.topLeft(),
            QPointF(r.center().x(), r.top()),
            r.topRight(),
            QPointF(r.left(), r.center().y()),
            r.center(),
            QPointF(r.right(), r.center().y()),
            r.bottomLeft(),
            QPointF(r.center().x(), r.bottom()),
            r.bottomRight(),
        ]

    def paint(self, painter, option, widget=None):
        pixmap = self._load_pixmap()

        if pixmap is not None:
            painter.drawPixmap(self._rect.toRect(), pixmap)
        else:
            painter.setPen(QPen(QColor("#a0a0a0"), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor("#f2f2f2")))
            painter.drawRect(self._rect)

            painter.setPen(QColor("#606060"))
            font = painter.font()
            font.setPointSizeF(max(font.pointSizeF() * 0.8, 6.0))
            painter.setFont(font)
            painter.drawText(
                self._rect, Qt.AlignCenter | Qt.TextWordWrap, "Broken Image"
            )

        if self.isSelected():
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._rect)

        self._paint_connection_points(painter)

    def resize_from_handle(self, handle, delta, original):
        rect = QRectF(original)

        if handle == "top_left":
            rect.setTopLeft(original.topLeft() + delta)
        elif handle == "top_right":
            rect.setTopRight(original.topRight() + delta)
        elif handle == "bottom_left":
            rect.setBottomLeft(original.bottomLeft() + delta)
        elif handle == "bottom_right":
            rect.setBottomRight(original.bottomRight() + delta)

        if rect.width() < self.MIN_WIDTH:
            rect.setWidth(self.MIN_WIDTH)

        if rect.height() < self.MIN_HEIGHT:
            rect.setHeight(self.MIN_HEIGHT)

        self.prepareGeometryChange()

        self._rect = rect

        self._update_handles()
        self.notify_connections()

        self.update()
