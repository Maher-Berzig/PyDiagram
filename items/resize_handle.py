# resize_handle.py

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsRectItem

from canvas.commands import ResizeItemCommand


class ResizeHandle(QGraphicsRectItem):

    SIZE = 8

    def __init__(self, owner, cursor):
        super().__init__(
            -self.SIZE / 2,
            -self.SIZE / 2,
            self.SIZE,
            self.SIZE,
            owner
        )

        self.owner = owner
        self.cursor_shape = cursor

        self.setBrush(
            QBrush(QColor("#ffffff"))
        )

        self.setPen(
            QPen(QColor("#1677ff"), 1)
        )

        self.setZValue(1000)

        self.setAcceptedMouseButtons(
            Qt.LeftButton
        )

        self._start_scene_pos = None
        self._start_rect = None
        self._start_item_rect = None

    def mousePressEvent(self, event):
        self._start_scene_pos = event.scenePos()
        self._start_rect = self.owner.boundingRect()

        self._start_item_rect = (
            QRectF(self.owner._rect)
            if hasattr(self.owner, "_rect") else None
        )

        self.setCursor(self.cursor_shape)

        event.accept()

    def mouseMoveEvent(self, event):
        if self._start_scene_pos is None:
            return

        current = event.scenePos()

        delta = (
            current - self._start_scene_pos
        )

        self.owner.resize_from_handle(
            self.name,
            delta,
            self._start_rect
        )

        event.accept()

    def mouseReleaseEvent(self, event):
        if self._start_item_rect is not None and hasattr(self.owner, "_rect"):
            new_rect = QRectF(self.owner._rect)

            if new_rect != self._start_item_rect:
                scene = self.owner.scene()

                if scene is not None and hasattr(scene, "undo_stack"):
                    scene.undo_stack.push(
                        ResizeItemCommand(
                            self.owner,
                            self._start_item_rect,
                            new_rect,
                            "Resize"
                        )
                    )

        self._start_scene_pos = None
        self._start_rect = None
        self._start_item_rect = None

        event.accept()