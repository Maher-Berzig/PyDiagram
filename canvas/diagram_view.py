from PyQt5.QtCore import Qt, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView

from canvas.commands import DeleteItemsCommand, MoveItemCommand


class DiagramView(QGraphicsView):

    # Emitted on Escape when it should switch the app back to the
    # select tool (as opposed to just leaving text-edit mode). The
    # MainWindow listens so the toolbar's checked tool stays in sync -
    # the view itself doesn't know about toolbar actions.
    escape_pressed = pyqtSignal()

    # Emitted on Space, to toggle between the select tool and whatever
    # drawing tool was last used (manual 4.1.1 tip).
    space_pressed = pyqtSignal()

    # The rulers (manual 3.3) listen to these two: mouse_moved keeps
    # each ruler's position arrow in sync with the cursor, and
    # viewport_changed tells them to redraw their tick marks whenever
    # panning or zooming shifts what's visible.
    mouse_moved = pyqtSignal(QPointF)
    mouse_left = pyqtSignal()
    viewport_changed = pyqtSignal()

    # Arrow-key nudging (app addition, not in the manual) - see
    # nudge_selected_items() below.
    ARROW_KEY_DIRECTIONS = {
        Qt.Key_Left: (-1, 0),
        Qt.Key_Right: (1, 0),
        Qt.Key_Up: (0, -1),
        Qt.Key_Down: (0, 1),
    }
    BASE_NUDGE_STEP = 10.0

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.setRenderHint(QPainter.Antialiasing)
        # Without this, ImageItem (items/image_item.py) scaling a
        # picture - including a LaTeX-rendered one, however high its
        # own DPI - up or down to fit its shape uses Qt's fast,
        # blocky-looking default pixmap scaling instead of smooth
        # interpolation, pixelating on screen regardless of the source
        # resolution. Matches the same hint added to every export
        # painter in app/document_io.py, so on-screen and exported
        # images scale the same way.
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.NoDrag)

        self.setTransformationAnchor(
            QGraphicsView.AnchorUnderMouse
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorUnderMouse
        )

        # Explicit rather than relying on Qt's default, so nothing
        # else in the app can end up silently suppressing scrollbars.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._zoom = 1.0
        self._panning = False
        self._pan_start = None
        self._drag_positions = None

        self.setMouseTracking(True)

        self.horizontalScrollBar().valueChanged.connect(
            lambda _value: self.viewport_changed.emit()
        )

        self.verticalScrollBar().valueChanged.connect(
            lambda _value: self.viewport_changed.emit()
        )

    def wheelEvent(self, event):
        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            self.scale(
                zoom_factor,
                zoom_factor
            )
            self._zoom *= zoom_factor

        else:
            self.scale(
                1 / zoom_factor,
                1 / zoom_factor
            )
            self._zoom /= zoom_factor

        self.viewport_changed.emit()

    def mousePressEvent(self, event):

        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()

            self.setCursor(
                Qt.ClosedHandCursor
            )

            event.accept()
            return

        super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            # Snapshot positions of whatever ended up selected, so
            # mouseReleaseEvent can tell whether a whole-item drag
            # happened (vs. a resize/connection handle, which is a
            # child item and doesn't change the parent's own .pos()).
            self._drag_positions = {
                item: item.pos()
                for item in self.scene().selectedItems()
            }

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(self.mapToScene(event.pos()))

        if self._panning:
            delta = (
                event.pos()
                - self._pan_start
            )

            self._pan_start = event.pos()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value()
                - delta.x()
            )

            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value()
                - delta.y()
            )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.mouse_left.emit()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Deferred rather than emitted synchronously here: this runs
        # in the middle of Qt's own resize/scrollbar-recalculation
        # handling, and immediately triggering ruler repaints (which
        # call back into this view's mapToScene/viewport geometry)
        # from inside that is asking for trouble. Posting it for the
        # next event-loop turn lets the resize finish first.
        QTimer.singleShot(0, self.viewport_changed.emit)

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.MiddleButton:
            self._panning = False

            self.setCursor(
                Qt.ArrowCursor
            )

            event.accept()
            return

        super().mouseReleaseEvent(event)

        if self._drag_positions:
            undo_stack = self.scene().undo_stack

            for item, old_pos in self._drag_positions.items():
                if item.scene() is not None and item.pos() != old_pos:
                    undo_stack.push(
                        MoveItemCommand(item, old_pos, item.pos(), "Move")
                    )

            self._drag_positions = None

    def keyPressEvent(self, event):
        key = event.key()

        # A focused item means we're mid-edit (e.g. typing into a
        # TextItem) - in that case Delete/Backspace/Escape must reach
        # the item itself, not be hijacked as diagram-level shortcuts.
        editing = self.scene().focusItem() is not None

        if key in (Qt.Key_Delete, Qt.Key_Backspace) and not editing:
            self.delete_selected_items()
            event.accept()
            return

        if key == Qt.Key_Escape:
            if editing:
                self.scene().focusItem().clearFocus()
            else:
                self.escape_pressed.emit()

            event.accept()
            return

        if key == Qt.Key_Space and not editing:
            self.space_pressed.emit()
            event.accept()
            return

        # App addition (not in the manual): arrow keys nudge the
        # current selection. The base step is in scene units at 100%
        # zoom; dividing by the current zoom factor keeps the ON-
        # SCREEN nudge visually consistent regardless of how zoomed in
        # or out the view is (zoomed in => fewer scene units per
        # screen pixel => a smaller scene-unit step for the same
        # apparent movement).
        if key in self.ARROW_KEY_DIRECTIONS and not editing:
            direction = self.ARROW_KEY_DIRECTIONS[key]
            shift_held = bool(event.modifiers() & Qt.ShiftModifier)
            self.nudge_selected_items(direction, shift_held)
            event.accept()
            return

        super().keyPressEvent(event)

    def nudge_selected_items(self, direction, shift_held):
        items = self.scene().selectedItems()

        if not items:
            return

        amount = self.BASE_NUDGE_STEP / max(self._zoom, 0.01)

        if shift_held:
            amount *= 10

        delta = QPointF(direction[0] * amount, direction[1] * amount)

        changed = [
            (item, QPointF(item.pos()), item.pos() + delta)
            for item in items
        ]

        if not changed:
            return

        undo_stack = self.scene().undo_stack
        undo_stack.beginMacro("Move")

        for item, old_pos, new_pos in changed:
            undo_stack.push(MoveItemCommand(item, old_pos, new_pos, "Move"))

        undo_stack.endMacro()

    def delete_selected_items(self):
        items = self.scene().selectedItems()

        if not items:
            return

        self.scene().undo_stack.push(
            DeleteItemsCommand(self.scene(), items, "Delete")
        )

    def reset_zoom(self):
        self.resetTransform()
        self._zoom = 1.0
        self.viewport_changed.emit()

    def set_zoom(self, factor):
        """
        Jump straight to an absolute zoom factor, e.g. from the View
        menu's fixed-percentage list (manual 3.5, Figure 3.6).
        """

        self.resetTransform()
        self.scale(factor, factor)
        self._zoom = factor
        self.viewport_changed.emit()

    def zoom_in(self):
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self):
        self.set_zoom(self._zoom / 1.25)