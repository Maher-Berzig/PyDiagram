"""Beziergon mask: an editable path that erases its interior.

The Mask follows the supplied Beziergon-mask reference: the editable
Bezier path is used as a clipping/hole path. On screen it is shown as a
subtle translucent hole while editing; during raster/vector painting it
uses DestinationOut so objects underneath are actually removed.
"""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen

from .beziergon_item import BeziergonItem
from .bezier_utils import build_bezier_path


class MaskItem(BeziergonItem):
    SHAPE_TYPE = "mask"
    LABEL = "Mask"

    def boundingRect(self):
        # The mask only needs to paint its own path.  Keep the same generous
        # stroke margin as BeziergonItem while avoiding an enormous repaint
        # area for an ordinary editable object.
        return super().boundingRect()

    def paint(self, painter, option, widget=None):
        path = self._path()

        scene = self.scene()
        exporting = bool(scene and getattr(scene, "export_mode", False))

        painter.save()
        if exporting:
            # The supplied reference uses the Beziergon as a clipping mask:
            # the region inside the closed path is removed from the content
            # underneath it.
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.white)
            painter.drawPath(path)
        else:
            # Editing view: make the masked region obvious without changing
            # the normal scene appearance until export/painting occurs.
            painter.setPen(QPen(QColor("#d62828"), 1.5, Qt.DashLine))
            painter.setBrush(QColor(214, 40, 40, 35))
            painter.drawPath(path)
        painter.restore()

        if self.isSelected():
            painter.save()
            painter.setPen(QPen(QColor("#1677ff"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            painter.restore()

        self._paint_connection_points(painter)
