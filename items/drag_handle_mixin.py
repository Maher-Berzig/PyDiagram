# drag_handle_mixin.py
"""
Every small draggable handle in the app (resize handles, line
endpoints, arc bow, polygon/polyline/bezier vertices and control
points) is a QGraphicsItem with ItemIsMovable but NOT ItemIsSelectable,
parented to the shape it belongs to.

Qt's *default* mouseMoveEvent for a movable item has a documented
quirk: if the item's PARENT is selected (which, for these handles, it
normally is - that's exactly when they're visible/grabbable), Qt
moves the selected PARENT instead of the child that was actually
clicked and grabbed. The result: dragging a single point translates
the whole shape, and the point itself never moves. This is
straightforward to confirm with a bare QGraphicsScene/QGraphicsItem
reproduction with no app code involved at all - it's Qt's behavior,
not a bug in any one handle class here.

The fix is to stop relying on ItemIsMovable's built-in dragging for
handles entirely and drive their position ourselves from raw mouse
events, computing the delta in the parent's coordinate system so it
still behaves correctly regardless of the parent's own transform.
"""


class DraggableHandleMixin:

    def mousePressEvent(self, event):
        self._press_scene_pos = event.scenePos()
        self._press_item_pos = self.pos()

        event.accept()

    def mouseMoveEvent(self, event):
        parent = self.parentItem()

        if parent is not None:
            new_local = parent.mapFromScene(event.scenePos())
            press_local = parent.mapFromScene(self._press_scene_pos)
        else:
            new_local = event.scenePos()
            press_local = self._press_scene_pos

        self.setPos(self._press_item_pos + (new_local - press_local))

        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()
