from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF

from items.rectangle_item import RectangleItem
from items.ellipse_item import EllipseItem
from items.diamond_item import DiamondItem
from items.cylinder_item import CylinderItem
from items.actor_item import ActorItem
from items.interface_item import InterfaceItem
from items.class_item import ClassItem
from items.text_item import TextItem
from items.line_item import LineItem
from items.arc_item import ArcItem
from items.polygon_item import PolygonItem
from items.polyline_item import PolylineItem
from items.zigzagline_item import ZigzaglineItem
from items.image_item import ImageItem
from items.bezierline_item import BezierlineItem
from items.beziergon_item import BeziergonItem
from items.mask_item import MaskItem
from items.bezier_utils import default_node
from items.group_item import GroupItem
from items.plot_item import PlotItem
from items.assorted_item import (
    SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
    CrossItem, RegularPolygonItem, StarItem, SpiralItem, CircleSectionItem,
)
from items.stencil_items import (
    CrescentItem, SpringItem, LShapeItem,
    DataItem, PredefinedProcessItem, PreparationItem, DocumentItem,
    DelayItem, SummingJunctionItem, ArrowReferenceItem, PaperTapeItem,
    DataStorageItem,
    PackageItem, ComponentItem, NodeItem, NoteItem, LifelineItem,
    RequiredInterfaceItem, EnumerationItem, ArtifactItem, FrameItem,
)
from canvas.commands import AddItemCommand, AddConnectionPointCommand


class DrawingTool:
    def __init__(self, scene):
        self.scene = scene
        self.start = None
        self.preview_item = None

    def mouse_press(self, pos):
        self.start = pos

    def mouse_move(self, pos):
        pass

    def mouse_release(self, pos):
        pass

    def cancel(self):
        if self.preview_item:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None

        self.start = None

    def _finish(self, label):
        """
        Common wrap-up for a successfully-placed shape: register it
        with the undo stack (idempotent - the item is already in the
        scene from the live preview) and hand control back to the
        select tool, matching Dia's default "Reset tools after create"
        behavior (manual 4.1.1, 9.1.1).

        Clears self.preview_item/self.start *before* pushing the undo
        command or emitting the signal: tool_finished causes the app
        to call scene.set_tool(None), which calls cancel() on this
        same tool instance (it's still "current" until that call
        returns) - if preview_item were still set at that point,
        cancel() would remove the very item we just finished creating.
        """

        item = self.preview_item
        self.preview_item = None
        self.start = None

        self.scene.layer_manager.assign_to_current(item)

        self.scene.undo_stack.push(
            AddItemCommand(self.scene, item, label)
        )

        # Selected immediately on creation, not left for a follow-up
        # click: for point-edited shapes (Polygon, Beziergon, Polyline,
        # Zigzagline, Bezierline) this is what makes their vertex/
        # anchor handles visible and grabbable right away, so a drag
        # on a point reshapes just that point instead of landing on
        # the shape's body underneath an invisible handle and moving
        # the whole thing. Same benefit for ordinary corner-resize
        # handles on Rectangle/Ellipse/etc.
        self.scene.clearSelection()
        item.setSelected(True)

        self.scene.tool_finished.emit()


class RectDrawingTool(DrawingTool):
    """
    Shared drag-out-a-rectangle-region behavior for any item whose
    geometry is just a bounding self._rect (Rectangle, Ellipse,
    Diamond, Cylinder all work this way) - only the concrete item
    class and undo label differ per subclass.
    """

    item_class = None
    label = "Create Shape"
    min_size = 5

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = self.item_class(QRectF(pos, pos))
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

    def _drag_rect(self, pos):
        rect = QRectF(self.start, pos).normalized()
        if getattr(self.preview_item, "CONSTRAIN_SQUARE", False):
            size = max(rect.width(), rect.height(), self.min_size)
            x0 = self.start.x() if pos.x() >= self.start.x() else self.start.x() - size
            y0 = self.start.y() if pos.y() >= self.start.y() else self.start.y() - size
            rect = QRectF(x0, y0, size, size)
        return rect

    def mouse_move(self, pos):
        if not self.start:
            return

        rect = self._drag_rect(pos)

        self.preview_item.prepareGeometryChange()
        self.preview_item._rect = rect
        self.preview_item.update()

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = self._drag_rect(pos)

        if rect.width() <= self.min_size or rect.height() <= self.min_size:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item._rect = rect

        self.start = None
        self._finish(self.label)


class RectangleTool(RectDrawingTool):
    item_class = RectangleItem
    label = "Create Rectangle"


class EllipseTool(RectDrawingTool):
    item_class = EllipseItem
    label = "Create Ellipse"


class PlotTool(RectDrawingTool):
    """App addition (not in the manual): drag out a Plot shape's
    bounding box, same as Rectangle/Ellipse/etc."""
    item_class = PlotItem
    label = "Create Plot"
    min_size = 40


class ImageTool(RectDrawingTool):
    """Manual 5.1.12: click-drag places a resizable "Broken Image"
    placeholder; the actual file is picked afterward via the
    Properties dialog's Browse button (see ImageItem)."""
    item_class = ImageItem
    label = "Create Image"


class SquareTool(RectDrawingTool):
    """Manual 6.1.1.1, "Assorted": a constrained-ratio "perfect Square"."""
    item_class = SquareItem
    label = "Create Square"


class CircleTool(RectDrawingTool):
    """Manual 6.1.1.1, "Assorted": a constrained-ratio "perfect Circle"."""
    item_class = CircleItem
    label = "Create Circle"


class RegularPolygonTool(RectDrawingTool):
    item_class = RegularPolygonItem
    label = "Create Polygon"
    min_size = 10


class StarTool(RectDrawingTool):
    item_class = StarItem
    label = "Create Star"
    min_size = 10


class SpiralTool(DrawingTool):
    label = "Create Spiral"

    def mouse_press(self, pos):
        self.start = QPointF(pos)
        self.preview_item = SpiralItem(self.start, self.start + QPointF(1, 0))
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

    def mouse_move(self, pos):
        if self.start is None or self.preview_item is None:
            return
        self.preview_item.prepareGeometryChange()
        self.preview_item._endpoint = QPointF(pos)
        self.preview_item._update_handles()
        self.preview_item.update()

    def mouse_release(self, pos):
        if self.start is None or self.preview_item is None:
            return
        self.preview_item._endpoint = QPointF(pos)
        if QLineF(self.preview_item._center, self.preview_item._endpoint).length() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return
        self.preview_item._update_handles()
        self._finish(self.label)


class CircleSectionTool(RectDrawingTool):
    item_class = CircleSectionItem
    label = "Create Three-Quarter Circle"
    min_size = 10


class IsoscelesTriangleTool(RectDrawingTool):
    item_class = IsoscelesTriangleItem
    label = "Create Isosceles Triangle"


class RightTriangleTool(RectDrawingTool):
    item_class = RightTriangleItem
    label = "Create Right Triangle"


class CrossTool(RectDrawingTool):
    item_class = CrossItem
    label = "Create Cross"


class DiamondTool(RectDrawingTool):
    """Flowchart "Decision" symbol (manual 6.1.1.14)."""
    item_class = DiamondItem
    label = "Create Decision"


class CylinderTool(RectDrawingTool):
    """Flowchart "Database" symbol (manual 6.1.1.14)."""
    item_class = CylinderItem
    label = "Create Database"
    min_size = 20  # cylinders need enough height for both end caps


class ActorTool(RectDrawingTool):
    """UML "Actor" symbol (manual 6.1.1.29)."""
    item_class = ActorItem
    label = "Create Actor"
    min_size = 20


class InterfaceTool(RectDrawingTool):
    """UML "Interface" (lollipop) symbol (manual 6.1.1.29)."""
    item_class = InterfaceItem
    label = "Create Interface"
    min_size = 10


class ClassTool(RectDrawingTool):
    """UML "Class" symbol (manual 6.1.1.29)."""
    item_class = ClassItem
    label = "Create Class"
    min_size = 20


# -- extra Flowchart shapes (see items/stencil_items.py) -------------------

class DataTool(RectDrawingTool):
    """Flowchart "Data" (Input/Output) parallelogram."""
    item_class = DataItem
    label = "Create Data"
    min_size = 20


class PredefinedProcessTool(RectDrawingTool):
    """Flowchart "Predefined Process" (box with double side bars)."""
    item_class = PredefinedProcessItem
    label = "Create Predefined Process"
    min_size = 20


class PreparationTool(RectDrawingTool):
    """Flowchart "Preparation" (elongated hexagon)."""
    item_class = PreparationItem
    label = "Create Preparation"
    min_size = 20


class DocumentTool(RectDrawingTool):
    """Flowchart "Document" (wavy bottom edge)."""
    item_class = DocumentItem
    label = "Create Document"
    min_size = 20


class DelayTool(RectDrawingTool):
    """Flowchart "Delay" (D shape)."""
    item_class = DelayItem
    label = "Create Delay"
    min_size = 20


class SummingJunctionTool(RectDrawingTool):
    """Flowchart "Summing Junction" (circle with an X)."""
    item_class = SummingJunctionItem
    label = "Create Summing Junction"
    min_size = 10


class ArrowReferenceTool(RectDrawingTool):
    item_class = ArrowReferenceItem
    label = "Create Arrow Reference"
    min_size = 20


class PaperTapeTool(RectDrawingTool):
    item_class = PaperTapeItem
    label = "Create Paper Tape"
    min_size = 20


class DataStorageTool(RectDrawingTool):
    item_class = DataStorageItem
    label = "Create Data Storage"
    min_size = 20


# -- extra UML shapes (see items/stencil_items.py) ---------------------------

class PackageTool(RectDrawingTool):
    """UML "Package" (box with a name tab)."""
    item_class = PackageItem
    label = "Create Package"
    min_size = 30


class ComponentTool(RectDrawingTool):
    """UML "Component" (box with two side tabs)."""
    item_class = ComponentItem
    label = "Create Component"
    min_size = 30


class NodeTool(RectDrawingTool):
    """UML deployment "Node" (3-D box)."""
    item_class = NodeItem
    label = "Create Node"
    min_size = 30


class NoteTool(RectDrawingTool):
    """UML "Note" (box with a folded corner)."""
    item_class = NoteItem
    label = "Create Note"
    min_size = 20


class LifelineTool(RectDrawingTool):
    """UML sequence-diagram "Lifeline" (head box + dashed line)."""
    item_class = LifelineItem
    label = "Create Lifeline"
    min_size = 30


class RequiredInterfaceTool(RectDrawingTool):
    """UML "Required Interface" (socket)."""
    item_class = RequiredInterfaceItem
    label = "Create Required Interface"
    min_size = 10


class EnumerationTool(RectDrawingTool):
    item_class = EnumerationItem
    label = "Create Enumeration"
    min_size = 30


class ArtifactTool(RectDrawingTool):
    item_class = ArtifactItem
    label = "Create Artifact"
    min_size = 30


class FrameTool(RectDrawingTool):
    item_class = FrameItem
    label = "Create Frame"
    min_size = 30


class LineTool(DrawingTool):
    """
    Draws a Line and lets both ends snap to a nearby shape's
    connection point, exactly as described in the manual (4.2.5): "you
    can save a step by clicking directly on the desired connection
    point of the first object."
    """

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = LineItem(pos, pos)
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

        # Try to connect the start point right away.
        self.preview_item.set_point("p1", pos, try_connect=True)

    def mouse_move(self, pos):
        if not self.start or not self.preview_item:
            return

        self.preview_item.set_point("p2", pos, try_connect=False)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = QRectF(self.start, pos).normalized()

        if rect.width() <= 5 and rect.height() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item.set_point("p2", pos, try_connect=True)

        self.start = None
        self._finish("Create Line")


class ArcTool(DrawingTool):
    """
    Manual 5.1.7: drawn the same way as a Line - drag out the two
    endpoints, which connect exactly like Line's do (4.2.5) - then
    bow it afterward by dragging the orange handle it gets once
    placed (see ArcItem/ArcBowHandle).
    """

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = ArcItem(pos, pos)
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

        self.preview_item.set_point("p1", pos, try_connect=True)

    def mouse_move(self, pos):
        if not self.start or not self.preview_item:
            return

        self.preview_item.set_point("p2", pos, try_connect=False)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = QRectF(self.start, pos).normalized()

        if rect.width() <= 5 and rect.height() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item.set_point("p2", pos, try_connect=True)

        self.start = None
        self._finish("Create Arc")


class PolygonTool(DrawingTool):
    """
    Manual 5.1.4: unlike a single drag defining a rectangle, a
    polygon's vertex count isn't fixed - so dragging out a bounding
    box here just sizes a starting triangle to it. The user reshapes
    from there: drag its vertex handles, or right-click for Add/Delete
    Point (see PolygonItem).
    """

    min_size = 10

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = PolygonItem(
            [QPointF(pos), QPointF(pos), QPointF(pos)]
        )
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

    def _drag_rect(self, pos):
        rect = QRectF(self.start, pos).normalized()
        if getattr(self.preview_item, "CONSTRAIN_SQUARE", False):
            size = max(rect.width(), rect.height(), self.min_size)
            x0 = self.start.x() if pos.x() >= self.start.x() else self.start.x() - size
            y0 = self.start.y() if pos.y() >= self.start.y() else self.start.y() - size
            rect = QRectF(x0, y0, size, size)
        return rect

    def mouse_move(self, pos):
        if not self.start:
            return

        self._resize_preview(pos)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = self._drag_rect(pos)

        if rect.width() <= self.min_size or rect.height() <= self.min_size:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self._resize_preview(pos)

        self.start = None
        self._finish("Create Polygon")

    def _resize_preview(self, pos):
        rect = QRectF(self.start, pos).normalized()
        item = self.preview_item

        item.prepareGeometryChange()
        item._points = [
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.bottom()),
            QPointF(rect.left(), rect.bottom()),
        ]
        item._update_handles()
        item.update()


class PolylineTool(DrawingTool):
    """
    Manual 5.1.9: "starts with one segment" - dragged out exactly
    like a Line, connecting the same way. Bends are added afterward
    via right-click Add segment (see PolylineItem).
    """

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = PolylineItem([pos, pos])
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

        self.preview_item.set_point("p1", pos, try_connect=True)

    def mouse_move(self, pos):
        if not self.start or not self.preview_item:
            return

        self.preview_item.set_point("p2", pos, try_connect=False)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = QRectF(self.start, pos).normalized()

        if rect.width() <= 5 and rect.height() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item.set_point("p2", pos, try_connect=True)

        self.start = None
        self._finish("Create Polyline")


class ZigzaglineTool(DrawingTool):
    """
    Manual 5.1.8: dragged like a Line, then auto-routed live into an
    orthogonal path between the two endpoints as the drag continues
    (see ZigzaglineItem._reroute).
    """

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = ZigzaglineItem([pos, pos])
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

        self.preview_item.set_point("p1", pos, try_connect=True)

    def mouse_move(self, pos):
        if not self.start or not self.preview_item:
            return

        self.preview_item.set_point("p2", pos, try_connect=False)
        self.preview_item._reroute()

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = QRectF(self.start, pos).normalized()

        if rect.width() <= 5 and rect.height() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item.set_point("p2", pos, try_connect=True)
        self.preview_item._reroute()

        self.start = None
        self._finish("Create Zigzagline")


class BeziergonTool(DrawingTool):
    """
    Manual 5.1.5: like Polygon, sizing a starting (here, curved)
    triangle to the drag - reshape afterward via the anchor/control
    handles, or right-click for Add/Delete Point (see BeziergonItem).
    """

    min_size = 10

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = BeziergonItem([QPointF(pos), QPointF(pos), QPointF(pos)])
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

    def _drag_rect(self, pos):
        rect = QRectF(self.start, pos).normalized()
        if getattr(self.preview_item, "CONSTRAIN_SQUARE", False):
            size = max(rect.width(), rect.height(), self.min_size)
            x0 = self.start.x() if pos.x() >= self.start.x() else self.start.x() - size
            y0 = self.start.y() if pos.y() >= self.start.y() else self.start.y() - size
            rect = QRectF(x0, y0, size, size)
        return rect

    def mouse_move(self, pos):
        if not self.start:
            return

        self._resize_preview(pos)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = self._drag_rect(pos)
        #rect = QRectF(self.start, pos).normalized()

        if rect.width() <= self.min_size or rect.height() <= self.min_size:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self._resize_preview(pos)

        self.start = None
        self._finish("Create Beziergon")

    def _resize_preview(self, pos):
        rect = QRectF(self.start, pos).normalized()
        item = self.preview_item

        item.prepareGeometryChange()
        item._nodes = [
            default_node(QPointF(rect.center().x(), rect.top())),
            default_node(QPointF(rect.right(), rect.bottom())),
            default_node(QPointF(rect.left(), rect.bottom())),
        ]
        item._position_handles()
        item.update()


class MaskTool(BeziergonTool):
    """Draw an editable Beziergon clipping/mask path."""

    def mouse_press(self, pos):
        self.start = pos
        self.preview_item = MaskItem([QPointF(pos), QPointF(pos), QPointF(pos)])
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

    def _finish(self, label="Create Mask"):
        super()._finish(label)


class BezierlineTool(DrawingTool):
    """
    Manual 5.1.10: drawn the same way as a Line - drag out the two
    endpoints, connecting exactly like Line's do - starting as a
    straight run (degenerate control points) until reshaped via its
    green/orange handles afterward.
    """

    def mouse_press(self, pos):
        self.start = pos

        self.preview_item = BezierlineItem([pos, pos])
        self.scene.apply_defaults(self.preview_item)
        self.scene.addItem(self.preview_item)

        self.preview_item.set_point("p1", pos, try_connect=True)

    def mouse_move(self, pos):
        if not self.start or not self.preview_item:
            return

        self.preview_item.set_point("p2", pos, try_connect=False)

    def mouse_release(self, pos):
        if not self.start:
            return

        rect = QRectF(self.start, pos).normalized()

        if rect.width() <= 5 and rect.height() <= 5:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None
            self.start = None
            return

        self.preview_item.set_point("p2", pos, try_connect=True)

        self.start = None
        self._finish("Create Bezierline")


class TextTool(DrawingTool):
    """
    Click-to-place text, Dia-style: a single click drops a text label
    at that position and immediately enters edit mode so the user can
    type right away. There is no drag/preview phase, so mouse_move and
    cancel just fall back to the DrawingTool defaults.
    """

    DEFAULT_WIDTH = 140
    DEFAULT_HEIGHT = 40

    def mouse_press(self, pos):
        item = TextItem(
            QRectF(
                pos.x(),
                pos.y(),
                self.DEFAULT_WIDTH,
                self.DEFAULT_HEIGHT
            )
        )

        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        item.enter_edit_mode()

        self.preview_item = item
        self._finish("Create Text")


class CustomShapeTool(DrawingTool):
    """
    App addition (not in the manual): click-to-place version of a
    user-saved custom shape (Objects -> Save as New Shape..., see
    app/custom_shapes.py and MainWindow.save_selection_as_shape()) -
    same click-to-place feel as TextTool above, just dropping a saved
    item (or group of items) instead of an empty text label.

    Not constructed directly off this class like the other tools:
    MainWindow registers one functools.partial(CustomShapeTool,
    shape_path=..., label=...) per saved shape, so shape_path/label
    are per-instance (passed in) rather than per-subclass class
    attributes (the item_class = XItem pattern the RectDrawingTool
    subclasses above use) - one concrete Tool subclass here serves
    every custom shape, in every category, rather than needing a
    freshly-generated subclass per shape.
    """

    def __init__(self, scene, shape_path, label="Place Shape"):
        super().__init__(scene)
        self.shape_path = shape_path
        self.label = label

    def mouse_press(self, pos):
        from app import custom_shapes

        try:
            roots = custom_shapes.load_shape_items(self.shape_path)
        except OSError:
            # The file went missing/became unreadable since the
            # toolbox button was built (e.g. deleted by hand outside
            # the app) - fail quietly rather than crashing the click.
            return

        roots = [r for r in roots if r is not None]

        if not roots:
            return

        if len(roots) == 1:
            item = roots[0]
        else:
            # Saved as several still-independent top-level items
            # (a multi-shape selection saved without having been
            # grouped first) - wrap them in a fresh group so the one
            # click drops them as a single rigid, movable unit.
            # Reparenting preserves each child's absolute position
            # (see GroupItemsCommand's docstring for the same Qt
            # behavior this relies on), so they land exactly as
            # they were saved, just packaged together.
            item = GroupItem()

            for child in roots:
                child.setParentItem(item)
                child.setFlag(child.ItemIsSelectable, False)
                child.setFlag(child.ItemIsMovable, False)

            item._children = list(roots)

        # Center the placed shape under the click point, same
        # convention as every drag-to-draw tool's initial rect.
        rect = QRectF(item.boundingRect())
        rect.translate(item.pos())
        delta = pos - rect.center()
        item.setPos(item.pos() + delta)

        self.scene.addItem(item)

        # App addition (not in the manual): assign .layer/local_z to
        # the placed shape *and any children* - layer_manager.assign()
        # (which _finish() below calls, but only on this top-level
        # item) doesn't recurse, so without this a placed group's
        # children would have no .layer at all: invisible to layer
        # show/hide and layer-based selectability
        # (LayerManager.items_in_layer()/_update_selectability())
        # even though they're sitting right there on the canvas.
        # Mirrors MainWindow._assign_layer_recursive(), used for the
        # same reason when pasting a copied group from the clipboard.
        _assign_layer_recursive(
            self.scene.layer_manager, item,
            self.scene.layer_manager.current_layer()
        )

        self.preview_item = item
        self._finish(self.label)


def _assign_layer_recursive(layer_manager, item, layer):
    """
    Shared by CustomShapeTool above - see its call site. Mirrors
    MainWindow._assign_layer_recursive() (app/main_window.py, used for
    the same reason when pasting a copied group from the clipboard):
    layer_manager.assign() sets ItemIsSelectable based on whether
    `layer` is the current layer - correct for the top-level item, but
    wrong for a group's children, which must stay non-selectable/
    non-movable (matching GroupItemsCommand's own invariant for
    grouped items) regardless of layer. So each child's flags are
    explicitly reasserted right after.
    """

    layer_manager.assign(item, layer)

    if isinstance(item, GroupItem):
        for child in item._children:
            _assign_layer_recursive(layer_manager, child, layer)
            child.setFlag(child.ItemIsSelectable, False)
            child.setFlag(child.ItemIsMovable, False)


class AnchorTool:
    """
    App addition (not in the manual): click a selected shape to add a
    connection point ("anchor") to it at the exact clicked position,
    on top of whatever fixed set connection_points() already defines
    for that shape type (see DiagramItem.add_custom_connection_point()/
    all_connection_points()). Replaces the toolbox's old "Text" mode
    icon (see app/main_window.py's mode_defs) - the Text *drawing*
    tool itself is unchanged and still lives in the Basic category/
    toolbar.

    Requires exactly one shape to already be selected (Select tool,
    beforehand) - clicking then adds the anchor to that shape,
    wherever on the canvas the click lands, rather than guessing which
    overlapping shape a click was "for". Stays active across multiple
    clicks (like Pan, unlike the one-shot drawing tools above, which
    switch back to Select via _finish()'s tool_finished signal after
    each use) - so several anchors can be dropped in a row without
    re-selecting the tool each time. Doesn't subclass DrawingTool:
    nothing is dragged or newly created here, just a single click
    handled through the same duck-typed mouse_press/mouse_move/
    mouse_release/cancel contract DiagramScene.set_tool() expects of
    every tool.

    Two extra bits of feedback beyond the click itself, both app
    additions (not in the manual):

    - reveals_connection_points (a plain class attribute, checked with
      getattr() rather than an isinstance import - see DiagramItem.
      _paint_connection_points()) keeps the selected shape's existing
      "x" marks visible while this tool is active, instead of them
      being hidden for as long as a shape stays selected.
    - mouse_move() records the live cursor position so DiagramScene.
      drawForeground() (see canvas/diagram_scene.py) can paint a
      matching "x" preview there, right up to the moment of the click
      - the mouse cursor itself is shaped the same way (MainWindow.
      activate_tool(), via app/icons.py's anchor_cursor()), but only
      the scene knows where the *selected shape's* connection point
      would actually land, so the preview is drawn here rather than
      left to the cursor bitmap alone.
    """

    reveals_connection_points = True

    def __init__(self, scene):
        self.scene = scene
        self.hover_pos = None

    def mouse_press(self, pos):
        from items.diagram_item import DiagramItem

        selected = [
            i for i in self.scene.selectedItems()
            if isinstance(i, DiagramItem)
        ]

        if len(selected) != 1:
            return

        item = selected[0]
        local_point = item.mapFromScene(pos)

        self.scene.undo_stack.push(
            AddConnectionPointCommand(item, local_point)
        )

    def mouse_move(self, pos):
        self.hover_pos = pos
        self.scene.update()

    def mouse_release(self, pos):
        pass

    def cancel(self):
        self.hover_pos = None


# -- extra Assorted shapes (see items/stencil_items.py) ---------------------

class CrescentTool(RectDrawingTool):
    """Assorted \"Crescent\" (thickness control point on the diameter)."""
    item_class = CrescentItem
    label = "Create Crescent"
    min_size = 10


class SpringTool(RectDrawingTool):
    """Assorted \"Spring\" (vertical coil)."""
    item_class = SpringItem
    label = "Create Spring"
    min_size = 20


class LShapeTool(RectDrawingTool):
    """Assorted \"L-shape\" (two arms, sizes in Properties)."""
    item_class = LShapeItem
    label = "Create L-shape"
    min_size = 20
