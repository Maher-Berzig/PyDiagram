# help_dialog.py
"""
App addition (not in the manual): Help -> Help (F1) - see
MainWindow._create_menu()'s Help menu and MainWindow.show_help() in
app/main_window.py.

A plain QDialog wrapped around a QTextBrowser, showing the bundled
HTML help pages under help/<language>/ (see HELP_ROOT below) - Qt's
own widgets, deliberately: QTextBrowser understands plain HTML/CSS
well enough for simple help pages on its own, with its own built-in
link navigation and Back/Forward history, so none of a QtWebEngine/
Chromium dependency or a compiled .chm help file is needed just to
show a few static pages.

    help/
    +-- en/
    |   +-- index.html
    |   +-- opening.html
    |   +-- saving.html
    +-- fr/
    +-- ar/

AVAILABLE_LANGUAGES lists every translated help/<code>/ folder that
actually exists (a tuple, not a single constant, so adding a future
translation is just a new help/<code>/ folder with the same files -
nothing in this module has to change). _help_language() picks
whichever of these matches the app's own current UI language
(app.translations.tr.lang, set from the toolbar's language button),
not the system locale - so Help always opens in whatever language the
rest of the interface is already showing, falling back to
DEFAULT_LANGUAGE if that language has no help translation (yet).
"""

import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.translations import tr

# help/ sits next to main.py, one level up from this file (app/
# help_dialog.py) - see the folder tree above.
HELP_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "help"
)

AVAILABLE_LANGUAGES = ("en", "fr", "ar")
DEFAULT_LANGUAGE = "en"

HOME_PAGE = "index.html"


def _help_language():
    """
    The app's own current UI language (tr.lang) if a matching
    help/<code>/ folder actually exists, else DEFAULT_LANGUAGE - the
    graceful fallback QTextBrowser itself has no notion of, since
    it's simply pointed at one fixed path.
    """

    return tr.lang if tr.lang in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE


def _page_url(folder, page):
    return QUrl.fromLocalFile(os.path.join(folder, page))


def show_help_dialog(parent=None, page=HOME_PAGE):
    """
    Shows the modal Help dialog, initially on `page` (index.html
    unless the caller asks for a more specific topic - nothing in the
    app does yet, but e.g. a future per-dialog "Help" button could
    jump straight to its own topic this way).
    """

    folder = os.path.join(HELP_ROOT, _help_language())

    dialog = QDialog(parent)
    # Mirrors the nav row (Home / Forward / Back, right to left) for an
    # RTL help language, matching how the rest of the app already
    # flips direction on language switch (see translations.py).
    dialog.setLayoutDirection(Qt.RightToLeft if tr.is_rtl() else Qt.LeftToRight)
    dialog.setWindowTitle("PyDiagram Help")
    dialog.resize(720, 560)

    layout = QVBoxLayout(dialog)

    browser = QTextBrowser()
    if tr.is_rtl():
        # Flipping the dialog's layout direction mirrors the widgets but
        # not the text inside QTextBrowser: its document has its own
        # default text direction.  The translated pages also mark their
        # blocks dir="rtl"; this default covers anything that doesn't.
        document = browser.document()
        text_option = document.defaultTextOption()
        text_option.setTextDirection(Qt.RightToLeft)
        document.setDefaultTextOption(text_option)
    browser.setOpenExternalLinks(True)
    browser.setSearchPaths([folder])
    browser.setSource(_page_url(folder, page))
    layout.addWidget(browser)

    nav = QHBoxLayout()

    back_button = QPushButton("< Back")
    back_button.setEnabled(False)
    back_button.clicked.connect(browser.backward)
    browser.backwardAvailable.connect(back_button.setEnabled)

    forward_button = QPushButton("Forward >")
    forward_button.setEnabled(False)
    forward_button.clicked.connect(browser.forward)
    browser.forwardAvailable.connect(forward_button.setEnabled)

    home_button = QPushButton("Home")
    home_button.clicked.connect(
        lambda: browser.setSource(_page_url(folder, HOME_PAGE))
    )

    nav.addWidget(back_button)
    nav.addWidget(forward_button)
    nav.addWidget(home_button)
    nav.addStretch(1)
    layout.addLayout(nav)

    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.button(QDialogButtonBox.Close).clicked.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec_()
