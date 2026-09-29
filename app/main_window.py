# main_window.py
import os
import math
import functools
import uuid

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QEvent, QSize, QPointF, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabBar,            
    QTabWidget,
    QToolBar,
    QToolButton,
    QWidgetAction,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import icons
from app import toolbar_icons
from app import document_io
from app import tikz_export
from app import custom_shapes
from app import settings
from app.translations import (
    tr, translations, LANGUAGE_NAMES, DEFAULT_LANGUAGE,
    apply_translations, localize_all_widgets, install_translation_filter,
)
from app import latex_render
from app.tikz_dialog import show_tikz_dialog
from app.export_pdf_dialog import ExportPdfDialog
from app.help_dialog import show_help_dialog
from app.about_dialog import show_about_dialog
from app.diagram_properties_dialog import open_diagram_properties
from app.position_dialog import open_position_dialog
from app.save_shape_dialog import prompt_save_shape
from canvas.diagram_scene import DiagramScene
from canvas.diagram_view import DiagramView
from canvas.ruler import RulerWidget, RulerCorner
from canvas.commands import (
    AddItemCommand,
    DeleteItemsCommand,
    MoveItemCommand,
    GroupItemsCommand,
    UngroupItemsCommand,
    TransformSelectionCommand,
    SwapZOrderCommand,
    RenameItemCommand,
)
from canvas.tools import (
    RectangleTool,
    EllipseTool,
    PlotTool,
    DiamondTool,
    CylinderTool,
    ActorTool,
    InterfaceTool,
    ClassTool,
    LineTool,
    ArcTool,
    PolygonTool,
    PolylineTool,
    ZigzaglineTool,
    ImageTool,
    BeziergonTool,
    MaskTool,
    BezierlineTool,
    SquareTool,
    CircleTool,
    IsoscelesTriangleTool,
    RightTriangleTool,
    CrossTool,
    RegularPolygonTool, StarTool, SpiralTool, CircleSectionTool,
    CrescentTool, SpringTool, LShapeTool,
    TextTool,
    CustomShapeTool,
    AnchorTool,
    DataTool, PredefinedProcessTool, PreparationTool, DocumentTool,
    DelayTool, SummingJunctionTool, ArrowReferenceTool, PaperTapeTool,
    DataStorageTool,
    PackageTool, ComponentTool, NodeTool, NoteTool, LifelineTool,
    RequiredInterfaceTool, EnumerationTool, ArtifactTool, FrameTool,
)
from items.diagram_item import DiagramItem
from items.color_picker import copy_color_value
from items.rectangle_item import RectangleItem
from items.ellipse_item import EllipseItem
from items.diamond_item import DiamondItem
from items.cylinder_item import CylinderItem
from items.actor_item import ActorItem
from items.interface_item import InterfaceItem
from items.class_item import ClassItem
from items.text_item import TextItem
from items.line_item import (
    LineItem,
    ARROW_STYLE_LABELS,
    ARROW_STYLES,
    LINE_STYLE_LABELS,
    LINE_STYLES,
)
from items.arc_item import ArcItem
from items.polygon_item import PolygonItem
from items.polyline_item import PolylineItem
from items.zigzagline_item import ZigzaglineItem
from items.image_item import ImageItem
from items.bezierline_item import BezierlineItem
from items.beziergon_item import BeziergonItem
from items.mask_item import MaskItem
from items.assorted_item import (
    SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
    CrossItem, RegularPolygonItem, StarItem, SpiralItem, CircleSectionItem,
)
from items.stencil_items import StencilItem, STENCIL_SHAPES
from items.group_item import GroupItem
from items.plot_item import PlotItem
from items.property_dialog import edit_shape_properties, _color_button, _option_combo

# Rectangle/Ellipse/Diamond/Cylinder/Actor/Interface all snapshot
# identically - just a bounding rect plus fill/border/border_width.
SIMPLE_SHAPE_TYPES = {
    "rect": RectangleItem,
    "ellipse": EllipseItem,
    "diamond": DiamondItem,
    "cylinder": CylinderItem,
    "actor": ActorItem,
    "interface": InterfaceItem,
    "square": SquareItem,
    "circle": CircleItem,
    "isosceles_triangle": IsoscelesTriangleItem,
    "right_triangle": RightTriangleItem,
    "cross": CrossItem,
    "regular_polygon": RegularPolygonItem,
    "star": StarItem,
}

# Manual 7.3.1.2: pasted/duplicated copies land "just below and to
# the left" of the originals.
PASTE_OFFSET = QPointF(-20, 20)

ZOOM_PRESETS = [800, 400, 200, 100, 50, 25, 12]


def _copy_bezier_node(node):
    """
    A defensive deep-enough copy of one Bezierline/Beziergon node for
    snapshotting (copy/paste/duplicate) - explicit QPointF copies,
    matching how every other shape's snapshot copies its points
    (e.g. PolygonItem's), even though this codebase always replaces
    rather than mutates QPointF values in place.
    """

    return {
        "anchor": QPointF(node["anchor"]),
        "control_in": (
            QPointF(node["control_in"])
            if node["control_in"] is not None else None
        ),
        "control_out": (
            QPointF(node["control_out"])
            if node["control_out"] is not None else None
        ),
        "mode": node["mode"],
    }


class _LayerNameLabel(QLabel):
    """
    A plain QLabel would let a double-click get eaten by the embedded
    item widget before QListWidget's own itemDoubleClicked ever fires -
    so rename-on-double-click is wired directly to this label instead
    of relying on that signal.
    """

    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        tr.set_language(settings.load_language())
        install_translation_filter()
        self.setWindowTitle(tr.get("app_title", "PyDiagram"))
        self.resize(1400, 900)

        self._tool_classes = {
            "Select": None,
            "Pan": None,
            "Rectangle": RectangleTool,
            "Ellipse": EllipseTool,
            "Plot": PlotTool,
            "Polygon": PolygonTool,
            "Line": LineTool,
            "Arc": ArcTool,
            "Polyline": PolylineTool,
            "Zigzagline": ZigzaglineTool,
            "Image": ImageTool,
            "Beziergon": BeziergonTool,
            "Mask": MaskTool,
            "Bezierline": BezierlineTool,
            "Square": SquareTool,
            "Circle": CircleTool,
            "Isosceles Triangle": IsoscelesTriangleTool,
            "Right Triangle": RightTriangleTool,
            "Cross": CrossTool,
            "Polygon": PolygonTool,
            "Regular Polygon": RegularPolygonTool,
            "Star": StarTool,
            "Spiral": SpiralTool,
            "Three-Quarter Circle": CircleSectionTool,
            # App additions: more Assorted shapes (items/stencil_items.py);
            # keys are the shapes' LABELs.
            "Crescent": CrescentTool,
            "Spring": SpringTool,
            "L-shape": LShapeTool,
            "Text": TextTool,
            # App addition (not in the manual): the toolbox's "Anchor"
            # mode button (replaces the old "Text" mode icon there -
            # see _build_mode_grid) - AnchorTool.
            "Anchor": AnchorTool,
            # Flowchart shapes (manual 6.1.1.14) - Process is just a
            # plain rectangle in real Dia too, so it reuses RectangleTool.
            "Process": RectangleTool,
            "Decision": DiamondTool,
            "Database": CylinderTool,
            # App additions (not in the manual): six more Flowchart and
            # six more UML shapes - see items/stencil_items.py. The keys
            # are the shapes' LABELs, which double as toolbox tooltips.
            "Data (I/O)": DataTool,
            "Predefined Process": PredefinedProcessTool,
            "Preparation": PreparationTool,
            "Document": DocumentTool,
            "Delay": DelayTool,
            "Summing Junction": SummingJunctionTool,
            "Arrow Reference": ArrowReferenceTool,
            "Paper Tape": PaperTapeTool,
            "Data Storage": DataStorageTool,
            # UML shapes (manual 6.1.1.29)
            "Class": ClassTool,
            "Interface": InterfaceTool,
            "Actor": ActorTool,
            "Package": PackageTool,
            "Component": ComponentTool,
            "Node": NodeTool,
            "Note": NoteTool,
            "Lifeline": LifelineTool,
            "Required Interface": RequiredInterfaceTool,
            "Enumeration": EnumerationTool,
            "Artifact": ArtifactTool,
            "Frame": FrameTool,
        }

        # label -> list of checkable widgets (QAction and/or QToolButton)
        # that represent this tool. The toolbar and the toolbox each
        # register their own widgets here; activate_tool() below keeps
        # every one of them in sync regardless of which was clicked.
        self._tool_widgets = {}

        # Tracked for the Space-key toggle (manual 4.1.1 tip): Space
        # swaps between Select and whichever drawing tool was last used.
        self._current_tool_label = "Select"
        self._last_drawing_tool = "Rectangle"

        # Snapshots (plain dicts, not live items - see _snapshot_item)
        # from the last Copy or Cut, consumed by Paste. Shared across
        # every tab (not per-document) - that's what lets a shape or
        # group be copied from one open diagram and pasted into
        # another.
        self._clipboard = []

        # App addition (not in the manual): the canvas is a QTabWidget
        # (see _create_scene), one tab per open document. These three
        # back the tab-naming/ruler-visibility logic; self.scene/
        # self.view/self.h_ruler/self.v_ruler/self.current_file_path
        # are properties defined below that resolve to whichever tab
        # is currently active, so the rest of this class can keep
        # reading/writing them exactly as it would with one document.
        self._next_doc_number = 1
        self._rulers_visible = True
        self._ui_ready = False

        # Known up front (rather than read off new_action/open_action,
        # which don't exist until _create_menu() - called after
        # _create_scene() builds the very first tab, which already
        # needs these for its empty-canvas hint).
        self._new_shortcut = "Ctrl+N"
        self._open_shortcut = "Ctrl+O"

        # User-defined shapes (app addition, not in the manual - see
        # app/custom_shapes.py): Objects -> Save as New Shape... adds
        # to these, and _create_toolbox()/_load_custom_shape_categories()
        # read them back to build one toolbox category per subfolder.
        # name -> folder path / name -> QStackedWidget page index,
        # kept in lockstep with self._category_combo's item order.
        self._custom_shapes_root = custom_shapes.user_shapes_root()
        self._custom_category_dir = {}
        self._custom_category_index = {}

        # App addition (not in the manual): most-recently-opened-or-
        # saved .pydia paths, most-recent-first - File -> Recent Files
        # (see _rebuild_recent_files_menu() et al. below). Loaded here
        # (rather than inside _create_menu()) since it only needs
        # app/settings.py, not any part of the UI itself.
        self._recent_files = settings.load_recent_files()

        self._create_scene()
        self._create_menu()
        self._create_toolbar()
        self._create_toolbox()
        self._create_layers_panel()
        self._create_diagram_tree_panel()
        self._create_status_bar()

        # Global panel-layout option: when enabled, Shapes/Layers/Diagram
        # Tree cannot be detached into floating windows.  It is deliberately
        # a separate option from visibility, because a panel may be hidden
        # while the floating lock remains active.
        self._lock_panels_action = QAction(self)
        self._lock_panels_action.setObjectName("LockPanelsAction")
        self._lock_panels_action.setText("Lock Panels")
        self._lock_panels_action.setCheckable(True)
        self._lock_panels_action.toggled.connect(self._set_panels_floating_locked)

        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if tr.is_rtl() else Qt.LeftToRight
        )        
        apply_translations(self)

        # Keep View-menu panel checkboxes synchronized with actual dock
        # visibility, including when the user closes/reopens a dock via
        # its title-bar close button or Qt's dock context menu.
        for dock, action_name in (
            (self.shapes_dock, "_shapes_visible_action"),
            (self.layers_dock, "_layers_visible_action"),
            (self.diagram_tree_dock, "_diagram_tree_action"),
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                dock.visibilityChanged.connect(
                    lambda visible, a=action: self._sync_dock_action(a, visible)
                )

        # App addition (not in the manual): brings back last session's
        # View-menu checkboxes and dock/toolbar layout (position, and
        # split-vs-tabbed style, for Shapes/Layers/Diagram Tree) - see
        # app/settings.py. Every dock/toolbar/action it touches now
        # exists, so this has to run after the loop just above, not
        # before it.
        settings.restore_view_state(self)

        # Now that every panel this depends on exists, bring it all in
        # sync with the one tab created by _create_scene() above -
        # from here on, _on_tab_changed/_on_document_changed/etc. keep
        # it that way as tabs are added, switched, or edited.
        self._ui_ready = True

        # Start in select mode, same as Dia does on launch.
        self.activate_tool("Select")

        self._sync_canvas_toggles()
        self._refresh_layers_list()
        self._refresh_diagram_tree()
        self._sync_undo_redo_actions()
        self._update_properties_action_text()
        self._update_window_title()
        self.statusBar().showMessage(tr.get("ready", "Ready"))

    # -- current-tab properties (app addition, not in the manual) -----
    #
    # Every other method in this class reads/writes self.scene,
    # self.view, self.h_ruler, self.v_ruler, and self.current_file_path
    # exactly as it would in a single-document app; these resolve that
    # to whichever tab is currently active, which is what makes the
    # rest of the class tab-agnostic.

    @property
    def scene(self):
        widget = self.tabs.currentWidget()
        return widget.scene if widget is not None else None

    @property
    def view(self):
        widget = self.tabs.currentWidget()
        return widget.view if widget is not None else None

    @property
    def h_ruler(self):
        return self.tabs.currentWidget().h_ruler

    @property
    def v_ruler(self):
        return self.tabs.currentWidget().v_ruler

    @property
    def current_file_path(self):
        widget = self.tabs.currentWidget()
        return widget.file_path if widget is not None else None

    @current_file_path.setter
    def current_file_path(self, value):
        widget = self.tabs.currentWidget()

        if widget is not None:
            widget.file_path = value

    def _create_status_bar(self):
        """
        Manual Figure 3.2: a "Snap-To-Grid Toggle Button... located
        below the canvas". It mirrors (and is mirrored by) the View
        menu's Snap To Grid action - see _set_snap_to_grid().
        """

        button = QToolButton()
        button.setText("#")
        button.setCheckable(True)
        button.setChecked(self.scene.snap_to_grid)
        button.setToolTip("Snap to Grid")
        button.setAutoRaise(True)
        button.toggled.connect(self._set_snap_to_grid)

        self._snap_to_grid_button = button
        self.statusBar().addPermanentWidget(button)

    def _create_scene(self):
        """
        App addition (not in the manual): the canvas lives inside a
        QTabWidget, one tab per open document (see _build_document_
        container/_add_document_tab below) - Dia itself is single-
        document, but this is what lets several diagrams be open at
        once so shapes/groups can be copied from one and pasted into
        another (self._clipboard, shared across every tab, already
        makes that "just work" once each tab has its own scene).

        self.scene/self.view/self.h_ruler/self.v_ruler/
        self.current_file_path are properties (defined further down)
        that resolve to whichever tab is currently active - every
        other method in this class keeps reading/writing them exactly
        as before a single-document app would, and transparently ends
        up talking to the right document.
        """

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        # Keep the document tab strip and its close buttons synchronized with
        # the current application direction.  Qt does not always move the
        # existing close-button widgets immediately when layoutDirection is
        # changed at runtime.
        
                       

        self.setCentralWidget(self.tabs)

        self._add_document_tab()

    def _build_document_container(self):
        """
        One tab's worth of canvas: its own DiagramScene/DiagramView
        plus the rulers framing it (manual 3.3) - the exact widget
        tree _create_scene used to build directly, now built fresh
        per tab. The returned QWidget carries .scene/.view/.h_ruler/
        .v_ruler/.file_path/.default_name as plain attributes; that's
        the "document" the self.scene/self.view/etc. properties read
        from for whichever tab is current.

        Every widget below is given `container` as its parent right
        from its own constructor call, rather than being built
        parentless and only reparented once added to the grid layout
        a few lines later - a briefly-parentless QWidget is, as far as
        Qt/the OS window manager are concerned, a top-level window in
        its own right, and building several of them in a row (one
        per tab) is what was causing the empty little windows that
        flash in and out on launch and on every new tab.
        """

        container = QWidget(self.tabs)

        scene = DiagramScene(self)
        paper_settings = settings.load_default_paper_settings()
        scene.set_paper_settings(*paper_settings)
        view = DiagramView(scene, container)

        h_ruler = RulerWidget(view, "horizontal", container)
        v_ruler = RulerWidget(view, "vertical", container)
        ruler_corner = RulerCorner(container)

        rulers_visible = getattr(self, "_rulers_visible", True)
        h_ruler.setVisible(rulers_visible)
        v_ruler.setVisible(rulers_visible)
        ruler_corner.setVisible(rulers_visible)

        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        grid.addWidget(ruler_corner, 0, 0)
        grid.addWidget(h_ruler, 0, 1)
        grid.addWidget(v_ruler, 1, 0)
        grid.addWidget(view, 1, 1)

        # The view's row/column should claim all extra space; the
        # rulers are fixed-breadth already, but being explicit here
        # rules out any layout ambiguity affecting the view's size
        # (and with it, whether its scrollbars have room to show).
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(1, 1)

        # App addition (not in the manual): a blank document shows a
        # faint "New File.../Open File..." hint over the canvas -
        # _update_empty_hint (called below and from _on_document_
        # changed/_add_document_tab) shows/hides it based on whether
        # the scene actually has anything on it.
        hint_label = QLabel("", view.viewport())
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        hint_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        hint_label.setWordWrap(True)
        hint_label.hide()

        view.mouse_moved.connect(self._on_mouse_moved_over_canvas)
        view.mouse_left.connect(h_ruler.clear_marker)
        view.mouse_left.connect(v_ruler.clear_marker)
        view.mouse_left.connect(scene.clear_hover_preview)
        view.viewport_changed.connect(h_ruler.update)
        view.viewport_changed.connect(v_ruler.update)
        view.viewport_changed.connect(
            lambda v=view, h=hint_label: h.setGeometry(v.viewport().rect())
        )

        view.escape_pressed.connect(lambda: self.activate_tool("Select"))
        view.space_pressed.connect(self._toggle_tool)

        # Dia's documented default: after a shape is placed, the tool
        # automatically resets to Select (manual 4.1.1, 9.1.1).
        scene.tool_finished.connect(lambda: self.activate_tool("Select"))

        # Every open document gets a persistent identity.  PDF links
        # store this ID rather than a PDF page number or filename, so
        # export order changes cannot invalidate the link.
        document_id = uuid.uuid4().hex
        scene.document_id = document_id
        container.document_id = document_id

        container.scene = scene
        container.view = view
        container.h_ruler = h_ruler
        container.v_ruler = v_ruler
        container.ruler_corner = ruler_corner
        container.hint_label = hint_label
        container.file_path = None
        container.default_name = None

        self._wire_document_signals(container)
        self._update_empty_hint(container)

        # App addition (not in the manual): a freshly created
        # QGraphicsView otherwise starts scrolled to whatever Qt
        # picks by default once the scene rect is bigger than the
        # viewport (usually the scene's center) - deferred because
        # the scrollbars' range isn't final until the widget has
        # actually been laid out and shown, which hasn't happened yet
        # at this point in construction.
        QTimer.singleShot(0, lambda v=view: self._reset_scroll_origin(v))

        return container

    def _reset_scroll_origin(self, view):
        try:
            view.horizontalScrollBar().setValue(0)
            view.verticalScrollBar().setValue(0)
            view.viewport_changed.emit()
        except RuntimeError:
            # The tab (and its view) could have been closed again
            # before this deferred call ran.
            pass

    def _update_empty_hint(self, container):
        """
        Shows the "New File.../Open File..." hint exactly when this
        document is both empty and has never been saved/loaded from a
        real file - an untouched blank canvas, in other words, rather
        than e.g. a file that was opened and happens to have no shapes
        in it.
        """

        from items.diagram_item import DiagramItem

        is_blank = (
            container.file_path is None
            and not any(
                isinstance(i, DiagramItem)
                for i in container.scene.items()
            )
        )

        container.hint_label.setText(
            f"New File ({self._new_shortcut})\nOpen File ({self._open_shortcut})"
        )
        container.hint_label.setVisible(is_blank)
        container.hint_label.setGeometry(container.view.viewport().rect())

    def _wire_document_signals(self, container):
        """
        Per-document signal wiring that used to be a one-time thing in
        __init__ back when there was only ever one scene - now done
        once per tab, each connection capturing `container` so the
        handler knows which document changed even when it isn't the
        one currently on screen (a background tab's title still needs
        its own "*" kept up to date for whenever it's switched to).
        """

        scene = container.scene

        # App addition (not in the manual): Ctrl-dragging on the
        # canvas can reorder/regroup items (see DiagramScene's own
        # mouse handlers) - keep the Diagram Tree panel in sync with
        # whatever that did, for whichever tab is active.
        scene.structure_changed.connect(
            lambda c=container: self._on_document_changed(c)
        )

        # Reflect unsaved-changes state in both the window title (for
        # the active tab) and that tab's own label (for every tab).
        scene.undo_stack.cleanChanged.connect(
            lambda clean, c=container: self._on_document_clean_changed(c, clean)
        )

        # The Diagram Tree (manual 4.5) reflects the current set of
        # objects - every create/delete/move/resize/group/align/etc.
        # goes through the undo stack, so this one connection covers
        # refreshing it after all of them uniformly. Also keeps the
        # Undo/Redo actions' enabled state current.
        scene.undo_stack.indexChanged.connect(
            lambda _i, c=container: self._on_document_changed(c)
        )

        # App addition (not in the manual): the Properties button/menu
        # item reads "Paper Sizes" instead while nothing is
        # selected (see _update_properties_action_text) - kept current
        # as the selection changes, for whichever tab is active.
        scene.selectionChanged.connect(
            lambda c=container: self._on_selection_changed(c)
        )

    def _on_document_changed(self, container):
        try:
            self._update_empty_hint(container)

            if not self._ui_ready or container is not self.tabs.currentWidget():
                return

            self._refresh_diagram_tree()
            self._sync_undo_redo_actions()
        except RuntimeError:
            # Underlying Qt objects can be torn down out of Python's
            # control during interpreter shutdown; a stale signal
            # delivery at that point is harmless to ignore.
            pass

    def _on_document_clean_changed(self, container, clean):
        try:
            self._update_tab_label(container)

            if self._ui_ready and container is self.tabs.currentWidget():
                self._update_window_title(clean=clean)
        except RuntimeError:
            pass

    def _on_selection_changed(self, container):
        try:
            if not self._ui_ready or container is not self.tabs.currentWidget():
                return

            self._update_properties_action_text()
        except RuntimeError:
            # See _on_document_changed above.
            pass

    def _add_document_tab(self, file_path=None, reserve_name=True):
        """
        Manual addition: creates one new tab/document, named after
        `file_path` if given, or the next "DiagramN.pydia" in line
        otherwise (New, and the very first tab at startup).
        `reserve_name=False` skips claiming a DiagramN number for a
        tab that's about to be loaded from a real file anyway
        (open_document creates the tab first, then loads into it) -
        it would never be shown, so it shouldn't consume a number
        that New's own counter would otherwise use next.
        """

        container = self._build_document_container()
        container.file_path = file_path

        if file_path is None:
            if reserve_name:
                container.default_name = f"Diagram{self._next_doc_number}.pydia"
                self._next_doc_number += 1
            else:
                container.default_name = "Untitled"

        index = self.tabs.addTab(container, self._tab_display_name(container))
        self.tabs.setCurrentIndex(index)
                        

        return container


                     
    def _tab_display_name(self, container):
        name = (
            os.path.basename(container.file_path)
            if container.file_path else container.default_name
        )

        dirty = not container.scene.undo_stack.isClean()

        return f"{name}*" if dirty else name

    def _update_tab_label(self, container):
        index = self.tabs.indexOf(container)

        if index >= 0:
            self.tabs.setTabText(index, self._tab_display_name(container))

    def _sync_undo_redo_actions(self):
        stack = self.scene.undo_stack
        self._undo_action.setEnabled(stack.canUndo())
        self._redo_action.setEnabled(stack.canRedo())

    def undo(self):
        self.scene.undo_stack.undo()

    def redo(self):
        self.scene.undo_stack.redo()

    def _on_tab_changed(self, index):
        if not self._ui_ready or index < 0:
            return

        # Switching documents resets to Select rather than carrying a
        # drawing tool over - the tool is tracked on this window, not
        # per tab, so it'd otherwise be ambiguous which canvas it
        # applied to.
        self.activate_tool("Select")

        self._sync_canvas_toggles()
        self._refresh_layers_list()
        self._refresh_diagram_tree()
        self._sync_undo_redo_actions()
        self._update_properties_action_text()
        self._update_window_title()

    def _confirm_close_tab(self, index):
        """
        Manual addition: prompts to save unsaved changes before a
        document closes - covers both an individual tab's close
        button (_on_tab_close_requested) and the whole window closing
        (closeEvent), since either one can discard unsaved work
        otherwise. Returns False if the user cancelled, meaning the
        close (of this tab, or of the whole window) should be aborted.
        """

        container = self.tabs.widget(index)

        if container is None or container.scene.undo_stack.isClean():
            return True

        name = self._tab_display_name(container).rstrip("*")

        choice = QMessageBox.question(
            self,
            "Unsaved Changes",
            f'Save changes to "{name}" before closing?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if choice == QMessageBox.Cancel:
            return False

        if choice == QMessageBox.Save:
            previous_index = self.tabs.currentIndex()
            self.tabs.setCurrentIndex(index)

            self.save_document()
            saved = container.scene.undo_stack.isClean()

            self.tabs.setCurrentIndex(previous_index)

            if not saved:
                # Save As was cancelled, or the save itself failed -
                # either way, nothing was actually saved.
                return False

        return True

    def _discard_document_container(self, container):
        """
        The scene is a QObject parented to this window (for Qt's
        C++-side cleanup at app exit), not to `container` itself - so
        closing a tab needs to explicitly tear its scene down too, or
        it (and everything in it) would simply leak for the rest of
        the session instead of being freed when its tab closes.
        """

        container.scene.deleteLater()
        container.deleteLater()

    def _on_tab_close_requested(self, index):
        if not self._confirm_close_tab(index):
            return

        if self.tabs.count() <= 1:
            # There's always at least one document open - every panel
            # in this window (Layers, Diagram Tree, the canvas itself)
            # assumes self.scene exists, so closing the last tab
            # starts a fresh, empty "Diagram1.pydia" in its place
            # rather than leaving no tab at all. The numbering resets
            # here rather than continuing on from wherever it was -
            # with nothing left open, there's nothing for a second
            # "Diagram1.pydia" to collide with.
            self._next_doc_number = 1
            container = self._build_document_container()
            container.default_name = f"Diagram{self._next_doc_number}.pydia"
            self._next_doc_number += 1

            old_container = self.tabs.widget(index)
            self.tabs.removeTab(index)
            self._discard_document_container(old_container)

            self.tabs.addTab(container, self._tab_display_name(container))
            self.tabs.setCurrentIndex(0)
            return

        container = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self._discard_document_container(container)

    def closeEvent(self, event):
        for index in range(self.tabs.count()):
            if not self._confirm_close_tab(index):
                event.ignore()
                return

        # App addition (not in the manual): persists the View-menu
        # checkboxes and dock/window layout for next launch - see
        # app/settings.py. Only once every open tab's confirmed closed
        # above, so a cancelled close doesn't overwrite last session's
        # saved state with a since-changed one the user just backed
        # out of.
        settings.save_view_state(self)

        event.accept()

    def _on_mouse_moved_over_canvas(self, scene_pos):
        self.h_ruler.set_marker(scene_pos)
        self.v_ruler.set_marker(scene_pos)

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_document)
        # Stashed (like self._rotate_action below) so _create_toolbar()
        # can reuse the very same QActions - one shortcut, one slot,
        # nothing to keep in sync between the menu and the toolbar.
        self._new_action = new_action

        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_document)
        self._open_action = open_action

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_document)
        self._save_action = save_action

        # App addition: saves every open document that has unsaved
        # changes in one go - see save_all_documents().
        save_all_action = QAction("Save A&ll", self)
        save_all_action.triggered.connect(self.save_all_documents)
        self._save_all_action = save_all_action

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_document_as)
        self._save_as_action = save_as_action

        # App addition (not in the manual): File -> Recent Files - a
        # submenu of up to settings.MAX_RECENT_FILES most-recently-
        # opened-or-saved .pydia paths (self._recent_files, loaded in
        # __init__ before any of the UI - including this menu - is
        # built), plus a "Clear Recent Files" action at the end.
        # Rebuilt from scratch on every change rather than patched
        # incrementally - see _rebuild_recent_files_menu() - since the
        # list is short and this keeps the two from ever drifting out
        # of sync. Actually inserted into file_menu below, between
        # Save As and the Export actions - not here, since menu order
        # follows addAction()/addMenu() call order, not where these
        # QAction/QMenu objects happen to be constructed.
        self._recent_files_menu = QMenu("Recent &Files", self)

        export_png_action = QAction("Export as &PNG...", self)
        export_png_action.triggered.connect(self.export_png)
        self._export_png_action = export_png_action

        export_svg_action = QAction("Export as &SVG...", self)
        export_svg_action.triggered.connect(self.export_svg)
        self._export_svg_action = export_svg_action

        export_pdf_action = QAction("Export to P&DF...", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        self._export_pdf_action = export_pdf_action

        export_tikz_action = QAction("Export as &Tikz...", self)
        export_tikz_action.triggered.connect(self.export_tikz)
        self._export_tikz_action = export_tikz_action

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_all_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        self._recent_files_menu_action = file_menu.addMenu(
            self._recent_files_menu
        )
        file_menu.addSeparator()
        file_menu.addAction(export_png_action)
        file_menu.addAction(export_svg_action)
        file_menu.addAction(export_pdf_action)
        file_menu.addAction(export_tikz_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        self._rebuild_recent_files_menu()

        edit_menu = self.menuBar().addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setEnabled(False)
        undo_action.triggered.connect(self.undo)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.setEnabled(False)
        redo_action.triggered.connect(self.redo)

        # App addition (not in the manual): stashed so
        # _sync_undo_redo_actions() (called on every tab switch, and
        # whenever the active tab's own undo stack changes) can keep
        # these enabled/disabled for whichever document is now
        # current - each tab has its own independent undo stack.
        self._undo_action = undo_action
        self._redo_action = redo_action

        delete_action = QAction("&Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(lambda: self.view.delete_selected_items())

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selection)
        # Stashed (like self._rotate_action etc.) so the toolbar's Edit
        # drop-down (see _create_toolbar) can reuse this very QAction.
        self._copy_action = copy_action

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut_selection)
        self._cut_action = cut_action

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_clipboard)
        self._paste_action = paste_action

        clone_action = QAction("Cl&one", self)
        clone_action.setShortcut("Ctrl+B")
        clone_action.triggered.connect(self.clone_diagram)
        self._clone_action = clone_action

        duplicate_action = QAction("D&uplicate", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self.duplicate_selection)
        self._duplicate_action = duplicate_action

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)
        edit_menu.addAction(cut_action)
        edit_menu.addAction(paste_action)
        edit_menu.addAction(clone_action)
        edit_menu.addAction(duplicate_action)
        edit_menu.addSeparator()
        edit_menu.addAction(delete_action)

        select_menu = self.menuBar().addMenu("&Select")

        select_all_action = QAction("&All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all)

        select_none_action = QAction("&None", self)
        select_none_action.triggered.connect(self.select_none)

        select_invert_action = QAction("&Invert", self)
        select_invert_action.setShortcut("Ctrl+I")
        select_invert_action.triggered.connect(self.select_invert)

        select_same_type_action = QAction("&Same Type", self)
        select_same_type_action.triggered.connect(self.select_same_type)

        select_transitive_action = QAction("&Transitive", self)
        select_transitive_action.triggered.connect(self.select_transitive)

        select_connected_action = QAction("&Connected", self)
        select_connected_action.triggered.connect(self.select_connected)

        select_menu.addAction(select_all_action)
        select_menu.addAction(select_none_action)
        select_menu.addAction(select_invert_action)
        select_menu.addSeparator()
        select_menu.addAction(select_same_type_action)
        select_menu.addAction(select_transitive_action)
        select_menu.addAction(select_connected_action)

        # Shared as-is (like self._align_menu below) as the drop-down
        # of the toolbar's own Select button - see _create_toolbar().
        self._select_menu = select_menu

        objects_menu = self.menuBar().addMenu("&Objects")

        send_to_back_action = QAction("Send to &Back", self)
        # Ctrl+B is Clone's shortcut (see clone_action above, added to
        # the same window) - Send to Back uses Ctrl+Shift+B instead so
        # the two don't collide as an ambiguous shortcut.
        send_to_back_action.setShortcut("Ctrl+Shift+B")
        send_to_back_action.triggered.connect(self.send_to_back)
        self._send_to_back_action = send_to_back_action

        bring_to_front_action = QAction("Bring to &Front", self)
        bring_to_front_action.setShortcut("Ctrl+Shift+F")
        bring_to_front_action.triggered.connect(self.bring_to_front)
        self._bring_to_front_action = bring_to_front_action

        send_backward_action = QAction("Send Backwards", self)
        # Ctrl+Up/Down also reorders rows in the Diagram Tree; that
        # panel claims the keys itself while it has focus - see the
        # ShortcutOverride handling in eventFilter().
        send_backward_action.setShortcut("Ctrl+Down")
        send_backward_action.triggered.connect(self.send_backward)
        self._send_backward_action = send_backward_action

        bring_forward_action = QAction("Bring Forwards", self)
        bring_forward_action.setShortcut("Ctrl+Up")
        bring_forward_action.triggered.connect(self.bring_forward)
        self._bring_forward_action = bring_forward_action

        objects_menu.addAction(send_to_back_action)
        objects_menu.addAction(bring_to_front_action)
        objects_menu.addAction(send_backward_action)
        objects_menu.addAction(bring_forward_action)
        objects_menu.addSeparator()

        group_action = QAction("&Group", self)
        group_action.setShortcut("Ctrl+G")
        group_action.triggered.connect(self.group_selection)
        self._group_action = group_action

        ungroup_action = QAction("&Ungroup", self)
        ungroup_action.setShortcut("Shift+Ctrl+G")
        ungroup_action.triggered.connect(self.ungroup_selection)
        self._ungroup_action = ungroup_action

        objects_menu.addAction(group_action)
        objects_menu.addAction(ungroup_action)
        objects_menu.addSeparator()

        align_menu = objects_menu.addMenu("&Align")
        # Also shown as the drop-down of the toolbar's Align button.
        self._align_menu = align_menu

        align_defs = [
            ("&Left", "Shift+Alt+L", self.align_left),
            ("&Center", "Shift+Alt+C", self.align_center_h),
            ("&Right", "Shift+Alt+R", self.align_right),
            None,
            ("&Top", "Shift+Alt+T", self.align_top),
            ("&Middle", "Shift+Alt+M", self.align_middle),
            ("&Bottom", "Shift+Alt+B", self.align_bottom),
            None,
            (
                "Spread Out &Horizontally",
                "Shift+Alt+H",
                self.spread_out_horizontally
            ),
            (
                "Spread Out &Vertically",
                "Shift+Alt+V",
                self.spread_out_vertically
            ),
            None,
            ("&Adjacent", "Shift+Alt+A", self.align_adjacent),
            ("&Stacked", "Shift+Alt+S", self.align_stacked),
        ]

        for entry in align_defs:
            if entry is None:
                align_menu.addSeparator()
                continue

            label, shortcut, slot = entry
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            align_menu.addAction(action)

        objects_menu.addSeparator()

        # App addition (not in the manual): shows/edits a selected
        # shape's position relative to the rulers' (0,0) origin
        # (manual 3.3) - see edit_position_selection().
        position_action = QAction(
            toolbar_icons.position_icon(), "&Position...", self
        )
        position_action.triggered.connect(self.edit_position_selection)
        objects_menu.addAction(position_action)
        self._position_action = position_action

        # App additions (not in the manual): rotate/flip the whole
        # selection as one rigid group - see _apply_group_rotation/
        # _apply_group_flip.
        rotate_action = QAction(
            toolbar_icons.rotate_icon(), "&Rotate...", self
        )
        rotate_action.triggered.connect(self.rotate_selection)
        objects_menu.addAction(rotate_action)
        self._rotate_action = rotate_action

        # One-degree nudges: Ctrl+R turns the selection by +1 degree
        # (the same direction as a positive angle in Rotate...),
        # Ctrl+Shift+R by -1 degree. Added to the menu so the
        # shortcuts are active window-wide and listed for discovery.
        rotate_plus_action = QAction("Rotate +1\u00b0", self)
        rotate_plus_action.setShortcut("Ctrl+R")
        rotate_plus_action.triggered.connect(
            lambda checked=False: self.rotate_selection_by(1.0)
        )
        objects_menu.addAction(rotate_plus_action)
        self._rotate_plus_action = rotate_plus_action

        rotate_minus_action = QAction("Rotate -1\u00b0", self)
        rotate_minus_action.setShortcut("Ctrl+Shift+R")
        rotate_minus_action.triggered.connect(
            lambda checked=False: self.rotate_selection_by(-1.0)
        )
        objects_menu.addAction(rotate_minus_action)
        self._rotate_minus_action = rotate_minus_action

        flip_menu = objects_menu.addMenu("&Flip")

        flip_h_action = QAction("&Horizontal", self)
        flip_h_action.setShortcut("Ctrl+Shift+H")
        flip_h_action.triggered.connect(self.flip_selection_horizontal)
        flip_menu.addAction(flip_h_action)
        self._flip_h_action = flip_h_action

        flip_v_action = QAction("&Vertical", self)
        flip_v_action.setShortcut("Ctrl+Shift+V")
        flip_v_action.triggered.connect(self.flip_selection_vertical)
        flip_menu.addAction(flip_v_action)
        self._flip_v_action = flip_v_action

        # Scale (app addition): Ctrl(+Shift)+L/M = +(-)1% Horizontal/
        # Vertical. The toolbar's Scale drop-down (see
        # _create_scale_menu) edits exact percentages.
        scale_menu = objects_menu.addMenu("&Scale")
        self._scale_actions = []

        for text, keys, dh, dv in (
            ("Horizontal +1%", "Ctrl+L", 1.0, 0.0),
            ("Horizontal -1%", "Ctrl+Shift+L", -1.0, 0.0),
            ("Vertical +1%", "Ctrl+M", 0.0, 1.0),
            ("Vertical -1%", "Ctrl+Shift+M", 0.0, -1.0),
        ):
            act = QAction(text, self)
            act.setShortcut(keys)
            act.triggered.connect(
                lambda checked=False, a=dh, b=dv: self.scale_selection_by(a, b)
            )
            scale_menu.addAction(act)
            self._scale_actions.append(act)

        objects_menu.addSeparator()

        properties_action = QAction("&Properties", self)
        properties_action.setShortcut("Alt+Return")
        properties_action.triggered.connect(self.edit_selected_properties)
        objects_menu.addAction(properties_action)
        self._properties_action = properties_action

        objects_menu.addSeparator()

        # App addition (not in the manual): save the current
        # selection into the user's shape library, shown in its own
        # toolbox category/categories - see app/custom_shapes.py.
        save_shape_action = QAction("Save as New Shape...", self)
        save_shape_action.triggered.connect(self.save_selection_as_shape)
        objects_menu.addAction(save_shape_action)
        self._save_shape_action = save_shape_action

        diagram_menu = self.menuBar().addMenu("&Diagram")

        diagram_properties_action = QAction("&Properties...", self)
        diagram_properties_action.triggered.connect(
            self.open_diagram_properties
        )
        diagram_menu.addAction(diagram_properties_action)

        # App addition (not in the manual): frees the on-disk cache
        # behind "Create from LaTeX..." (app/latex_render.py) - safe
        # to wipe entirely, since every ImageItem that needs one of
        # those files back can re-render it from its own saved
        # latex_recipe - see clean_up_latex_cache() below.
        cleanup_latex_cache_action = QAction(
            "Clean Up &LaTeX Image Cache...", self
        )
        cleanup_latex_cache_action.triggered.connect(
            self.clean_up_latex_cache
        )
        diagram_menu.addAction(cleanup_latex_cache_action)
        self._cleanup_latex_cache_action = cleanup_latex_cache_action

        view_menu = self.menuBar().addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.view.zoom_in())
        # Stashed so the toolbar's own Zoom drop-down (see
        # _create_toolbar) can reuse these same QActions.
        self._zoom_in_action = zoom_in_action

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.view.zoom_out())
        self._zoom_out_action = zoom_out_action

        reset_zoom_action = QAction("&Normal Size", self)
        reset_zoom_action.setShortcut("Ctrl+1")
        reset_zoom_action.triggered.connect(lambda: self.view.reset_zoom())
        self._reset_zoom_action = reset_zoom_action

        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(reset_zoom_action)

        zoom_menu = view_menu.addMenu("&Zoom")

        # Also collected so the toolbar's Zoom drop-down can list the
        # very same preset QActions alongside Zoom In/Out/Normal Size.
        self._zoom_preset_actions = []

        for pct in ZOOM_PRESETS:
            action = QAction(f"{pct}%", self)
            action.triggered.connect(
                lambda checked, p=pct: self.view.set_zoom(p / 100)
            )
            zoom_menu.addAction(action)
            self._zoom_preset_actions.append(action)

        best_fit_action = QAction("&Best Fit", self)
        best_fit_action.setShortcut("Ctrl+F")
        best_fit_action.triggered.connect(self.best_fit)
        view_menu.addAction(best_fit_action)
        self._best_fit_action = best_fit_action

        view_menu.addSeparator()
        
        # App addition (not in the manual): forces the canvas to
        # redraw from scratch, in case anything ever leaves a stale
        # paint behind that Qt's own paint scheduling doesn't catch.
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_view)
        view_menu.addAction(refresh_action)
        # Stashed so the toolbar's own Refresh button (see
        # _create_toolbar) can reuse this same QAction.
        self._refresh_action = refresh_action


        view_menu.addSeparator()        

        show_rulers_action = QAction("Show &Rulers", self)
        show_rulers_action.setShortcut("F6")
        show_rulers_action.setCheckable(True)
        show_rulers_action.setChecked(True)
        show_rulers_action.toggled.connect(self._set_rulers_visible)
        view_menu.addAction(show_rulers_action)
        self._show_rulers_action = show_rulers_action

        # App addition (not in the manual): the same panel-visibility
        # toggles already available by right-clicking the toolbar/dock
        # area (Qt's own built-in context menu there), surfaced in the
        # View menu too for discoverability. Wrapped in lambdas since
        # _create_menu() runs before the toolbar/docks themselves are
        # built (self.shapes_dock etc. don't exist yet at this point -
        # same reason the existing Diagram Tree toggle below is a
        # lambda too) - checked=True matches their actual default.
        shapes_visible_action = QAction("&Shapes", self)
        shapes_visible_action.setShortcut("F7")
        shapes_visible_action.setCheckable(True)
        shapes_visible_action.setChecked(True)
        shapes_visible_action.toggled.connect(
            lambda visible: self.shapes_dock.setVisible(visible)
        )
        view_menu.addAction(shapes_visible_action)
        self._shapes_visible_action = shapes_visible_action

        layers_visible_action = QAction("&Layers", self)
        layers_visible_action.setShortcut("F8")
        layers_visible_action.setCheckable(True)
        layers_visible_action.setChecked(True)
        layers_visible_action.toggled.connect(
            lambda visible: self.layers_dock.setVisible(visible)
        )
        view_menu.addAction(layers_visible_action)
        self._layers_visible_action = layers_visible_action

        tools_visible_action = QAction("&Tools", self)
        tools_visible_action.setShortcut("F9")
        tools_visible_action.setCheckable(True)
        tools_visible_action.setChecked(True)
        tools_visible_action.toggled.connect(
            lambda visible: self.tools_toolbar.setVisible(visible)
        )
        view_menu.addAction(tools_visible_action)
        self._tools_visible_action = tools_visible_action

        diagram_tree_action = QAction("&Diagram Tree", self)
        diagram_tree_action.setShortcut("F10")
        diagram_tree_action.setCheckable(True)
        diagram_tree_action.setChecked(True)
        diagram_tree_action.toggled.connect(
            lambda visible: self.diagram_tree_dock.setVisible(visible)
        )
        view_menu.addAction(diagram_tree_action)
        self._diagram_tree_action = diagram_tree_action

        view_menu.addSeparator()

        # Manual 3.6, "Other View Menu Options": Show Grid, Snap To
        # Grid, Snap To Objects, and Show Connection Points all toggle
        # a DiagramScene flag of the same name.
        show_grid_action = QAction("Show &Grid", self)       
        show_grid_action.setCheckable(True)
        show_grid_action.setChecked(self.scene.show_grid)
        show_grid_action.toggled.connect(self._set_show_grid)
        view_menu.addAction(show_grid_action)
        self._show_grid_action = show_grid_action

        snap_to_grid_action = QAction("&Snap To Grid", self)
        snap_to_grid_action.setCheckable(True)
        snap_to_grid_action.setChecked(self.scene.snap_to_grid)
        snap_to_grid_action.toggled.connect(self._set_snap_to_grid)
        view_menu.addAction(snap_to_grid_action)
        self._snap_to_grid_action = snap_to_grid_action

        snap_to_objects_action = QAction("Snap To &Objects", self)
        snap_to_objects_action.setCheckable(True)
        snap_to_objects_action.setChecked(self.scene.snap_to_objects)
        snap_to_objects_action.toggled.connect(self._set_snap_to_objects)
        view_menu.addAction(snap_to_objects_action)
        self._snap_to_objects_action = snap_to_objects_action

        show_conn_points_action = QAction("Show &Connection Points", self)
        show_conn_points_action.setCheckable(True)
        show_conn_points_action.setChecked(self.scene.show_connection_points)
        show_conn_points_action.toggled.connect(
            self._set_show_connection_points
        )
        view_menu.addAction(show_conn_points_action)
        self._show_conn_points_action = show_conn_points_action

        view_menu.addSeparator()

        # App addition: View -> Language. The very same QMenu is also
        # the drop-down of the toolbar's language button (see
        # _create_language_button), like Recent Files above, so the
        # two can never disagree. Checkmarks are kept in step by
        # _set_language().
        language_menu = QMenu("&Language", self)

        for code, name in LANGUAGE_NAMES.items():
            action = QAction(name, language_menu)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(code == tr.lang)
            action.triggered.connect(
                lambda checked=False, c=code: self._set_language(c)
            )
            language_menu.addAction(action)

        self._language_menu = language_menu
        view_menu.addMenu(language_menu)




        help_menu = self.menuBar().addMenu("&Help")

        help_action = QAction("&Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        # Stashed so the toolbar's own Help button (see
        # _create_toolbar) can reuse this same QAction.
        self._help_action = help_action

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.setShortcut("F3")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_help(self):
        show_help_dialog(self)

    def show_about(self):
        show_about_dialog(self)

    def _refresh_view(self):
        self.scene.invalidate()
        self.view.viewport().update()

    def _set_rulers_visible(self, visible):
        # Applied to every open tab uniformly (rather than just the
        # current one) so the View menu's checkbox always matches
        # what's shown after switching tabs - unlike show_grid/snap/
        # etc., ruler visibility isn't part of a scene's own saved
        # settings.
        self._rulers_visible = visible

        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            container.h_ruler.setVisible(visible)
            container.v_ruler.setVisible(visible)
            container.ruler_corner.setVisible(visible)

    # -- canvas settings (manual Chapter 3 / Diagram -> Properties) ----

    def _set_show_grid(self, visible):
        self.scene.show_grid = visible
        self.scene.update()

    def _set_snap_to_grid(self, enabled):
        self.scene.snap_to_grid = enabled
        self.scene.update()

        # Keep the View menu action and the status-bar toggle button
        # (manual Figure 3.2, "located below the canvas") in sync
        # regardless of which one the user actually clicked.
        if hasattr(self, "_snap_to_grid_action"):
            self._snap_to_grid_action.blockSignals(True)
            self._snap_to_grid_action.setChecked(enabled)
            self._snap_to_grid_action.blockSignals(False)

        if hasattr(self, "_snap_to_grid_button"):
            self._snap_to_grid_button.blockSignals(True)
            self._snap_to_grid_button.setChecked(enabled)
            self._snap_to_grid_button.blockSignals(False)

    def _set_snap_to_objects(self, enabled):
        self.scene.snap_to_objects = enabled

    def _set_show_connection_points(self, visible):
        self.scene.show_connection_points = visible
        self.scene.update()

    def open_diagram_properties(self):
        open_diagram_properties(self.scene, self)
        self._sync_canvas_toggles()
        # Paper Sizes changes the page rectangle; immediately show
        # the complete exportable paper and refresh both rulers.
        self.view.fitInView(self.scene.paper_rect(), Qt.KeepAspectRatio)
        self.view._zoom = self.view.transform().m11()
        self.view.viewport_changed.emit()

    def clean_up_latex_cache(self):
        """
        App addition (not in the manual): Diagram -> Clean Up LaTeX
        Image Cache... Always safe to wipe outright - see
        app/latex_render.py's module docstring and ImageItem.
        latex_recipe (items/image_item.py): any Image shape that
        still needs one of these files re-renders it from its own
        saved recipe the next time it's painted, so nothing here is
        this cache's only copy.
        """

        count, total_bytes = latex_render.cache_usage()

        if count == 0:
            QMessageBox.information(
                self,
                "Clean Up LaTeX Image Cache",
                "The LaTeX image cache is already empty.",
            )
            return

        size_mb = total_bytes / (1024 * 1024)

        choice = QMessageBox.question(
            self,
            "Clean Up LaTeX Image Cache",
            (
                f"This will delete {count} cached equation image"
                f"{'s' if count != 1 else ''} ({size_mb:.1f} MB).\n\n"
                "Any diagram that still uses one will regenerate it "
                "automatically the next time it's displayed (this "
                "requires a local LaTeX installation - pdflatex and "
                "pdftocairo - to still be available).\n\n"
                "Continue?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if choice != QMessageBox.Yes:
            return

        count, total_bytes = latex_render.clear_cache()
        size_mb = total_bytes / (1024 * 1024)

        QMessageBox.information(
            self,
            "Clean Up LaTeX Image Cache",
            f"Deleted {count} cached equation image"
            f"{'s' if count != 1 else ''}, freeing {size_mb:.1f} MB.",
        )

        # Cached files just disappeared out from under any Image shape
        # currently on screen using one - repaint so shapes with no
        # latex_recipe to self-heal from show "Broken Image" right
        # away, instead of only on the next unrelated repaint.
        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)

            if getattr(container, "scene", None) is not None:
                container.scene.update()

    def best_fit(self):
        """
        Manual 3.6: "Best Fit automatically zooms to the highest zoom
        value that will fit the entire diagram in the window."
        """

        rect = document_io.content_rect(self.scene, margin=20)
        self.view.fitInView(rect, Qt.KeepAspectRatio)
        self.view._zoom = self.view.transform().m11()
        self.view.viewport_changed.emit()

    def _set_language(self, language_code):
        tr.set_language(language_code)
        settings.save_language(tr.lang)
        localize_all_widgets()
        self._refresh_undo_redo_icons()
        self.setWindowTitle(tr.get("app_title", "PyDiagram"))
        if hasattr(self, "_language_menu"):
            for action in self._language_menu.actions():
                action.blockSignals(True)
                action.setChecked(action.data() == tr.lang)
                action.blockSignals(False)
        if hasattr(self, "_language_button"):
            self._language_button.setToolTip(tr.get("language_tooltip", "Language"))
        self._update_window_title()

    def _create_language_button(self, toolbar, icon_size):
        # Shares View -> Language's own QMenu (built in _create_menu()).
        menu = self._language_menu
        button = QToolButton()
        button.setText("A/文")
        button.setIcon(toolbar_icons.language_icon())

        button.setIconSize(icon_size)
        button.setToolTip(tr.get("language_tooltip", "Language"))
        button.setAutoRaise(True)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(menu)
        toolbar.addWidget(button)
        self._language_button = button
        for action in menu.actions():
            action.setChecked(action.data() == tr.lang)
        return button

    def _create_toolbar(self):
        """
        Slim icon toolbar across the top. Left to right: New, Open,
        Save (drop-down: Save / Save All / Save As), Clean (Clean Up LaTeX Image
        Cache...), Recent Files (drop-down),
        Export (drop-down: PNG / SVG / TikZ); Edit (drop-down: Copy /
        Cut / Paste), Duplicate, Select (drop-down: All / None /
        Invert / Same Type / Transitive / Connected); Undo, Redo;
        Zoom (drop-down of presets), Best Fit; Rules, Shapes, Layers,
        Diagram Tree (each a checkable button kept in sync with its
        View-menu checkbox - they share the very same QAction); Show
        Grid, Snap to Grid, Snap to Objects, Show Connections (same
        idea); the stacking-order drop-down (Send to Back / Bring to Front /
        Send Backwards / Bring Forwards), Group, Ungroup, Align
        (drop-down), Rotate, Flip (drop-down) and Properties; and
        finally Help. Every button reuses a QAction (or QMenu) built
        in _create_menu(), so shortcuts and behavior are defined in
        exactly one place. The drawing tools themselves (Select,
        Rectangle, Ellipse, Line, Text...) live in the Shapes dock -
        see _create_toolbox().
        """

        toolbar = QToolBar("Tools", self)
        # App addition (not in the manual): QMainWindow.saveState()/
        # restoreState() (app/settings.py) need a unique objectName on
        # every dock widget and toolbar to tell them apart - without
        # one, Qt can't reliably match a saved entry back to the right
        # widget (and warns about it on every saveState() call, one
        # such warning per widget below that's missing one).
        toolbar.setObjectName("ToolsToolbar")
        toolbar.setMovable(False)

        icon_size = QSize(toolbar_icons.ICON_SIZE, toolbar_icons.ICON_SIZE)
        toolbar.setIconSize(icon_size)

        def add_button(action, icon, tooltip, icon_in_menu=False):
            """A plain one-click button for an existing QAction."""

            action.setIcon(icon)
            # The menus were never meant to grow icons (Rotate... is
            # the one that already had one) - only the toolbar shows
            # them.
            action.setIconVisibleInMenu(icon_in_menu)
            action.setToolTip(tooltip)
            toolbar.addAction(action)

        def add_menu_button(icon, tooltip, menu):
            """
            A button that opens `menu` right away when clicked, same
            idea as the Flip button always was.
            """

            button = QToolButton()
            button.setIcon(icon)
            button.setIconSize(icon_size)
            button.setToolTip(tooltip)
            button.setAutoRaise(True)
            button.setPopupMode(QToolButton.InstantPopup)
            button.setMenu(menu)
            toolbar.addWidget(button)
            return button

        # -- File ---------------------------------------------------
        add_button(
            self._new_action, toolbar_icons.new_icon(), "New (Ctrl+N)"
        )
        add_button(
            self._open_action, toolbar_icons.open_icon(), "Open... (Ctrl+O)"
        )

        toolbar.addSeparator()

        save_button = add_menu_button(
            toolbar_icons.save_icon(),
            "Save / Save All / Save As...",
            QMenu(self),
        )
        save_button.menu().addAction(self._save_action)
        save_button.menu().addAction(self._save_all_action)
        save_button.menu().addAction(self._save_as_action)

        # App addition (not in the manual): same action as Diagram ->

        # Shares File -> Recent Files' own QMenu, which
        # _rebuild_recent_files_menu() refills in place.
        self._recent_button = add_menu_button(
            toolbar_icons.recent_files_icon(),
            "Recent files",
            self._recent_files_menu,
        )
        self._recent_button.setEnabled(bool(self._recent_files))

        export_menu = QMenu(self)
        export_menu.addAction(self._export_png_action)
        export_menu.addAction(self._export_svg_action)
        export_menu.addAction(self._export_pdf_action)
        export_menu.addAction(self._export_tikz_action)
        add_menu_button(toolbar_icons.export_icon(), "Export", export_menu)

        toolbar.addSeparator()

        # -- Edit / Duplicate / Select --------------------------------
        edit_menu = QMenu(self)
        edit_menu.addAction(self._copy_action)
        edit_menu.addAction(self._cut_action)
        edit_menu.addAction(self._paste_action)
        edit_menu.addAction(self._clone_action)
        add_menu_button(toolbar_icons.edit_icon(), "Edit", edit_menu)

        add_button(
            self._duplicate_action,
            toolbar_icons.duplicate_icon(),
            "Duplicate (Ctrl+D)",
        )

        # Shares Select menu's own QMenu, same trick as Align below.
        add_menu_button(
            toolbar_icons.select_icon(), "Select", self._select_menu
        )

        toolbar.addSeparator()

        # -- Undo / Redo ----------------------------------------------
        # add_button(
            # self._undo_action, 
            # toolbar_icons.undo_icon(), 
            # "Undo (Ctrl+Z)"
        # )
        # add_button(
            # self._redo_action,
            # toolbar_icons.redo_icon(),
            # "Redo (Ctrl+Shift+Z)",
        # )

        # -- Undo / Redo ----------------------------------------------
        undo_icon, redo_icon = self._undo_redo_icons()
        add_button(
            self._undo_action, undo_icon, "Undo (Ctrl+Z)"
        )
        add_button(
            self._redo_action, redo_icon, "Redo (Ctrl+Shift+Z)"
        )

        toolbar.addSeparator()

        # -- Zoom / Best Fit --------------------------------------------
        zoom_menu = QMenu(self)
        zoom_menu.addAction(self._zoom_in_action)
        zoom_menu.addAction(self._zoom_out_action)
        zoom_menu.addAction(self._reset_zoom_action)
        zoom_menu.addSeparator()
        for preset_action in self._zoom_preset_actions:
            zoom_menu.addAction(preset_action)
        add_menu_button(
            toolbar_icons.zoom_icon(), 
            "Scroll the mouse wheel to zoom", 
            zoom_menu)

        add_button(
            self._best_fit_action,
            toolbar_icons.best_fit_icon(),
            "Best Fit (Ctrl+F)",
        )

        toolbar.addSeparator()

        # Refresh shares its View-menu QAction, like every button below.
        add_button(
            self._refresh_action, toolbar_icons.refresh_icon(), "Refresh (F5)"
        )

        # -- Panels - each button shares its View-menu QAction, so
        # toggling one from either place keeps the other in sync.
        add_button(
            self._show_rulers_action, 
            toolbar_icons.rules_icon(), 
            "Show Rulers (F6)"
        )
        add_button(
            self._shapes_visible_action,
            toolbar_icons.shapes_icon(),
            "Shapes (F7)",
        )
        add_button(
            self._layers_visible_action,
            toolbar_icons.layers_icon(),
            "Layers (F8)",
        )
        add_button(
            self._diagram_tree_action,
            toolbar_icons.diagram_tree_icon(),
            "Diagram Tree (F10)",
        )

        toolbar.addSeparator()

        # -- Grid / snapping / connection points -----------------------
        add_button(
            self._show_grid_action, toolbar_icons.show_grid_icon(), "Show Grid"
        )
        add_button(
            self._snap_to_grid_action,
            toolbar_icons.snap_to_grid_icon(),
            "Snap to Grid",
        )
        add_button(
            self._snap_to_objects_action,
            toolbar_icons.snap_to_objects_icon(),
            "Snap to Objects",
        )
        add_button(
            self._show_conn_points_action,
            toolbar_icons.show_connections_icon(),
            "Show Connections",
        )

        toolbar.addSeparator()

        # -- Stacking order -----------------------------------------
        # One drop-down holding the four z-order actions, which are the
        # same QActions as Objects menu's (so shortcuts and behavior
        # live in one place).
        stacking_menu = QMenu(self)

        for action, tooltip in (
            (self._send_to_back_action, "Send to Back (Ctrl+Shift+B)"),
            (self._bring_to_front_action, "Bring to Front (Ctrl+Shift+F)"),
            (self._send_backward_action, "Send Backwards (Ctrl+Down)"),
            (self._bring_forward_action, "Bring Forwards (Ctrl+Up)"),
        ):
            action.setToolTip(tooltip)
            stacking_menu.addAction(action)

        add_menu_button(
            toolbar_icons.move_forward_backward_icon(),
            "Stacking Order",
            stacking_menu,
        )

        toolbar.addSeparator()

        # -- Grouping and alignment ---------------------------------
        add_button(
            self._group_action, toolbar_icons.group_icon(), "Group (Ctrl+G)"
        )
        add_button(
            self._ungroup_action,
            toolbar_icons.ungroup_icon(),
            "Ungroup (Ctrl+Shift+G)",
        )

        # Shares Objects -> Align's own QMenu.
        add_menu_button(
            toolbar_icons.align_icon(), "Align", self._align_menu
        )

        toolbar.addSeparator()

        # -- Position ---------------------------------------------------
        # App addition (not in the manual): shows/edits a selected
        # shape's position relative to the rulers' (0,0) origin.
        add_button(
            self._position_action,
            toolbar_icons.position_icon(),
            "Position...",
            icon_in_menu=True,
        )

        # -- Rotate / Flip ------------------------------------------
        # Clicking Rotate asks for an angle; Ctrl+R / Ctrl+Shift+R
        # turn the selection by +1 / -1 degree straight away.
        add_button(
            self._rotate_action,
            toolbar_icons.rotate_icon(),
            "Rotate... (Ctrl+R: +1\u00b0, Ctrl+Shift+R: -1\u00b0)",
            icon_in_menu=True,
        )

        add_menu_button(
            toolbar_icons.scale_icon(),
            "Scale (Ctrl(+Shift)+L/M: +(-)1% Horizontal/Vertical)",
            self._create_scale_menu(),
        )

        flip_menu = QMenu(self)
        flip_menu.addAction(self._flip_h_action)
        flip_menu.addAction(self._flip_v_action)
        add_menu_button(
            toolbar_icons.flip_icon(),
            "Flip selection (Ctrl+Shift+H: horizontal, "
            "Ctrl+Shift+V: vertical)",
            flip_menu,
        )

        toolbar.addSeparator()

        # -- Properties -----------------------------------------------
        add_button(
            self._properties_action,
            toolbar_icons.properties_icon(),
            "Properties (Alt+Enter)",
        )

        #toolbar.addSeparator()

        # Save as New Shape... (see save_selection_as_shape()); shares
        # Objects -> Save as New Shape...'s own QAction.
        add_button(
            self._save_shape_action,
            toolbar_icons.save_shape_icon(),
            "Save as New Shape...",
        )

        # Clean Up LaTeX Image Cache... (see clean_up_latex_cache()).
        add_button(
            self._cleanup_latex_cache_action,
            toolbar_icons.clean_icon(),
            "Clean Up LaTeX Image Cache...",
        )


        # -- Language / Help -------------------------------------------
        self._create_language_button(toolbar, icon_size)
        add_button(self._help_action, toolbar_icons.help_icon(), "Help (F1)")

        self.tools_toolbar = toolbar
        self.addToolBar(toolbar)

    def _undo_redo_icons(self):
        """(undo_icon, redo_icon) for the current language.

        In Arabic (RTL) the arrows are swapped - the arrow that curves
        back-to-the-left is shown on the Undo button and the one that
        curves forward-to-the-right on the Redo button, matching the
        reversed reading direction.
        """
        if tr.is_rtl():
            return toolbar_icons.redo_icon(), toolbar_icons.undo_icon()
        return toolbar_icons.undo_icon(), toolbar_icons.redo_icon()

    def _refresh_undo_redo_icons(self):
        """(Re-)apply the undo/redo arrow icons for the current language.

        Called once from _create_toolbar() so a session already started
        in Arabic shows the swapped icons immediately, and again from
        _set_language() so a live switch flips them too. Both the
        Edit-menu entries and the toolbar buttons share these QActions,
        so one setIcon() per action is enough.
        """
        if not hasattr(self, "_undo_action"):
            return
        undo_icon, redo_icon = self._undo_redo_icons()
        self._undo_action.setIcon(undo_icon)
        self._redo_action.setIcon(redo_icon)

    def _create_toolbox(self):
        """
        Left-hand dock laid out like Dia's toolbox:
        - a small grid of general tool-mode icons at top (pointer,
          zoom, pan, text)
        - a shape-category dropdown ("Basic", ...) below it
        - a grid of per-category shape icons under that
        """

        dock = QDockWidget("Shapes", self)
        # See ToolsToolbar's setObjectName() above for why.
        dock.setObjectName("ShapesDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        dock.setMinimumWidth(160)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addLayout(self._build_mode_grid())

        self._category_combo = QComboBox()
        layout.addWidget(self._category_combo)

        self._shape_stack = QStackedWidget()

        # App addition (not in the manual): wraps every category's
        # shape grid - built-in and custom alike - in one shared
        # scroll area, so a category that keeps growing (Objects ->
        # Save as New Shape..., saved repeatedly into the same
        # category) scrolls internally instead of forcing the dock,
        # and with it the whole main window, to keep growing taller
        # to fit every button at once. Without this, a large enough
        # category could demand more height than the screen actually
        # has, which is what was producing Qt's own
        # "QWindowsWindow::setGeometry: Unable to set geometry..."
        # warning and a squashed, broken-looking window layout.
        # setWidgetResizable(True) lets the stack's width track the
        # scroll area's viewport (so it isn't stuck at its own
        # sizeHint width, which would otherwise add a pointless
        # horizontal scrollbar); _build_shape_grid()'s trailing
        # setRowStretch() keeps a short category's buttons pinned to
        # the top of that extra width-driven height instead of
        # spreading out to fill it.
        shape_scroll = QScrollArea()
        shape_scroll.setWidget(self._shape_stack)
        shape_scroll.setWidgetResizable(True)
        shape_scroll.setFrameShape(QScrollArea.NoFrame)
        shape_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        shape_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(shape_scroll, 1)

        categories = [
            ("Basic", [
                ("Rectangle", icons.rectangle_icon()),
                ("Ellipse", icons.ellipse_icon()),
                ("Plot", icons.plot_icon()),
                ("Polygon", icons.polygon_icon()),
                ("Beziergon", icons.beziergon_icon()),
                ("Line", icons.line_icon()),
                ("Arc", icons.arc_icon()),
                ("Polyline", icons.polyline_icon()),
                ("Zigzagline", icons.zigzagline_icon()),
                ("Bezierline", icons.bezierline_icon()),
                ("Image", icons.image_icon()),
                ("Mask", icons.mask_icon()),
            ]),
            ("Flowchart", [
                ("Process", icons.rectangle_icon()),
                ("Decision", icons.diamond_icon()),
                ("Database", icons.cylinder_icon()),
                ("Data (I/O)", icons.data_icon()),
                ("Predefined Process", icons.predefined_process_icon()),
                ("Preparation", icons.preparation_icon()),
                ("Document", icons.document_icon()),
                ("Delay", icons.delay_icon()),
                ("Summing Junction", icons.summing_junction_icon()),
                ("Arrow Reference", icons.arrow_reference_icon()),
                ("Paper Tape", icons.paper_tape_icon()),
                ("Data Storage", icons.data_storage_icon()),
            ]),
            ("UML", [
                ("Class", icons.class_icon()),
                ("Interface", icons.interface_icon()),
                ("Actor", icons.actor_icon()),
                ("Package", icons.package_icon()),
                ("Component", icons.component_icon()),
                ("Node", icons.node_icon()),
                ("Note", icons.note_icon()),
                ("Lifeline", icons.lifeline_icon()),
                ("Required Interface", icons.required_interface_icon()),
                ("Enumeration", icons.enumeration_icon()),
                ("Artifact", icons.artifact_icon()),
                ("Frame", icons.frame_icon()),
            ]),
            ("Assorted", [
                ("Square", icons.square_icon()),
                ("Circle", icons.circle_icon()),
                ("Polygon", icons.polygon_icon(), "Regular Polygon"),
                ("Star", icons.star_icon()),
                ("Spiral", icons.spiral_icon()),
                ("Three-Quarter Circle", icons.circle_section_icon()),
                ("Crescent", icons.crescent_icon()),
                ("Spring", icons.spring_icon()),
                ("L-shape", icons.l_shape_icon()),
                ("Isosceles Triangle", icons.isosceles_triangle_icon()),
                ("Right Triangle", icons.right_triangle_icon()),
                ("Cross", icons.cross_icon()),
            ]),
        ]

        for name, shapes in categories:
            self._category_combo.addItem(name)
            self._shape_stack.addWidget(
                self._build_shape_grid(shapes)
            )

        self._category_combo.currentIndexChanged.connect(
            self._shape_stack.setCurrentIndex
        )

        # User-defined categories (app addition, not in the manual):
        # one more combo entry/stacked page per subfolder found under
        # the custom-shapes root - see app/custom_shapes.py.
        self._load_custom_shape_categories()

        layout.addWidget(self._build_defaults_panel())

        dock.setWidget(container)
        self.shapes_dock = dock
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _build_defaults_panel(self):
        """
        Manual 4.1.7, "Default Color, Line Width, and Line Style": the
        bottom of the Toolbox sets default properties for objects not
        yet created (self.scene.defaults, applied by DiagramScene.
        apply_defaults() - see canvas/tools.py). Changing these never
        touches shapes already on the canvas.
        """

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        colors_row = QHBoxLayout()

        self._fg_color_btn = _color_button(self.scene.defaults["border_color"])
        self._fg_color_btn.setToolTip("Default foreground (line) color")
        self._fg_color_btn.clicked.disconnect()
        self._fg_color_btn.clicked.connect(self._pick_default_border_color)

        self._bg_color_btn = _color_button(self.scene.defaults["fill_color"])
        self._bg_color_btn.setToolTip("Default background (fill) color")
        self._bg_color_btn.clicked.disconnect()
        self._bg_color_btn.clicked.connect(self._pick_default_fill_color)

        restore_btn = QToolButton()
        restore_btn.setIcon(icons.restore_colors_icon())
        restore_btn.setAutoRaise(True)
        restore_btn.setToolTip("Restore default colors")
        restore_btn.clicked.connect(self._restore_default_colors)

        reverse_btn = QToolButton()
        reverse_btn.setIcon(icons.reverse_colors_icon())
        reverse_btn.setAutoRaise(True)
        reverse_btn.setToolTip("Reverse colors")
        reverse_btn.clicked.connect(self._reverse_default_colors)

        colors_row.addWidget(self._fg_color_btn)
        colors_row.addWidget(self._bg_color_btn)
        colors_row.addWidget(restore_btn)
        colors_row.addWidget(reverse_btn)
        layout.addLayout(colors_row)

        width_row = QHBoxLayout()
        width_group = QButtonGroup(panel)

        for width in (1, 2, 4, 6, 8):
            btn = QToolButton()
            btn.setIcon(icons.line_width_icon(width))
            btn.setAutoRaise(True)
            btn.setCheckable(True)
            btn.setChecked(width == self.scene.defaults["line_width"])
            btn.setToolTip(f"{width}px line width")
            btn.clicked.connect(
                lambda checked, w=width: self._set_default_line_width(w)
            )
            width_group.addButton(btn)
            width_row.addWidget(btn)

        layout.addLayout(width_row)

        style_combo = _option_combo(
            LINE_STYLES, LINE_STYLE_LABELS, self.scene.defaults["line_style"]
        )
        style_combo.setToolTip("Default line style")
        style_combo.currentIndexChanged.connect(
            lambda _i: self._set_default_line_style(style_combo.currentData())
        )
        layout.addWidget(style_combo)

        arrows_row = QHBoxLayout()

        start_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, self.scene.defaults["start_arrow"]
        )
        start_combo.setToolTip("Default start arrow")
        start_combo.currentIndexChanged.connect(
            lambda _i: self._set_default_start_arrow(start_combo.currentData())
        )

        end_combo = _option_combo(
            ARROW_STYLES, ARROW_STYLE_LABELS, self.scene.defaults["end_arrow"]
        )
        end_combo.setToolTip("Default end arrow")
        end_combo.currentIndexChanged.connect(
            lambda _i: self._set_default_end_arrow(end_combo.currentData())
        )

        arrows_row.addWidget(start_combo)
        arrows_row.addWidget(end_combo)
        layout.addLayout(arrows_row)

        return panel

    def _pick_default_fill_color(self):
        from items.color_picker import pick_color_or_gradient
        chosen = pick_color_or_gradient(
            self, "Default Background Color", self.scene.defaults["fill_color"]
        )
        if chosen is not None:
            self.scene.defaults["fill_color"] = chosen
            self._refresh_default_color_swatches()
    def _pick_default_border_color(self):
        from items.color_picker import pick_color_or_gradient
        chosen = pick_color_or_gradient(
            self, "Default Foreground Color", self.scene.defaults["border_color"]
        )
        if chosen is not None:
            self.scene.defaults["border_color"] = chosen
            self._fg_color_btn.color = chosen
            self._refresh_default_color_swatches()

    def _refresh_default_color_swatches(self):
        from items.color_picker import copy_color_value, paint_swatch

        for btn, color in (
            (self._fg_color_btn, self.scene.defaults["border_color"]),
            (self._bg_color_btn, self.scene.defaults["fill_color"]),
        ):
            btn.color = copy_color_value(color)
            btn.setIcon(paint_swatch(btn.color))

    def _restore_default_colors(self):
        """Manual Figure 4.8: reset to Dia's own factory defaults."""

        self.scene.defaults["fill_color"] = QColor("#ffffff")
        self.scene.defaults["border_color"] = QColor("#000000")
        self._refresh_default_color_swatches()

    def _reverse_default_colors(self):
        """Manual Figure 4.9: swap the default foreground/background."""

        fg = self.scene.defaults["border_color"]
        bg = self.scene.defaults["fill_color"]
        self.scene.defaults["border_color"] = bg
        self.scene.defaults["fill_color"] = fg
        self._refresh_default_color_swatches()

    def _set_default_line_width(self, width):
        self.scene.defaults["line_width"] = width

    def _set_default_line_style(self, style):
        self.scene.defaults["line_style"] = style

    def _set_default_start_arrow(self, style):
        self.scene.defaults["start_arrow"] = style

    def _set_default_end_arrow(self, style):
        self.scene.defaults["end_arrow"] = style

    def _create_layers_panel(self):
        """
        Manual Chapter 10: a dockable panel listing every layer in the
        diagram, each with a checkbox for visibility (the "Eye Icon",
        10.3), reorder/new/delete buttons, and double-click to rename.
        Clicking a row makes that the current layer - new objects go
        there, and only its objects can be selected (10.2.2).

        The visibility checkbox is a real embedded QCheckBox (via
        setItemWidget), not the list item's own built-in checkbox.
        Qt's default item-view behavior selects a row when you click
        anywhere in it, checkbox included, which would otherwise make
        toggling a layer's visibility silently switch the *current*
        layer too (confirmed while testing this the first way). A
        separate child widget intercepts its own clicks, so toggling
        visibility can never affect row selection at all.
        """

        dock = QDockWidget("Layers", self)
        # See ToolsToolbar's setObjectName() in _create_toolbar() above
        # for why.
        dock.setObjectName("LayersDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # Give the dock a small, user-draggable minimum instead of
        # letting its contents dictate one - see below.
        dock.setMinimumWidth(160)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        self.layers_list = QListWidget()
        # The embedded row widgets (checkbox + label) give the view a
        # content-driven minimumSizeHint; Ignored tells the layout to
        # disregard it, so the dock's own minimumWidth is what counts.
        self.layers_list.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Expanding
        )
        self.layers_list.setMinimumWidth(0)
        self.layers_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.layers_list.currentRowChanged.connect(self._on_layer_row_changed)
        layout.addWidget(self.layers_list)
        button_row = QHBoxLayout()
        button_row.setSpacing(2)
        button_defs = [
            ("New", self.new_layer),
            ("Up", self.move_layer_up),
            ("Down", self.move_layer_down),
            ("Del", self.delete_layer),
        ]
        for text, slot in button_defs:
            button = QToolButton()
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            # A QPushButton's minimumSizeHint is text+padding and can't
            # be talked down; a QToolButton with an Ignored minimum can,
            # so the four of them no longer force the dock wide.
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Ignored, QSizePolicy.Fixed
            )
            button.clicked.connect(slot)
            button_row.addWidget(button)
        layout.addLayout(button_row)
        dock.setWidget(container)
        self.layers_dock = dock
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._refresh_layers_list()

    def _refresh_layers_list(self):
        manager = self.scene.layer_manager

        self.layers_list.blockSignals(True)
        self.layers_list.clear()

        # Manual's own Layers dialog lists layers top-of-stack first.
        for layer in reversed(manager.layers):
            item = QListWidgetItem()
            self.layers_list.addItem(item)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 0, 4, 0)
            row_layout.setSpacing(6)

            checkbox = QCheckBox()
            checkbox.setChecked(layer.visible)

            checkbox.toggled.connect(
                lambda checked, l=layer: self._on_layer_visibility_toggled(
                    l, checked
                )
            )

            label = _LayerNameLabel(layer.name)
            label.doubleClicked.connect(
                lambda l=layer: self._rename_layer_by_reference(l)
            )

            row_layout.addWidget(checkbox)
            row_layout.addWidget(label, 1)

            self.layers_list.setItemWidget(item, row_widget)

        current_row = (
            len(manager.layers) - 1 - manager.current_index
        )
        self.layers_list.setCurrentRow(current_row)

        self.layers_list.blockSignals(False)

    def _row_to_layer_index(self, row):
        return len(self.scene.layer_manager.layers) - 1 - row

    def _on_layer_visibility_toggled(self, layer, visible):
        if layer not in self.scene.layer_manager.layers:
            return

        index = self.scene.layer_manager.layers.index(layer)
        self.scene.layer_manager.set_visible(index, visible)

    def _on_layer_row_changed(self, row):
        if row < 0:
            return

        index = self._row_to_layer_index(row)
        self.scene.layer_manager.set_current(index)
        self.statusBar().showMessage(
            f"Current layer: {self.scene.layer_manager.current_layer().name}"
        )

    def _rename_layer_by_reference(self, layer):
        if layer not in self.scene.layer_manager.layers:
            return

        index = self.scene.layer_manager.layers.index(layer)

        name, ok = QInputDialog.getText(
            self, "Rename Layer", "Layer name:", text=layer.name
        )

        if ok and name.strip():
            self.scene.layer_manager.rename_layer(index, name.strip())
            self._refresh_layers_list()

    def new_layer(self):
        name, ok = QInputDialog.getText(
            self, "New Layer", "Layer name:",
            text=f"Layer {len(self.scene.layer_manager.layers) + 1}"
        )

        if not ok or not name.strip():
            return

        self.scene.layer_manager.add_layer(name.strip())
        self._refresh_layers_list()

    def delete_layer(self):
        row = self.layers_list.currentRow()

        if row < 0:
            return

        if len(self.scene.layer_manager.layers) <= 1:
            self.statusBar().showMessage("Can't delete the last layer")
            return

        index = self._row_to_layer_index(row)
        self.scene.layer_manager.delete_layer(index)
        self._refresh_layers_list()

    def move_layer_up(self):
        row = self.layers_list.currentRow()

        if row < 0:
            return

        index = self._row_to_layer_index(row)
        self.scene.layer_manager.move_layer_up(index)
        self._refresh_layers_list()

    def move_layer_down(self):
        row = self.layers_list.currentRow()

        if row < 0:
            return

        index = self._row_to_layer_index(row)
        self.scene.layer_manager.move_layer_down(index)
        self._refresh_layers_list()

    # -- diagram tree (manual 4.5) -------------------------------------

    def _create_diagram_tree_panel(self):
        """
        Manual 4.5: "displays a list of all objects in the diagram...
        By right-clicking on an object, you can perform a number of
        operations" - Locate, Properties, Hide this type, Show object
        type (4.5.2). Sort options (by name/type/as inserted) aren't
        included: this clone has no meaningful "name" per object and
        insertion order isn't tracked, so only the operations that
        apply cleanly here are implemented.
        """

        self._hidden_diagram_tree_types = set()

        dock = QDockWidget("Diagram Tree", self)
        # See ToolsToolbar's setObjectName() in _create_toolbar() above
        # for why.
        dock.setObjectName("DiagramTreeDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setMinimumWidth(160)
        self.diagram_tree_dock = dock

        self.diagram_tree = QTreeWidget()
        self.diagram_tree.setHeaderHidden(True)

        self.diagram_tree.setSizePolicy(
            QSizePolicy.Ignored, QSizePolicy.Expanding
        )
        self.diagram_tree.setMinimumWidth(0)
        self.diagram_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # App addition (not in the manual): lets Shift/Ctrl-click
        # build up a multi-selection here, the same way it does on the
        # canvas - mainly so "Group (Ctrl+G)" can be driven from the
        # tree (see _on_diagram_tree_selection_changed below).
        self.diagram_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.diagram_tree.itemSelectionChanged.connect(
            self._on_diagram_tree_selection_changed
        )

        # App addition (not in the manual): F2 or right-click ->
        # Rename lets each item's label be edited in place (see
        # eventFilter() and _show_diagram_tree_context_menu() below);
        # this picks up the result once editing finishes.
        self.diagram_tree.itemChanged.connect(
            self._on_diagram_tree_item_changed
        )

        self.diagram_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.diagram_tree.customContextMenuRequested.connect(
            self._show_diagram_tree_context_menu
        )

        # App addition (not in the manual): Ctrl+Up/Down reorders the
        # selected item's stacking position - see eventFilter() and
        # _diagram_tree_move_selected() below.
        self.diagram_tree.installEventFilter(self)

        dock.setWidget(self.diagram_tree)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self._refresh_diagram_tree()

    def _diagram_tree_label(self, item):
        # App addition (not in the manual): a user-given name (F2 or
        # right-click -> Rename - see _on_diagram_tree_item_changed())
        # takes over the tree's usual type-based label entirely.
        if item.custom_name:
            return item.custom_name

        if isinstance(item, TextItem):
            text = item.text().strip()
            return f"Text: {text[:24]}" if text else "Text"

        if isinstance(item, GroupItem):
            return f"Group ({len(item._children)} objects)"

        if isinstance(item, ClassItem):
            return f"Class: {item.class_name}"

        if isinstance(item, StencilItem):
            return item.LABEL

        for type_name, cls in (
            ("Rectangle", RectangleItem),
            ("Ellipse", EllipseItem),
            ("Polygon", PolygonItem),
            ("Beziergon", BeziergonItem),
            ("Decision", DiamondItem),
            ("Database", CylinderItem),
            ("Actor", ActorItem),
            ("Interface", InterfaceItem),
            ("Image", ImageItem),
            ("Arc", ArcItem),
            ("Zigzagline", ZigzaglineItem),
            ("Polyline", PolylineItem),
            ("Bezierline", BezierlineItem),
            ("Line", LineItem),
            ("Square", SquareItem),
            ("Circle", CircleItem),
            ("Polygon", RegularPolygonItem),
            ("Star", StarItem),
            ("Spiral", SpiralItem),
            ("Three-Quarter Circle", CircleSectionItem),
            ("Isosceles Triangle", IsoscelesTriangleItem),
            ("Right Triangle", RightTriangleItem),
            ("Cross", CrossItem),
        ):
            if isinstance(item, cls):
                return type_name

        return type(item).__name__

    def _refresh_diagram_tree(self):
        if not hasattr(self, "diagram_tree"):
            return

        self.diagram_tree.blockSignals(True)
        self.diagram_tree.clear()

        top_level = [
            i for i in self.scene.items()
            if isinstance(i, DiagramItem) and i.parentItem() is None
        ]

        # Front-most first (manual has no equivalent - this ordering,
        # and the Ctrl+Up/Down reordering it enables, are both app
        # additions). scene.items() is already in front-to-back order
        # and correctly resolves ties for same-zValue items (see
        # GroupItemsCommand's own note on this) - filtering it rather
        # than sorting top_level by zValue() directly.
        top_level_set = set(top_level)
        top_level = [i for i in self.scene.items() if i in top_level_set]

        for item in top_level:
            type_name = type(item).__name__

            if type_name in self._hidden_diagram_tree_types:
                continue

            tree_item = QTreeWidgetItem([self._diagram_tree_label(item)])
            tree_item.setData(0, Qt.UserRole, item)
            # App addition (not in the manual): F2 / right-click ->
            # Rename edits this label in place - see
            # _on_diagram_tree_item_changed().
            tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)
            self.diagram_tree.addTopLevelItem(tree_item)

            if isinstance(item, GroupItem):
                children = sorted(
                    item._children,
                    key=lambda c: self.scene.layer_manager.local_z(c),
                    reverse=True
                )

                for child in children:
                    child_type = type(child).__name__

                    if child_type in self._hidden_diagram_tree_types:
                        continue

                    child_tree_item = QTreeWidgetItem(
                        [self._diagram_tree_label(child)]
                    )
                    child_tree_item.setData(0, Qt.UserRole, child)
                    child_tree_item.setFlags(
                        child_tree_item.flags() | Qt.ItemIsEditable
                    )
                    tree_item.addChild(child_tree_item)

        self.diagram_tree.expandAll()
        self.diagram_tree.blockSignals(False)

    def _on_diagram_tree_item_changed(self, tree_item, column):
        """
        App addition (not in the manual): fires once inline editing
        (F2 or right-click -> Rename) finishes. An empty name reverts
        to the usual type-based label instead of leaving a blank row.
        Pushed onto the undo stack like any other edit; the tree's own
        text is then normalized via _refresh_diagram_tree() (covers
        both the "reverted to blank" case and stray leading/trailing
        whitespace) whether or not the name actually changed.
        """

        if column != 0:
            return

        item = tree_item.data(0, Qt.UserRole)

        if item is None:
            return

        new_name = tree_item.text(0).strip() or None
        old_name = item.custom_name

        if new_name != old_name:
            self.scene.undo_stack.push(
                RenameItemCommand(item, old_name, new_name, "Rename")
            )

        self._refresh_diagram_tree()
        self._reselect_diagram_tree_item(item)

    def _diagram_tree_selectable_target(self, item):
        """Non-selectable children (i.e. inside a group) resolve to
        the enclosing group instead - a child isn't independently
        selectable in the scene while grouped."""

        if not (item.flags() & item.ItemIsSelectable) and item.parentItem() is not None:
            return item.parentItem()

        return item

    def _locate_diagram_tree_item(self, item):
        """
        Manual 4.5.2, "Locate": "will bring the selected object into
        view on the canvas." Selecting a group's child selects (and
        centers on) the group itself instead, since children aren't
        independently selectable while grouped.
        """

        target = self._diagram_tree_selectable_target(item)

        self.scene.clearSelection()
        target.setSelected(True)
        self.view.centerOn(target)

    def _on_diagram_tree_selection_changed(self):
        """
        App addition (not in the manual): keeps the scene's selection
        in sync with the tree's, rather than just the single
        just-clicked item - Shift/Ctrl-click here builds up a
        multi-selection the same way it does on the canvas, so
        Group (Ctrl+G) and the rest of the Objects menu (all of which
        read scene.selectedItems() via _selected_shapes()) work the
        same regardless of where the selection was made. Only
        recenters the view when exactly one item ends up selected -
        jumping the view on every click of a multi-select would be
        disorienting.
        """

        targets = []

        for tree_item in self.diagram_tree.selectedItems():
            item = tree_item.data(0, Qt.UserRole)

            if item is None:
                continue

            target = self._diagram_tree_selectable_target(item)

            if target not in targets:
                targets.append(target)

        self.scene.clearSelection()

        for target in targets:
            target.setSelected(True)

        if len(targets) == 1:
            self.view.centerOn(targets[0])

    def eventFilter(self, obj, event):
        # Objects -> Send Backwards / Bring Forwards own Ctrl+Down /
        # Ctrl+Up window-wide. While the Diagram Tree has focus it must
        # keep reordering its own rows instead, so it claims those two
        # keys here (an accepted ShortcutOverride is delivered as a
        # normal KeyPress, handled just below, rather than firing the
        # shortcut).
        if (
            obj is self.diagram_tree
            and event.type() == QEvent.ShortcutOverride
            and event.modifiers() == Qt.ControlModifier
            and event.key() in (Qt.Key_Up, Qt.Key_Down)
        ):
            event.accept()
            return True

        if (
            obj is self.diagram_tree
            and event.type() == QEvent.KeyPress
            and event.modifiers() & Qt.ControlModifier
            and event.key() in (Qt.Key_Up, Qt.Key_Down)
        ):
            self._diagram_tree_move_selected(event.key() == Qt.Key_Up)
            return True

        # App addition (not in the manual): F2 renames the current
        # Diagram Tree item in place, same as Rename on its context
        # menu (_show_diagram_tree_context_menu below).
        if (
            obj is self.diagram_tree
            and event.type() == QEvent.KeyPress
            and event.key() == Qt.Key_F2
        ):
            tree_item = self.diagram_tree.currentItem()

            if tree_item is not None:
                self.diagram_tree.editItem(tree_item, 0)

            return True

        return super().eventFilter(obj, event)

    def _diagram_tree_siblings(self, tree_item):
        """
        The z-ordered (front-first, matching the tree's own display
        order) list that `tree_item`'s underlying object currently
        belongs to: either the whole diagram's top-level items, or -
        if tree_item is nested under a group - just that group's
        children.
        """

        parent_tree_item = tree_item.parent()

        if parent_tree_item is not None:
            group = parent_tree_item.data(0, Qt.UserRole)

            return sorted(
                group._children,
                key=lambda c: self.scene.layer_manager.local_z(c),
                reverse=True
            )

        siblings = [
            i for i in self.scene.items()
            if isinstance(i, DiagramItem) and i.parentItem() is None
        ]

        # Same reasoning as _refresh_diagram_tree: filter scene.items()
        # (already front-to-back, ties resolved) rather than sort by
        # zValue() directly, which can't tell same-z items apart.
        siblings_set = set(siblings)
        siblings = [i for i in self.scene.items() if i in siblings_set]

        return siblings

    def _diagram_tree_move_selected(self, move_up):
        """
        App addition (not in the manual): Ctrl+Up/Down in the Diagram
        Tree swaps the selected item's stacking position with its
        neighbor in the same list - the whole top-level list, or a
        group's sublist if the selected item is one of its children.
        "Up" moves toward the front (earlier in the tree, which lists
        frontmost first - see _refresh_diagram_tree). Swapping a
        Group's own entry moves the whole group (all its children
        along with it) as one unit relative to its top-level
        siblings, without touching anything inside the group.
        """

        tree_item = self.diagram_tree.currentItem()

        if tree_item is None:
            return

        item = tree_item.data(0, Qt.UserRole)

        if item is None:
            return

        siblings = self._diagram_tree_siblings(tree_item)

        try:
            index = siblings.index(item)
        except ValueError:
            return

        neighbor_index = index - 1 if move_up else index + 1

        if neighbor_index < 0 or neighbor_index >= len(siblings):
            return

        self.scene.undo_stack.push(
            SwapZOrderCommand(
                self.scene.layer_manager, siblings, index, neighbor_index, "Reorder"
            )
        )

        self._refresh_diagram_tree()
        self._reselect_diagram_tree_item(item)
        self._locate_diagram_tree_item(item)

    def _reselect_diagram_tree_item(self, target):
        def find(tree_item):
            if tree_item.data(0, Qt.UserRole) is target:
                return tree_item

            for i in range(tree_item.childCount()):
                found = find(tree_item.child(i))

                if found is not None:
                    return found

            return None

        for i in range(self.diagram_tree.topLevelItemCount()):
            found = find(self.diagram_tree.topLevelItem(i))

            if found is not None:
                self.diagram_tree.setCurrentItem(found)
                return

    def _show_diagram_tree_context_menu(self, pos):
        tree_item = self.diagram_tree.itemAt(pos)
        menu = QMenu(self)
        item = tree_item.data(0, Qt.UserRole) if tree_item else None

        if item is not None:
            locate_action = menu.addAction("Locate")
            locate_action.triggered.connect(
                lambda: self._locate_diagram_tree_item(item)
            )

            # App addition (not in the manual): same rename as F2
            # (see eventFilter above) reached from the context menu.
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(
                lambda: self.diagram_tree.editItem(tree_item, 0)
            )

            properties_action = menu.addAction("Properties")
            properties_action.triggered.connect(
                lambda: edit_shape_properties(item, self.scene)
            )
            properties_action.setEnabled(
                isinstance(item, (
                    RectangleItem, EllipseItem, DiamondItem, CylinderItem,
                    ActorItem, InterfaceItem, ClassItem, LineItem,
                    StencilItem
                ))
            )

            menu.addSeparator()

            type_name = type(item).__name__
            hide_action = menu.addAction(
                f"Hide this type ({self._diagram_tree_label(item)})"
            )
            hide_action.triggered.connect(
                lambda: self._hide_diagram_tree_type(type_name)
            )

        if self._hidden_diagram_tree_types:
            show_menu = menu.addMenu("Show object type")

            for hidden_type in sorted(self._hidden_diagram_tree_types):
                action = show_menu.addAction(hidden_type)
                action.triggered.connect(
                    lambda checked, t=hidden_type: self._show_diagram_tree_type(t)
                )

        if not menu.isEmpty():
            menu.exec_(self.diagram_tree.viewport().mapToGlobal(pos))

    def _hide_diagram_tree_type(self, type_name):
        self._hidden_diagram_tree_types.add(type_name)
        self._refresh_diagram_tree()

    def _show_diagram_tree_type(self, type_name):
        self._hidden_diagram_tree_types.discard(type_name)
        self._refresh_diagram_tree()

    def _build_mode_grid(self):
        grid = QGridLayout()
        grid.setSpacing(2)

        mode_defs = [
            ("Select", icons.select_icon(), None),
            #("Zoom", icons.zoom_icon(), "Scroll the mouse wheel to zoom"),
            ("Text", icons.text_icon(), None),
            ("Pan", icons.pan_icon(), "Drag with the left mouse button to move the canvas"),
            (
                "Anchor",
                icons.anchor_icon(),
                "Select a shape, then click to add a connection point",
            ),
        ]

        for i, (label, icon, hint) in enumerate(mode_defs):
            button = QToolButton()
            button.setIcon(icon)
            button.setIconSize(icons.ICON_SIZE)
            button.setAutoRaise(True)
            button.setToolTip(hint or label)

            row, col = divmod(i, 4)
            grid.addWidget(button, row, col)

            if label in self._tool_classes:
                button.setCheckable(True)

                button.clicked.connect(
                    lambda checked, label=label:
                        self.activate_tool(label)
                )

                self._register_tool_widget(label, button)

            else:
                button.clicked.connect(
                    lambda checked, hint=hint:
                        self.statusBar().showMessage(hint)
                )

        return grid


    def _build_shape_grid(self, shapes):
        """
        One category's page in self._shape_stack - a 3-column grid of
        shape buttons. The trailing setRowStretch() below adds an
        empty stretchy row after the last button row, so that when
        the scroll area added around _shape_stack in _create_toolbox()
        stretches this widget taller than its own contents (a short
        category, given a tall dock), the extra space collapses into
        that empty row instead of spreading the button rows themselves
        apart.
        """

        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setSpacing(2)

        for i, shape_def in enumerate(shapes):
            label, icon = shape_def[:2]
            tool_label = shape_def[2] if len(shape_def) > 2 else label
            button = QToolButton()
            button.setIcon(icon)
            button.setIconSize(icons.ICON_SIZE)
            button.setAutoRaise(True)
            button.setToolTip(label)

            row, col = divmod(i, 4)
            grid.addWidget(button, row, col)

            if tool_label in self._tool_classes:
                button.setCheckable(True)
                button.clicked.connect(
                    lambda checked, label=tool_label: self.activate_tool(label)
                )
                self._register_tool_widget(tool_label, button)
            else:
                button.clicked.connect(
                    lambda checked, label=label: self.statusBar().showMessage(
                        f"{label} isn't implemented yet"
                    )
                )

        last_row = (len(shapes) - 1) // 3 if shapes else 0
        grid.setRowStretch(last_row + 1, 1)

        return widget

    def _register_tool_widget(self, label, widget):
        self._tool_widgets.setdefault(label, []).append(widget)

    # -- user-defined shape categories (app addition, not in the ------
    # -- manual - see app/custom_shapes.py) ---------------------------

    def _load_custom_shape_categories(self):
        for name, folder in custom_shapes.list_categories(
            self._custom_shapes_root
        ):
            self._add_custom_shape_category(name, folder)

    def _add_custom_shape_category(self, category_name, folder):
        """
        Adds one new combo entry + stacked shape-grid page for a
        custom-shape category - either a folder found under the
        custom-shapes root at startup, or one just created by Save as
        New Shape... for a name that didn't exist yet.
        """

        self._custom_category_dir[category_name] = folder
        self._custom_category_index[category_name] = self._category_combo.count()

        self._category_combo.addItem(category_name)
        self._shape_stack.addWidget(
            self._build_custom_shape_grid(category_name, folder)
        )

    def _refresh_custom_shape_category(self, category_name):
        """
        Rebuilds an existing custom category's shape grid in place -
        used right after Save as New Shape... adds a shape to a
        category that already has a toolbox page, so the new button
        shows up immediately with no restart needed.
        """

        folder = self._custom_category_dir[category_name]
        index = self._custom_category_index[category_name]
        old_widget = self._shape_stack.widget(index)

        self._shape_stack.insertWidget(
            index, self._build_custom_shape_grid(category_name, folder)
        )
        self._shape_stack.removeWidget(old_widget)
        old_widget.deleteLater()

    def _build_custom_shape_grid(self, category_name, folder):
        """
        Builds one category's page of shape buttons from whatever
        .pdshape/.svg pairs are currently in `folder`, registering a
        CustomShapeTool (see canvas/tools.py) for each - reuses
        _build_shape_grid() exactly as the four built-in categories
        do, just fed shape defs assembled from disk instead of
        hardcoded in _create_toolbox().

        Purges this category's previous tool registrations first, so
        calling this again (a Save-as-New-Shape refresh) doesn't
        leave stale entries in self._tool_classes/_tool_widgets
        pointing at QToolButtons the old page's removeWidget() call
        is about to destroy.
        """

        prefix = f"Custom::{category_name}::"

        for label in [l for l in self._tool_classes if l.startswith(prefix)]:
            del self._tool_classes[label]

        for label in [l for l in self._tool_widgets if l.startswith(prefix)]:
            del self._tool_widgets[label]

        shapes = []

        for stem, shape_path, svg_path in custom_shapes.list_shapes(folder):
            icon = QIcon(svg_path) if svg_path else icons.square_icon()
            tool_label = f"{prefix}{stem}"

            self._tool_classes[tool_label] = functools.partial(
                CustomShapeTool, shape_path=shape_path, label=f'Place "{stem}"'
            )

            shapes.append((stem, icon, tool_label))

        return self._build_shape_grid(shapes)

    def save_selection_as_shape(self):
        """
        Objects -> Save as New Shape...: saves the current selection
        (one or more shapes, combined - each stays independently
        positioned relative to the others, see
        document_io.serialize_items) as a new entry in the user's
        shape library, in an existing or brand-new category, and adds
        it to the toolbox immediately.
        """

        items = self._selected_shapes()

        if not items:
            self.statusBar().showMessage(
                "Select one or more shapes to save as a new shape first"
            )
            return

        result = prompt_save_shape(
            self, sorted(self._custom_category_dir.keys())
        )

        if result is None:
            return

        category_name, shape_name = result
        is_new_category = category_name not in self._custom_category_dir

        try:
            folder = custom_shapes.ensure_category(
                self._custom_shapes_root, category_name
            )
        except OSError as exc:
            QMessageBox.warning(
                self, "Save as New Shape", f"Couldn't save the shape:\n{exc}"
            )
            return

        if custom_shapes.category_is_full(folder):
            QMessageBox.warning(
                self, "Save as New Shape",
                f'The "{category_name}" category already holds the '
                f"maximum of {custom_shapes.MAX_SHAPES_PER_CATEGORY} "
                "shapes. Please save this one under a new category "
                'instead (choose "New Category..." above) - each '
                "category is its own sub-folder under CustomShapes."
            )
            return

        try:
            _, _, stem = custom_shapes.save_shape(
                self.scene, items, folder, shape_name
            )
        except OSError as exc:
            QMessageBox.warning(
                self, "Save as New Shape", f"Couldn't save the shape:\n{exc}"
            )
            return

        if is_new_category:
            self._add_custom_shape_category(category_name, folder)
        else:
            self._refresh_custom_shape_category(category_name)

        self._category_combo.setCurrentIndex(
            self._custom_category_index[category_name]
        )

        self.statusBar().showMessage(
            f'Saved "{stem}" to the {category_name} category'
        )

    # def activate_tool(self, label):
        # """
        # Single place that switches the active drawing tool. Every
        # checkable widget representing a tool - toolbar action, mode
        # icon, shape icon, wherever it's registered - is kept in sync
        # here, rather than relying on any one QActionGroup/QButtonGroup
        # (there are several, one per widget group, and they don't know
        # about each other).
        # """

        # tool_cls = self._tool_classes[label]

        # if tool_cls is None:
            # self.scene.set_tool(None)
            # self.view.setDragMode(DiagramView.RubberBandDrag)
        # else:
            # self.scene.set_tool(tool_cls(self.scene))
            # self.view.setDragMode(DiagramView.NoDrag)

        # for lbl, widgets in self._tool_widgets.items():
            # for widget in widgets:
                # widget.setChecked(lbl == label)

        # self._current_tool_label = label

        # if label != "Select":
            # self._last_drawing_tool = label

        # self.statusBar().showMessage(f"{label} tool")

    def activate_tool(self, label):
        """
        Single place that switches the active drawing tool. Every
        checkable widget representing a tool - toolbar action, mode
        icon, shape icon, wherever it's registered - is kept in sync
        here, rather than relying on any one QActionGroup/QButtonGroup
        (there are several, one per widget group, and they don't know
        about each other).       
        Switch the active tool and keep all corresponding widgets synchronized.
        """

        tool_cls = self._tool_classes[label]

        if label == "Pan":
            # No drawing tool is active while panning.
            self.scene.set_tool(None)

            # Left-button dragging pans the scene.
            self.view.setDragMode(DiagramView.ScrollHandDrag)

        elif tool_cls is None:
            # Select mode.
            self.scene.set_tool(None)
            self.view.setDragMode(DiagramView.RubberBandDrag)

        else:
            # Drawing tool.
            self.scene.set_tool(tool_cls(self.scene))
            self.view.setDragMode(DiagramView.NoDrag)

        # App addition (not in the manual): the Anchor tool gets its
        # own "x"-shaped cursor (app/icons.py: anchor_cursor()) rather
        # than the ordinary arrow, so the cursor itself previews where
        # a click will add the point - reset to the default arrow for
        # every other tool, in case Anchor was active just before.
        if label == "Anchor":
            self.view.setCursor(icons.anchor_cursor())
        else:
            self.view.unsetCursor()

        # Synchronize toolbar/toolbox buttons.
        for lbl, widgets in self._tool_widgets.items():
            for widget in widgets:
                widget.blockSignals(True)
                widget.setChecked(lbl == label)
                widget.blockSignals(False)

        self._current_tool_label = label

        if label not in ("Select", "Pan"):
            self._last_drawing_tool = label

        if label == "Pan":
            self.statusBar().showMessage(
                "Pan mode: drag with the left mouse button"
            )
        else:
            self.statusBar().showMessage(f"{label} tool")


    def _toggle_tool(self):
        """
        Space key: swap between Select and the last-used drawing tool,
        so you can add several shapes of the same kind in a row without
        reaching for the mouse each time (manual 4.1.1 tip).
        """

        if self._current_tool_label == "Select":
            self.activate_tool(self._last_drawing_tool)
        else:
            self.activate_tool("Select")

    def new_document(self):
        # App addition (not in the manual): New now opens another tab
        # rather than resetting the current one in place - "Diagram
        # N.pydia", N incrementing each time (self._next_doc_number).
        self._add_document_tab()
        self.statusBar().showMessage("New document")

    def createPopupMenu(self):
        """
        Extend Qt's standard main-window context menu.

        Qt normally creates this menu from every toolbar/dock's
        ``toggleViewAction()``.  Keep that native menu intact, but insert
        our global panel-floating lock immediately before the Tools entry,
        giving the order: Shapes, Layers, Diagram Tree, Lock Panels, Tools.
        """
        menu = super().createPopupMenu()

        # createPopupMenu() may be called more than once during a session,
        # so make sure the custom action is present only once.
        if self._lock_panels_action not in menu.actions():
            tools_action = self.tools_toolbar.toggleViewAction()
            actions = menu.actions()
            if tools_action in actions:
                menu.insertAction(tools_action, self._lock_panels_action)
            else:
                menu.addAction(self._lock_panels_action)

        return menu

    def _set_panels_floating_locked(self, locked):
        """Enable/disable floating for the Shapes, Layers and Tree docks."""
        docks = (
            getattr(self, "shapes_dock", None),
            getattr(self, "layers_dock", None),
            getattr(self, "diagram_tree_dock", None),
        )

        for dock in docks:
            if dock is None:
                continue

            features = dock.features()

            if locked:
                # A panel must not remain detached after the lock is enabled.
                if dock.isFloating():
                    dock.setFloating(False)
                dock.setFeatures(features & ~QDockWidget.DockWidgetFloatable)
            else:
                dock.setFeatures(features | QDockWidget.DockWidgetFloatable)

    def _sync_dock_action(self, action, visible):
        action.blockSignals(True)
        action.setChecked(visible)
        action.blockSignals(False)

    def _sync_canvas_toggles(self):
        """
        Re-checks the View menu's canvas toggles and the status-bar
        Snap-to-Grid button against the scene's actual current state -
        needed after New Document (resets to defaults) and after
        Open (loads whatever the file had saved).
        """

        pairs = (
            (self._show_grid_action, self.scene.show_grid),
            (self._snap_to_grid_action, self.scene.snap_to_grid),
            (self._snap_to_objects_action, self.scene.snap_to_objects),
            (
                self._show_conn_points_action,
                self.scene.show_connection_points
            ),
        )

        for action, checked in pairs:
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)

        self._snap_to_grid_button.blockSignals(True)
        self._snap_to_grid_button.setChecked(self.scene.snap_to_grid)
        self._snap_to_grid_button.blockSignals(False)

    # -- loading / saving (manual Chapter 8) --------------------------

    def _update_window_title(self, clean=None):
        name = (
            os.path.basename(self.current_file_path)
            if self.current_file_path else self.tabs.currentWidget().default_name
        )

        if clean is None:
            clean = self.scene.undo_stack.isClean()

        dirty = "" if clean else "*"

        self.setWindowTitle(f"{dirty}{name} - PyDiagram")

    def save_to_path(self, path, container=None):
        """
        Saves `container`'s document (default: the current tab) to
        `path`. Taking the container explicitly is what lets Save All
        write background tabs without switching to each of them.
        """

        if container is None:
            container = self.tabs.currentWidget()

        document_io.save_scene(container.scene, path)
        container.file_path = path
        container.scene.undo_stack.setClean()

        if container is self.tabs.currentWidget():
            self._update_window_title()

        self._update_tab_label(container)
        self._update_empty_hint(container)
        self._add_recent_file(path)
        self.statusBar().showMessage(f"Saved to {path}")

    def load_from_path(self, path):
        document_io.load_scene(path, self.scene)
        # The loader restores the persistent document ID when the file
        # has one.  Keep the tab container and scene IDs synchronized so
        # PDF link destination lookup sees exactly the same identity.
        self.tabs.currentWidget().document_id = getattr(
            self.scene, "document_id", self.tabs.currentWidget().document_id
        )
        self.current_file_path = path
        self.scene.undo_stack.setClean()
        self.activate_tool("Select")
        self._sync_canvas_toggles()
        self._refresh_layers_list()
        self._refresh_diagram_tree()
        self._update_properties_action_text()
        self._update_window_title()
        self._update_tab_label(self.tabs.currentWidget())
        self._update_empty_hint(self.tabs.currentWidget())
        self._add_recent_file(path)
        self.statusBar().showMessage(f"Opened {path}")

    def save_document(self):
        if self.current_file_path:
            self.save_to_path(self.current_file_path)
        else:
            self.save_document_as()

    def _prompt_save_path(self, initial_name=""):
        """The Save As file picker; the chosen path, or None if cancelled."""

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagram", initial_name, "PyDiagram Files (*.pydia)"
        )

        if not path:
            return None

        if not path.endswith(".pydia"):
            path += ".pydia"

        return path

    def save_document_as(self):
        path = self._prompt_save_path()

        if path:
            self.save_to_path(path)

    def save_all_documents(self):
        """
        File -> Save All (app addition): saves every open diagram that
        has unsaved changes, in tab order, in a single operation.
        Diagrams that already have a file are written straight to it;
        a never-saved one is brought to the front and asks where to
        go (Save As), suggesting its tab name. Cancelling one of those
        pickers stops the operation there (the ones already written
        stay saved). A file that can't be written is reported at the
        end and doesn't stop the others.
        """

        original = self.tabs.currentWidget()
        saved_count = 0
        failures = []

        for index in range(self.tabs.count()):
            container = self.tabs.widget(index)

            if container.scene.undo_stack.isClean():
                continue

            path = container.file_path

            if not path:
                self.tabs.setCurrentIndex(index)
                path = self._prompt_save_path(container.default_name)

                if not path:
                    break

            try:
                self.save_to_path(path, container)
                saved_count += 1
            except OSError as exc:
                failures.append((path, exc))

        if (
            self.tabs.indexOf(original) >= 0
            and self.tabs.currentWidget() is not original
        ):
            self.tabs.setCurrentWidget(original)

        for path, exc in failures:
            QMessageBox.warning(
                self, "Save Diagram", f"Couldn't save {path}:\n{exc}"
            )

        if saved_count:
            self.statusBar().showMessage(
                f"Saved {saved_count} diagram{'s' if saved_count != 1 else ''}"
            )
        elif not failures:
            self.statusBar().showMessage("No unsaved changes")

    def open_document(self):
        """
        Manual Chapter 8, "Opening a Diagram" - opened into a fresh
        tab rather than replacing whatever's currently on screen, so
        the diagram that was already open (and the one just opened)
        can both stay open at once - e.g. to copy a shape or group
        from one into the other.

        The picker allows selecting several .pydia files at once
        (Ctrl/Shift+click); each one gets its own tab, in the order
        the picker returns them. A file that fails to load reports
        its own error and doesn't stop the rest.
        """

        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Diagram", "", "PyDiagram Files (*.pydia)"
        )

        for path in paths:
            self._open_path_in_new_tab(path)

    def open_recent_file(self, path):
        """
        File -> Recent Files -> one of the listed paths (app addition,
        not in the manual - see _rebuild_recent_files_menu()). A
        missing file (moved, renamed, or deleted since it was last
        opened/saved) is quietly dropped from the list rather than
        left there to fail the same way every time it's clicked.
        """

        if not os.path.isfile(path):
            QMessageBox.warning(
                self, "Open Diagram",
                f"Couldn't find {path}.\nIt's been removed from Recent Files."
            )
            self._recent_files = [p for p in self._recent_files if p != path]
            settings.save_recent_files(self._recent_files)
            self._rebuild_recent_files_menu()
            return

        self._open_path_in_new_tab(path)

    def _open_path_in_new_tab(self, path):
        """
        Shared by open_document() (after its file-picker dialog) and
        open_recent_file() above: a new tab for `path`, cleaned back
        up if loading it fails.
        """

        new_tab = self._add_document_tab(reserve_name=False)

        try:
            self.load_from_path(path)
        except (OSError, ValueError) as exc:
            index = self.tabs.indexOf(new_tab)

            if index >= 0:
                self.tabs.removeTab(index)

            self._discard_document_container(new_tab)

            QMessageBox.warning(
                self, "Open Diagram", f"Couldn't open {path}:\n{exc}"
            )

    def _add_recent_file(self, path):
        """
        Records `path` as the most recently opened/saved diagram -
        called from save_to_path()/load_from_path() above, the shared
        funnel every Save, Save As, Open and Open Recent already goes
        through. Moves an already-listed path back to the front
        instead of duplicating it, and persists immediately (rather
        than waiting for closeEvent(), unlike the rest of
        app/settings.py's view-configuration state) so the list
        survives even an abnormal exit.
        """

        path = os.path.abspath(path)

        self._recent_files = [p for p in self._recent_files if p != path]
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:settings.MAX_RECENT_FILES]

        settings.save_recent_files(self._recent_files)
        self._rebuild_recent_files_menu()

    def clear_recent_files(self):
        self._recent_files = []
        settings.save_recent_files(self._recent_files)
        self._rebuild_recent_files_menu()

    def _rebuild_recent_files_menu(self):
        """
        Rebuilds File -> Recent Files from scratch against
        self._recent_files - called after every change to that list
        (_add_recent_file(), clear_recent_files()) and once from
        _create_menu() to show whatever was loaded at startup. Simpler
        than patching the menu incrementally, and the list is short
        enough (settings.MAX_RECENT_FILES = 30) that rebuilding it
        every time is in no way a performance concern.
        """

        menu = self._recent_files_menu
        menu.clear()

        self._recent_files_menu_action.setEnabled(bool(self._recent_files))

        # The toolbar's Recent button (see _create_toolbar) shares this
        # very menu, so it only needs its enabled state kept in step.
        # It doesn't exist yet on the first call, from _create_menu().
        recent_button = getattr(self, "_recent_button", None)

        if recent_button is not None:
            recent_button.setEnabled(bool(self._recent_files))

        for i, path in enumerate(self._recent_files, start=1):
            # &1, &2, ... &9 get an Alt-key mnemonic like a real
            # top-level menu item would; 10 and up just show the
            # plain (unmnemonic'd) number - QMenu only assigns
            # single-digit accelerators like this one meaningfully.
            prefix = f"&{i}" if i < 10 else str(i)
            action = QAction(f"{prefix} {path}", self)
            action.triggered.connect(
                lambda checked, p=path: self.open_recent_file(p)
            )
            menu.addAction(action)

        menu.addSeparator()

        clear_action = QAction("Clear Recent Files", self)
        clear_action.setEnabled(bool(self._recent_files))
        clear_action.triggered.connect(self.clear_recent_files)
        menu.addAction(clear_action)

    def export_png_to_path(self, path):
        document_io.export_png(self.scene, path)
        self.statusBar().showMessage(f"Exported PNG to {path}")

    def export_svg_to_path(self, path):
        document_io.export_svg(self.scene, path)
        self.statusBar().showMessage(f"Exported SVG to {path}")

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as PNG", "", "PNG Files (*.png)"
        )

        if not path:
            return

        if not path.endswith(".png"):
            path += ".png"

        self.export_png_to_path(path)

    def export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as SVG", "", "SVG Files (*.svg)"
        )

        if not path:
            return

        if not path.endswith(".svg"):
            path += ".svg"

        self.export_svg_to_path(path)

    def export_pdf(self):
        """
        File -> Export to PDF...: pick which open tabs to export and in
        what order (app/export_pdf_dialog.py), then write them as one
        multi-page PDF, one page per diagram. Uses each tab's current
        content, including changes not saved to the .pydia file yet.
        """

        entries = []

        for i in range(self.tabs.count()):
            container = self.tabs.widget(i)
            name = (
                os.path.basename(container.file_path)
                if container.file_path else container.default_name
            )
            entries.append(
                (container, name, container.file_path or "Not saved yet")
            )

        dialog = ExportPdfDialog(
            entries, self, current=self.tabs.currentWidget()
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        containers = dialog.selected_containers()
        path = dialog.output_path

        try:
            document_io.export_pdf(containers, path)
        except Exception as error:
            QMessageBox.warning(
                self, "Export to PDF", f"Could not write the PDF:\n{error}"
            )
            return

        self.statusBar().showMessage(
            f"Exported {len(containers)} page(s) to {path}"
        )

    def export_tikz(self):
        """
        App addition (not in the manual): both the toolbar's Tikz
        button and File -> Export as Tikz... land here - generates
        the diagram's Tikz code (tikz_export.py) and shows it in a
        popup (tikz_dialog.py) rather than writing straight to a file,
        so it can be reviewed/copied/tweaked before use, matching how
        the person actually asked for this ("popup a dialog box
        containing the Tikz code").
        """

        code = tikz_export.export_tikz(self.scene)
        show_tikz_dialog(code, self)

    # -- copy / cut / paste / duplicate (manual 7.3.1.2) -------------

    def _snapshot_item(self, item):
        """
        A plain-dict description of one item's visible properties -
        deliberately not the live QGraphicsItem itself, so Paste can
        stamp out however many independent fresh copies it needs
        without fighting over which scene owns the original object.
        Connections aren't captured: pasted/duplicated copies start
        unconnected, same simplification as delete/undo.
        """

        snapshot = self._snapshot_item_data(item)

        if snapshot is not None:
            snapshot["rotation"] = item.rotation_angle
            snapshot["flip_h"] = item.flip_horizontal
            snapshot["flip_v"] = item.flip_vertical
            snapshot["scale_x"] = item.scale_x
            snapshot["scale_y"] = item.scale_y
            # App addition (not in the manual): carry a user-given
            # Diagram Tree name (see items.diagram_item.DiagramItem
            # .custom_name) through Copy/Paste/Duplicate too, same as
            # any other visible property.
            snapshot["custom_name"] = item.custom_name
            # App addition (not in the manual): carry the internal PDF
            # page-link destination through Copy/Paste/Duplicate.
            snapshot["pdf_link_target"] = getattr(item, "pdf_link_target", None)
            # App addition (not in the manual): same, for an
            # ImageItem's LaTeX recipe (items.image_item.ImageItem
            # .latex_recipe) - absent entirely for every other item
            # type, and for a plain Browse...'d image.
            if hasattr(item, "latex_recipe"):
                snapshot["latex_recipe"] = item.latex_recipe
            snapshot["custom_connection_points"] = [
                QPointF(p) for p in item._custom_connection_points
            ]

        return snapshot

    def _snapshot_item_data(self, item):
        pos = QPointF(item.pos())

        if isinstance(item, GroupItem):
            # Recurses via the full _snapshot_item wrapper (not
            # _snapshot_item_data directly), so each child's own
            # rotation/flip are captured too, same as any top-level
            # item's. Children's .pos() is already group-local (Qt
            # keeps it that way across setParentItem - see
            # GroupItemsCommand), which is exactly what's needed to
            # reconstruct the group's internal layout unchanged.
            return {
                "type": "group",
                "pos": pos,
                "children": [
                    snap for snap in (
                        self._snapshot_item(c) for c in item._children
                    ) if snap is not None
                ],
            }

        if isinstance(item, TextItem):
            return {
                "type": "text",
                "rect": QRectF(item._rect),
                "pos": pos,
                "text": item.text(),
                "font_family": item.font_family,
                "font_size": item.font_size,
                "font_weight": item.font_weight,
                "text_align": item.text_align,
                "text_color": copy_color_value(item.text_color),
                "fill_color": copy_color_value(item.fill_color),
                "draw_background": item.draw_background,
                "letter_spacing": item.letter_spacing,
                "outline_enabled": item.outline_enabled,
                "outline_color": copy_color_value(item.outline_color),
                "outline_width": item.outline_width,
            }

        if isinstance(item, StencilItem):
            # Flowchart/UML shapes from items/stencil_items.py: the
            # common fill/border/style fields plus whatever size
            # parameters (item.PARAMS) that particular shape has.
            snap = {
                "type": item.SHAPE_TYPE,
                "rect": QRectF(item._rect),
                "pos": pos,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "draw_background": item.draw_background,
            }
            snap.update(item.param_values())
            return snap

        for type_name, cls in SIMPLE_SHAPE_TYPES.items():
            if isinstance(item, cls):
                snap = {
                    "type": type_name,
                    "rect": QRectF(item._rect),
                    "pos": pos,
                    "fill": copy_color_value(item.fill_color),
                    "border": copy_color_value(item.border_color),
                    "border_width": item.border_width,
                }

                if type_name == "rect":
                    snap["corner_radii"] = item.corner_radii
                    snap["draw_background"] = item.draw_background
                elif type_name == "regular_polygon":
                    snap["num_points"] = item.num_points
                    snap["corner_radius"] = item.corner_radius
                    snap["draw_background"] = item.draw_background
                    snap["line_style"] = item.line_style
                    snap["dash_length"] = item.dash_length
                elif type_name == "star":
                    snap["num_points"] = item.num_points
                    snap["inner_radius_ratio"] = item.inner_radius_ratio
                    snap["outer_corner_radius"] = item.outer_corner_radius
                    snap["inner_corner_radius"] = item.inner_corner_radius
                    snap["draw_background"] = item.draw_background
                    snap["line_style"] = item.line_style
                    snap["dash_length"] = item.dash_length

                return snap

        if isinstance(item, CircleSectionItem):
            return {
                "type": "circle_section",
                "rect": QRectF(item._rect),
                "pos": pos,
                "missing_angle": item.missing_angle,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "draw_background": item.draw_background,
            }

        if isinstance(item, SpiralItem):
            return {
                "type": "spiral",
                "center": QPointF(item._center),
                "endpoint": QPointF(item._endpoint),
                "pos": pos,
                "turns": item.turns,
                "pen_color": copy_color_value(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
            }

        if isinstance(item, ClassItem):
            return {
                "type": "class",
                "rect": QRectF(item._rect),
                "pos": pos,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
                "class_name": item.class_name,
                "attributes": item.attributes,
                "operations": item.operations,
            }

        if isinstance(item, PlotItem):
            return {
                "type": "plot",
                "rect": QRectF(item._rect),
                "pos": pos,
                "f1_expr": item.f1_expr,
                "f2_expr": item.f2_expr,
                "x_min": item.x_min, "x_max": item.x_max,
                "x1": item.x1, "x2": item.x2,
                "y_min": item.y_min, "y_max": item.y_max,
                "axis_type": item.axis_type,
                "show_grid": item.show_grid,
                "show_bounds_lines": item.show_bounds_lines,
                "show_xtick_labels": item.show_xtick_labels,
                "show_ytick_labels": item.show_ytick_labels,
                "xtick_interval": item.xtick_interval,
                "ytick_interval": item.ytick_interval,
                "x_tick_label_format": item.x_tick_label_format,
                "y_tick_label_format": item.y_tick_label_format,
                "num_points": item.num_points,
                "f1_color": copy_color_value(item.f1_color),
                "f2_color": copy_color_value(item.f2_color),
                "curve_width": item.curve_width,
                "x1_line_color": copy_color_value(item.x1_line_color),
                "x2_line_color": copy_color_value(item.x2_line_color),
                "bounds_line_width": item.bounds_line_width,
                "bounds_line_style": item.bounds_line_style,
                "fill_color": copy_color_value(item.fill_color),
                "border_color": copy_color_value(item.border_color),
                "border_width": item.border_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
            }

        if isinstance(item, ArcItem):
            # Checked before the plain LineItem branch below - Arc is
            # a LineItem subclass and would otherwise match there
            # first, losing its bow.
            return {
                "type": "arc",
                "p1": QPointF(item._p1),
                "p2": QPointF(item._p2),
                "bow": item._bow,
                "pos": pos,
                "pen_color": QColor(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "start_arrow": item.start_arrow,
                "end_arrow": item.end_arrow,
                "start_arrow_size": item.start_arrow_size,
                "end_arrow_size": item.end_arrow_size,
            }

        if isinstance(item, LineItem):
            return {
                "type": "line",
                "p1": QPointF(item._p1),
                "p2": QPointF(item._p2),
                "pos": pos,
                "pen_color": QColor(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "start_arrow": item.start_arrow,
                "end_arrow": item.end_arrow,
                "start_arrow_size": item.start_arrow_size,
                "end_arrow_size": item.end_arrow_size,
            }

        if isinstance(item, PolygonItem):
            return {
                "type": "polygon",
                "points": [QPointF(p) for p in item._points],
                "pos": pos,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
            }

        if isinstance(item, ZigzaglineItem):
            # Checked before the plain PolylineItem branch below, same
            # reasoning as elsewhere - Zigzagline is a subclass.
            return {
                "type": "zigzagline",
                "points": [QPointF(p) for p in item._points],
                "pos": pos,
                "pen_color": QColor(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "start_arrow": item.start_arrow,
                "end_arrow": item.end_arrow,
                "start_arrow_size": item.start_arrow_size,
                "end_arrow_size": item.end_arrow_size,
                "corner_radius": item.corner_radius,
                "autoroute": item.autoroute,
            }

        if isinstance(item, PolylineItem):
            return {
                "type": "polyline",
                "points": [QPointF(p) for p in item._points],
                "pos": pos,
                "pen_color": QColor(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "start_arrow": item.start_arrow,
                "end_arrow": item.end_arrow,
                "start_arrow_size": item.start_arrow_size,
                "end_arrow_size": item.end_arrow_size,
                "corner_radius": item.corner_radius,
            }

        if isinstance(item, ImageItem):
            return {
                "type": "image",
                "rect": QRectF(item._rect),
                "pos": pos,
                "file_path": item.file_path,
            }

        if isinstance(item, MaskItem):
            return {
                "type": "mask",
                "nodes": [_copy_bezier_node(n) for n in item._nodes],
                "pos": pos,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
            }

        if isinstance(item, BeziergonItem):
            return {
                "type": "beziergon",
                "nodes": [_copy_bezier_node(n) for n in item._nodes],
                "pos": pos,
                "fill": copy_color_value(item.fill_color),
                "border": copy_color_value(item.border_color),
                "border_width": item.border_width,
            }

        if isinstance(item, BezierlineItem):
            return {
                "type": "bezierline",
                "nodes": [_copy_bezier_node(n) for n in item._nodes],
                "pos": pos,
                "pen_color": QColor(item.pen_color),
                "pen_width": item.pen_width,
                "line_style": item.line_style,
                "dash_length": item.dash_length,
                "start_arrow": item.start_arrow,
                "end_arrow": item.end_arrow,
                "start_arrow_size": item.start_arrow_size,
                "end_arrow_size": item.end_arrow_size,
            }

        return None

    def _instantiate_snapshot(self, snapshot, offset):
        kind = snapshot["type"]

        if kind == "group":
            item = GroupItem()

            children = []

            for child_snap in snapshot["children"]:
                # No offset for children - only the group's own
                # top-level position shifts by the paste offset; each
                # child's position is already relative to the group
                # and must stay exactly as it was.
                child = self._instantiate_snapshot(child_snap, QPointF(0, 0))

                if child is None:
                    continue

                child.setParentItem(item)
                child.setFlag(child.ItemIsSelectable, False)
                child.setFlag(child.ItemIsMovable, False)
                children.append(child)

            item._children = children

        elif kind == "text":
            item = TextItem(QRectF(snapshot["rect"]), snapshot["text"])
            item.font_family = snapshot.get("font_family", "Sans Serif")
            item.font_size = snapshot.get("font_size", 11)
            item.font_weight = snapshot.get("font_weight", "normal")
            item.text_align = snapshot.get("text_align", "left")
            item.text_color = copy_color_value(snapshot.get("text_color", "#202020"))
            item.fill_color = copy_color_value(snapshot.get("fill_color", "#ffffff"))
            item.draw_background = snapshot.get("draw_background", False)
            item.letter_spacing = snapshot.get("letter_spacing", 0.0)
            item.outline_enabled = snapshot.get("outline_enabled", False)
            item.outline_color = copy_color_value(snapshot.get("outline_color", "#000000"))
            item.outline_width = snapshot.get("outline_width", 2.0)
        elif kind in STENCIL_SHAPES:
            item = STENCIL_SHAPES[kind](QRectF(snapshot["rect"]))
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.draw_background = snapshot.get("draw_background", True)
            item.set_param_values(snapshot)
        elif kind in SIMPLE_SHAPE_TYPES:
            item = SIMPLE_SHAPE_TYPES[kind](QRectF(snapshot["rect"]))
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]

            if kind == "rect":
                if "corner_radii" in snapshot:
                    item.corner_radii = snapshot["corner_radii"]
                else:
                    item.corner_radius = snapshot.get("corner_radius", 0.0)

                item.draw_background = snapshot.get("draw_background", True)
            elif kind == "regular_polygon":
                item.num_points = max(item.MIN_POINTS, int(snapshot.get("num_points", item.num_points)))
                item.corner_radius = snapshot.get("corner_radius", item.corner_radius)
                item.draw_background = snapshot.get("draw_background", True)
                item.line_style = snapshot.get("line_style", item.line_style)
                item.dash_length = snapshot.get("dash_length", item.dash_length)
            elif kind == "star":
                item.num_points = max(item.MIN_POINTS, int(snapshot.get("num_points", item.num_points)))
                item.inner_radius_ratio = snapshot.get("inner_radius_ratio", item.inner_radius_ratio)
                item.outer_corner_radius = snapshot.get("outer_corner_radius", item.outer_corner_radius)
                item.inner_corner_radius = snapshot.get("inner_corner_radius", item.inner_corner_radius)
                item.draw_background = snapshot.get("draw_background", True)
                item.line_style = snapshot.get("line_style", item.line_style)
                item.dash_length = snapshot.get("dash_length", item.dash_length)
                item._update_special_handles()
        elif kind == "circle_section":
            item = CircleSectionItem(QRectF(snapshot["rect"]))
            item.missing_angle = max(item.MIN_MISSING_ANGLE, min(item.MAX_MISSING_ANGLE, float(snapshot.get("missing_angle", item.missing_angle))))
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]
            item.line_style = snapshot.get("line_style", item.line_style)
            item.dash_length = snapshot.get("dash_length", item.dash_length)
            item.draw_background = snapshot.get("draw_background", True)
            item._update_angle_handle()
        elif kind == "spiral":
            item = SpiralItem(
                QPointF(snapshot.get("center", QPointF(0, 0))),
                QPointF(snapshot.get("endpoint", QPointF(100, 0))),
            )
            item.turns = snapshot.get("turns", item.turns)
            item.pen_color = copy_color_value(snapshot.get("pen_color", item.pen_color))
            item.pen_width = snapshot.get("pen_width", item.pen_width)
            item.line_style = snapshot.get("line_style", item.line_style)
            item.dash_length = snapshot.get("dash_length", item.dash_length)
            item._update_handles()
        elif kind == "class":
            item = ClassItem(
                QRectF(snapshot["rect"]),
                snapshot["class_name"],
                snapshot["attributes"],
                snapshot["operations"],
            )
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]
        elif kind == "plot":
            item = PlotItem(QRectF(snapshot["rect"]))
            item.f1_expr = snapshot.get("f1_expr", item.f1_expr)
            item.f2_expr = snapshot.get("f2_expr", item.f2_expr)
            item.x1 = snapshot.get("x1", item.x1)
            item.x2 = snapshot.get("x2", item.x2)
            item.x_min = snapshot.get("x_min", item.x_min)
            item.x_max = snapshot.get("x_max", item.x_max)
            item.y_min = snapshot.get("y_min", item.y_min)
            item.y_max = snapshot.get("y_max", item.y_max)
            item.axis_type = snapshot.get("axis_type", item.axis_type)
            item.show_grid = snapshot.get("show_grid", item.show_grid)
            item.show_bounds_lines = snapshot.get(
                "show_bounds_lines", item.show_bounds_lines
            )
            item.show_xtick_labels = snapshot.get(
                "show_xtick_labels", item.show_xtick_labels
            )
            item.show_ytick_labels = snapshot.get(
                "show_ytick_labels", item.show_ytick_labels
            )
            item.xtick_interval = snapshot.get("xtick_interval", item.xtick_interval)
            item.ytick_interval = snapshot.get("ytick_interval", item.ytick_interval)
            item.x_tick_label_format = snapshot.get(
                "x_tick_label_format", item.x_tick_label_format
            )
            item.y_tick_label_format = snapshot.get(
                "y_tick_label_format", item.y_tick_label_format
            )
            item.num_points = snapshot.get("num_points", item.num_points)
            item.f1_color = copy_color_value(snapshot.get("f1_color", item.f1_color))
            item.f2_color = copy_color_value(snapshot.get("f2_color", item.f2_color))
            item.curve_width = snapshot.get("curve_width", item.curve_width)
            item.x1_line_color = copy_color_value(
                snapshot.get("x1_line_color", item.x1_line_color)
            )
            item.x2_line_color = copy_color_value(
                snapshot.get("x2_line_color", item.x2_line_color)
            )
            item.bounds_line_width = snapshot.get(
                "bounds_line_width", item.bounds_line_width
            )
            item.bounds_line_style = snapshot.get(
                "bounds_line_style", item.bounds_line_style
            )
            item.fill_color = copy_color_value(snapshot.get("fill_color", item.fill_color))
            item.border_color = copy_color_value(
                snapshot.get("border_color", item.border_color)
            )
            item.border_width = snapshot.get("border_width", item.border_width)
            item.line_style = snapshot.get("line_style", item.line_style)
            item.dash_length = snapshot.get("dash_length", item.dash_length)
        elif kind == "line":
            item = LineItem(QPointF(snapshot["p1"]), QPointF(snapshot["p2"]))
            item.pen_color = copy_color_value(snapshot["pen_color"])
            item.pen_width = snapshot["pen_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.start_arrow = snapshot.get("start_arrow", "none")
            item.end_arrow = snapshot.get("end_arrow", "none")
            item.start_arrow_size = snapshot.get("start_arrow_size", 1.0)
            item.end_arrow_size = snapshot.get("end_arrow_size", 1.0)
        elif kind == "arc":
            item = ArcItem(QPointF(snapshot["p1"]), QPointF(snapshot["p2"]))
            item._bow = snapshot.get("bow", 30.0)
            item.pen_color = copy_color_value(snapshot["pen_color"])
            item.pen_width = snapshot["pen_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.start_arrow = snapshot.get("start_arrow", "none")
            item.end_arrow = snapshot.get("end_arrow", "none")
            item.start_arrow_size = snapshot.get("start_arrow_size", 1.0)
            item.end_arrow_size = snapshot.get("end_arrow_size", 1.0)
            item._position_handles()
        elif kind == "polygon":
            item = PolygonItem([QPointF(p) for p in snapshot["points"]])
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]
        elif kind == "zigzagline":
            item = ZigzaglineItem([QPointF(p) for p in snapshot["points"]])
            item.autoroute = snapshot.get("autoroute", True)
            item.pen_color = copy_color_value(snapshot["pen_color"])
            item.pen_width = snapshot["pen_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.start_arrow = snapshot.get("start_arrow", "none")
            item.end_arrow = snapshot.get("end_arrow", "none")
            item.start_arrow_size = snapshot.get("start_arrow_size", 1.0)
            item.end_arrow_size = snapshot.get("end_arrow_size", 1.0)
            item.corner_radius = snapshot.get("corner_radius", 0.0)
            item._position_handles()
        elif kind == "polyline":
            item = PolylineItem([QPointF(p) for p in snapshot["points"]])
            item.pen_color = copy_color_value(snapshot["pen_color"])
            item.pen_width = snapshot["pen_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.start_arrow = snapshot.get("start_arrow", "none")
            item.end_arrow = snapshot.get("end_arrow", "none")
            item.start_arrow_size = snapshot.get("start_arrow_size", 1.0)
            item.end_arrow_size = snapshot.get("end_arrow_size", 1.0)
            item.corner_radius = snapshot.get("corner_radius", 0.0)
            item._position_handles()
        elif kind == "image":
            item = ImageItem(QRectF(snapshot["rect"]))
            item.file_path = snapshot.get("file_path", "")
        elif kind == "mask":
            item = MaskItem()
            item._nodes = [_copy_bezier_node(n) for n in snapshot["nodes"]]
            item._rebuild_handles()
            item.fill_color = copy_color_value(snapshot.get("fill", "#DCEBFF"))
            item.border_color = copy_color_value(snapshot.get("border", "#202020"))
            item.border_width = snapshot.get("border_width", 2)
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
        elif kind == "beziergon":
            item = BeziergonItem()
            item._nodes = [_copy_bezier_node(n) for n in snapshot["nodes"]]
            item._rebuild_handles()
            item.fill_color = copy_color_value(snapshot["fill"])
            item.border_color = copy_color_value(snapshot["border"])
            item.border_width = snapshot["border_width"]
        elif kind == "bezierline":
            item = BezierlineItem()
            item._nodes = [_copy_bezier_node(n) for n in snapshot["nodes"]]
            item._rebuild_handles()
            item.pen_color = copy_color_value(snapshot["pen_color"])
            item.pen_width = snapshot["pen_width"]
            item.line_style = snapshot.get("line_style", "solid")
            item.dash_length = snapshot.get("dash_length", 10.0)
            item.start_arrow = snapshot.get("start_arrow", "none")
            item.end_arrow = snapshot.get("end_arrow", "none")
            item.start_arrow_size = snapshot.get("start_arrow_size", 1.0)
            item.end_arrow_size = snapshot.get("end_arrow_size", 1.0)
        else:
            return None

        item.setPos(snapshot["pos"] + offset)
        item.rotation_angle = snapshot.get("rotation", 0.0)
        item.flip_horizontal = snapshot.get("flip_h", False)
        item.flip_vertical = snapshot.get("flip_v", False)
        item.scale_x = snapshot.get("scale_x", 1.0)
        item.scale_y = snapshot.get("scale_y", 1.0)
        item.custom_name = snapshot.get("custom_name")
        item.pdf_link_target = snapshot.get("pdf_link_target")

        if hasattr(item, "latex_recipe"):
            item.latex_recipe = snapshot.get("latex_recipe")

        # App addition (not in the manual): carry any user-placed
        # connection points (Anchor tool) through Copy/Paste/Duplicate
        # too, same as any other visible property.
        item._custom_connection_points = [
            QPointF(p) for p in snapshot.get("custom_connection_points", [])
        ]

        return item

    def _paste_snapshots(self, snapshots, label):
        new_items = [
            self._instantiate_snapshot(snap, PASTE_OFFSET)
            for snap in snapshots
        ]

        new_items = [item for item in new_items if item is not None]

        if not new_items:
            return

        self.scene.clearSelection()

        self.scene.undo_stack.beginMacro(label)

        for item in new_items:
            self._assign_layer_recursive(item, self.scene.layer_manager.current_layer())

            self.scene.undo_stack.push(
                AddItemCommand(self.scene, item, label)
            )
            item.setSelected(True)

        self.scene.undo_stack.endMacro()

        self.statusBar().showMessage(
            f"{label}: {len(new_items)} object(s)"
        )

    def _assign_layer_recursive(self, item, layer):
        """
        layer_manager.assign() sets ItemIsSelectable based on whether
        `layer` is the current layer - correct for a pasted top-level
        item, but wrong for a pasted group's children, which must stay
        non-selectable/non-movable (matching GroupItemsCommand's own
        invariant for grouped items) regardless of layer. So each
        child's flags are explicitly reasserted right after.
        """

        self.scene.layer_manager.assign(item, layer)

        if isinstance(item, GroupItem):
            for child in item._children:
                self._assign_layer_recursive(child, layer)
                child.setFlag(child.ItemIsSelectable, False)
                child.setFlag(child.ItemIsMovable, False)

    def copy_selection(self):
        items = self._selected_shapes()

        if not items:
            return

        self._clipboard = [
            snap for snap in (self._snapshot_item(i) for i in items)
            if snap is not None
        ]

        self.statusBar().showMessage(
            f"Copied {len(self._clipboard)} object(s)"
        )

    def cut_selection(self):
        items = self._selected_shapes()

        if not items:
            return

        self.copy_selection()

        self.scene.undo_stack.push(
            DeleteItemsCommand(self.scene, items, "Cut")
        )

    def paste_clipboard(self):
        if not self._clipboard:
            return

        self._paste_snapshots(self._clipboard, "Paste")

    def clone_diagram(self):
        """
        App addition (not in the manual): Edit -> Clone (Ctrl+B) -
        unlike Copy/Paste/Duplicate above (which work on the current
        selection, and only restore items themselves - see
        MainWindow._snapshot_item), this clones the *entire* diagram
        currently on screen - every item, inter-item connection, layer
        and canvas setting - into a brand new, unsaved tab. Reuses
        document_io.serialize_scene()/deserialize_scene(), the same
        full round trip Save/Open already go through, rather than the
        simplified snapshot mechanism above, so nothing about the
        original diagram is lost in the clone.
        """

        data = document_io.serialize_scene(self.scene)

        new_container = self._add_document_tab()
        document_io.deserialize_scene(data, new_container.scene)
        new_container.scene.undo_stack.setClean()

        self.activate_tool("Select")
        self._sync_canvas_toggles()
        self._refresh_layers_list()
        self._refresh_diagram_tree()
        self._update_properties_action_text()
        self._update_window_title()
        self._update_tab_label(new_container)
        self._update_empty_hint(new_container)
        self.statusBar().showMessage("Cloned diagram into a new tab")

    def duplicate_selection(self):
        items = self._selected_shapes()

        if not items:
            return

        snapshots = [
            snap for snap in (self._snapshot_item(i) for i in items)
            if snap is not None
        ]

        self._paste_snapshots(snapshots, "Duplicate")

    # -- select all / none / invert / same type (manual 7.2.3) -------

    def _selected_shapes(self):
        return [
            item for item in self.scene.selectedItems()
            if isinstance(item, DiagramItem)
        ]

    def select_all(self):
        for item in self.scene.items():
            if isinstance(item, DiagramItem):
                item.setSelected(True)

    def select_none(self):
        self.scene.clearSelection()

    def select_invert(self):
        for item in self.scene.items():
            if isinstance(item, DiagramItem):
                item.setSelected(not item.isSelected())

    def select_same_type(self):
        items = self._selected_shapes()

        if not items:
            return

        types = {type(item) for item in items}

        for item in self.scene.items():
            if isinstance(item, DiagramItem) and type(item) in types:
                item.setSelected(True)

    def _directly_connected(self, item):
        """
        Everything exactly one hop away from `item` in the
        connection graph. A shape's neighbors are the lines touching
        it (not the shape on the far end of those lines - that's two
        hops away); a line's neighbors are the shape(s) attached to
        its ends. This matches the manual's own worked example for
        Select Connected (7.2.3.7): "if box A is connected by a line
        to box B... Select->Connected will only select the line, not
        box B. If you do Select->Connected a second time, then box B
        will also be [selected]" - i.e. line-then-shape are two
        separate hops, not one. Used by both Select -> Transitive and
        Select -> Connected (7.2.3.6/7.2.3.7).
        """

        # LineItem (and Arc) qualify by subclassing; Polyline/
        # Zigzagline qualify by duck-typing the same _start_conn/
        # _end_conn attributes (see polyline_item.py) without
        # subclassing it - hasattr covers both without needing every
        # line-like type named here individually.
        if isinstance(item, LineItem) or hasattr(item, "_start_conn"):
            return {
                conn[0] for conn in (item._start_conn, item._end_conn)
                if conn
            }

        return {
            line for line, _which in getattr(item, "_connected_lines", [])
        }

    def select_transitive(self):
        """
        Manual 7.2.3.6: "selects ALL objects connected directly or
        indirectly to the currently selected objects, no matter how
        many levels deep."
        """

        seen = set(self._selected_shapes())
        frontier = list(seen)

        while frontier:
            item = frontier.pop()

            for neighbor in self._directly_connected(item):
                if neighbor not in seen:
                    seen.add(neighbor)
                    frontier.append(neighbor)

        for item in seen:
            item.setSelected(True)

    def select_connected(self):
        """
        Manual 7.2.3.7: like Transitive, but "only goes out one
        level" - objects directly connected to the current selection,
        added in a single pass (calling it again reaches one more hop).
        """

        items = self._selected_shapes()

        if not items:
            return

        for item in items:
            for neighbor in self._directly_connected(item):
                neighbor.setSelected(True)

    # -- aligning objects (manual 4.2.7) ------------------------------

    def _move_items(self, moves, label):
        changed = [
            (item, item.pos(), new_pos)
            for item, new_pos in moves
            if item.pos() != new_pos
        ]

        if not changed:
            return

        self.scene.undo_stack.beginMacro(label)

        for item, old_pos, new_pos in changed:
            self.scene.undo_stack.push(
                MoveItemCommand(item, old_pos, new_pos, label)
            )

        self.scene.undo_stack.endMacro()

    def align_left(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        target = min(i.sceneBoundingRect().left() for i in items)

        moves = [
            (i, i.pos() + QPointF(target - i.sceneBoundingRect().left(), 0))
            for i in items
        ]

        self._move_items(moves, "Align Left")

    def align_right(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        target = max(i.sceneBoundingRect().right() for i in items)

        moves = [
            (i, i.pos() + QPointF(target - i.sceneBoundingRect().right(), 0))
            for i in items
        ]

        self._move_items(moves, "Align Right")

    def align_center_h(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        left = min(i.sceneBoundingRect().left() for i in items)
        right = max(i.sceneBoundingRect().right() for i in items)
        mid = (left + right) / 2

        moves = [
            (
                i,
                i.pos() + QPointF(mid - i.sceneBoundingRect().center().x(), 0)
            )
            for i in items
        ]

        self._move_items(moves, "Align Center")

    def align_top(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        target = min(i.sceneBoundingRect().top() for i in items)

        moves = [
            (i, i.pos() + QPointF(0, target - i.sceneBoundingRect().top()))
            for i in items
        ]

        self._move_items(moves, "Align Top")

    def align_bottom(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        target = max(i.sceneBoundingRect().bottom() for i in items)

        moves = [
            (i, i.pos() + QPointF(0, target - i.sceneBoundingRect().bottom()))
            for i in items
        ]

        self._move_items(moves, "Align Bottom")

    def align_middle(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        top = min(i.sceneBoundingRect().top() for i in items)
        bottom = max(i.sceneBoundingRect().bottom() for i in items)
        mid = (top + bottom) / 2

        moves = [
            (
                i,
                i.pos() + QPointF(0, mid - i.sceneBoundingRect().center().y())
            )
            for i in items
        ]

        self._move_items(moves, "Align Middle")

    def spread_out_horizontally(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        items_sorted = sorted(
            items, key=lambda i: i.sceneBoundingRect().center().x()
        )

        left = items_sorted[0].sceneBoundingRect().left()
        right = items_sorted[-1].sceneBoundingRect().right()
        total_w = sum(i.sceneBoundingRect().width() for i in items_sorted)

        gap = (
            (right - left - total_w) / (len(items_sorted) - 1)
            if len(items_sorted) > 1 else 0
        )

        moves = []
        x = left

        for i in items_sorted:
            moves.append(
                (i, i.pos() + QPointF(x - i.sceneBoundingRect().left(), 0))
            )
            x += i.sceneBoundingRect().width() + gap

        self._move_items(moves, "Spread Out Horizontally")

    def spread_out_vertically(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        items_sorted = sorted(
            items, key=lambda i: i.sceneBoundingRect().center().y()
        )

        top = items_sorted[0].sceneBoundingRect().top()
        bottom = items_sorted[-1].sceneBoundingRect().bottom()
        total_h = sum(i.sceneBoundingRect().height() for i in items_sorted)

        gap = (
            (bottom - top - total_h) / (len(items_sorted) - 1)
            if len(items_sorted) > 1 else 0
        )

        moves = []
        y = top

        for i in items_sorted:
            moves.append(
                (i, i.pos() + QPointF(0, y - i.sceneBoundingRect().top()))
            )
            y += i.sceneBoundingRect().height() + gap

        self._move_items(moves, "Spread Out Vertically")

    def align_adjacent(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        items_sorted = sorted(
            items, key=lambda i: i.sceneBoundingRect().center().x()
        )

        x = items_sorted[0].sceneBoundingRect().left()
        moves = []

        for i in items_sorted:
            moves.append(
                (i, i.pos() + QPointF(x - i.sceneBoundingRect().left(), 0))
            )
            x += i.sceneBoundingRect().width()

        self._move_items(moves, "Align Adjacent")

    def align_stacked(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        items_sorted = sorted(
            items, key=lambda i: i.sceneBoundingRect().center().y()
        )

        y = items_sorted[0].sceneBoundingRect().top()
        moves = []

        for i in items_sorted:
            moves.append(
                (i, i.pos() + QPointF(0, y - i.sceneBoundingRect().top()))
            )
            y += i.sceneBoundingRect().height()

        self._move_items(moves, "Align Stacked")

    # -- position -----------------------------------------------------
    # App addition (not in the manual): Objects -> Position.

    def edit_position_selection(self):
        """
        Shows the selection's current position relative to the
        rulers' (0,0) origin - the top-left corner of its combined
        sceneBoundingRect(), since the rulers themselves are drawn
        directly in scene units (canvas/ruler.py) - and lets the user
        type in a new one. A multi-item selection moves as one rigid
        group (every item shifts by the same delta), the same
        "selection treated as one unit" approach _apply_group_rotation
        and _apply_group_flip use for Rotate/Flip.
        """

        items = self._selected_shapes()

        if not items:
            return

        combined = None

        for item in items:
            r = item.sceneBoundingRect()
            combined = r if combined is None else combined.united(r)

        result = open_position_dialog(combined.left(), combined.top(), self)

        if result is None:
            return

        new_x, new_y = result
        delta = QPointF(new_x - combined.left(), new_y - combined.top())

        if delta.isNull():
            return

        moves = [(item, item.pos() + delta) for item in items]
        self._move_items(moves, "Position")

    # -- rotate/flip a whole selection as one rigid group ----------------
    # App additions (not in the manual): Objects -> Rotate/Flip.

    def rotate_selection(self):
        items = self._selected_shapes()

        if not items:
            return

        angle, ok = QInputDialog.getDouble(
            self, "Rotate", "Angle (degrees):", 90.0, -3600.0, 3600.0, 1
        )

        if not ok or angle == 0:
            return

        self._apply_group_rotation(items, angle)

    def rotate_selection_by(self, angle):
        """
        Turns the selection by `angle` degrees without asking - what
        Ctrl+R (+1) and Ctrl+Shift+R (-1) call. Same rigid-group
        rotation, and same single undo step per press, as Rotate...
        """

        items = self._selected_shapes()

        if not items:
            return

        self._apply_group_rotation(items, angle)

    def flip_selection_horizontal(self):
        self._apply_group_flip(self._selected_shapes(), horizontal=True)

    def flip_selection_vertical(self):
        self._apply_group_flip(self._selected_shapes(), horizontal=False)

    def _group_center(self, items):
        combined = None

        for item in items:
            r = item.sceneBoundingRect()
            combined = r if combined is None else combined.united(r)

        return combined.center()

    def _apply_group_rotation(self, items, angle_degrees):
        """
        Revolves every item's own center around the combined
        selection's center by angle_degrees, and adds the same amount
        to each item's own rotation_angle - so a multi-item selection
        rotates as one rigid group (both orbiting AND spinning),
        while a single selected item just spins in place (its own
        center IS the group center, so the orbit term is zero).
        """

        center = self._group_center(items)
        rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        old_states = []
        new_states = []

        for item in items:
            old_states.append({
                "pos": QPointF(item.pos()),
                "rotation_angle": item.rotation_angle,
                "flip_h": item.flip_horizontal,
                "flip_v": item.flip_vertical,
            })

            old_center = item.sceneBoundingRect().center()
            dx = old_center.x() - center.x()
            dy = old_center.y() - center.y()
            new_dx = dx * cos_a - dy * sin_a
            new_dy = dx * sin_a + dy * cos_a
            delta = QPointF(new_dx - dx, new_dy - dy)

            new_states.append({
                "pos": item.pos() + delta,
                "rotation_angle": (item.rotation_angle + angle_degrees) % 360,
                "flip_h": item.flip_horizontal,
                "flip_v": item.flip_vertical,
            })

        self.scene.undo_stack.push(
            TransformSelectionCommand(items, old_states, new_states, "Rotate")
        )

    def _apply_group_flip(self, items, horizontal):
        """
        Mirrors every item's own center across the axis through the
        combined selection's center (vertical axis for a horizontal
        flip, horizontal axis for a vertical one) and toggles each
        item's own flip flag - so a multi-item selection flips as one
        rigid group (both reflecting position AND mirroring each
        shape), while a single selected item just mirrors in place.
        """

        if not items:
            return

        center = self._group_center(items)

        old_states = []
        new_states = []

        for item in items:
            old_states.append({
                "pos": QPointF(item.pos()),
                "rotation_angle": item.rotation_angle,
                "flip_h": item.flip_horizontal,
                "flip_v": item.flip_vertical,
            })

            old_center = item.sceneBoundingRect().center()

            if horizontal:
                new_center = QPointF(
                    2 * center.x() - old_center.x(), old_center.y()
                )
            else:
                new_center = QPointF(
                    old_center.x(), 2 * center.y() - old_center.y()
                )

            delta = new_center - old_center

            new_states.append({
                "pos": item.pos() + delta,
                "rotation_angle": item.rotation_angle,
                "flip_h": (
                    not item.flip_horizontal if horizontal
                    else item.flip_horizontal
                ),
                "flip_v": (
                    item.flip_vertical if horizontal
                    else not item.flip_vertical
                ),
            })

        label = "Flip Horizontal" if horizontal else "Flip Vertical"

        self.scene.undo_stack.push(
            TransformSelectionCommand(items, old_states, new_states, label)
        )

    # -- scale ------------------------------------------------------------
    # App addition: Objects -> Scale and the toolbar's Scale drop-down.

    def _create_scale_menu(self):
        """Drop-down: Horizontal %, Vertical % and a 'link' checkbox."""

        menu = QMenu(self)
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)

        def make_spin():
            spin = QDoubleSpinBox()
            spin.setRange(1.0, 1000.0)
            spin.setDecimals(1)
            spin.setSuffix(" %")
            spin.setValue(100.0)
            # Apply on Enter / focus-out / arrow click, not per keystroke.
            spin.setKeyboardTracking(False)
            return spin

        self._scale_h_spin = make_spin()
        self._scale_v_spin = make_spin()
        self._scale_link_check = QCheckBox("Link Horizontal and Vertical")

        grid.addWidget(QLabel("Horizontal:"), 0, 0)
        grid.addWidget(self._scale_h_spin, 0, 1)
        grid.addWidget(QLabel("Vertical:"), 1, 0)
        grid.addWidget(self._scale_v_spin, 1, 1)
        grid.addWidget(self._scale_link_check, 2, 0, 1, 2)

        self._scale_h_spin.valueChanged.connect(
            lambda v: self._on_scale_field_changed(True, v)
        )
        self._scale_v_spin.valueChanged.connect(
            lambda v: self._on_scale_field_changed(False, v)
        )

        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        menu.aboutToShow.connect(self._sync_scale_fields)

        return menu

    @staticmethod
    def _scene_scale(item):
        """(horizontal, vertical) scale as seen on screen. An item
        turned by 90/270 degrees has its own axes swapped."""

        if abs((item.rotation_angle % 180) - 90) < 0.5:
            return item.scale_y, item.scale_x

        return item.scale_x, item.scale_y

    def _sync_scale_fields(self):
        items = self._selected_shapes()
        sh, sv = self._scene_scale(items[0]) if items else (1.0, 1.0)

        for spin, value in (
            (self._scale_h_spin, sh), (self._scale_v_spin, sv)
        ):
            spin.blockSignals(True)
            spin.setValue(round(value * 100.0, 1))
            spin.blockSignals(False)

    def _on_scale_field_changed(self, horizontal, value):
        items = self._selected_shapes()

        if not items:
            return

        linked = self._scale_link_check.isChecked()

        if linked:
            other = self._scale_v_spin if horizontal else self._scale_h_spin
            other.blockSignals(True)
            other.setValue(value)
            other.blockSignals(False)

        ref_h, ref_v = self._scene_scale(items[0])
        target = value / 100.0
        rx = target / ref_h if (horizontal or linked) else 1.0
        ry = target / ref_v if (not horizontal or linked) else 1.0

        self._apply_group_scale(items, rx, ry)

    def scale_selection_by(self, delta_h, delta_v):
        """Ctrl(+Shift)+L/M: add delta (percentage points) to the
        first selected item's scale and scale the whole selection by
        the same ratio. With 'link' on, both axes change."""

        items = self._selected_shapes()

        if not items:
            return

        if self._scale_link_check.isChecked():
            delta_h = delta_v = delta_h or delta_v

        ref_h, ref_v = self._scene_scale(items[0])
        lo, hi = DiagramItem.SCALE_MIN, DiagramItem.SCALE_MAX
        new_h = min(hi, max(lo, ref_h + delta_h / 100.0))
        new_v = min(hi, max(lo, ref_v + delta_v / 100.0))

        self._apply_group_scale(items, new_h / ref_h, new_v / ref_v)

    def _apply_group_scale(self, items, rx, ry):
        """
        Scales the selection by ratios rx (horizontal) / ry (vertical)
        about the selection's center: item centers move away from /
        toward it, and each item's own scale is multiplied. One undo
        step; a single item just scales in place.
        """

        if not items or (abs(rx - 1) < 1e-9 and abs(ry - 1) < 1e-9):
            return

        lo, hi = DiagramItem.SCALE_MIN, DiagramItem.SCALE_MAX
        center = self._group_center(items)
        old_states = []
        new_states = []

        for item in items:
            old = {
                "pos": QPointF(item.pos()),
                "rotation_angle": item.rotation_angle,
                "flip_h": item.flip_horizontal,
                "flip_v": item.flip_vertical,
                "scale_x": item.scale_x,
                "scale_y": item.scale_y,
            }
            old_states.append(old)

            c = item.sceneBoundingRect().center()
            delta = QPointF(
                (c.x() - center.x()) * (rx - 1),
                (c.y() - center.y()) * (ry - 1),
            )
            swap = abs((item.rotation_angle % 180) - 90) < 0.5
            ix, iy = (ry, rx) if swap else (rx, ry)

            new = dict(old)
            new["pos"] = item.pos() + delta
            new["scale_x"] = min(hi, max(lo, item.scale_x * ix))
            new["scale_y"] = min(hi, max(lo, item.scale_y * iy))
            new_states.append(new)

        self.scene.undo_stack.push(
            TransformSelectionCommand(items, old_states, new_states, "Scale")
        )

    # -- z-order (manual's Objects menu: Send to Back / Bring to Front) --

    def send_to_back(self):
        items = self._selected_shapes()

        if not items:
            return

        layer = self.scene.layer_manager.current_layer()
        all_shapes = self.scene.layer_manager.items_in_layer(layer)

        min_z = min(
            (self.scene.layer_manager.local_z(i) for i in all_shapes),
            default=0
        )

        for item in items:
            min_z -= 1
            self.scene.layer_manager.set_local_z(item, min_z)

    def bring_to_front(self):
        items = self._selected_shapes()

        if not items:
            return

        layer = self.scene.layer_manager.current_layer()
        all_shapes = self.scene.layer_manager.items_in_layer(layer)

        max_z = max(
            (self.scene.layer_manager.local_z(i) for i in all_shapes),
            default=0
        )

        for item in items:
            max_z += 1
            self.scene.layer_manager.set_local_z(item, max_z)

    def send_backward(self):
        for item in self._selected_shapes():
            self.scene.layer_manager.set_local_z(
                item, self.scene.layer_manager.local_z(item) - 1
            )

    def bring_forward(self):
        for item in self._selected_shapes():
            self.scene.layer_manager.set_local_z(
                item, self.scene.layer_manager.local_z(item) + 1
            )

    # -- grouping (manual 4.2.8) --------------------------------------

    def group_selection(self):
        items = self._selected_shapes()

        if len(items) < 2:
            return

        group = GroupItem()
        self.scene.layer_manager.assign_to_current(group)

        self.scene.undo_stack.push(
            GroupItemsCommand(self.scene, group, items, "Group")
        )

        self.scene.clearSelection()
        group.setSelected(True)

    def ungroup_selection(self):
        groups = [
            item for item in self._selected_shapes()
            if isinstance(item, GroupItem)
        ]

        if not groups:
            return

        self.scene.clearSelection()

        for group in groups:
            self.scene.undo_stack.push(
                UngroupItemsCommand(self.scene, group, "Ungroup")
            )

    # -- object properties (manual 4.3) --------------------------------

    def _update_properties_action_text(self):
        """
        App addition (not in the manual): the Properties button (menu
        item and toolbar button - they're the same QAction, see
        _create_toolbar) reads "Paper Sizes" instead whenever
        nothing is selected, matching what clicking it does in that
        case (see edit_selected_properties below). Called whenever the
        current tab's selection changes, and once per tab switch.
        """

        if not self._selected_shapes():
            self._properties_action.setText("&Paper Sizes")
            self._properties_action.setToolTip(
                "Paper Sizes (Alt+Enter)"
            )
        else:
            self._properties_action.setText("&Properties")
            self._properties_action.setToolTip("Properties (Alt+Enter)")

    def edit_selected_properties(self):
        items = self._selected_shapes()

        if not items:
            # Nothing selected - same as the Diagram menu's own
            # Properties... action (see _update_properties_action_text
            # above for why the button/menu text already says so).
            self.open_diagram_properties()
            return

        if len(items) != 1:
            return

        edit_shape_properties(items[0], self.scene)
