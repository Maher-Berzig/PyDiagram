# diagram_item.py

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QFont, QPainter, QPen, QTransform
from PyQt5.QtWidgets import QGraphicsItem

from .resize_handle import ResizeHandle


def draw_connection_marker(painter, point, size=3):
    """
    Draws one "⨉" glyph centered on `point`, in whatever coordinate
    system `painter` is currently set up for - shared by
    DiagramItem._paint_connection_points() (an item's own fixed/custom
    points, painted in its own local coordinates),
    DiagramScene._paint_group_connection_points() (a GroupItem's
    custom points, painted in scene coordinates - see that method's
    docstring for why groups need special handling here), and
    DiagramScene's Anchor-tool live cursor preview (canvas/tools.py's
    AnchorTool + DiagramScene.drawForeground()).

    Painted with CompositionMode_Difference rather than a fixed color:
    each pixel drawn becomes the underlying color's difference from
    white, i.e. its inverse, so the mark stays visible against any
    fill color underneath it (including one close to the marker's old
    fixed blue) instead of risking blending into it. save()/restore()
    around the font/pen/drawText calls, since this is called in a
    loop over several points per paint() call and callers expect
    their own painter state (pen, font, composition mode) back
    afterward.
    """

    painter.save()

    painter.setCompositionMode(QPainter.CompositionMode_Difference)
    painter.setPen(QPen(Qt.white, 1))

    font = QFont()
    font.setPixelSize(max(size * 4, 8))
    font.setBold(True)
    painter.setFont(font)

    symbol_rect = painter.boundingRect(QRectF(0, 0, 0, 0), Qt.AlignCenter, "⨉")
    symbol_rect.moveCenter(point)

    painter.drawText(symbol_rect, Qt.AlignCenter, "⨉")

    painter.restore()


class DiagramItem(QGraphicsItem):

    HANDLE_SIZE = 8

    MIN_WIDTH = 20
    MIN_HEIGHT = 20

    def __init__(self, parent=None):
        super().__init__(parent)

        # Allow the item to be moved with the mouse
        self.setFlag(
            QGraphicsItem.ItemIsMovable,
            True
        )

        # Allow the item to be selected
        self.setFlag(
            QGraphicsItem.ItemIsSelectable,
            True
        )

        # Tell us when geometry/position changes
        self.setFlag(
            QGraphicsItem.ItemSendsGeometryChanges,
            True
        )

        self._handles = []

        # App addition (not in the manual): a user-given name shown
        # in the Diagram Tree (manual 4.5) in place of the usual
        # type-based label - see MainWindow._diagram_tree_label()/
        # _on_diagram_tree_item_changed(). None means "no custom name
        # set yet", i.e. fall back to the type-based label.
        self.custom_name = None

        # App addition (not in the manual): optional destination used
        # by the PDF exporter for an internal page link.  This stores
        # the target document's persistent ID, never its PDF page
        # number, so links remain correct when the user reorders pages
        # in the PDF export dialog.
        self.pdf_link_target = None

        # App addition (not in the manual): user-placed connection
        # points added via the Anchor tool (canvas/tools.py:
        # AnchorTool), on top of whatever fixed set connection_points()
        # already defines for this shape type - see
        # all_connection_points().
        self._custom_connection_points = []

        # (line_item, "p1"|"p2") pairs for every LineItem currently
        # snapped to one of this item's connection_points(). Kept so
        # that moving or resizing this item can pull those line
        # endpoints along with it (Dia manual 4.2.5).
        self._connected_lines = []

        # Rotation/flip (app additions - not in the manual) - backing
        # fields only; deliberately not set through their own property
        # setters here; see _update_transform()'s docstring for why.
        self._rotation_angle = 0.0
        self._flip_h = False
        self._flip_v = False
        self._scale_x = 1.0
        self._scale_y = 1.0

    # -- rotation & flip (app additions - not in the manual) -----------
    # Named rotation_angle/flip_horizontal/flip_vertical rather than
    # "rotation"/etc. so they don't shadow QGraphicsItem's own
    # rotation()/scale() methods. All three are Python properties
    # (not plain attributes) so that the generic Properties-dialog
    # machinery (ChangePropertiesCommand, which just does
    # setattr(item, name, value)) automatically pushes each change
    # through to the item's actual transform - see _update_transform().
    #
    # Implemented as one hand-built QTransform rather than Qt's own
    # rotation()/scale(), because scale() is a single uniform factor
    # and can't flip just one axis - a flip needs an independent
    # negative X or Y scale, which only a real transform matrix can
    # express alongside a rotation.

    @property
    def rotation_angle(self):
        return self._rotation_angle

    @rotation_angle.setter
    def rotation_angle(self, value):
        self._rotation_angle = value % 360
        self._update_transform()

    @property
    def flip_horizontal(self):
        return self._flip_h

    @flip_horizontal.setter
    def flip_horizontal(self, value):
        self._flip_h = bool(value)
        self._update_transform()

    @property
    def flip_vertical(self):
        return self._flip_v

    @flip_vertical.setter
    def flip_vertical(self, value):
        self._flip_v = bool(value)
        self._update_transform()

    # Scale (app addition): independent horizontal/vertical scale
    # factors (1.0 = 100%), applied in the item's own axes like flip,
    # so they work for every shape type. Range 1% - 1000%.
    SCALE_MIN = 0.01
    SCALE_MAX = 10.0

    @property
    def scale_x(self):
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value):
        self._scale_x = max(self.SCALE_MIN, min(self.SCALE_MAX, float(value)))
        self._update_transform()

    @property
    def scale_y(self):
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value):
        self._scale_y = max(self.SCALE_MIN, min(self.SCALE_MAX, float(value)))
        self._update_transform()

    def _update_transform(self):
        """
        Recomputes the whole rotation+flip transform from scratch and
        applies it, centered on the shape's own current bounding-rect
        center - re-centered on every call (not tracked continuously
        as the shape resizes/reshapes elsewhere), which is simple and
        correct for the normal case of setting these once in the
        Properties dialog or via Objects -> Rotate/Flip.
        """

        origin = self.boundingRect().center()

        transform = QTransform()
        transform.translate(origin.x(), origin.y())
        transform.rotate(self._rotation_angle)
        transform.scale(
            self._scale_x * (-1 if self._flip_h else 1),
            self._scale_y * (-1 if self._flip_v else 1),
        )
        transform.translate(-origin.x(), -origin.y())

        self.setTransform(transform)

    def connection_points(self):
        """
        Local-coordinate points other objects can snap a line to.
        Empty by default; shapes that support connections (Rectangle,
        Ellipse) override this. Matches the small "x" marks the Dia
        manual shows on an unselected shape's border and center.
        """

        return []

    def add_custom_connection_point(self, point):
        """
        App addition (not in the manual): adds one user-placed
        connection point (Anchor tool - canvas/tools.py: AnchorTool),
        at local coordinate `point`, on top of whatever fixed set
        connection_points() already returns for this shape type.
        """

        self._custom_connection_points.append(QPointF(point))
        self.update()

    def remove_custom_connection_point(self, point):
        """
        Removes the most recently added custom connection point equal
        to `point` - pairs with add_custom_connection_point() for
        AddConnectionPointCommand's undo. Removing the *last* matching
        occurrence (rather than the first) is what correctly undoes
        the most recent Anchor-tool click if the same exact position
        was ever clicked more than once.
        """

        points = self._custom_connection_points

        for i in range(len(points) - 1, -1, -1):
            if points[i] == point:
                del points[i]
                break

        self.update()

    def all_connection_points(self):
        """
        Every connection point a line can snap to on this item: the
        shape type's own fixed set (connection_points(), overridden
        per shape) plus any custom ones added via the Anchor tool -
        this is what LineItem's connection search and
        _paint_connection_points() below actually use, rather than
        connection_points() directly, so custom points behave exactly
        like built-in ones everywhere connections are made or drawn.
        """

        return list(self.connection_points()) + list(
            self._custom_connection_points
        )

    def register_connection(self, line, which):
        self._connected_lines.append((line, which))

    def unregister_connection(self, line, which):
        self._connected_lines = [
            pair for pair in self._connected_lines
            if pair != (line, which)
        ]

    def notify_connections(self):
        """
        Call after this item's position or shape changes so any line
        connected to it can follow (Dia manual 4.2.5: "If you move
        either object, the line will stretch to keep them connected").
        """

        for line, which in list(self._connected_lines):
            line.update_connection_endpoint(which)

    def disconnect_all_lines(self):
        """
        Called before this item is removed from the scene, so attached
        lines fall back to a plain unconnected (green) endpoint instead
        of holding a reference to a shape that's no longer there.
        """

        for line, which in list(self._connected_lines):
            line.clear_connection(which)

        self._connected_lines = []

    def _paint_connection_points(self, painter):
        """
        Draw small "x" marks (draw_connection_marker() above) at each
        connection point, but only while the shape is unselected -
        once selected, the resize handles take over that visual role
        (Dia manual 4.2.5). The one exception is the Anchor tool
        (canvas/tools.py: AnchorTool): it requires a shape to stay
        selected while it's active (so several points can be dropped
        in a row without reselecting), so without this exception a
        shape's existing points - and the exact spot a click will add
        the next one - would be invisible for the entire time the
        Anchor tool is actually in use. reveals_connection_points is
        checked with getattr() rather than an isinstance() import of
        AnchorTool, to avoid items/ importing back from canvas/.
        Also suppressed entirely during PNG/SVG export: these are an
        editing aid, not part of the diagram content.
        """

        scene = self.scene()

        if self.isSelected() and not getattr(
            getattr(scene, "current_tool", None),
            "reveals_connection_points", False
        ):
            return

        if scene is not None and getattr(scene, "export_mode", False):
            return

        if scene is not None and not getattr(
            scene, "show_connection_points", True
        ):
            return

        points = self.all_connection_points()

        if not points:
            return

        for p in points:
            draw_connection_marker(painter, p)

    def _create_handles(self):
        """
        Create the four resize handles.
        """

        if self._handles:
            return

        handles = [
            ("top_left", Qt.SizeFDiagCursor),
            ("top_right", Qt.SizeBDiagCursor),
            ("bottom_left", Qt.SizeBDiagCursor),
            ("bottom_right", Qt.SizeFDiagCursor),
        ]

        for name, cursor in handles:

            handle = ResizeHandle(
                self,
                cursor
            )

            handle.name = name

            self._handles.append(handle)

        self._update_handles()

    def _remove_handles(self):
        """
        Hide the resize handles (they stay parented to this item and
        are reused next time it's selected, instead of being rebuilt
        from scratch on every select/deselect).
        """

        for handle in self._handles:
            handle.hide()

    def _update_handles(self):
        """
        Position the four handles around the item.
        """

        if not self._handles:
            return

        rect = self.boundingRect()

        positions = {
            "top_left": rect.topLeft(),
            "top_right": rect.topRight(),
            "bottom_left": rect.bottomLeft(),
            "bottom_right": rect.bottomRight(),
        }

        for handle in self._handles:

            handle.setPos(
                positions[handle.name]
            )

            handle.show()

    def itemChange(self, change, value):

        if change == QGraphicsItem.ItemPositionChange:

            # Manual 3.2: "the snap-to-grid feature... When this is
            # enabled, objects are forced to align on a grid line."
            # Snapping the proposed position here (before it's applied)
            # makes dragging itself feel snapped, not just the final
            # drop - matching Dia's live behavior.
            scene = self.scene()

            if scene is not None and getattr(scene, "snap_to_grid", False):
                grid_x = getattr(scene, "grid_x_size", 20)
                grid_y = getattr(scene, "grid_y_size", 20)

                return QPointF(
                    round(value.x() / grid_x) * grid_x,
                    round(value.y() / grid_y) * grid_y,
                )

        elif change == QGraphicsItem.ItemPositionHasChanged:

            self._update_handles()
            self.notify_connections()

        elif change == QGraphicsItem.ItemSelectedHasChanged:

            if value:
                self._create_handles()
                self._update_handles()
            else:
                self._remove_handles()

            self.update()

        return super().itemChange(
            change,
            value
        )