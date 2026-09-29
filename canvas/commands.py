# commands.py
"""
Undo/redo commands (Dia manual 3.7: "Dia supports Undo and Redo on
most operations"). Kept deliberately simple:

- AddItemCommand / DeleteItemsCommand assume the item is either fully
  in the scene or fully out of it, and are idempotent about it (redo
  checks item.scene() is None before adding, so pushing a command for
  an item that's already on the canvas - e.g. a shape mid-drag-preview -
  doesn't double-add it).
- Deleting an item detaches any line connections touching it (see
  items/diagram_item.py / items/line_item.py). Undoing a delete brings
  the item itself back, but previously-attached lines stay detached -
  a deliberate simplification rather than trying to replay connection
  history.
"""

from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtWidgets import QUndoCommand


def _pos_for_target_point(item, target_point):
    """
    Back-computes the pos() to give `item` so it ends up sitting at
    target_point - a point in whatever coordinate system the item is
    about to belong to: scene coordinates for a top-level item, or a
    group's local coordinates for one of its children.

    item.mapToParent(0, 0) - where the item's own local origin lands
    in that outer coordinate system - is item.pos() + item.transform()
    .map(0, 0), not pos() alone: DiagramItem's rotation/flip transform
    (_update_transform()) is centered on the item's own bounding-rect
    center, not its local origin, so it shifts where (0, 0) maps to
    unless that center already *is* (0, 0). Every reparent below
    captures target_point from scenePos()/mapFromScene() - the item's
    already fully-transformed position - so restoring it means
    solving that same equation for pos(), rather than assigning
    target_point to pos() directly, which would apply the rotation's
    offset a second time (or lose it, on the way out of a group) and
    scatter any rotated item away from where it actually belongs.
    """

    return target_point - item.transform().map(QPointF(0, 0))



def _detach(item):
    disconnect = getattr(item, "disconnect_all_lines", None)
    if disconnect:
        disconnect()

    detach = getattr(item, "detach", None)
    if detach:
        detach()


class AddItemCommand(QUndoCommand):

    def __init__(self, scene, item, text="Create"):
        super().__init__(text)
        self.scene = scene
        self.item = item

    def redo(self):
        if self.item.scene() is None:
            self.scene.addItem(self.item)

    def undo(self):
        _detach(self.item)

        if self.item.scene() is not None:
            self.scene.removeItem(self.item)


class DeleteItemsCommand(QUndoCommand):

    def __init__(self, scene, items, text="Delete"):
        super().__init__(text)
        self.scene = scene
        self.items = list(items)

    def redo(self):
        for item in self.items:
            _detach(item)

            if item.scene() is not None:
                self.scene.removeItem(item)

    def undo(self):
        for item in self.items:
            if item.scene() is None:
                self.scene.addItem(item)


class MoveItemCommand(QUndoCommand):

    def __init__(self, item, old_pos, new_pos, text="Move"):
        super().__init__(text)
        self.item = item
        self.old_pos = type(old_pos)(old_pos)
        self.new_pos = type(new_pos)(new_pos)

    def _set_pos_exact(self, pos):
        """
        old_pos/new_pos are already-finalized positions (e.g. wherever
        a completed drag ended up, snapped or not) at the moment this
        command is created - redo()/undo() must reproduce that exact
        position every time they run, not re-round it against whatever
        scene.snap_to_grid happens to be set to right now. Without
        this, DiagramItem.itemChange's own grid-rounding (manual 3.2)
        can silently swallow a redo/undo back to the wrong spot -
        most visibly for Move commands smaller than the grid spacing,
        like a single arrow-key nudge.
        """

        scene = self.item.scene()
        previous = getattr(scene, "snap_to_grid", False) if scene else False

        if scene is not None:
            scene.snap_to_grid = False

        try:
            self.item.setPos(pos)
        finally:
            if scene is not None:
                scene.snap_to_grid = previous

    def redo(self):
        self._set_pos_exact(self.new_pos)

    def undo(self):
        self._set_pos_exact(self.old_pos)


class ResizeItemCommand(QUndoCommand):
    """
    Covers any item that keeps its geometry in a self._rect attribute
    (Rectangle, Ellipse, Text) - which is every resizable shape so far.
    The resize has usually already been applied live (the handle drags
    the shape as the mouse moves); redo()/undo() just re-assert one of
    the two end states, which is harmless to repeat.
    """

    def __init__(self, item, old_rect, new_rect, text="Resize"):
        super().__init__(text)
        self.item = item
        self.old_rect = QRectF(old_rect)
        self.new_rect = QRectF(new_rect)

    def _apply(self, rect):
        self.item.prepareGeometryChange()
        self.item._rect = QRectF(rect)

        relayout = getattr(self.item, "_layout_text_child", None)
        if relayout:
            relayout()

        self.item._update_handles()
        self.item.notify_connections()
        self.item.update()

    def redo(self):
        self._apply(self.new_rect)

    def undo(self):
        self._apply(self.old_rect)


class GroupItemsCommand(QUndoCommand):
    """
    Manual 4.2.8: "select two or more objects and then select
    Objects->Group." Reparents each child under the (already
    constructed, not-yet-added) GroupItem, and locks their individual
    selectable/movable flags so the group behaves as one object.

    Children are sorted by their current stacking order (back to
    front) before reparenting, and each is given a fresh sequential
    local_z among its new siblings - without this, Qt's tie-breaking
    for same-z siblings depends on the order they happened to be
    selected in, not the order they were actually stacked in, so the
    frontmost object could silently end up buried in the group.

    redo()/undo() are self-contained - each one fully reasserts either
    the grouped or ungrouped state from self.children, rather than
    depending on whatever state a previous call left things in - so
    repeated undo/redo cycles can't drift.
    """

    def __init__(self, scene, group, children, text="Group"):
        super().__init__(text)
        self.scene = scene
        self.group = group

        # scene.items() is Qt's own authoritative front-to-back
        # render order, correctly resolving ties for items that share
        # the exact same zValue() (the common case for freshly
        # created shapes, which all default to local_z=0.0) - sorting
        # by zValue() directly can't distinguish those, so it would
        # silently scramble the relative order of any same-z items
        # being grouped.
        children_set = set(children)
        front_to_back = [c for c in scene.items() if c in children_set]
        self.children = list(reversed(front_to_back))

        layer_manager = getattr(scene, "layer_manager", None)
        self.original_local_z = (
            [layer_manager.local_z(c) for c in self.children]
            if layer_manager is not None else [0.0] * len(self.children)
        )

    def redo(self):
        if self.group.scene() is None:
            self.scene.addItem(self.group)

        layer_manager = getattr(self.scene, "layer_manager", None)

        for index, child in enumerate(self.children):
            child.setSelected(False)
            child.setParentItem(self.group)
            child.setFlag(child.ItemIsSelectable, False)
            child.setFlag(child.ItemIsMovable, False)

            if layer_manager is not None and hasattr(child, "layer"):
                layer_manager.set_local_z(child, index)

        self.group._children = list(self.children)
        self.group.prepareGeometryChange()
        self.group.update()

    def undo(self):
        layer_manager = getattr(self.scene, "layer_manager", None)

        for child, old_z in zip(self.children, self.original_local_z):
            scene_pos = child.scenePos()
            child.setParentItem(None)
            child.setPos(_pos_for_target_point(child, scene_pos))
            child.setFlag(child.ItemIsSelectable, True)
            child.setFlag(child.ItemIsMovable, True)

            if layer_manager is not None and hasattr(child, "layer"):
                layer_manager.set_local_z(child, old_z)

        self.group._children = []

        if self.group.scene() is not None:
            self.scene.removeItem(self.group)


class UngroupItemsCommand(QUndoCommand):
    """
    The mirror image of GroupItemsCommand - captures the group's
    current children up front, since redo() clears that list.
    """

    def __init__(self, scene, group, text="Ungroup"):
        super().__init__(text)
        self.scene = scene
        self.group = group
        self.children = list(group._children)

    def redo(self):
        for child in self.children:
            scene_pos = child.scenePos()
            child.setParentItem(None)
            child.setPos(_pos_for_target_point(child, scene_pos))
            child.setFlag(child.ItemIsSelectable, True)
            child.setFlag(child.ItemIsMovable, True)
            child.setSelected(True)

        self.group._children = []

        if self.group.scene() is not None:
            self.scene.removeItem(self.group)

    def undo(self):
        if self.group.scene() is None:
            self.scene.addItem(self.group)

        for child in self.children:
            scene_pos = child.scenePos()
            child.setSelected(False)
            child.setParentItem(self.group)
            child.setPos(
                _pos_for_target_point(child, self.group.mapFromScene(scene_pos))
            )
            child.setFlag(child.ItemIsSelectable, False)
            child.setFlag(child.ItemIsMovable, False)

        self.group._children = list(self.children)
        self.group.setSelected(True)


class MoveIntoGroupCommand(QUndoCommand):
    """
    App addition (not in the manual): Ctrl-dragging an item onto a
    group on the canvas (see DiagramScene's Ctrl-drag handling)
    integrates it into that group - whether it was a free top-level
    item before, or already a child of a *different* group (dragged
    straight from one group into another in a single gesture).

    Mirrors GroupItemsCommand's own child-reparenting (lock
    selectable/movable, park at the front of the new group's stack)
    but for exactly one item joining an *already-existing* group,
    and - unlike GroupItemsCommand's redo(), which can assume a
    freshly-made group still sits at (0, 0) - explicitly remaps
    through scenePos() so the item doesn't visually jump if the
    target group has since been moved, rotated, or flipped.
    """

    def __init__(self, scene, item, group, text="Move Into Group"):
        super().__init__(text)
        self.scene = scene
        self.item = item
        self.group = group
        self.old_parent = item.parentItem()

        layer_manager = getattr(scene, "layer_manager", None)
        self.layer_manager = layer_manager

        self.old_z = layer_manager.local_z(item) if layer_manager is not None else 0.0
        self.old_selectable = bool(item.flags() & item.ItemIsSelectable)
        self.old_movable = bool(item.flags() & item.ItemIsMovable)

        self.new_z = (
            max(
                (layer_manager.local_z(c) for c in group._children),
                default=0.0,
            ) + 1
            if layer_manager is not None else 0.0
        )

    def redo(self):
        item, group = self.item, self.group

        scene_pos = item.scenePos()
        item.setParentItem(group)
        item.setPos(_pos_for_target_point(item, group.mapFromScene(scene_pos)))
        item.setFlag(item.ItemIsSelectable, False)
        item.setFlag(item.ItemIsMovable, False)

        if self.layer_manager is not None:
            self.layer_manager.set_local_z(item, self.new_z)

        if self.old_parent is not None:
            self.old_parent._children.remove(item)
            self.old_parent.prepareGeometryChange()
            self.old_parent.update()

        group._children.append(item)
        group.prepareGeometryChange()
        group.update()

    def undo(self):
        item, group = self.item, self.group

        scene_pos = item.scenePos()
        item.setParentItem(self.old_parent)
        item.setPos(
            _pos_for_target_point(
                item, self.old_parent.mapFromScene(scene_pos)
            )
            if self.old_parent is not None
            else _pos_for_target_point(item, scene_pos)
        )
        item.setFlag(item.ItemIsSelectable, self.old_selectable)
        item.setFlag(item.ItemIsMovable, self.old_movable)

        if self.layer_manager is not None:
            self.layer_manager.set_local_z(item, self.old_z)

        group._children.remove(item)
        group.prepareGeometryChange()
        group.update()

        if self.old_parent is not None:
            self.old_parent._children.append(item)
            self.old_parent.prepareGeometryChange()
            self.old_parent.update()


class ExtractFromGroupCommand(QUndoCommand):
    """
    App addition (not in the manual): the mirror image of
    MoveIntoGroupCommand - Ctrl-dragging a group's child out past
    that group's own area pulls it back out to the top level, same
    reparent-via-scenePos() dance as UngroupItemsCommand but for one
    child at a time rather than the whole group at once, and the
    group itself is left in place (with its remaining children)
    rather than being dissolved.
    """

    def __init__(self, scene, item, text="Extract From Group"):
        super().__init__(text)
        self.scene = scene
        self.item = item
        self.old_parent = item.parentItem()

        layer_manager = getattr(scene, "layer_manager", None)
        self.layer_manager = layer_manager
        self.old_z = layer_manager.local_z(item) if layer_manager is not None else 0.0

        top_level = [i for i in scene.items() if i.parentItem() is None]
        self.new_z = (
            max(
                (layer_manager.local_z(i) for i in top_level),
                default=0.0,
            ) + 1
            if layer_manager is not None else 0.0
        )

    def redo(self):
        item, old_parent = self.item, self.old_parent

        scene_pos = item.scenePos()
        item.setParentItem(None)
        item.setPos(_pos_for_target_point(item, scene_pos))
        item.setFlag(item.ItemIsSelectable, True)
        item.setFlag(item.ItemIsMovable, True)

        if self.layer_manager is not None:
            self.layer_manager.set_local_z(item, self.new_z)

        old_parent._children.remove(item)
        old_parent.prepareGeometryChange()
        old_parent.update()

    def undo(self):
        item, old_parent = self.item, self.old_parent

        scene_pos = item.scenePos()
        item.setParentItem(old_parent)
        item.setPos(
            _pos_for_target_point(item, old_parent.mapFromScene(scene_pos))
        )
        item.setFlag(item.ItemIsSelectable, False)
        item.setFlag(item.ItemIsMovable, False)

        if self.layer_manager is not None:
            self.layer_manager.set_local_z(item, self.old_z)

        old_parent._children.append(item)
        old_parent.prepareGeometryChange()
        old_parent.update()


class ChangePropertiesCommand(QUndoCommand):
    """
    Manual 4.3: editing a shape's color/line-width/etc. through its
    Properties dialog. old_props/new_props are {attribute_name: value}
    dicts - generic enough to cover Rectangle/Ellipse (fill_color,
    border_color, border_width) and Line (pen_color, pen_width) alike.
    """

    def __init__(self, item, old_props, new_props, text="Edit Properties"):
        super().__init__(text)
        self.item = item
        self.old_props = dict(old_props)
        self.new_props = dict(new_props)

    def _apply(self, props):
        for name, value in props.items():
            setattr(self.item, name, value)

        # Shapes with custom manipulation handles (e.g. Star/Spiral)
        # need those handles repositioned when a property changes.
        updater = getattr(self.item, "_update_handles", None)
        if callable(updater):
            updater()

        self.item.update()

    def redo(self):
        self._apply(self.new_props)

    def undo(self):
        self._apply(self.old_props)


class TransformSelectionCommand(QUndoCommand):
    """
    App addition (not in the manual): Objects -> Rotate/Flip, applied
    to a whole multi-item selection as one rigid group. Each item's
    position and its own rotation_angle/flip_horizontal/flip_vertical
    are captured before and after (see MainWindow._apply_group_rotation/
    _apply_group_flip), so the operation is a single undo step no
    matter how many items were selected - same shape of fix as
    ChangePropertiesCommand above, just across several items instead
    of several attributes on one.
    """

    def __init__(self, items, old_states, new_states, text):
        super().__init__(text)
        self.items = list(items)
        self.old_states = old_states
        self.new_states = new_states

    def _apply(self, states):
        for item, state in zip(self.items, states):
            item.setPos(state["pos"])
            item.rotation_angle = state["rotation_angle"]
            item.flip_horizontal = state["flip_h"]
            item.flip_vertical = state["flip_v"]
            item.scale_x = state.get("scale_x", item.scale_x)
            item.scale_y = state.get("scale_y", item.scale_y)
            item.update()

    def redo(self):
        self._apply(self.new_states)

    def undo(self):
        self._apply(self.old_states)


class RenameItemCommand(QUndoCommand):
    """
    App addition (not in the manual): the Diagram Tree's inline rename
    (F2 or right-click -> Rename - see MainWindow._diagram_tree_label/
    _on_diagram_tree_item_changed). Just old/new text on the item's
    own custom_name, same minimal shape as MoveItemCommand.
    """

    def __init__(self, item, old_name, new_name, text="Rename"):
        super().__init__(text)
        self.item = item
        self.old_name = old_name
        self.new_name = new_name

    def redo(self):
        self.item.custom_name = self.new_name

    def undo(self):
        self.item.custom_name = self.old_name


class SwapZOrderCommand(QUndoCommand):
    """
    App addition (not in the manual): swaps two sibling items'
    stacking order - "sibling" meaning either two top-level items (in
    the same or different layers) or two children of the same group.
    Used by the Diagram Tree's Ctrl+Up/Down reordering (see
    MainWindow._diagram_tree_move_selected). Swapping a GroupItem's
    own local_z this way moves the whole group, children included, as
    a single unit relative to its top-level siblings - it doesn't
    touch anything inside the group.

    `siblings` is the *entire* sibling list, front-most first (the
    same list _diagram_tree_move_selected already built), and
    index_a/index_b are the two adjacent positions to swap within it
    - not the two items directly. This is deliberate: freshly created
    shapes (and anything never touched by Send to Back/Bring to
    Front) all share the same default local_z of 0.0, with the
    on-screen order among ties coming from Qt's own insertion-order
    tie-break rather than local_z itself (see GroupItemsCommand's own
    note on this). Just swapping item_a's and item_b's raw local_z
    values - which is what this command used to do - is a no-op
    whenever those two values happen to be equal, so nothing visibly
    moves. Renumbering the whole sibling list with fresh, strictly
    descending values that match the swapped order sidesteps ties
    entirely: every item ends up with a distinct local_z reflecting
    its (possibly unchanged) position, so the swap always takes
    effect regardless of what the previous values were.
    """

    def __init__(self, layer_manager, siblings, index_a, index_b, text="Reorder"):
        super().__init__(text)
        self.layer_manager = layer_manager
        self.siblings = list(siblings)
        self.index_a = index_a
        self.index_b = index_b

        # Front-most item gets the highest value, matching the
        # convention used everywhere else (higher local_z == more in
        # front - see LayerManager._apply_item_z and
        # _refresh_diagram_tree's reverse=True sort).
        n = len(self.siblings)
        self.new_z = [float(n - 1 - position) for position in range(n)]

        self.original_z = [
            layer_manager.local_z(item) for item in self.siblings
        ]

    def _apply(self, order):
        for item, z in zip(order, self.new_z):
            self.layer_manager.set_local_z(item, z)

    def redo(self):
        swapped = list(self.siblings)
        swapped[self.index_a], swapped[self.index_b] = (
            swapped[self.index_b],
            swapped[self.index_a],
        )
        self._apply(swapped)

    def undo(self):
        for item, z in zip(self.siblings, self.original_z):
            self.layer_manager.set_local_z(item, z)


class AddConnectionPointCommand(QUndoCommand):
    """
    App addition (not in the manual): Anchor tool (canvas/tools.py:
    AnchorTool) - adds one user-placed connection point to an existing
    item, in addition to whatever fixed set its shape type already
    defines (see DiagramItem.add_custom_connection_point()/
    all_connection_points()).
    """

    def __init__(self, item, local_point, text="Add Connection Point"):
        super().__init__(text)
        self.item = item
        self.local_point = QPointF(local_point)

    def redo(self):
        self.item.add_custom_connection_point(self.local_point)

    def undo(self):
        self.item.remove_custom_connection_point(self.local_point)
