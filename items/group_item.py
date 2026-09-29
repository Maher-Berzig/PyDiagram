# group_item.py
"""
Manual 4.2.8: "Grouping allows you to treat several objects as a
single entity... When the group is created or subsequently selected,
a set of black handles displays around the outside of the group...
you can move the entire group just like you would move a single
object."

GroupItem itself doesn't do the reparenting/flag-locking - that's
handled by GroupItemsCommand/UngroupItemsCommand in canvas/commands.py,
so grouping and ungrouping both go through undo/redo cleanly. This
class just draws the group's outline and reports its combined bounds.
"""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem

from .diagram_item import DiagramItem


class GroupItem(DiagramItem):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._children = []

    def boundingRect(self):
        if not self._children:
            return QRectF()

        rect = None

        for child in self._children:
            child_rect = child.mapRectToParent(child.boundingRect())
            rect = child_rect if rect is None else rect.united(child_rect)

        margin = 6

        return rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter, option, widget=None):
        if not self._children:
            return

        if self.isSelected():
            painter.setPen(QPen(QColor("#202020"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)

            margin = 6
            painter.drawRect(self.boundingRect().adjusted(margin, margin, -margin, -margin))

        # App addition (not in the manual): a group can carry
        # user-placed connection points of its own (Anchor tool - see
        # DiagramItem.add_custom_connection_point()), but they're
        # deliberately NOT drawn here. Qt always paints an item's
        # children after (and therefore visually on top of) the item
        # itself, with no per-item way to reverse that for one
        # specific child - so a mark drawn here, sitting right on top
        # of a child shape (which is the whole point of adding one "on
        # the shape"), would just get immediately painted over by that
        # child. DiagramScene._paint_group_connection_points() draws
        # them instead, once every item has been painted, sidestepping
        # the ordering rule entirely.

    # A group is moved as a whole (children ride along automatically
    # since they're child items), never individually resized via
    # corner handles - so the usual four-handle machinery is switched
    # off, same as LineItem does for its own dedicated endpoint handles.
    def _create_handles(self):
        pass

    def _remove_handles(self):
        pass

    def _update_handles(self):
        pass

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Children ride along automatically (they're child items),
            # but only they get their own ItemPositionHasChanged
            # notification from Qt - each still needs telling
            # explicitly to update any line attached to it.
            for child in self._children:
                child.notify_connections()

            # App addition (not in the manual): the group itself can
            # now also carry connection points directly (Anchor tool -
            # see DiagramItem.add_custom_connection_point()), so a
            # line attached to one of *those* needs the same nudge -
            # this one Qt does deliver directly to self.
            self.notify_connections()

        return super().itemChange(change, value)
