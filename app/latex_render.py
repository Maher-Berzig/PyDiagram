# latex_render.py
"""
App addition (not in the manual): renders a LaTeX equation to a PNG
for the Image shape's Properties dialog "Create from LaTeX..." button
(see app/latex_image_dialog.py and items/property_dialog.py's
ImageItem branch) - pdflatex compiles a small standalone-class
document to a PDF, then pdftocairo rasterizes that PDF to a PNG at a
chosen DPI. Adapted from a reference PyQt5 implementation; see
LatexRenderWorker's docstring below for exactly what changed.

Rendered files are cached persistently rather than written to a temp
directory: an Image shape reloads its file from disk on every paint
(items/image_item.py) rather than embedding it, so a file that later
disappeared would otherwise turn back into "Broken Image" the next
time the diagram was opened, even though nothing about the diagram
itself had changed. Both the PNG and a same-stem .json "recipe"
sidecar (the exact equation, colors, padding and DPI that produced
it) live under custom_shapes.app_data_root()/LatexImages/, named by a
hash of that recipe - so re-rendering the exact same equation is
instant (the cached PNG is reused, pdflatex isn't even invoked).

The recipe is also saved on the ImageItem itself (.latex_recipe -
see items/image_item.py) and travels with the .pydia file
(app/document_io.py), rather than living only in this on-disk cache's
sidecar. That means the cache is a disposable, rebuildable-on-demand
copy rather than the recipe's only home: a missing/deleted cached
file is regenerated the next time the shape is painted (see
ImageItem._load_pixmap()), and Diagram -> Clean Up LaTeX Image
Cache... (clear_cache() below) can always wipe the whole cache
without permanently losing anything. load_recipe() below still reads
the sidecar too, purely as a fallback for Image shapes saved before
ImageItem.latex_recipe existed.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from app import custom_shapes

DEFAULT_DPI = 300
DEFAULT_PADDING = 12

# Max width the LaTeX field's content wraps against (see _render()) -
# only reached by content long enough to need it; anything shorter,
# a single equation included, still crops to its own natural size.
MAX_CONTENT_WIDTH = "12cm"

_SUBPROCESS_TIMEOUT = 30


def images_root():
    root = os.path.join(custom_shapes.app_data_root(), "LatexImages")
    os.makedirs(root, exist_ok=True)
    return root


def _recipe_key(recipe):
    encoded = json.dumps(recipe, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:20]


def cached_paths(recipe):
    """(png_path, json_path) this exact recipe belongs at - whether or
    not either file exists yet."""

    stem = _recipe_key(recipe)
    root = images_root()
    return (
        os.path.join(root, f"{stem}.png"),
        os.path.join(root, f"{stem}.json"),
    )


def find_cached(recipe):
    """The already-rendered PNG path for `recipe`, or None if it
    hasn't been (or its sidecar has gone missing)."""

    png_path, json_path = cached_paths(recipe)

    if os.path.isfile(png_path) and os.path.isfile(json_path):
        return png_path

    return None


def load_recipe(image_path):
    """
    The recipe that produced `image_path`, if it's one of ours (a
    same-stem .json sidecar sits next to it under images_root()) -
    used by app/latex_image_dialog.py to prefill "Create from
    LaTeX..." when reopened on an Image shape that doesn't already
    carry its own ImageItem.latex_recipe - i.e. one saved before that
    attribute existed. None for any other image (one picked via
    Browse..., or moved/renamed since it was rendered).
    """

    if not image_path:
        return None

    if os.path.dirname(os.path.abspath(image_path)) != images_root():
        return None

    json_path = os.path.splitext(image_path)[0] + ".json"

    if not os.path.isfile(json_path):
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return None


def render_recipe(recipe):
    """
    Synchronous cache-or-render: returns the PNG path for `recipe`,
    (blocking) rendering it first if it isn't already cached. Raises
    whatever LatexRenderWorker._render() can raise (FileNotFoundError,
    subprocess.TimeoutExpired, RuntimeError, ...).

    This is that same worker's compile step, called directly rather
    than via its usual QThread + finished/error signals (see
    app/latex_image_dialog.py) - used by items/image_item.py to
    self-heal an Image shape whose cached file has gone missing (for
    instance, after Diagram -> Clean Up LaTeX Image Cache... below)
    but whose ImageItem.latex_recipe survived, since it's saved in the
    .pydia file itself rather than only in the cache's sidecar.
    Blocking is acceptable there because it only ever runs once per
    missing file (see ImageItem._load_pixmap()'s own guard against
    retrying every repaint), not on some hot path.
    """

    cached = find_cached(recipe)

    if cached is not None:
        return cached

    return LatexRenderWorker(recipe)._render()


def cache_usage():
    """(pair_count, total_bytes) currently sitting in images_root() -
    each pair being one rendered equation's .png + its .json recipe
    sidecar. Used by Diagram -> Clean Up LaTeX Image Cache... to show
    what a cleanup would free before doing it."""

    root = images_root()
    total_bytes = 0
    stems = set()

    for name in os.listdir(root):
        path = os.path.join(root, name)

        if not os.path.isfile(path):
            continue

        total_bytes += os.path.getsize(path)
        stem, ext = os.path.splitext(name)

        if ext in (".png", ".json"):
            stems.add(stem)

    return len(stems), total_bytes


def clear_cache():
    """
    Deletes every rendered-equation file under images_root() - the
    whole point of ImageItem.latex_recipe travelling in the .pydia
    file now (see items/image_item.py) is that this is always safe:
    any Image shape that needs one of these files back renders it
    again, on demand, from its own saved recipe the next time it's
    painted (requires pdflatex/pdftocairo still being on PATH - if
    they aren't, the shape just shows "Broken Image" again, exactly
    as it would if its file were missing for any other reason).

    Returns the same (pair_count, total_bytes) cache_usage() would
    have reported beforehand, for a confirmation/result message -
    see MainWindow.clean_up_latex_cache().
    """

    count, total_bytes = cache_usage()
    root = images_root()

    for name in os.listdir(root):
        path = os.path.join(root, name)

        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    return count, total_bytes


def hidden_process_options():
    """Hide console windows when running external programs on Windows."""

    options = {}

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        options["startupinfo"] = startupinfo
        options["creationflags"] = subprocess.CREATE_NO_WINDOW

    return options


class LatexRenderWorker(QObject):
    """
    Runs pdflatex + pdftocairo on a background thread - moveToThread()
    from LatexImageDialog.render_preview() in app/latex_image_dialog.py
    - so a slow compile can't freeze the dialog. The compile pipeline
    itself (the two subprocess calls, the "border=Npt" standalone-class
    trick for a tight crop, hiding the console window on Windows) is
    unchanged from the reference implementation this was adapted from.
    What's changed: a `recipe` dict in, rather than separate
    constructor arguments, and the result is written into the
    persistent, content-hashed images_root() cache above instead of a
    throwaway tempfile.mkdtemp() directory - checked first, so a
    repeat of the exact same recipe finishes instantly without
    invoking either program at all.
    """

    finished = pyqtSignal(str)   # -> the rendered (or cached) PNG's path
    error = pyqtSignal(str)

    def __init__(self, recipe):
        super().__init__()
        self.recipe = recipe

    @pyqtSlot()
    def compile_latex(self):
        cached = find_cached(self.recipe)

        if cached is not None:
            self.finished.emit(cached)
            return

        try:
            png_path = self._render()
        except FileNotFoundError as exc:
            self.error.emit(
                "A required program was not found.\n\n"
                "Make sure pdflatex and pdftocairo (Poppler) are "
                "installed and available on PATH.\n\n"
                f"Details:\n{exc}"
            )
        except subprocess.TimeoutExpired:
            self.error.emit("The LaTeX or Poppler operation timed out.")
        except Exception as exc:
            self.error.emit(str(exc))
        else:
            self.finished.emit(png_path)

    def _render(self):
        # "latex" is the current recipe key; "equation" is read as a
        # fallback so a recipe sidecar from before the Preamble field
        # existed (app/latex_image_dialog.py) still renders unchanged.
        latex_body = self.recipe.get("latex") or self.recipe.get("equation", "")
        preamble = self.recipe.get("preamble", "")
        text_color = self.recipe["text_color"]
        background_color = self.recipe["background_color"]
        padding = self.recipe["padding"]
        dpi = self.recipe["dpi"]

        temp_dir = tempfile.mkdtemp(prefix="pydiagram_latex_")

        try:
            tex_path = os.path.join(temp_dir, "equation.tex")
            pdf_path = os.path.join(temp_dir, "equation.pdf")
            temp_png_path = os.path.join(temp_dir, "equation.png")

            # MAX_CONTENT_WIDTH via a manually-scoped varwidth
            # environment, not standalone's own varwidth=<dim> class
            # option: that option remeasures the *entire* document
            # body (color commands included) to find its natural
            # width, and \color isn't safe to run twice - it silently
            # falls back to the full given width whenever the body
            # contains one (verified directly with pdflatex), which
            # left every simple, short equation padded out to the
            # full max width instead of tightly cropped. Setting
            # \pagecolor/\color first and only wrapping the content
            # itself in \begin{varwidth} keeps what gets remeasured
            # free of color commands, so a short equation still crops
            # tightly and only genuinely long content (a theorem
            # statement mixing text and math) wraps at the max width.
            latex_source = rf"""
\documentclass[border={padding}pt]{{standalone}}

\usepackage{{amsmath}}
\usepackage{{amssymb}}
\usepackage{{xcolor}}
\usepackage{{varwidth}}
{preamble}

\definecolor{{EquationText}}{{HTML}}{{{text_color}}}
\definecolor{{EquationBackground}}{{HTML}}{{{background_color}}}

\begin{{document}}

\pagecolor{{EquationBackground}}%
\color{{EquationText}}%
\begin{{varwidth}}{{{MAX_CONTENT_WIDTH}}}
{latex_body}
\end{{varwidth}}

\end{{document}}
"""

            with open(tex_path, "w", encoding="utf-8") as file:
                file.write(latex_source)

            process_options = hidden_process_options()

            pdflatex_path = shutil.which("pdflatex")

            if not pdflatex_path:
                raise FileNotFoundError("pdflatex was not found on PATH.")

            result = subprocess.run(
                [
                    pdflatex_path,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-file-line-error",
                    "-output-directory",
                    temp_dir,
                    tex_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
                **process_options,
            )

            if result.returncode != 0 or not os.path.exists(pdf_path):
                log_path = os.path.join(temp_dir, "equation.log")
                log_text = ""

                if os.path.exists(log_path):
                    with open(
                        log_path, "r", encoding="utf-8", errors="replace"
                    ) as file:
                        log_text = file.read()

                raise RuntimeError(
                    "LaTeX compilation failed.\n\n"
                    + (log_text[-6000:] or result.stderr)
                )

            pdftocairo_path = shutil.which("pdftocairo")

            if not pdftocairo_path:
                raise FileNotFoundError("pdftocairo was not found on PATH.")

            temp_png_base = os.path.splitext(temp_png_path)[0]

            result = subprocess.run(
                [
                    pdftocairo_path,
                    "-png",
                    "-singlefile",
                    "-r", str(dpi),
                    pdf_path,
                    temp_png_base,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
                **process_options,
            )

            if result.returncode != 0 or not os.path.exists(temp_png_path):
                raise RuntimeError(
                    "PDF-to-PNG conversion failed:\n\n"
                    + (result.stderr or result.stdout)
                )

            png_path, json_path = cached_paths(self.recipe)
            shutil.copyfile(temp_png_path, png_path)

            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(self.recipe, file)

            return png_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
