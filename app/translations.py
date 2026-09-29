# translation.py
"""Application translations and the small runtime translation helper."""

from PyQt5.QtCore import Qt, QEvent, QObject, QTimer
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import (
    QAction, QAbstractButton, QComboBox, QDialogButtonBox, QDockWidget,
    QApplication, QLabel, QLineEdit, QMenu, QMenuBar, QTabWidget, QToolBar,
    QToolTip, QWidget,
)

LANGUAGE_NAMES = {
    "en": "English",
    "ar": "العربية",
    "fr": "Français",
}

LANGUAGE_DIRECTION = {
    "en": "ltr",
    "ar": "rtl",
    "fr": "ltr",
}

DEFAULT_LANGUAGE = "en"

# Keys are deliberately semantic rather than English sentences.  This makes
# the source code independent of the translated wording and leaves room for
# future languages without changing the UI code.
translations = {
    "en": {
        "app_title": "PyDiagram",
        "language": "Language",
        "file": "&File", "edit": "&Edit", "select": "&Select",
        "objects": "&Objects", "diagram": "&Diagram", "view": "&View",
        "help_menu": "&Help", "new": "&New", "open": "&Open...",
        "save": "&Save", "save_as": "Save &As...", "recent_files": "Recent &Files",
        "clear_recent_files": "Clear Recent Files", "exit": "E&xit",
        "export_png": "Export as &PNG...", "export_svg": "Export as &SVG...",
        "export_pdf": "Export to P&DF...", "export_tikz": "Export as &Tikz...",
        "undo": "&Undo", "redo": "&Redo", "delete": "&Delete",
        "copy": "&Copy", "cut": "Cu&t", "paste": "&Paste", "clone": "Cl&one",
        "duplicate": "D&uplicate", "all": "&All", "none": "&None",
        "invert": "&Invert", "same_type": "&Same Type", "transitive": "&Transitive",
        "connected": "&Connected", "send_to_back": "Send to &Back",
        "bring_to_front": "Bring to &Front", "send_backwards": "Send Backwards",
        "bring_forwards": "Bring Forwards", "group": "&Group", "ungroup": "&Ungroup",
        "align": "&Align", "left": "&Left", "center": "&Center", "right": "&Right",
        "top": "&Top", "middle": "&Middle", "bottom": "&Bottom",
        "spread_horizontal": "Spread Out &Horizontally", "spread_vertical": "Spread Out &Vertically",
        "position": "&Position...", "rotate": "&Rotate...", "rotate_plus": "Rotate +1°",
        "rotate_minus": "Rotate -1°", "scale": "&Scale", "flip": "&Flip", "horizontal": "&Horizontal",
        "vertical": "&Vertical", "properties": "&Properties", "save_shape": "Save as New Shape...",
        "diagram_properties": "&Properties...", "cleanup_latex": "Clean Up &LaTeX Image Cache...",
        "zoom": "&Zoom", "zoom_in": "Zoom &In", "zoom_out": "Zoom &Out", "normal_size": "&Normal Size",
        "best_fit": "&Best Fit", "refresh": "&Refresh", "show_rulers": "Show &Rulers",
        "shapes": "&Shapes", "layers": "&Layers", "tools": "&Tools", "diagram_tree": "&Diagram Tree", "lock_panels": "Lock Panels",
        "show_grid": "Show &Grid", "snap_to_grid": "&Snap To Grid", "snap_to_objects": "Snap To &Objects",
        "show_connection_points": "Show &Connection Points", "help": "&Help", "about": "&About",
        "export": "Export", "edit_toolbar": "Edit", "select_toolbar": "Select", "align_toolbar": "Align",
        "tools_toolbar": "Tools", "recent_files_tooltip": "Recent files", "language_tooltip": "Language",
        "new_tooltip": "New (Ctrl+N)", "open_tooltip": "Open... (Ctrl+O)",
        "save_tooltip": "Save / Save All / Save As...", "export_tooltip": "Export",
        "edit_tooltip": "Edit", "duplicate_tooltip": "Duplicate (Ctrl+D)",
        "select_tooltip": "Select", "undo_tooltip": "Undo (Ctrl+Z)",
        "redo_tooltip": "Redo (Ctrl+Shift+Z)", "zoom_tooltip": "Scroll the mouse wheel to zoom",
        "best_fit_tooltip": "Best Fit (Ctrl+F)", "refresh_tooltip": "Refresh (F5)",
        "rulers_tooltip": "Show Rulers (F6)", "shapes_tooltip": "Shapes (F7)",
        "layers_tooltip": "Layers (F8)", "tree_tooltip": "Diagram Tree (F10)",
        "grid_tooltip": "Show Grid", "snap_grid_tooltip": "Snap to Grid",
        "snap_objects_tooltip": "Snap to Objects", "connections_tooltip": "Show Connections",
        "send_back_tooltip": "Send to Back (Ctrl+Shift+B)", "front_tooltip": "Bring to Front (Ctrl+Shift+F)",
        "backwards_tooltip": "Send Backwards (Ctrl+Down)", "forwards_tooltip": "Bring Forwards (Ctrl+Up)",
        "group_tooltip": "Group (Ctrl+G)", "ungroup_tooltip": "Ungroup (Ctrl+Shift+G)",
        "rotate_tooltip": "Rotate... (Ctrl+R: +1°, Ctrl+Shift+R: -1°)",
        "scale_tooltip": "Scale (Ctrl(+Shift)+L/M: +(-)1% Horizontal/Vertical)",
        "properties_tooltip": "Properties (Alt+Enter)", "cleanup_tooltip": "Clean Up LaTeX Image Cache...",
        "help_tooltip": "Help (F1)",
        "paper_sizes": "&Paper Sizes", "paper_size": "Paper size:", "paper_orientation": "Paper orientation:",
        "custom_width": "Custom width:", "custom_height": "Custom height:", "best_fit_paper": "Best Fit",
        "custom_size": "Custom Size", "portrait": "portrait", "landscape": "landscape",
        "grid": "Grid", "colors": "Colors", "visible": "Visible:", "snap_to": "Snap to:",
        "x_size": "X Size:", "y_size": "Y Size:", "color": "Color:", "background": "Background:",
        "ok": "OK", "cancel": "Cancel", "close": "Close", "save_button": "Save", "discard": "Discard", "yes": "Yes", "no": "No", "open_button": "Open", "export_button": "Export",
        "move_up": "Move Up", "move_down": "Move Down", "insert": "Insert",
        "save_as_new_shape": "Save as New Shape", "folder_name": "Folder name for the new category",
        "shape_name": "Shape name", "browse": "Browse...", "copy_clipboard": "Copy to Clipboard",
        "tikz_code": "Tikz Code", "save_tikz_code": "Save Tikz Code", "latex_error": "LaTeX Error",
        "create_image_latex": "Create Image from LaTeX", "latex_failed": "LaTeX compilation failed:",
        "text_color": "Text Color", "background_color": "Background Color", "render_preview": "Render Preview",
        "padding": "Padding:", "dpi": "DPI:", "preamble": "Preamble:", "latex": "LaTeX:",
        "preview": "Preview:", "rendering": "Rendering...", "rendering_failed": "Rendering failed",
        "position_dialog": "Position", "about": "&About", "help_dialog": "PyDiagram Help",
        "back": "< Back", "forward": "Forward >", "home": "Home", "version": "Version",
        "export_to_pdf": "Export to PDF", "check_files": "Check the files to export, one PDF page each, in the order listed:",
        "invalid_function": "Invalid Function", "note": "Note:",
        "autoroute": "Autoroute", "add_segment": "Add segment", "delete_segment": "Delete segment",
        "add_point": "Add Point", "delete_point": "Delete Point", "linear": "Linear", "radial": "Radial",
        "image": "Image...", "no_file_selected": "(no file selected)",
        "gradient_hint": "Drag the point on the preview to move the gradient's center.",
        "solid_gradient_pattern": "Use a solid color, a two-color gradient, or a pattern?",
        "functions_range": "Functions & Range", "axes_ticks": "Axes & Ticks", "lines_fill": "Lines & Fill",
        "curve_colors_note": "Curve colors are set on the Functions & Range tab.",
        "corner": "Corner", "properties_dialog": "Properties", "pdf_link": "PDF Link:", "pdf_link_none": "None", "pdf_link_unavailable": "Unavailable destination (document is closed)", "clean_cache_empty": "The LaTeX image cache is already empty.",
        "continue": "Continue?", "deleted_cache": "Deleted {count} cached equation image{plural}, freeing {size:.1f} MB.",
        "cache_cleanup_question": "This will delete {count} cached equation image{plural} ({size:.1f} MB).\n\nAny diagram that still uses one will regenerate it automatically the next time it's displayed (this requires a local LaTeX installation - pdflatex and pdftocairo - to still be available).\n\nContinue?",
        "runtime_description": "A Dia-inspired 2D diagram editor: draw Flowchart, UML and general-purpose diagrams, connect shapes with lines, organize them into layers, and export to PNG, SVG or Tikz.",
        "built_with": "Built with PyQt5 {pyqt} · Qt {qt}", "copyright": "(c) 2026 Maher Berzig",
    },
    "fr": {
        "app_title": "PyDiagram", "language": "Langue", "file": "&Fichier", "edit": "&Édition", "select": "&Sélection",
        "objects": "&Objets", "diagram": "&Diagramme", "view": "&Affichage", "help_menu": "&Aide",
        "new": "&Nouveau", "open": "&Ouvrir...", "save": "&Enregistrer", "save_as": "Enregistrer sous...",
        "recent_files": "Fichiers &récents", "clear_recent_files": "Effacer les fichiers récents", "exit": "&Quitter",
        "export_png": "Exporter en &PNG...", "export_svg": "Exporter en &SVG...", "export_pdf": "Exporter en P&DF...", "export_tikz": "Exporter en &Tikz...",
        "undo": "&Annuler", "redo": "&Rétablir", "delete": "&Supprimer", "copy": "&Copier", "cut": "Co&uper", "paste": "&Coller", "clone": "C&loner", "duplicate": "D&upliquer",
        "all": "&Tous", "none": "&Aucun", "invert": "&Inverser", "same_type": "&Même type", "transitive": "&Transitif", "connected": "&Connectés",
        "send_to_back": "Mettre tout à l'&arrière", "bring_to_front": "Mettre tout à l'&avant", "send_backwards": "Reculer", "bring_forwards": "Avancer",
        "group": "&Grouper", "ungroup": "&Dégrouper", "align": "&Aligner", "left": "À &gauche", "center": "&Centrer", "right": "À d&roite", "top": "En &haut", "middle": "Au &milieu", "bottom": "En &bas",
        "spread_horizontal": "Répartir &horizontalement", "spread_vertical": "Répartir &verticalement", "position": "&Position...", "rotate": "&Rotation...", "rotate_plus": "Rotation +1°", "rotate_minus": "Rotation -1°", "scale": "&Échelle", "flip": "&Retourner", "horizontal": "&Horizontal", "vertical": "&Vertical",
        "properties": "&Propriétés", "save_shape": "Enregistrer comme nouvelle forme...", "diagram_properties": "&Propriétés...", "cleanup_latex": "Nettoyer le &cache des images LaTeX...",
        "zoom": "&Zoom","zoom_in": "&Zoom avant", "zoom_out": "Zoom &arrière", "normal_size": "Taille &normale", "best_fit": "&Ajuster", "refresh": "&Actualiser", "show_rulers": "Afficher les &règles", "shapes": "&Formes", "layers": "&Calques", "tools": "&Outils", "diagram_tree": "Arbre du &diagramme", "lock_panels": "Verrouiller les panneaux", "show_grid": "Afficher la &grille", "snap_to_grid": "&Aligner sur la grille", "snap_to_objects": "Aligner sur les &objets", "show_connection_points": "Afficher les points de &connexion", "help": "&Aide", "about": "À &propos",
        "export": "Exporter", "edit_toolbar": "Édition", "select_toolbar": "Sélection", "align_toolbar": "Aligner", "tools_toolbar": "Outils", "recent_files_tooltip": "Fichiers récents", "language_tooltip": "Langue",
        "new_tooltip": "Nouveau (Ctrl+N)", "open_tooltip": "Ouvrir... (Ctrl+O)", "save_tooltip": "Enregistrer / Tout enregistrer / Enregistrer sous...", "export_tooltip": "Exporter", "edit_tooltip": "Édition", "duplicate_tooltip": "Dupliquer (Ctrl+D)", "select_tooltip": "Sélection", "undo_tooltip": "Annuler (Ctrl+Z)", "redo_tooltip": "Rétablir (Ctrl+Shift+Z)", "zoom_tooltip": "Faire défiler la souris pour zoomer", "best_fit_tooltip": "Ajuster (Ctrl+F)", "refresh_tooltip": "Actualiser (F5)", "rulers_tooltip": "Afficher les règles (F6)", "shapes_tooltip": "Formes (F7)", "layers_tooltip": "Calques (F8)", "tree_tooltip": "Arbre du diagramme (F10)", "grid_tooltip": "Afficher la grille", "snap_grid_tooltip": "Aligner sur la grille", "snap_objects_tooltip": "Aligner sur les objets", "connections_tooltip": "Afficher les connexions", "send_back_tooltip": "Mettre tout à l'arrière (Ctrl+Shift+B)", "front_tooltip": "Mettre tout à l'avant (Ctrl+Shift+F)", "backwards_tooltip": "Reculer (Ctrl+Down)", "forwards_tooltip": "Avancer (Ctrl+Up)", "group_tooltip": "Grouper (Ctrl+G)", "ungroup_tooltip": "Dégrouper (Ctrl+Shift+G)", 
        "rotate_tooltip": "Rotation... (Ctrl+R : +1°, Ctrl+Shift+R : -1°)",
        "scale_tooltip": "Échelle (Ctrl(+Shift)+L/M : +(-)1% horizontal/vertical)",
        "properties_tooltip": "Propriétés (Alt+Entrée)", "cleanup_tooltip": "Nettoyer le cache des images LaTeX...", "help_tooltip": "Aide (F1)",
        "paper_sizes": "Formats de papier", "paper_sizes_action": "&Formats de papier", "paper_sizes_tooltip": "Formats de papier (Alt+Entrée)",
        "paper_size": "Format de papier :", "paper_orientation": "Orientation du papier :",
        "custom_width": "Largeur personnalisée :", "custom_height": "Hauteur personnalisée :", "best_fit_paper": "Ajuster", "custom_size": "Taille personnalisée", "portrait": "portrait", "landscape": "paysage", "grid": "Grille", "colors": "Couleurs", "visible": "Visible :", "snap_to": "Aligner sur :", "x_size": "Taille X :", "y_size": "Taille Y :", "color": "Couleur :", "background": "Arrière-plan :",
        "ok": "OK", "cancel": "Annuler", "close": "Fermer", "save_button": "Enregistrer", "discard": "Ignorer", "yes": "Oui", "no": "Non", "open_button": "Ouvrir", "export_button": "Exporter", "move_up": "Monter", "move_down": "Descendre", "insert": "Insérer", "save_as_new_shape": "Enregistrer comme nouvelle forme", "folder_name": "Nom du dossier pour la nouvelle catégorie", "shape_name": "Nom de la forme", "browse": "Parcourir...", "copy_clipboard": "Copier dans le presse-papiers", "tikz_code": "Code Tikz", "save_tikz_code": "Enregistrer le code Tikz", "latex_error": "Erreur LaTeX", "create_image_latex": "Créer une image depuis LaTeX", "latex_failed": "Échec de la compilation LaTeX :", "text_color": "Couleur du texte", "background_color": "Couleur d'arrière-plan", "render_preview": "Afficher l'aperçu", "padding": "Marge :", "dpi": "DPI :", "preamble": "Préambule :", "latex": "LaTeX :", "preview": "Aperçu :", "rendering": "Rendu...", "rendering_failed": "Échec du rendu", "position_dialog": "Position", "help_dialog": "Aide PyDiagram", "back": "< Retour", "forward": "Suivant >", "home": "Accueil", "version": "Version", "export_to_pdf": "Exporter en PDF", "check_files": "Cochez les fichiers à exporter, une page PDF par fichier, dans l'ordre indiqué :", "invalid_function": "Fonction invalide", "note": "Note :", "autoroute": "Autoroutage", "add_segment": "Ajouter un segment", "delete_segment": "Supprimer le segment", "add_point": "Ajouter un point", "delete_point": "Supprimer le point", "linear": "Linéaire", "radial": "Radial", "image": "Image...", "no_file_selected": "(aucun fichier sélectionné)", "gradient_hint": "Faites glisser le point dans l'aperçu pour déplacer le centre du dégradé.", "solid_gradient_pattern": "Utiliser une couleur unie, un dégradé à deux couleurs ou un motif ?", "functions_range": "Fonctions et plage", "axes_ticks": "Axes et graduations", "lines_fill": "Lignes et remplissage", "curve_colors_note": "Les couleurs des courbes sont définies dans l'onglet Fonctions et plage.", "corner": "Coin", "properties_dialog": "Propriétés", "pdf_link": "Lien PDF :", "pdf_link_none": "Aucun", "pdf_link_unavailable": "Destination indisponible (le document est fermé)", "clean_cache_empty": "Le cache des images LaTeX est déjà vide.", "continue": "Continuer ?", "runtime_description": "Un éditeur de diagrammes 2D inspiré de Dia : créez des diagrammes d'organigrammes, UML et généraux, reliez les formes, organisez-les en calques et exportez en PNG, SVG ou Tikz.", "built_with": "Créé avec PyQt5 {pyqt} · Qt {qt}", "copyright": "(c) 2026 Maher Berzig",
    },
    "ar": {
        "app_title": "PyDiagram", "language": "اللغة", "file": "ملف", "edit": "تحرير", "select": "تحديد", "objects": "الكائنات", "diagram": "المخطط", "view": "عرض", "help_menu": "مساعدة",
        "new": "جديد", "open": "فتح...", "save": "حفظ", "save_as": "حفظ باسم...", "recent_files": "الملفات الأخيرة", "clear_recent_files": "مسح الملفات الأخيرة", "exit": "خروج",
        "export_png": "تصدير بصيغة PNG...", "export_svg": "تصدير بصيغة SVG...", "export_pdf": "تصدير إلى PDF...", "export_tikz": "تصدير بصيغة Tikz...", "undo": "تراجع", "redo": "إعادة", "delete": "حذف", "copy": "نسخ", "cut": "قص", "paste": "لصق", "clone": "استنساخ", "duplicate": "تكرار",
        "all": "الكل", "none": "لا شيء", "invert": "عكس التحديد", "same_type": "نفس النوع", "transitive": "متعدٍ", "connected": "المتصلة", "send_to_back": "إلى الخلف", "bring_to_front": "إلى الأمام", "send_backwards": "تحريك للخلف", "bring_forwards": "تحريك للأمام", "group": "تجميع", "ungroup": "إلغاء التجميع", "align": "محاذاة", "left": "يسار", "center": "توسيط", "right": "يمين", "top": "أعلى", "middle": "وسط", "bottom": "أسفل", 
        "spread_horizontal": "توزيع أفقيًا", "spread_vertical": "توزيع عموديًا", "position": "الموضع...", "rotate": "تدوير...", "rotate_plus": "تدوير +1°", "rotate_minus": "تدوير -1°", "scale": "مقياس", "flip": "قلب", "horizontal": "أفقي", "vertical": "عمودي",
        "properties": "الخصائص", "save_shape": "حفظ كشكل جديد...", "diagram_properties": "الخصائص...", "cleanup_latex": "تنظيف ذاكرة صور LaTeX المؤقتة...",
        "zoom": "تكبير/تصغير", "zoom_in": "تكبير", "zoom_out": "تصغير", "normal_size": "الحجم الطبيعي", "best_fit": "أفضل ملاءمة", "refresh": "تحديث", "show_rulers": "إظهار المساطر", "shapes": "الأشكال", "layers": "الطبقات", "tools": "الأدوات", "diagram_tree": "شجرة المخطط", "lock_panels": "قفل اللوحات", "show_grid": "إظهار الشبكة", "snap_to_grid": "محاذاة إلى الشبكة", "snap_to_objects": "محاذاة إلى الكائنات", "show_connection_points": "إظهار نقاط الاتصال", "help": "مساعدة", "about": "حول البرنامج",
        "export": "تصدير", "edit_toolbar": "تحرير", "select_toolbar": "تحديد", "align_toolbar": "محاذاة", "tools_toolbar": "الأدوات", "recent_files_tooltip": "الملفات الأخيرة", "language_tooltip": "اللغة", "new_tooltip": "جديد (Ctrl+N)", "open_tooltip": "فتح... (Ctrl+O)", "save_tooltip": "حفظ / حفظ الكل / حفظ باسم...", "export_tooltip": "تصدير", "edit_tooltip": "تحرير", "duplicate_tooltip": "تكرار (Ctrl+D)", "select_tooltip": "تحديد", "undo_tooltip": "تراجع (Ctrl+Z)", "redo_tooltip": "إعادة (Ctrl+Shift+Z)", "zoom_tooltip": "استخدم عجلة الفأرة للتكبير والتصغير", "best_fit_tooltip": "أفضل ملاءمة (Ctrl+F)", "refresh_tooltip": "تحديث (F5)", "rulers_tooltip": "إظهار المساطر (F6)", "shapes_tooltip": "الأشكال (F7)", "layers_tooltip": "الطبقات (F8)", "tree_tooltip": "شجرة المخطط (F10)", "grid_tooltip": "إظهار الشبكة", "snap_grid_tooltip": "محاذاة إلى الشبكة", "snap_objects_tooltip": "محاذاة إلى الكائنات", "connections_tooltip": "إظهار الاتصالات", "send_back_tooltip": "إلى الخلف (Ctrl+Shift+B)", "front_tooltip": "إلى الأمام (Ctrl+Shift+F)", "backwards_tooltip": "تحريك للخلف (Ctrl+Down)", "forwards_tooltip": "تحريك للأمام (Ctrl+Up)", "group_tooltip": "تجميع (Ctrl+G)", "ungroup_tooltip": "إلغاء التجميع (Ctrl+Shift+G)", 
        "rotate_tooltip": "تدوير... (Ctrl+R: +1°، Ctrl+Shift+R: -1°)",
        "scale_tooltip": "مقياس (Ctrl(+Shift)+L/M: +(-)1% أفقي/عمودي)",
        "properties_tooltip": "الخصائص (Alt+Enter)", "cleanup_tooltip": "تنظيف ذاكرة صور LaTeX المؤقتة...", "help_tooltip": "مساعدة (F1)",
        "paper_sizes": "أحجام الورق", "paper_sizes_action": "أحجام الورق", "paper_sizes_tooltip": "أحجام الورق (Alt+Enter)",
        "paper_size": "حجم الورق:", "paper_orientation": "اتجاه الورق:",
        "custom_width": "العرض المخصص:", "custom_height": "الارتفاع المخصص:", "best_fit_paper": "أفضل ملاءمة", "custom_size": "حجم مخصص", "portrait": "عمودي", "landscape": "أفقي", "grid": "الشبكة", "colors": "الألوان", "visible": "مرئية:", "snap_to": "محاذاة إلى:", "x_size": "حجم X:", "y_size": "حجم Y:", "color": "اللون:", "background": "الخلفية:",
        "ok": "موافق", "cancel": "إلغاء", "close": "إغلاق", "save_button": "حفظ", "discard": "تجاهل", "yes": "نعم", "no": "لا", "open_button": "فتح", "export_button": "تصدير", "move_up": "تحريك لأعلى", "move_down": "تحريك لأسفل", "insert": "إدراج", "save_as_new_shape": "حفظ كشكل جديد", "folder_name": "اسم المجلد للفئة الجديدة", "shape_name": "اسم الشكل", "browse": "استعراض...", "copy_clipboard": "نسخ إلى الحافظة", "tikz_code": "كود Tikz", "save_tikz_code": "حفظ كود Tikz", "latex_error": "خطأ في LaTeX", "create_image_latex": "إنشاء صورة من LaTeX", "latex_failed": "فشل تجميع LaTeX:", "text_color": "لون النص", "background_color": "لون الخلفية", "render_preview": "عرض المعاينة", "padding": "الهامش:", "dpi": "DPI:", "preamble": "المقدمة:", "latex": "LaTeX:", "preview": "المعاينة:", "rendering": "جارٍ العرض...", "rendering_failed": "فشل العرض", "position_dialog": "الموضع", "help_dialog": "مساعدة PyDiagram", "back": "< رجوع", "forward": "التالي >", "home": "الرئيسية", "version": "الإصدار", "export_to_pdf": "تصدير إلى PDF", "check_files": "حدد الملفات المراد تصديرها، صفحة PDF واحدة لكل ملف، بالترتيب الموضح:", "invalid_function": "دالة غير صالحة", "note": "ملاحظة:", "autoroute": "توجيه تلقائي", "add_segment": "إضافة مقطع", "delete_segment": "حذف المقطع", "add_point": "إضافة نقطة", "delete_point": "حذف النقطة", "linear": "خطي", "radial": "شعاعي", "image": "صورة...", "no_file_selected": "(لم يتم تحديد ملف)", "gradient_hint": "اسحب النقطة في المعاينة لتحريك مركز التدرج.", "solid_gradient_pattern": "استخدام لون ثابت أم تدرج بلونين أم نمط؟", "functions_range": "الدوال والمجال", "axes_ticks": "المحاور والتدريجات", "lines_fill": "الخطوط والتعبئة", "curve_colors_note": "يتم تحديد ألوان المنحنيات في علامة تبويب الدوال والمجال.", "corner": "الزاوية", "properties_dialog": "الخصائص", "pdf_link": "رابط PDF:", "pdf_link_none": "لا شيء", "pdf_link_unavailable": "وجهة غير متاحة (المستند مغلق)", "clean_cache_empty": "ذاكرة صور LaTeX المؤقتة فارغة بالفعل.", "continue": "متابعة؟", "runtime_description": "محرر مخططات ثنائي الأبعاد مستوحى من Dia: أنشئ مخططات التدفق وUML والمخططات العامة، واربط الأشكال، ونظمها في طبقات، وصدّرها إلى PNG أو SVG أو Tikz.", "built_with": "تم إنشاؤه باستخدام PyQt5 {pyqt} · Qt {qt}", "copyright": "(c) 2026 ماهر برزيق",
    },
}

# Additional labels used by the toolbox, defaults panel, and common
# property controls.  Keeping these here also makes the automatic widget
# translation pass cover dialogs that are assembled dynamically.
translations["en"].update({
    "ready": "Ready", "default_fg": "Default foreground (line) color",
    "default_bg": "Default background (fill) color", "restore_colors": "Restore default colors",
    "reverse_colors": "Reverse colors", "line_width_px": "{width}px line width",
    "default_line_style": "Default line style", "default_start_arrow": "Default start arrow",
    "default_end_arrow": "Default end arrow", "select_tool": "Select", "pan_tool": "Pan",
    "rectangle": "Rectangle", "ellipse": "Ellipse", "plot": "Plot", "polygon": "Polygon",
    "line": "Line", "arc": "Arc", "polyline": "Polyline", "zigzagline": "Zigzagline",
    "image_tool": "Image","mask_tool": "Mask", "beziergon": "Beziergon", "bezierline": "Bezierline", "square": "Square",
    "circle": "Circle", "isosceles_triangle": "Isosceles Triangle", "right_triangle": "Right Triangle",
    "cross": "Cross", "regular_polygon": "Regular Polygon", "star": "Star", "spiral": "Spiral",
    "three_quarter_circle": "Three-Quarter Circle", "crescent": "Crescent", "spring": "Spring",
    "l_shape": "L-shape", "text_tool": "Text", "anchor": "Anchor", "process": "Process",
    "decision": "Decision", "database": "Database", "data_io": "Data (I/O)",
    "predefined_process": "Predefined Process", "preparation": "Preparation", "document": "Document",
    "delay": "Delay", "summing_junction": "Summing Junction", "class": "Class", "interface": "Interface",
    "actor": "Actor", "package": "Package", "component": "Component", "node": "Node", "note": "Note",
    "lifeline": "Lifeline", "required_interface": "Required Interface", "basic": "Basic",
    "flowchart": "Flowchart", "uml": "UML", "assorted": "Assorted",
    "drag_pan": "Drag with the left mouse button to move the canvas",
    "anchor_hint": "Select a shape, then click to add a connection point",
    "not_implemented": "{label} isn't implemented yet", "new_layer": "New", "up": "Up", "down": "Down", "del": "Del",
    "solid": "Solid", "dashed": "Dashed", "dash_dot": "Dash-Dot", "dash_dot_dot": "Dash-Dot-Dot", "dotted": "Dotted",
    "none_style": "None", "line_arrow": "Line Arrow", "filled_triangle": "Filled Triangle", "hollow_triangle": "Hollow Triangle",
    "filled_diamond": "Filled Diamond", "hollow_diamond": "Hollow Diamond", "filled_circle": "Filled Circle", "hollow_circle": "Hollow Circle",
    "filled_square": "Filled Square", "hollow_square": "Hollow Square", "half_head": "Half Head",
    "horizontal_lines": "Horizontal Lines", "vertical_lines": "Vertical Lines", "backward_diagonal": "Backward Diagonal",
    "forward_diagonal": "Forward Diagonal", "diagonal_cross": "Diagonal Cross", "dense1": "Dense 1 (sparsest)",
    "dense2": "Dense 2", "dense3": "Dense 3", "dense4": "Dense 4", "dense5": "Dense 5", "dense6": "Dense 6", "dense7": "Dense 7 (densest)",
    "default_background_color": "Default Background Color",
    "unsaved_changes": "Unsaved Changes", "save_changes_before_closing": 'Save changes to "{name}" before closing?',
    "save_shape_error": "Couldn't save the shape:\n{error}", "open_diagram": "Open Diagram",
    "couldnt_find_recent": "Couldn't find {path}.\nIt's been removed from Recent Files.", "couldnt_open": "Couldn't open {path}:\n{error}",
    "export_pdf_error": "Could not write the PDF:\n{error}", "empty_latex": "Empty LaTeX", "enter_latex": "Please enter some LaTeX to render.",
    "about_app": "About {name}", "version_dynamic": "Version {version}", "window_title": "{dirty}{name} - PyDiagram",
    "prop_fill_color": "Fill color:",
    "prop_line_color": "Line color:",
    "prop_line_width": "Line width:",
    "prop_line_style": "Line style:",
    "prop_dash_length": "Dash length:",
    "prop_draw_background": "Draw background:",
    "prop_num_points": "Number of points:",
    "prop_outer_corner_radius": "Outer Corner Radius:",
    "prop_inner_corner_radius": "Inner Corner Radius:",
    "prop_inner_radius": "Inner Radius:",
    "prop_corner_radius": "Corner Radius:",
    "prop_missing_angle": "Missing angle:",
    "prop_turns": "Turns:",
    "prop_class_name": "Class name:",
    "prop_attributes": "Attributes:",
    "prop_operations": "Operations:",
    "prop_corner_n_radius": "Corner {n} radius:",
    "prop_corner_n_tooltip": "Corner {n} ({tip})",
    "prop_corner_tip_tl": "top-left",
    "prop_corner_tip_tr": "top-right",
    "prop_corner_tip_br": "bottom-right",
    "prop_corner_tip_bl": "bottom-left",
    "prop_start_arrow": "Start arrow:",
    "prop_start_arrow_size": "Start arrow size:",
    "prop_end_arrow": "End arrow:",
    "prop_end_arrow_size": "End arrow size:",
    "prop_autoroute": "Autoroute:",
    "prop_image_file": "Image file:",
    "prop_text": "Text:",
    "prop_font": "Font:",
    "prop_alignment": "Alignment:",
    "prop_font_size": "Font size:",
    "prop_letter_spacing": "Letter spacing:",
    "prop_text_color": "Text color:",
    "prop_outline": "Outline:",
    "prop_outline_color": "Outline color:",
    "prop_outline_width": "Outline width:",
    "prop_rotation": "Rotation:",
    "prop_flip_horizontal": "Flip horizontal:",
    "prop_flip_vertical": "Flip vertical:",
    "prop_f1": "f1(x):",
    "prop_color": "Color:",
    "prop_f2": "f2(x):",
    "prop_x_minimum": "X minimum:",
    "prop_x_maximum": "X maximum:",
    "prop_fill_x1": "Fill x1:",
    "prop_fill_x2": "Fill x2:",
    "prop_y_minimum": "Y minimum:",
    "prop_y_maximum": "Y maximum:",
    "prop_sample_points": "Sample points:",
    "prop_axis_type": "Axis type:",
    "prop_show_grid": "Show grid:",
    "prop_x_tick_interval": "X tick interval:",
    "prop_show_x_labels": "Show X labels:",
    "prop_x_tick_label_format": "X tick label format:",
    "prop_y_tick_interval": "Y tick interval:",
    "prop_show_y_labels": "Show Y labels:",
    "prop_y_tick_label_format": "Y tick label format:",
    "prop_label_help": "Label help:",
    "prop_tick_hint": "Use {value} as the tick value. Examples:  x={value}   or   {value} cm",
    "prop_x_tick_placeholder": "e.g. x={value}",
    "prop_y_tick_placeholder": "e.g. y={value}",
    "prop_tick_tooltip": "Use {value} for the numeric tick value; surrounding text is preserved.",
    "prop_curve_width": "Curve width:",
    "prop_boundary_box": "x1 / x2 boundary lines",
    "prop_x1_color": "x1 color:",
    "prop_x2_color": "x2 color:",
    "prop_width": "Width:",
    "prop_style": "Style:",
    "prop_show_boundary_lines": "Show boundary lines:",
    "prop_curves_fill_box": "Curves and fill",
    "prop_fill": "Fill:",
    "prop_axis_border": "Axis/border:",
    "prop_axis_border_width": "Axis/border width:",
    "prop_axis_border_style": "Axis/border style:",
    "create_from_latex": "Create from LaTeX...",
    "select_image": "Select Image",
    "choose_color": "Choose Color",    
})
translations["fr"].update({
    "ready": "Prêt", "default_fg": "Couleur de premier plan par défaut (ligne)", "default_bg": "Couleur d'arrière-plan par défaut (remplissage)", "restore_colors": "Restaurer les couleurs par défaut", "reverse_colors": "Inverser les couleurs", "line_width_px": "Épaisseur de ligne : {width}px", "default_line_style": "Style de ligne par défaut", "default_start_arrow": "Flèche de début par défaut", "default_end_arrow": "Flèche de fin par défaut",
    "select_tool": "Sélection", "pan_tool": "Déplacer", "rectangle": "Rectangle", "ellipse": "Ellipse", "plot": "Graphe", "polygon": "Polygone", "line": "Ligne", "arc": "Arc", "polyline": "Polyligne", "zigzagline": "Ligne en zigzag", "image_tool": "Image", "mask_tool": "Masque", "beziergon": "Bézier", "bezierline": "Ligne de Bézier", "square": "Carré", "circle": "Cercle", "isosceles_triangle": "Triangle isocèle", "right_triangle": "Triangle rectangle", "cross": "Croix", "regular_polygon": "Polygone régulier", "star": "Étoile", "spiral": "Spirale", "three_quarter_circle": "Cercle aux trois quarts", "crescent": "Croissant", "spring": "Ressort", "l_shape": "Forme en L", "text_tool": "Texte", "anchor": "Point d'ancrage", "process": "Processus", "decision": "Décision", "database": "Base de données", "data_io": "Données (E/S)", "predefined_process": "Processus prédéfini", "preparation": "Préparation", "document": "Document", "delay": "Délai", "summing_junction": "Jonction sommante", "class": "Classe", "interface": "Interface", "actor": "Acteur", "package": "Paquet", "component": "Composant", "node": "Nœud", "note": "Note", "lifeline": "Ligne de vie", "required_interface": "Interface requise", "basic": "Base", "flowchart": "Organigramme", "uml": "UML", "assorted": "Divers", "drag_pan": "Faites glisser avec le bouton gauche pour déplacer le canevas", "anchor_hint": "Sélectionnez une forme, puis cliquez pour ajouter un point de connexion", "not_implemented": "{label} n'est pas encore implémenté", "new_layer": "Nouveau", "up": "Monter", "down": "Descendre", "del": "Suppr.", "solid": "Plein", "dashed": "Tirets", "dash_dot": "Tiret-point", "dash_dot_dot": "Tiret-point-point", "dotted": "Pointillé", "none_style": "Aucun", "line_arrow": "Flèche simple", "filled_triangle": "Triangle plein", "hollow_triangle": "Triangle creux", "filled_diamond": "Losange plein", "hollow_diamond": "Losange creux", "filled_circle": "Cercle plein", "hollow_circle": "Cercle creux", "filled_square": "Carré plein", "hollow_square": "Carré creux", "half_head": "Demi-pointe", "horizontal_lines": "Lignes horizontales", "vertical_lines": "Lignes verticales", "backward_diagonal": "Diagonale descendante", "forward_diagonal": "Diagonale montante", "diagonal_cross": "Croix diagonale", "dense1": "Dense 1 (le plus espacé)", "dense2": "Dense 2", "dense3": "Dense 3", "dense4": "Dense 4", "dense5": "Dense 5", "dense6": "Dense 6", "dense7": "Dense 7 (le plus dense)", "default_background_color": "Couleur d'arrière-plan par défaut",
    "unsaved_changes": "Modifications non enregistrées", "save_changes_before_closing": 'Enregistrer les modifications de « {name} » avant de fermer ?',
    "save_shape_error": "Impossible d'enregistrer la forme :\n{error}", "open_diagram": "Ouvrir le diagramme", "couldnt_find_recent": "Impossible de trouver {path}.\nIl a été retiré des fichiers récents.", "couldnt_open": "Impossible d'ouvrir {path} :\n{error}", "export_pdf_error": "Impossible d'écrire le PDF :\n{error}", "empty_latex": "LaTeX vide", "enter_latex": "Veuillez saisir du LaTeX à afficher.", "about_app": "À propos de {name}", "version_dynamic": "Version {version}", "window_title": "{dirty}{name} - PyDiagram",
    "prop_fill_color": "Couleur de remplissage :",
    "prop_line_color": "Couleur de ligne :",
    "prop_line_width": "Épaisseur de ligne :",
    "prop_line_style": "Style de ligne :",
    "prop_dash_length": "Longueur du tiret :",
    "prop_draw_background": "Dessiner l'arrière-plan :",
    "prop_num_points": "Nombre de points :",
    "prop_outer_corner_radius": "Rayon du coin extérieur :",
    "prop_inner_corner_radius": "Rayon du coin intérieur :",
    "prop_inner_radius": "Rayon intérieur :",
    "prop_corner_radius": "Rayon du coin :",
    "prop_missing_angle": "Angle manquant :",
    "prop_turns": "Tours :",
    "prop_class_name": "Nom de la classe :",
    "prop_attributes": "Attributs :",
    "prop_operations": "Opérations :",
    "prop_corner_n_radius": "Rayon du coin {n} :",
    "prop_corner_n_tooltip": "Coin {n} ({tip})",
    "prop_corner_tip_tl": "en haut à gauche",
    "prop_corner_tip_tr": "en haut à droite",
    "prop_corner_tip_br": "en bas à droite",
    "prop_corner_tip_bl": "en bas à gauche",
    "prop_start_arrow": "Flèche de début :",
    "prop_start_arrow_size": "Taille de la flèche de début :",
    "prop_end_arrow": "Flèche de fin :",
    "prop_end_arrow_size": "Taille de la flèche de fin :",
    "prop_autoroute": "Autoroutage :",
    "prop_image_file": "Fichier image :",
    "prop_text": "Texte :",
    "prop_font": "Police :",
    "prop_alignment": "Alignement :",
    "prop_font_size": "Taille de police :",
    "prop_letter_spacing": "Espacement des lettres :",
    "prop_text_color": "Couleur du texte :",
    "prop_outline": "Contour :",
    "prop_outline_color": "Couleur du contour :",
    "prop_outline_width": "Épaisseur du contour :",
    "prop_rotation": "Rotation :",
    "prop_flip_horizontal": "Retourner horizontalement :",
    "prop_flip_vertical": "Retourner verticalement :",
    "prop_f1": "f1(x) :",
    "prop_color": "Couleur :",
    "prop_f2": "f2(x) :",
    "prop_x_minimum": "X minimum :",
    "prop_x_maximum": "X maximum :",
    "prop_fill_x1": "Remplissage x1 :",
    "prop_fill_x2": "Remplissage x2 :",
    "prop_y_minimum": "Y minimum :",
    "prop_y_maximum": "Y maximum :",
    "prop_sample_points": "Points d'échantillonnage :",
    "prop_axis_type": "Type d'axe :",
    "prop_show_grid": "Afficher la grille :",
    "prop_x_tick_interval": "Intervalle des graduations X :",
    "prop_show_x_labels": "Afficher les étiquettes X :",
    "prop_x_tick_label_format": "Format des étiquettes X :",
    "prop_y_tick_interval": "Intervalle des graduations Y :",
    "prop_show_y_labels": "Afficher les étiquettes Y :",
    "prop_y_tick_label_format": "Format des étiquettes Y :",
    "prop_label_help": "Aide sur les étiquettes :",
    "prop_tick_hint": "Utilisez {value} comme valeur de graduation. Exemples : x={value} ou {value} cm",
    "prop_x_tick_placeholder": "ex. : x={value}",
    "prop_y_tick_placeholder": "ex. : y={value}",
    "prop_tick_tooltip": "Utilisez {value} pour la valeur numérique de la graduation ; le texte autour est conservé.",
    "prop_curve_width": "Épaisseur de la courbe :",
    "prop_boundary_box": "Lignes de délimitation x1 / x2",
    "prop_x1_color": "Couleur x1 :",
    "prop_x2_color": "Couleur x2 :",
    "prop_width": "Épaisseur :",
    "prop_style": "Style :",
    "prop_show_boundary_lines": "Afficher les lignes de délimitation :",
    "prop_curves_fill_box": "Courbes et remplissage",
    "prop_fill": "Remplissage :",
    "prop_axis_border": "Axe/bordure :",
    "prop_axis_border_width": "Épaisseur axe/bordure :",
    "prop_axis_border_style": "Style axe/bordure :",
    "create_from_latex": "Créer depuis LaTeX...",
    "select_image": "Sélectionner une image",
    "choose_color": "Choisir une couleur",    
})
translations["ar"].update({
    "ready": "جاهز", "default_fg": "لون المقدمة الافتراضي (الخط)", "default_bg": "لون الخلفية الافتراضي (التعبئة)", "restore_colors": "استعادة الألوان الافتراضية", "reverse_colors": "عكس الألوان", "line_width_px": "سماكة الخط {width}px", "default_line_style": "نمط الخط الافتراضي", "default_start_arrow": "سهم البداية الافتراضي", "default_end_arrow": "سهم النهاية الافتراضي",
    "select_tool": "تحديد", "pan_tool": "تحريك", "rectangle": "مستطيل", "ellipse": "بيضاوي", "plot": "رسم بياني", "polygon": "مضلع", "line": "خط", "arc": "قوس", "polyline": "خط متعدد", "zigzagline": "خط متعرج", "image_tool": "صورة", "mask_tool": "قناع",  "beziergon": "منحنى بيزييه", "bezierline": "خط بيزييه", "square": "مربع", "circle": "دائرة", "isosceles_triangle": "مثلث متساوي الساقين", "right_triangle": "مثلث قائم الزاوية", "cross": "علامة تقاطع", "regular_polygon": "مضلع منتظم", "star": "نجمة", "spiral": "حلزون", "three_quarter_circle": "دائرة بثلاثة أرباع", "crescent": "هلال", "spring": "نابض", "l_shape": "شكل L", "text_tool": "نص", "anchor": "نقطة ربط", "process": "عملية", "decision": "قرار", "database": "قاعدة بيانات", "data_io": "بيانات (إدخال/إخراج)", "predefined_process": "عملية معرفة مسبقًا", "preparation": "تحضير", "document": "مستند", "delay": "تأخير", "summing_junction": "وصلة جمع", "class": "فئة", "interface": "واجهة", "actor": "ممثل", "package": "حزمة", "component": "مكوّن", "node": "عقدة", "note": "ملاحظة", "lifeline": "خط الحياة", "required_interface": "واجهة مطلوبة", "basic": "أساسي", "flowchart": "مخطط تدفق", "uml": "UML", "assorted": "متنوع", "drag_pan": "اسحب بزر الفأرة الأيسر لتحريك اللوحة", "anchor_hint": "حدد شكلاً ثم انقر لإضافة نقطة اتصال", "not_implemented": "{label} غير مطبق بعد", "new_layer": "جديد", "up": "أعلى", "down": "أسفل", "del": "حذف", "solid": "متصل", "dashed": "متقطع", "dash_dot": "شرطة-نقطة", "dash_dot_dot": "شرطة-نقطة-نقطة", "dotted": "منقط", "none_style": "لا شيء", "line_arrow": "سهم خطي", "filled_triangle": "مثلث ممتلئ", "hollow_triangle": "مثلث مجوف", "filled_diamond": "معين ممتلئ", "hollow_diamond": "معين مجوف", "filled_circle": "دائرة ممتلئة", "hollow_circle": "دائرة مجوفة", "filled_square": "مربع ممتلئ", "hollow_square": "مربع مجوف", "half_head": "رأس نصف سهم", "horizontal_lines": "خطوط أفقية", "vertical_lines": "خطوط عمودية", "backward_diagonal": "قطري للخلف", "forward_diagonal": "قطري للأمام", "diagonal_cross": "تقاطع قطري", "dense1": "كثيف 1 (الأقل كثافة)", "dense2": "كثيف 2", "dense3": "كثيف 3", "dense4": "كثيف 4", "dense5": "كثيف 5", "dense6": "كثيف 6", "dense7": "كثيف 7 (الأكثر كثافة)", "default_background_color": "لون الخلفية الافتراضي",
    "unsaved_changes": "تغييرات غير محفوظة", "save_changes_before_closing": 'حفظ التغييرات في «{name}» قبل الإغلاق؟', "save_shape_error": "تعذر حفظ الشكل:\n{error}", "open_diagram": "فتح المخطط", "couldnt_find_recent": "تعذر العثور على {path}.\nتمت إزالته من الملفات الأخيرة.", "couldnt_open": "تعذر فتح {path}:\n{error}", "export_pdf_error": "تعذر كتابة ملف PDF:\n{error}", "empty_latex": "LaTeX فارغ", "enter_latex": "يرجى إدخال LaTeX للعرض.", "about_app": "حول {name}", "version_dynamic": "الإصدار {version}", "window_title": "{dirty}{name} - PyDiagram",
    "prop_fill_color": "لون التعبئة:",
    "prop_line_color": "لون الخط:",
    "prop_line_width": "سماكة الخط:",
    "prop_line_style": "نمط الخط:",
    "prop_dash_length": "طول الشرطة:",
    "prop_draw_background": "رسم الخلفية:",
    "prop_num_points": "عدد النقاط:",
    "prop_outer_corner_radius": "نصف قطر الزاوية الخارجية:",
    "prop_inner_corner_radius": "نصف قطر الزاوية الداخلية:",
    "prop_inner_radius": "نصف القطر الداخلي:",
    "prop_corner_radius": "نصف قطر الزاوية:",
    "prop_missing_angle": "الزاوية المفقودة:",
    "prop_turns": "اللفات:",
    "prop_class_name": "اسم الفئة:",
    "prop_attributes": "الخصائص:",
    "prop_operations": "العمليات:",
    "prop_corner_n_radius": "نصف قطر الزاوية {n}:",
    "prop_corner_n_tooltip": "الزاوية {n} ({tip})",
    "prop_corner_tip_tl": "أعلى اليسار",
    "prop_corner_tip_tr": "أعلى اليمين",
    "prop_corner_tip_br": "أسفل اليمين",
    "prop_corner_tip_bl": "أسفل اليسار",
    "prop_start_arrow": "سهم البداية:",
    "prop_start_arrow_size": "حجم سهم البداية:",
    "prop_end_arrow": "سهم النهاية:",
    "prop_end_arrow_size": "حجم سهم النهاية:",
    "prop_autoroute": "توجيه تلقائي:",
    "prop_image_file": "ملف الصورة:",
    "prop_text": "النص:",
    "prop_font": "الخط:",
    "prop_alignment": "المحاذاة:",
    "prop_font_size": "حجم الخط:",
    "prop_letter_spacing": "تباعد الأحرف:",
    "prop_text_color": "لون النص:",
    "prop_outline": "المحيط:",
    "prop_outline_color": "لون المحيط:",
    "prop_outline_width": "سماكة المحيط:",
    "prop_rotation": "التدوير:",
    "prop_flip_horizontal": "قلب أفقي:",
    "prop_flip_vertical": "قلب عمودي:",
    "prop_f1": "f1(x):",
    "prop_color": "اللون:",
    "prop_f2": "f2(x):",
    "prop_x_minimum": "الحد الأدنى لـ X:",
    "prop_x_maximum": "الحد الأقصى لـ X:",
    "prop_fill_x1": "تعبئة x1:",
    "prop_fill_x2": "تعبئة x2:",
    "prop_y_minimum": "الحد الأدنى لـ Y:",
    "prop_y_maximum": "الحد الأقصى لـ Y:",
    "prop_sample_points": "نقاط العينة:",
    "prop_axis_type": "نوع المحور:",
    "prop_show_grid": "إظهار الشبكة:",
    "prop_x_tick_interval": "فاصل تدريجات X:",
    "prop_show_x_labels": "إظهار تسميات X:",
    "prop_x_tick_label_format": "تنسيق تسميات X:",
    "prop_y_tick_interval": "فاصل تدريجات Y:",
    "prop_show_y_labels": "إظهار تسميات Y:",
    "prop_y_tick_label_format": "تنسيق تسميات Y:",
    "prop_label_help": "مساعدة التسميات:",
    "prop_tick_hint": "استخدم {value} كقيمة للتدريج. أمثلة: x={value} أو {value} cm",
    "prop_x_tick_placeholder": "مثال: x={value}",
    "prop_y_tick_placeholder": "مثال: y={value}",
    "prop_tick_tooltip": "استخدم {value} للقيمة الرقمية للتدريج؛ يتم الاحتفاظ بالنص المحيط.",
    "prop_curve_width": "سماكة المنحنى:",
    "prop_boundary_box": "خطوط حدود x1 / x2",
    "prop_x1_color": "لون x1:",
    "prop_x2_color": "لون x2:",
    "prop_width": "العرض:",
    "prop_style": "النمط:",
    "prop_show_boundary_lines": "إظهار خطوط الحدود:",
    "prop_curves_fill_box": "المنحنيات والتعبئة",
    "prop_fill": "التعبئة:",
    "prop_axis_border": "المحور/الحدود:",
    "prop_axis_border_width": "سماكة المحور/الحدود:",
    "prop_axis_border_style": "نمط المحور/الحدود:",
    "create_from_latex": "إنشاء من LaTeX...",
    "select_image": "اختيار صورة",
    "choose_color": "اختيار لون",    
})




# Added with: multi-file Open, Save All, View > Language, the stacking-order
# drop-down and the About > License button.
translations["en"].update({
    "save_all": "Save A&ll", "language_menu": "&Language",
    "stacking_tooltip": "Stacking Order", "save_diagram": "Save Diagram",
    "couldnt_save": "Couldn't save {path}:\n{error}",
    "license_button": "License", "license_language": "Language:",
    "license_note": "The English text is the authoritative version; the translations are unofficial.",
})
translations["fr"].update({
    "save_all": "Tout enregistrer", "language_menu": "Langue",
    "stacking_tooltip": "Ordre d'empilement", "save_diagram": "Enregistrer le diagramme",
    "couldnt_save": "Impossible d'enregistrer {path} :\n{error}",
    "license_button": "Licence", "license_language": "Langue :",
    "license_note": "Le texte anglais fait foi ; les traductions ne sont pas officielles.",
})
translations["ar"].update({
    "save_all": "حفظ الكل", "language_menu": "اللغة",
    "stacking_tooltip": "ترتيب التراص", "save_diagram": "حفظ المخطط",
    "couldnt_save": "تعذر حفظ {path}:\n{error}",
    "license_button": "الرخصة", "license_language": "اللغة:",
    "license_note": "النص الإنجليزي هو النسخة المعتمدة؛ والترجمات غير رسمية.",
})


# Exact English UI strings -> semantic translation keys.  This lets the
# existing dialogs remain readable while still using tr.get() everywhere
# through one common translation pass.
SOURCE_KEYS = {}
for _key, _value in translations["en"].items():
    if "{" not in _value:
        SOURCE_KEYS[_value] = _key

# Menu/action text carries a "&" mnemonic (e.g. "&Shapes") that a window
# or dock title for the same word never has (e.g. the Shapes toolbox
# panel's title is plain "Shapes") - build a second lookup, keyed by the
# mnemonic-stripped text, so those titles can still be matched back to
# the same translation key.
SOURCE_KEYS_STRIPPED = {
    _value.replace("&", ""): _key
    for _value, _key in SOURCE_KEYS.items()
    if "&" in _value
}

class _Translator:
    def __init__(self, table, default_lang=DEFAULT_LANGUAGE):
        self._table = table
        self.lang = default_lang if default_lang in table else DEFAULT_LANGUAGE

    def set_language(self, lang_code):
        self.lang = lang_code if lang_code in self._table else DEFAULT_LANGUAGE

    def get(self, key, default=""):
        return self._table.get(self.lang, {}).get(key, default)

    def is_rtl(self):
        return LANGUAGE_DIRECTION.get(self.lang, "ltr") == "rtl"

tr = _Translator(translations)


def _translated(source):
    key = SOURCE_KEYS.get(source)
    if key:
        return tr.get(key, source)
    # Window/dock titles (e.g. the Shapes/Layers/Diagram Tree toolbox
    # panels) are set without the "&" mnemonic that the corresponding
    # menu entry uses for the same word, since a title bar isn't a
    # keyboard-shortcut target. Fall back to matching the mnemonic-
    # stripped form so those titles get translated too, and strip "&"
    # back out of the result so a literal ampersand doesn't show up in
    # a title that never had one to begin with.
    if isinstance(source, str):
        stripped_key = SOURCE_KEYS_STRIPPED.get(source)
        if stripped_key:
            return tr.get(stripped_key, source).replace("&", "")
    if isinstance(source, str) and source.endswith("px line width") and source[:-14].isdigit():
        return tr.get("line_width_px", "{width}px line width").format(width=source[:-14])
    if isinstance(source, str) and source.endswith(" isn't implemented yet"):
        label = source[:-22]
        return tr.get("not_implemented", "{label} isn't implemented yet").format(label=_translated(label))
    if isinstance(source, str) and source.startswith('Save changes to "') and source.endswith('" before closing?'):
        name = source[len('Save changes to "'):-len('" before closing?')]
        return tr.get("save_changes_before_closing", source).format(name=name)
    if isinstance(source, str) and source.startswith("Couldn't find ") and source.endswith(".\nIt's been removed from Recent Files."):
        path = source[len("Couldn't find "):-len(".\nIt's been removed from Recent Files.")]
        return tr.get("couldnt_find_recent", source).format(path=path)
    if isinstance(source, str) and source.startswith("Couldn't open ") and ":\n" in source:
        path, error = source[len("Couldn't open "):].split(":\n", 1)
        return tr.get("couldnt_open", source).format(path=path, error=error)
    if isinstance(source, str) and source.startswith("Could not write the PDF:\n"):
        return tr.get("export_pdf_error", source).format(error=source.split("\n", 1)[1])
    if isinstance(source, str) and source.startswith("Couldn't save the shape:\n"):
        return tr.get("save_shape_error", source).format(error=source.split("\n", 1)[1])
    if isinstance(source, str) and source.startswith("Couldn't save ") and ":\n" in source:
        path, error = source[len("Couldn't save "):].split(":\n", 1)
        return tr.get("couldnt_save", source).format(path=path, error=error)
    if isinstance(source, str) and source.startswith("About "):
        return tr.get("about_app", source).format(name=source[6:])
    if isinstance(source, str) and source.startswith("Version "):
        return tr.get("version_dynamic", source).format(version=source[8:])
    if isinstance(source, str) and source.endswith(" - PyDiagram"):
        left = source[:-len(" - PyDiagram")]
        dirty = "*" if left.startswith("*") else ""
        name = left[1:] if dirty else left
        return tr.get("window_title", source).format(dirty=dirty, name=name)
    return source


def _resolved_source(cached, current):
    """
    Figure out the true (English) source text for `current`, the text a
    widget is showing right now. `cached` is a (source, last_output)
    pair remembered from the previous pass, or None.

    Widgets are always first built with their literal English text -
    translation only happens afterwards, in this sweep - so the first
    time we ever see a piece of text, it IS the source.

    After that, two things can have happened to it:

    - Nothing has touched it since we last wrote to it (`current`
      still equals what we output last time): the source we remembered
      is still right, so we keep using it. This is what lets repeated
      language switches (English -> Arabic -> French -> English...)
      keep re-translating correctly, instead of only working the first
      time and then getting stuck.
    - Application code has since put new text into the widget - a
      changed filename, a live value, a newly-selected shape's
      properties: `current` no longer matches what we last wrote, so
      it must be fresh, untranslated English content, and we adopt it
      as the new source. This is the important part: it stops a
      dynamic label/title from being silently stomped back to a stale
      or blank value the next time this sweep runs (which is what was
      making dialog contents disappear/revert after switching
      languages) - it also fixes the main window title reverting to
      its very first value instead of tracking the current file/dirty
      state.
    """
    if cached is not None and cached[1] == current:
        return cached[0]
    return current


def _translate_text_property(obj, prop_key, current, setter):
    cached = obj.property(prop_key)
    source = _resolved_source(cached, current)
    new_text = _translated(source)
    setter(new_text)
    obj.setProperty(prop_key, (source, new_text))
    return new_text


def _translate_action(action):
    _translate_text_property(action, "_translation_text", action.text(), action.setText)
    has_tip = bool(action.toolTip()) or action.property("_translation_tooltip") is not None
    if has_tip:
        _translate_text_property(
            action, "_translation_tooltip", action.toolTip(), action.setToolTip
        )


def _repolish_chrome(w):
    """
    Force a widget to redraw its native chrome - title bars, toolbar
    handles, and the like - from scratch.

    Plain content widgets (labels, buttons, layouts...) pick up a
    layoutDirection change immediately. A QDockWidget's title bar -
    where the float/close buttons live and which side the title text
    hugs - is different: it caches that chrome, and in practice only
    ever draws it correctly for whichever direction was already in
    effect when the dock was created. That's the reason a live
    language switch used to leave dock titles laid out the old way
    until the app was restarted (which rebuilds the docks from
    scratch, this time with the new direction already set). Setting
    the direction explicitly on the widget itself (not just relying on
    it being inherited from a parent) and then repolishing forces that
    cached chrome to be redrawn right away instead.
    """
    style = w.style()
    style.unpolish(w)
    style.polish(w)
    w.updateGeometry()
    w.update()


def _refresh_tab_widget(tabw, direction):
    """
    Make a QTabWidget re-lay out its tab strip for a new layout direction.

    QTabBar caches its tab rectangles and the positions of the per-tab
    close buttons, and QTabWidget caches where the bar sits inside it.
    Neither is invalidated by a plain layout-direction change: the layout
    only gets recomputed on the next resize / style change / tab insertion,
    which is why the strip used to "catch up" only after switching to
    another application and back, or after opening a new document.
    Here everything is invalidated explicitly and immediately.
    """
    bar = tabw.tabBar()
    tabw.setLayoutDirection(direction)
    bar.setLayoutDirection(direction)

    # Destroys and recreates every close button, so each one is placed by
    # the bar's own layout code using the direction now in effect.
    if bar.tabsClosable():
        bar.setTabsClosable(False)
        bar.setTabsClosable(True)

    # Re-polish so the style re-reads its direction-dependent hints
    # (e.g. which side of the tab the close button goes on).
    for w in (tabw, bar):
        style = w.style()
        style.unpolish(w)
        style.polish(w)

    # QTabWidget::resizeEvent -> setUpLayout() repositions the bar;
    # QTabBar::resizeEvent -> relayouts the tabs and their buttons.
    for w in (tabw, bar):
        QApplication.sendEvent(w, QResizeEvent(w.size(), w.size()))
        w.updateGeometry()
        w.update()


def apply_translations(root=None):
    """Translate an existing widget tree, preserving original English text."""
    if root is None:
        return
    direction = Qt.RightToLeft if tr.is_rtl() else Qt.LeftToRight
    widgets = [root] + root.findChildren(QWidget)
    for w in widgets:
        if isinstance(w, QAction):
            _translate_action(w)
        if hasattr(w, "windowTitle"):
            _translate_text_property(
                w, "_translation_title", w.windowTitle(), w.setWindowTitle
            )
        if hasattr(w, "toolTip"):
            has_tip = bool(w.toolTip()) or w.property("_translation_tooltip") is not None
            if has_tip:
                _translate_text_property(
                    w, "_translation_tooltip", w.toolTip(), w.setToolTip
                )
        if isinstance(w, (QAbstractButton, QLabel)):
            _translate_text_property(w, "_translation_text", w.text(), w.setText)
        if isinstance(w, QLineEdit):
            has_placeholder = (
                bool(w.placeholderText()) or w.property("_translation_placeholder") is not None
            )
            if has_placeholder:
                _translate_text_property(
                    w, "_translation_placeholder", w.placeholderText(), w.setPlaceholderText
                )
        if isinstance(w, QComboBox):
            for i in range(w.count()):
                current = w.itemText(i)
                cached = w.itemData(i, Qt.UserRole + 1)
                source = _resolved_source(cached, current)
                new_text = _translated(source)
                w.setItemText(i, new_text)
                w.setItemData(i, (source, new_text), Qt.UserRole + 1)
        if isinstance(w, QTabWidget):
            bar = w.tabBar()
            for i in range(w.count()):
                current = w.tabText(i)
                cached = bar.tabData(i)
                source = _resolved_source(cached, current)
                new_text = _translated(source)
                w.setTabText(i, new_text)
                bar.setTabData(i, (source, new_text))
            # Only when the direction actually changed since the last time
            # this tab widget was laid out (this function also runs on
            # every Show/WindowActivate event).
            if w.property("_tab_direction") != int(direction):
                w.setProperty("_tab_direction", int(direction))
                _refresh_tab_widget(w, direction)
                # Once more after the event loop has processed the
                # direction change, in case Qt defers part of it.
                QTimer.singleShot(0, lambda tw=w, d=direction: _refresh_tab_widget(tw, d))
        # Docks, the menu bar, and toolbars each draw their own frame
        # chrome (title bars, drag handles) rather than relying purely
        # on child-widget layout, so they need to be told about the new
        # direction and repainted explicitly - see _repolish_chrome().
        if isinstance(w, (QDockWidget, QMenuBar, QToolBar)):
            w.setLayoutDirection(direction)
            _repolish_chrome(w)
    # Menus/actions are QObject children rather than QWidget children.
    for action in root.findChildren(QAction):
        _translate_action(action)
    # Show/activation events may be delivered for QWindow objects as well as
    # QWidget objects. QWindow has no setLayoutDirection(); the application
    # direction is set separately in localize_all_widgets().
    if isinstance(root, QWidget):
        root.setLayoutDirection(direction)
        _repolish_chrome(root)


class _TranslationEventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Show, QEvent.WindowActivate):
            try:
                apply_translations(obj)
            except RuntimeError:
                pass
        return False


_translation_filter = None

def install_translation_filter():
    global _translation_filter
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    if _translation_filter is None:
        _translation_filter = _TranslationEventFilter(app)
        app.installEventFilter(_translation_filter)


def localize_all_widgets():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    direction = Qt.RightToLeft if tr.is_rtl() else Qt.LeftToRight
    app.setLayoutDirection(direction)
    for w in app.topLevelWidgets():
        apply_translations(w)