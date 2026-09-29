# about_dialog.py
"""
App addition (not in the manual): Help -> About - see
MainWindow._create_menu()'s Help menu and MainWindow.show_about() in
app/main_window.py.

A small read-only QDialog with the essentials about the application
itself (name, version, the Qt/PyQt runtime it's built on) - not to be
confused with diagram_properties_dialog.py, which is about the
current *diagram* rather than the app.
"""

from html import escape

from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)

from app.translations import (
    LANGUAGE_DIRECTION,
    LANGUAGE_NAMES,
    translations,
    tr,
)

DESCRIPTION = (
    "A Dia-inspired 2D diagram editor: draw Flowchart, UML and "
    "general-purpose diagrams, connect shapes with lines, organize "
    "them into layers, and export to PNG, SVG or Tikz."
)


COPYRIGHT_LINE = "Copyright (C) 2025 Maher Berzig"

URL = "https://www.gnu.org/licenses/"

# The GPL v3 "how to apply" notice, per language. Only the English text
# is authoritative - the French and Arabic versions are unofficial
# translations (the license dialog says so). The three paragraphs are
# kept as plain text; the link is added when rendering.
LICENSE_NOTICES = {
    "en": (
        "This program is free software: you can redistribute it and/or "
        "modify it under the terms of the GNU General Public License as "
        "published by the Free Software Foundation, either version 3 of "
        "the License, or (at your option) any later version.",
        "This program is distributed in the hope that it will be useful, "
        "but WITHOUT ANY WARRANTY; without even the implied warranty of "
        "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the "
        "GNU General Public License for more details.",
        "You should have received a copy of the GNU General Public "
        "License along with this program. If not, see {url}.",
    ),
    "fr": (
        "Ce programme est un logiciel libre : vous pouvez le "
        "redistribuer et/ou le modifier selon les termes de la GNU "
        "General Public License telle que publiée par la Free Software "
        "Foundation, soit la version 3 de la licence, soit (à votre "
        "convenance) toute version ultérieure.",
        "Ce programme est distribué dans l'espoir qu'il sera utile, "
        "mais SANS AUCUNE GARANTIE ; sans même la garantie implicite de "
        "COMMERCIALISATION ou d'ADÉQUATION À UN USAGE PARTICULIER. "
        "Consultez la GNU General Public License pour plus de détails.",
        "Vous devriez avoir reçu une copie de la GNU General Public "
        "License avec ce programme. Si ce n'est pas le cas, consultez "
        "{url}.",
    ),
    "ar": (
        "هذا البرنامج برنامج حر: يمكنك إعادة توزيعه و/أو تعديله بموجب "
        "شروط رخصة جنو العمومية (GNU General Public License) كما "
        "نشرتها مؤسسة البرمجيات الحرة (Free Software Foundation)، إما "
        "الإصدار 3 من الرخصة، أو، وفق اختيارك، أي إصدار لاحق.",
        "يُوزَّع هذا البرنامج على أمل أن يكون مفيدًا، ولكن دون أي ضمان؛ "
        "ودون حتى الضمان الضمني الخاص بقابلية التسويق أو الملاءمة لغرض "
        "معيّن. راجع رخصة جنو العمومية (GNU General Public License) "
        "لمزيد من التفاصيل.",
        "ينبغي أن تكون قد تلقيت نسخة من رخصة جنو العمومية مع هذا "
        "البرنامج. وإن لم يكن الأمر كذلك، فراجع: {url}",
    ),
}

def _license_html(code):
    """The notice for language `code` as rich text, right-to-left when
    that language reads that way."""

    if code not in LICENSE_NOTICES:
        code = "en"

    rtl = LANGUAGE_DIRECTION.get(code) == "rtl"
    attrs = ' dir="rtl" align="right"' if rtl else ' dir="ltr"'

    link = f'&lt;<a href="{URL}">{URL}</a>&gt;'

    parts = [f"<p{attrs}><b>{escape(COPYRIGHT_LINE)}</b></p>"]

    for paragraph in LICENSE_NOTICES[code]:
        if rtl and "{url}" in paragraph:
            # Mixing a left-to-right address into the middle of a
            # right-to-left line scrambles the brackets and lets the
            # address wrap in two, so it gets its own line instead.
            before = paragraph.split("{url}")[0].rstrip()
            parts.append(f"<p{attrs}>{escape(before)}</p>")
            parts.append(f'<p dir="ltr" align="right">{link}</p>')
            continue

        text = escape(paragraph).replace("{url}", link)
        parts.append(f"<p{attrs}>{text}</p>")

    if code != "en":
        note = translations.get(code, {}).get("license_note", "")

        if note:
            parts.append(
                f'<p{attrs}><span style="color:#808080;">'
                f"<i>{escape(note)}</i></span></p>"
            )

    return "".join(parts)


def show_license_dialog(parent=None):
    """The GNU GPL notice, in the app's current language to begin with;
    the drop-down at the top switches it between English, French and
    Arabic."""

    dialog = QDialog(parent)
    dialog.setWindowTitle("License")
    dialog.resize(540, 420)

    layout = QVBoxLayout(dialog)

    row = QHBoxLayout()
    row.addWidget(QLabel("Language:"))

    combo = QComboBox()

    for code, name in LANGUAGE_NAMES.items():
        combo.addItem(name, code)

    row.addWidget(combo)
    row.addStretch(1)
    layout.addLayout(row)

    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    layout.addWidget(browser, 1)

    def show_language():
        browser.setHtml(_license_html(combo.currentData()))

    combo.currentIndexChanged.connect(lambda _index: show_language())

    start = combo.findData(tr.lang if tr.lang in LICENSE_NOTICES else "en")
    combo.setCurrentIndex(max(start, 0))
    show_language()

    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.exec_()


def show_about_dialog(parent=None):
    app = QApplication.instance()
    name = app.applicationName() if app else "PyDiagram"
    version = app.applicationVersion() if app else ""

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"About {name}")
    dialog.setFixedWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(6)

    title_label = QLabel(name)
    title_font = QFont()
    title_font.setPointSize(16)
    title_font.setBold(True)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignHCenter)
    layout.addWidget(title_label)

    if version:
        version_label = QLabel(f"Version {version}")
        version_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(version_label)

    layout.addSpacing(10)

    description_label = QLabel(DESCRIPTION)
    description_label.setWordWrap(True)
    description_label.setAlignment(Qt.AlignHCenter)
    layout.addWidget(description_label)

    layout.addSpacing(10)

    runtime_label = QLabel(
        f"Built with PyQt5 {PYQT_VERSION_STR} \u00b7 Qt {QT_VERSION_STR}"
    )
    runtime_label.setAlignment(Qt.AlignHCenter)
    runtime_label.setStyleSheet("color: #808080;")
    layout.addWidget(runtime_label)
    
    copyright_label = QLabel(
        f"(c) 2026 Maher Berzig"
    )
    copyright_label.setAlignment(Qt.AlignHCenter)
    copyright_label.setStyleSheet("color: #808080;")
    layout.addWidget(copyright_label)    

    layout.addSpacing(10)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok)
    buttons.accepted.connect(dialog.accept)

    license_button = buttons.addButton("License", QDialogButtonBox.ActionRole)
    license_button.clicked.connect(lambda: show_license_dialog(dialog))

    layout.addWidget(buttons)

    dialog.exec_()
