# custom_shapes.py
"""
App addition (not in the manual): user-defined custom shapes, saved
from Objects -> Save as New Shape... and shown in their own toolbox
category/categories alongside Basic/Flowchart/UML/Assorted (see
MainWindow._create_toolbox() / _add_custom_shape_category() in
app/main_window.py).

Each category is a subfolder under a per-user "PyDiagram/CustomShapes"
folder in the OS's standard per-user application-data location
(QStandardPaths.AppDataLocation - %APPDATA% on Windows, ~/Library/
Application Support on macOS, $XDG_DATA_HOME, or ~/.local/share, on
Linux). A shape is a pair of same-named files in that folder:

- a ".pdshape" JSON file: the reusable, scene-independent format from
  document_io.serialize_items()/deserialize_items() - deliberately
  not the full-diagram ".pydia" format, since a shape is just a
  handful of items, not a whole document with layers/canvas settings.
- a same-stem ".svg" rendering of it (document_io.export_items_svg),
  used both as its toolbox icon and - since the file's stem is also
  the shape's name - its tooltip and its click-to-place label.
"""

import json
import os
import re

from PyQt5.QtCore import QStandardPaths

from app import document_io

SHAPE_EXTENSION = ".pdshape"
ICON_EXTENSION = ".svg"

# App addition (not in the manual): a soft ceiling on how many shapes
# one category folder is allowed to hold. Nothing on disk actually
# enforces this - it's MainWindow.save_selection_as_shape() (see
# category_is_full() below) that stops adding to a category once it's
# reached, and tells the user to save further shapes under a new
# category (a new CustomShapes sub-folder) instead. This keeps any one
# category's toolbox page - now scrollable rather than forcing the
# whole window to grow (see MainWindow._create_toolbox()) - from
# growing so large that scrolling through it stops being practical.
MAX_SHAPES_PER_CATEGORY = 50

# Characters illegal in a filename on at least one of Windows/macOS/
# Linux - stripped so a category or shape name typed into the
# Save-as-New-Shape dialog always makes a valid folder/file name.
_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def app_data_root():
    """
    The per-user, per-application data folder everything else in this
    module lives under - also shared by app/settings.py's INI-format
    settings file (settings.ini sits right in this same folder,
    beside the "CustomShapes" subfolder below), so the two are always
    found together. Resolved via Qt rather than hand-rolled per-OS
    paths, so it automatically does the right thing on Windows/macOS/
    Linux (and respects XDG_DATA_HOME if the user has set it) using
    the application name set in main.py (app.setApplicationName) -
    %APPDATA%\\PyDiagram on Windows, ~/Library/Application Support/
    PyDiagram on macOS, $XDG_DATA_HOME/PyDiagram or ~/.local/share/
    PyDiagram on Linux.
    """

    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)

    if not base:
        # Extremely unlikely (Qt couldn't resolve any per-user data
        # directory at all) - fall back to a folder next to the
        # user's home directory rather than custom-shapes/settings
        # persistence silently not working at all.
        base = os.path.join(os.path.expanduser("~"), ".pydiagram")

    os.makedirs(base, exist_ok=True)
    return base


def user_shapes_root():
    """
    The root folder every custom-shape category lives under, creating
    it (and any missing parents) if this is the first time it's been
    needed.
    """

    root = os.path.join(app_data_root(), "CustomShapes")
    os.makedirs(root, exist_ok=True)
    return root


def sanitize_name(name):
    """
    Strips characters that are illegal in a filename on at least one
    of Windows/macOS/Linux, and any leading/trailing dots/whitespace
    (illegal or troublesome on Windows in particular). Never returns
    an empty string, so a blank/symbols-only name still produces a
    usable folder/file name rather than failing to save.
    """

    name = _INVALID_CHARS.sub("", name).strip().strip(".")
    return name or "Shape"


def list_categories(root):
    """
    Every immediate subfolder of root, sorted by name (case-
    insensitively) - each one is a toolbox category. Returns
    [(name, full_path), ...]. Safe to call on a root that doesn't
    exist yet (returns []) - user_shapes_root() always creates it,
    but a caller might be pointed at a stale/removed path.
    """

    if not os.path.isdir(root):
        return []

    entries = []

    for entry in sorted(os.listdir(root), key=str.lower):
        path = os.path.join(root, entry)

        if os.path.isdir(path):
            entries.append((entry, path))

    return entries


def list_shapes(category_dir):
    """
    Every shape file in a category folder, paired with its sibling
    icon - [(name, shape_path, svg_path_or_None), ...], sorted by
    name (case-insensitively). A shape file with no matching .svg
    (e.g. hand-copied in from elsewhere) still lists - the toolbox
    falls back to a generic icon for it rather than hiding it.
    """

    if not os.path.isdir(category_dir):
        return []

    shapes = []

    for entry in sorted(os.listdir(category_dir), key=str.lower):
        if not entry.endswith(SHAPE_EXTENSION):
            continue

        stem = entry[: -len(SHAPE_EXTENSION)]
        shape_path = os.path.join(category_dir, entry)
        svg_path = os.path.join(category_dir, stem + ICON_EXTENSION)

        if not os.path.isfile(svg_path):
            svg_path = None

        shapes.append((stem, shape_path, svg_path))

    return shapes


def ensure_category(root, name):
    """Creates (if missing) and returns the folder for category `name`."""

    folder = os.path.join(root, sanitize_name(name))
    os.makedirs(folder, exist_ok=True)
    return folder


def category_is_full(category_dir):
    """
    True once `category_dir` already holds MAX_SHAPES_PER_CATEGORY
    shapes. MainWindow.save_selection_as_shape() checks this before
    calling save_shape() below, and refuses to add another shape to a
    full category rather than letting one category grow without
    bound.
    """

    return len(list_shapes(category_dir)) >= MAX_SHAPES_PER_CATEGORY


def unique_shape_stem(category_dir, stem):
    """
    "Square", "Square (2)", "Square (3)", ... - so saving a second
    shape under a name already taken in this category adds a new
    shape instead of silently overwriting the existing one.
    """

    candidate = stem
    n = 2

    while os.path.isfile(
        os.path.join(category_dir, candidate + SHAPE_EXTENSION)
    ):
        candidate = f"{stem} ({n})"
        n += 1

    return candidate


def save_shape(scene, items, category_dir, name):
    """
    Saves `items` (top-level DiagramItems currently on `scene` - a
    GroupItem's children are pulled in automatically, see
    document_io.serialize_items) as a new reusable shape: a
    <name><SHAPE_EXTENSION> data file plus a same-stem <name>.svg
    rendering used as its toolbox icon. `name` is sanitized and,
    if it collides with a shape already saved in this category,
    disambiguated (see unique_shape_stem) rather than overwriting it.

    Returns (shape_path, svg_path, stem) - `stem` is the name the
    shape actually got saved under (after sanitizing/disambiguating),
    which is what the toolbox button's tooltip/label should show.
    """

    stem = unique_shape_stem(category_dir, sanitize_name(name))

    shape_path = os.path.join(category_dir, stem + SHAPE_EXTENSION)
    svg_path = os.path.join(category_dir, stem + ICON_EXTENSION)

    data = document_io.serialize_items(items)

    with open(shape_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    document_io.export_items_svg(scene, items, svg_path)

    return shape_path, svg_path, stem


def load_shape_items(shape_path):
    """
    Reconstructs the freestanding items (not yet added to any scene)
    saved at shape_path, ready for a tool to position and drop onto
    the canvas - see canvas.tools.CustomShapeTool.
    """

    with open(shape_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return document_io.deserialize_items(data)
