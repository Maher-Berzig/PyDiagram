from PyQt5.QtCore import QLineF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QUndoStack

from canvas.layers import LayerManager
from canvas.commands import (
    SwapZOrderCommand,
    MoveIntoGroupCommand,
    ExtractFromGroupCommand,
)
from items.color_picker import copy_color_value

# Kept as a module-level fallback (e.g. DiagramItem's snap-to-grid
# reads scene.grid_x_size/grid_y_size with this as its default) - the
# per-diagram values below are what Diagram -> Properties (manual 3.1,
# 9.1.5) actually edits.
GRID_SIZE = 20

# Standard ISO 216 paper sizes, portrait orientation, in millimetres.
# Scene units use the application's 96 dpi convention: 1 scene unit = 1/96 in.
PAPER_SIZES_MM = {
    **{f"A{i}": size for i, size in enumerate([
        (841, 1189), (594, 841), (420, 594), (297, 420), (210, 297),
        (148, 210), (105, 148), (74, 105), (52, 74), (37, 52), (26, 37)
    ])},
    **{f"B{i}": size for i, size in enumerate([
        (1000, 1414), (707, 1000), (500, 707), (353, 500), (250, 353),
        (176, 250), (125, 176), (88, 125), (62, 88), (44, 62), (31, 44)
    ])},
}
MM_TO_SCENE = 96.0 / 25.4


class DiagramScene(QGraphicsScene):

    GRID_SIZE = GRID_SIZE

    # Emitted by a drawing tool right after it finishes placing a
    # shape, so the app can switch back to the select tool - Dia's
    # documented default ("Reset tools after create", manual 9.1.1).
    tool_finished = pyqtSignal()

    # App addition (not in the manual): emitted after a Ctrl-drag
    # reorders or regroups something (see the mouse handlers below),
    # so MainWindow can refresh the Diagram Tree panel to match -
    # DiagramScene itself doesn't know that panel exists.
    structure_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSceneRect(QRectF(0, 0, 210 * MM_TO_SCENE, 297 * MM_TO_SCENE))

        self.current_tool = None
        self.undo_stack = QUndoStack(self)
        self.layer_manager = LayerManager(self)

        # App addition (not in the manual): the item currently being
        # Ctrl-dragged (see mousePressEvent/_ctrl_drag_target below),
        # and the scene-y at which the last up/down step was
        # triggered. None/None when no Ctrl-drag is in progress.
        self._ctrl_drag_item = None
        self._ctrl_drag_last_y = None

        # App addition (not in the manual): the screen position of the
        # Ctrl-press that started the current _ctrl_drag_item, so
        # mouseReleaseEvent below can tell a Ctrl+*click* (opens
        # Properties - see the comment there) from a Ctrl+*drag*
        # (reorder/regroup, unchanged). None when no Ctrl-drag is in
        # progress, same lifetime as _ctrl_drag_item.
        self._ctrl_click_start_screen_pos = None

        # Set true (briefly) by document_io.export_png/export_svg, so
        # the grid - a screen/editing aid, not part of the diagram
        # content - doesn't end up baked into exported images.
        self.export_mode = False

        # -- Canvas settings (manual Chapter 3 / Diagram -> Properties) --

        # 3.2 "Grid Lines": visibility, spacing (independent X/Y, per
        # 9.1.5), and color. "Dynamic grid" and "Hex grid" from the
        # real dialog aren't implemented - this clone's grid is always
        # drawn in fixed scene units.
        self.show_grid = True
        self.grid_x_size = GRID_SIZE
        self.grid_y_size = GRID_SIZE
        self.grid_color = QColor("#d3d3d3")

        # 3.2/3.6: snap-to-grid, toggled from the View menu or the
        # toggle button below the canvas (Figure 3.2).
        self.snap_to_grid = True

        # 3.6, "Snap To Objects": off by default, matching this app's
        # pre-existing tolerance-based connecting (see LineItem).
        self.snap_to_objects = False

        # 3.6/9.1.2, "Show Connection Points" / "Connection Points:
        # Visible".
        self.show_connection_points = True

        # 3.4, "Background Color": defaults to white, same as Dia.
        self.background_color = QColor("#ffffff")

        # Exportable page; shapes outside it remain editable but are clipped
        # by page-based exports.
        self.paper_format = "A4"
        self.paper_orientation = "portrait"
        self.custom_width_mm = 210.0
        self.custom_height_mm = 297.0

        # 4.1.7, "Default Color, Line Width, and Line Style": applied
        # to every newly-created object by DrawingTool subclasses (see
        # canvas/tools.py), not to anything already on the canvas.
        self.defaults = {
            "fill_color": QColor("#DCEBFF"),
            "border_color": QColor("#202020"),
            "line_width": 2,
            "line_style": "solid",
            "dash_length": 10.0,
            "start_arrow": "none",
            "end_arrow": "none",
        }

    def set_paper_settings(self, paper_format, orientation="portrait",
                           custom_width_mm=210.0, custom_height_mm=297.0):
        """Set paper format, orientation, and optional custom dimensions."""
        paper_format = str(paper_format)
        if paper_format.lower() in ("not defined", "best fit"):
            paper_format = "Best Fit"
        elif paper_format.lower() == "custom size":
            paper_format = "Custom Size"
        else:
            paper_format = paper_format.upper()

        if paper_format not in ("Best Fit", "Custom Size") and paper_format not in PAPER_SIZES_MM:
            paper_format = "A4"

        orientation = str(orientation).lower()
        if orientation not in ("portrait", "landscape"):
            orientation = "portrait"

        try:
            custom_width_mm = max(1.0, float(custom_width_mm))
            custom_height_mm = max(1.0, float(custom_height_mm))
        except (TypeError, ValueError):
            custom_width_mm, custom_height_mm = 210.0, 297.0

        self.paper_format = paper_format
        self.paper_orientation = orientation
        self.custom_width_mm = custom_width_mm
        self.custom_height_mm = custom_height_mm

        if paper_format == "Best Fit":
            # Keep a useful editable canvas until content exists. The export
            # rectangle itself follows the same content rectangle as Best Fit.
            self.setSceneRect(QRectF(0, 0, 100, 100))
            return

        if paper_format == "Custom Size":
            width_mm, height_mm = custom_width_mm, custom_height_mm
        else:
            width_mm, height_mm = PAPER_SIZES_MM[paper_format]

        if orientation == "landscape":
            width_mm, height_mm = height_mm, width_mm

        self.setSceneRect(
            QRectF(0, 0, width_mm * MM_TO_SCENE, height_mm * MM_TO_SCENE)
        )

    def set_paper_format(self, paper_format):
        """Backward-compatible paper-format setter."""
        self.set_paper_settings(
            paper_format,
            getattr(self, "paper_orientation", "portrait"),
            getattr(self, "custom_width_mm", 210.0),
            getattr(self, "custom_height_mm", 297.0),
        )

    def content_rect(self, margin=20):
        """Return the content/export rectangle used by Best Fit."""
        from items.diagram_item import DiagramItem

        shapes = [i for i in self.items() if isinstance(i, DiagramItem)]
        if not shapes:
            return QRectF(0, 0, 100, 100)

        rect = None
        for item in shapes:
            item_rect = item.mapRectToScene(item.boundingRect())
            rect = item_rect if rect is None else rect.united(item_rect)

        return rect.adjusted(-margin, -margin, margin, margin)

    def paper_rect(self):
        """Return the current exportable rectangle in scene units."""
        if getattr(self, "paper_format", "A4") == "Best Fit":
            return self.content_rect()
        return self.sceneRect()

    def apply_defaults(self, item):
        """
        Stamps the current Toolbox defaults onto a freshly-created
        item, attribute by attribute (via hasattr, since not every
        item type has every attribute - Text has none of these, Line
        has pen_color/pen_width instead of fill/border).
        """

        d = self.defaults

        if hasattr(item, "fill_color"):
            item.fill_color = copy_color_value(d["fill_color"])

        if hasattr(item, "border_color"):
            item.border_color = copy_color_value(d["border_color"])

        if hasattr(item, "border_width"):
            item.border_width = d["line_width"]

        if hasattr(item, "pen_color"):
            item.pen_color = copy_color_value(d["border_color"])

        if hasattr(item, "pen_width"):
            item.pen_width = d["line_width"]

        if hasattr(item, "line_style"):
            item.line_style = d["line_style"]

        if hasattr(item, "dash_length"):
            item.dash_length = d["dash_length"]

        if hasattr(item, "start_arrow"):
            item.start_arrow = d["start_arrow"]

        if hasattr(item, "end_arrow"):
            item.end_arrow = d["end_arrow"]

    def reset_canvas_settings(self):
        """
        Restores the per-diagram canvas settings (manual 3.1-3.4) to
        their factory defaults - used by "New Document", so a fresh
        diagram doesn't inherit grid/background changes made to
        whatever was open before it.
        """

        self.show_grid = True
        self.grid_x_size = GRID_SIZE
        self.grid_y_size = GRID_SIZE
        self.grid_color = QColor("#d3d3d3")
        self.snap_to_grid = True
        self.snap_to_objects = False
        self.show_connection_points = True
        self.background_color = QColor("#ffffff")
        self.paper_format = "A4"
        self.paper_orientation = "portrait"
        self.custom_width_mm = 210.0
        self.custom_height_mm = 297.0
        self.set_paper_settings("A4", "portrait", 210.0, 297.0)

    def drawBackground(self, painter, rect):
        """
        Paint the background color and grid procedurally instead of as
        real QGraphicsItems.

        Two reasons:
        - scene.clear() (used by "New Document") removes every item in
          the scene; if the grid were made of items, clearing the
          document would wipe the grid along with it.
        - hundreds of QGraphicsLineItem objects just for a background
          grid is wasted overhead once diagrams get large - painting
          only the currently-visible `rect` costs nothing extra.
        """

        painter.fillRect(rect, self.background_color)

        if self.export_mode or not self.show_grid:
            return

        pen = QPen(self.grid_color)
        pen.setWidth(0)
        painter.setPen(pen)

        grid_x = self.grid_x_size
        grid_y = self.grid_y_size

        left = int(rect.left()) - (int(rect.left()) % grid_x)
        top = int(rect.top()) - (int(rect.top()) % grid_y)

        x = left
        while x < rect.right():
            painter.drawLine(
                QLineF(x, rect.top(), x, rect.bottom())
            )
            x += grid_x

        y = top
        while y < rect.bottom():
            painter.drawLine(
                QLineF(rect.left(), y, rect.right(), y)
            )
            y += grid_y

    def drawForeground(self, painter, rect):
        """
        Final overlay pass, after every item has painted - the only
        reliable place to draw a GroupItem's own connection points
        (see _paint_group_connection_points()).
        """

        super().drawForeground(painter, rect)
        self._paint_group_connection_points(painter)
        self._paint_anchor_preview(painter)
        self._paint_paper_boundary(painter)

    def _paint_paper_boundary(self, painter):
        """Draw the non-exported editing aid showing the page boundary."""
        if self.export_mode or getattr(self, "paper_format", "A4") == "Best Fit":
            return

        paper = self.paper_rect()
        if not paper.isValid():
            return

        painter.save()
        pen = QPen(QColor("#e02020"), 0, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(paper)
        painter.restore()

    def _paint_group_connection_points(self, painter):
        """
        App addition (not in the manual): draws each GroupItem's
        user-placed connection points (Anchor tool - see
        DiagramItem.add_custom_connection_point()), in scene
        coordinates, directly on the scene's foreground overlay.

        A GroupItem can't draw these reliably in its own paint(): Qt
        always paints an item's children after (and therefore visually
        on top of) the item itself, with no per-item way to reverse
        that for one specific child, so a mark drawn in the group's
        own paint() would sit underneath the very child shape it was
        added onto. An ordinary (non-group) shape has no such problem
        - it draws its own fill/border and its connection points in
        the same paint() call, in the right order - so this is only
        needed for groups; see DiagramItem._paint_connection_points()
        for everything else.
        """

        if self.export_mode or not self.show_connection_points:
            return

        from items.diagram_item import draw_connection_marker
        from items.group_item import GroupItem

        for item in self.items():
            if not isinstance(item, GroupItem) or item.isSelected():
                continue

            for point in item._custom_connection_points:
                draw_connection_marker(painter, item.mapToScene(point))

    def _paint_anchor_preview(self, painter):
        """
        App addition (not in the manual): while the Anchor tool
        (canvas/tools.py: AnchorTool) is active, draws a live "x"
        preview at the exact scene position of the mouse cursor - the
        same mark a click would leave behind (draw_connection_marker(),
        reused here so the preview and the permanent result look
        identical). `hover_pos` is read with getattr() rather than an
        isinstance check against AnchorTool, the same duck-typed
        pattern as DiagramItem._paint_connection_points()'s
        reveals_connection_points - only AnchorTool happens to set it,
        so its mere presence is enough. Skipped during PNG/SVG export
        for the same reason the marks themselves are: an editing aid,
        not diagram content.
        """

        if self.export_mode:
            return

        hover_pos = getattr(self.current_tool, "hover_pos", None)

        if hover_pos is not None:
            from items.diagram_item import draw_connection_marker

            draw_connection_marker(painter, hover_pos)

    def clear_hover_preview(self):
        """
        Clears the Anchor tool's live cursor preview above when the
        mouse leaves the view entirely (DiagramView.mouse_left) -
        without this, the last preview position drawn just inside the
        edge would be left stuck on screen, since no further
        mouse_move() would come in to update or clear it.
        """

        tool = self.current_tool

        if getattr(tool, "hover_pos", None) is not None:
            tool.hover_pos = None
            self.update()

    def set_tool(self, tool):
        if self.current_tool:
            self.current_tool.cancel()

        self.current_tool = tool

    def mousePressEvent(self, event):
        if (
            self.current_tool is None
            and event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        ):
            item = self._ctrl_drag_target(event.scenePos())

            if item is not None:
                self._ctrl_drag_item = item
                self._ctrl_drag_last_y = event.scenePos().y()
                self._ctrl_click_start_screen_pos = event.screenPos()
                event.accept()
                return

        if self.current_tool:
            self.current_tool.mouse_press(
                event.scenePos()
            )

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._ctrl_drag_item is not None:
            self._ctrl_drag_step(event.scenePos())
            event.accept()
            return

        if self.current_tool:
            self.current_tool.mouse_move(
                event.scenePos()
            )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._ctrl_drag_item is not None:
            item = self._ctrl_drag_item
            start_screen_pos = self._ctrl_click_start_screen_pos
            self._ctrl_drag_item = None
            self._ctrl_drag_last_y = None
            self._ctrl_click_start_screen_pos = None

            # App addition (not in the manual): a Ctrl+click - press
            # and release without moving past the platform's normal
            # click/drag threshold - opens item's Properties dialog,
            # replacing double-click for that job everywhere except
            # Text (see each shape's own now-removed
            # mouseDoubleClickEvent override, and TextItem's, which
            # keeps double-click for entering edit mode instead).
            # Double-click was too easy to trigger by accident while
            # trying to drag a shape a short distance, popping the
            # dialog open mid-move; requiring Ctrl rules out any
            # ordinary click/drag doing that, and checking the actual
            # release distance here (rather than treating every
            # Ctrl+click as a drag) is what keeps a real Ctrl-drag
            # (reorder/regroup, below) working exactly as before.
            moved = (
                start_screen_pos is None
                or (
                    (event.screenPos() - start_screen_pos).manhattanLength()
                    > QApplication.startDragDistance()
                )
            )

            if moved:
                self._ctrl_drag_finish(item, event.scenePos())
            else:
                from items.property_dialog import open_shape_properties
                open_shape_properties(item, self)

            event.accept()
            return

        if self.current_tool:
            self.current_tool.mouse_release(
                event.scenePos()
            )

            event.accept()
            return

        super().mouseReleaseEvent(event)

    # -- Ctrl-drag: reorder/regroup with the mouse (app addition, not
    # in the manual); Ctrl-click (no real movement): open Properties,
    # see mouseReleaseEvent above ---------------------------------------
    #
    # Holding Ctrl while dragging a shape doesn't move it - it's a
    # mouse-driven version of the Diagram Tree's Ctrl+Up/Down (see
    # MainWindow._diagram_tree_move_selected): vertical drag distance
    # steps the item up/down through whichever sibling list it
    # currently belongs to (the whole top-level stack, or - if it's
    # one of a group's children - just that group's own children),
    # one step per _ctrl_drag_step_size() pixels, exactly like
    # repeated presses of Ctrl+Up/Down would. Releasing the drag over
    # a *different* group's area integrates the item into that group
    # (MoveIntoGroupCommand); releasing it somewhere that isn't its
    # *current* parent group's area pulls it back out to the top
    # level instead (ExtractFromGroupCommand). All three go through
    # the undo stack, same as their keyboard/menu equivalents.

    def _ctrl_drag_target(self, scene_pos):
        """
        The topmost real shape at `scene_pos`, or None. Resize
        handles don't count - Ctrl-dragging a handle should still
        resize the shape, not reorder/regroup it.
        """

        from items.resize_handle import ResizeHandle
        from items.diagram_item import DiagramItem

        for candidate in self.items(scene_pos):
            if isinstance(candidate, ResizeHandle):
                continue

            if isinstance(candidate, DiagramItem):
                return candidate

        return None

    def _ctrl_drag_step_size(self):
        # Reuses the diagram's own grid spacing as the "how far is one
        # step" distance, so a finer/coarser grid also makes Ctrl-drag
        # reordering finer/coarser - floored so a very small grid
        # doesn't make every pixel of movement trigger a swap.
        return max(self.grid_y_size, 8)

    def _sibling_list(self, item):
        """
        The z-ordered (front-first) list `item` currently belongs to:
        the whole diagram's top-level items, or - if it's nested
        under a group - just that group's children. Same rule
        MainWindow._diagram_tree_siblings applies from the tree side,
        just keyed directly off item.parentItem() instead of a
        QTreeWidgetItem.
        """

        parent = item.parentItem()

        if parent is not None:
            return sorted(
                parent._children,
                key=lambda c: self.layer_manager.local_z(c),
                reverse=True,
            )

        from items.diagram_item import DiagramItem

        top_level = [
            i for i in self.items()
            if isinstance(i, DiagramItem) and i.parentItem() is None
        ]

        top_level_set = set(top_level)
        return [i for i in self.items() if i in top_level_set]

    def _ctrl_drag_step(self, scene_pos):
        step = self._ctrl_drag_step_size()
        dy = scene_pos.y() - self._ctrl_drag_last_y

        if abs(dy) < step:
            return

        item = self._ctrl_drag_item
        move_up = dy < 0

        siblings = self._sibling_list(item)

        try:
            index = siblings.index(item)
        except ValueError:
            self._ctrl_drag_last_y = scene_pos.y()
            return

        neighbor_index = index - 1 if move_up else index + 1

        if 0 <= neighbor_index < len(siblings):
            self.undo_stack.push(
                SwapZOrderCommand(
                    self.layer_manager, siblings, index, neighbor_index, "Reorder"
                )
            )

            self.structure_changed.emit()

        # Consumed this step's worth of movement either way (even if
        # already at the front/back), so continuing to drag doesn't
        # instantly re-trigger the moment it crosses back.
        self._ctrl_drag_last_y = scene_pos.y()

    def _ctrl_drag_finish(self, item, scene_pos):
        """
        On release: reparents `item` if the drag crossed a group
        boundary (see the docstring above _ctrl_drag_target for the
        two directions this covers). No-op if the release point is
        still within whatever group `item` already belongs to (or
        still outside any group, for a top-level item) - the drag was
        then purely a reordering gesture, already applied step by
        step in _ctrl_drag_step.
        """

        from items.group_item import GroupItem

        current_parent = item.parentItem()
        hit_item = self._ctrl_drag_target(scene_pos)

        if hit_item is None:
            hit_group = None
        elif hit_item is item:
            # Released back over itself (the common case for a
            # reorder-only drag, since the item never actually moves)
            # - that's still "inside" whatever it already belongs to.
            hit_group = current_parent
        elif isinstance(hit_item, GroupItem):
            hit_group = hit_item
        else:
            hit_group = hit_item.parentItem()

        # Never let an item (a group, in practice) become its own
        # parent, or a descendant of itself - either would corrupt
        # the scene's item tree.
        if hit_group is not None and self._is_or_descends_from(hit_group, item):
            hit_group = current_parent

        if hit_group is not None and hit_group is not current_parent:
            self.undo_stack.push(
                MoveIntoGroupCommand(self, item, hit_group, "Move Into Group")
            )
            self.structure_changed.emit()
        elif current_parent is not None and hit_group is not current_parent:
            self.undo_stack.push(
                ExtractFromGroupCommand(self, item, "Extract From Group")
            )
            self.structure_changed.emit()

    @staticmethod
    def _is_or_descends_from(candidate, ancestor):
        node = candidate

        while node is not None:
            if node is ancestor:
                return True

            node = node.parentItem()

        return False