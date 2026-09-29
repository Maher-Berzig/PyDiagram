# settings.py
"""
App addition (not in the manual): persists the "view configuration"
across runs - see MainWindow.__init__ (restore_view_state(), called
once every dock/toolbar/menu action exists) and MainWindow.closeEvent
(save_view_state()) in app/main_window.py:

- the View menu's nine checkboxes (Show Rulers, Shapes, Layers,
  Tools, Diagram Tree, Show Grid, Snap To Grid, Snap To Objects, Show
  Connection Points)
- the Shapes/Layers/Diagram Tree docks' position and style (split
  area vs tabbed) - via QMainWindow's own saveState()/restoreState(),
  which already captures exactly this (plus every toolbar's position,
  and every dock/toolbar's visibility) for the whole window in one
  opaque QByteArray blob
- the main window's own size/position (saveGeometry()/restoreGeometry())
- the Recent Files list (see save_recent_files()/load_recent_files()
  below, and MainWindow._add_recent_file() et al.)

Stored as a plain INI file - QSettings opened directly against a file
path with QSettings.IniFormat, rather than Qt's platform default (the
Windows registry, or a macOS plist) - named settings.ini, right next
to custom_shapes.py's own per-user "CustomShapes" folder; see
custom_shapes.app_data_root() for exactly which OS path that is.
"""

import os

from PyQt5.QtCore import QSettings

from app import custom_shapes

SETTINGS_FILENAME = "settings.ini"

MAX_RECENT_FILES = 30

# action attribute name on MainWindow -> its settings.ini key, and the
# built-in default it falls back to on a first run (or if settings.ini
# can't be read) - matches each QAction's own setChecked() default in
# MainWindow._create_menu().
_VIEW_TOGGLES = (
    ("_show_rulers_action", "ShowRulers", True),
    ("_shapes_visible_action", "Shapes", True),
    ("_layers_visible_action", "Layers", True),
    ("_tools_visible_action", "Tools", True),
    ("_diagram_tree_action", "DiagramTree", True),
    ("_lock_panels_action", "LockPanels", False),
    ("_show_grid_action", "ShowGrid", True),
    ("_snap_to_grid_action", "SnapToGrid", True),
    ("_snap_to_objects_action", "SnapToObjects", False),
    ("_show_conn_points_action", "ShowConnectionPoints", True),
)

# Dock/toolbar visibility (a subset of _VIEW_TOGGLES above) is set by
# QMainWindow.restoreState() itself, not read back from settings.ini
# directly - restore_view_state() instead syncs each of these
# checkboxes to match the widget's actual post-restoreState()
# visibility. action attribute name -> widget attribute name, both on
# MainWindow.
_PANEL_ACTIONS = (
    ("_shapes_visible_action", "shapes_dock"),
    ("_layers_visible_action", "layers_dock"),
    ("_tools_visible_action", "tools_toolbar"),
    ("_diagram_tree_action", "diagram_tree_dock"),
)


def settings_path():
    return os.path.join(custom_shapes.app_data_root(), SETTINGS_FILENAME)


def open_settings():
    """
    A fresh QSettings handle on settings.ini. Cheap enough (Qt reads
    the file lazily, and only on first access) to open one each time
    rather than keep a single instance alive for the whole session.
    """

    return QSettings(settings_path(), QSettings.IniFormat)



# -- default diagram paper format -------------------------------------

DEFAULT_PAPER_FORMAT = "A4"
DEFAULT_PAPER_ORIENTATION = "portrait"
DEFAULT_CUSTOM_WIDTH_MM = 210.0
DEFAULT_CUSTOM_HEIGHT_MM = 297.0


def load_default_paper_settings():
    """Return paper settings used for newly-created diagrams."""
    settings = open_settings()
    return (
        settings.value("Diagram/PaperFormat", DEFAULT_PAPER_FORMAT),
        settings.value("Diagram/PaperOrientation", DEFAULT_PAPER_ORIENTATION),
        float(settings.value("Diagram/CustomWidth", DEFAULT_CUSTOM_WIDTH_MM)),
        float(settings.value("Diagram/CustomHeight", DEFAULT_CUSTOM_HEIGHT_MM)),
    )


def save_default_paper_settings(paper_format, orientation, custom_width_mm, custom_height_mm):
    """Persist paper format, orientation, and custom dimensions globally."""
    settings = open_settings()
    settings.setValue("Diagram/PaperFormat", str(paper_format))
    settings.setValue("Diagram/PaperOrientation", str(orientation))
    settings.setValue("Diagram/CustomWidth", float(custom_width_mm))
    settings.setValue("Diagram/CustomHeight", float(custom_height_mm))
    settings.sync()


def load_default_paper_format():
    """Backward-compatible paper-format-only loader."""
    return load_default_paper_settings()[0]


def load_language():
    """Return the persisted UI language, falling back to English."""
    value = open_settings().value("General/Language", "en")
    return str(value) if str(value) in ("en", "ar", "fr") else "en"


def save_language(language):
    """Persist the UI language for the next application launch."""
    settings = open_settings()
    settings.setValue("General/Language", str(language))
    settings.sync()


def save_default_paper_format(paper_format):
    """Backward-compatible paper-format-only saver."""
    current = load_default_paper_settings()
    save_default_paper_settings(paper_format, current[1], current[2], current[3])

# -- view configuration (View menu + dock/window layout) -------------


def save_view_state(window):
    settings = open_settings()

    settings.beginGroup("MainWindow")
    settings.setValue("Geometry", window.saveGeometry())
    settings.setValue("State", window.saveState())
    settings.endGroup()

    settings.beginGroup("View")

    for action_name, key, _default in _VIEW_TOGGLES:
        action = getattr(window, action_name, None)

        if action is not None:
            settings.setValue(key, action.isChecked())

    settings.endGroup()

    settings.sync()


def restore_view_state(window):
    """
    Applies whatever save_view_state() above last saved. Called once
    from MainWindow.__init__, after every dock, toolbar and View-menu
    action it touches already exists, but before _sync_canvas_toggles()
    - the show_grid/snap_to_grid/snap_to_objects/show_connection_points
    settings are actually per-DiagramScene attributes (canvas/
    diagram_scene.py), not window-level state, so they're applied here
    directly to window.scene (the one tab _create_scene() has already
    made) and left for that later, already-scheduled call to reflect
    into their checkboxes - exactly as opening a .pydia file that
    happened to save them this way would. Wherever settings.ini has no
    value yet (first run) or can't be read, each setting is simply
    left at whatever built-in default it already had.
    """

    settings = open_settings()

    settings.beginGroup("MainWindow")
    geometry = settings.value("Geometry")
    state = settings.value("State")
    settings.endGroup()

    if geometry is not None:
        window.restoreGeometry(geometry)

    if state is not None:
        window.restoreState(state)

    # Dock/toolbar visibility is already correct post-restoreState()
    # above (or, on a first run / if nothing was saved, at whatever
    # each one's own built-in default already is) - this just brings
    # each View-menu checkbox back in line with it, the same
    # blockSignals()-guarded pattern MainWindow._sync_canvas_toggles()
    # uses for the grid/snap ones below. isVisibleTo(window) rather
    # than plain isVisible(): this runs from MainWindow.__init__(),
    # before the window itself has ever been shown, and isVisible()
    # unconditionally reports False for every child of a not-yet-shown
    # top-level window regardless of that child's own visibility -
    # isVisibleTo(window) is Qt's own way to ask "would this widget be
    # visible if `window` were shown", ignoring window's own state.
    for action_name, widget_name in _PANEL_ACTIONS:
        action = getattr(window, action_name, None)
        widget = getattr(window, widget_name, None)

        if action is not None and widget is not None:
            action.blockSignals(True)
            action.setChecked(widget.isVisibleTo(window))
            action.blockSignals(False)

    settings.beginGroup("View")
    values = {
        key: settings.value(key, default, type=bool)
        for _action_name, key, default in _VIEW_TOGGLES
    }
    settings.endGroup()

    # Show Rulers has no dock/toolbar of its own to have just been
    # restored above - applied the same way the View menu itself
    # would (setChecked() firing MainWindow._set_rulers_visible()), a
    # no-op if it already matches the built-in default.
    window._show_rulers_action.setChecked(values["ShowRulers"])
    window._lock_panels_action.setChecked(values["LockPanels"])

    if window.scene is not None:
        window.scene.show_grid = values["ShowGrid"]
        window.scene.snap_to_grid = values["SnapToGrid"]
        window.scene.snap_to_objects = values["SnapToObjects"]
        window.scene.show_connection_points = values["ShowConnectionPoints"]


# -- recent files ------------------------------------------------------


def load_recent_files():
    settings = open_settings()
    files = settings.value("RecentFiles/Files", [])

    # QSettings' own long-standing IniFormat quirk: a *one*-item list
    # written with setValue() reads back as a bare string rather than
    # a one-item list, since the ini text alone can't tell the two
    # apart without an explicit type hint - normalized back into a
    # list here rather than pushed onto every caller.
    if isinstance(files, str):
        files = [files] if files else []

    return list(files)[:MAX_RECENT_FILES]


def save_recent_files(paths):
    settings = open_settings()
    settings.setValue("RecentFiles/Files", list(paths)[:MAX_RECENT_FILES])
    settings.sync()
