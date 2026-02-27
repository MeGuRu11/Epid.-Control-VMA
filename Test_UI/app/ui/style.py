from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Core palette from context.md with semantic aliases for styling.
COL = {
    "bg": "#F7F2EC",
    "surface": "#FFF9F2",
    "surface2": "#FFFDF8",
    "menubar": "#EFE6DA",
    "border": "#E3D9CF",
    "text": "#3A3A38",
    "muted": "#7A7A78",
    "accent": "#A1E3D8",
    "accent2": "#8FDCCF",
    "accent_border": "#6FB9AD",
    "link": "#61C9B6",
    "success_bg": "#E6F6EA",
    "success": "#9AD8A6",
    "warn_bg": "#FFF4DB",
    "warn": "#F4D58D",
    "error_bg": "#FDE7E5",
    "error": "#E18A85",
    "info_bg": "#F2F1EF",
    "info": "#7A7A78",
    "danger_pressed": "#D8746F",
    "border_soft": "#EDE4D8",
    "surface_elevated": "#FFFCF7",
    "surface_glass": "rgba(255, 253, 248, 0.92)",
    "text_primary": "#2F3135",
    "text_muted": "#707070",
    "accent_primary": "#8FDCCF",
    "accent_hover": "#A1E3D8",
    "accent_pressed": "#76CABC",
    "focus_ring": "rgba(143, 220, 207, 0.35)",
}


def apply_theme(app: QApplication) -> None:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(COL["bg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(COL["surface"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(COL["surface2"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(COL["text_primary"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(COL["text_primary"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(COL["surface"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(COL["text_primary"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(COL["accent2"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(COL["text_primary"]))
    app.setPalette(pal)

    app.setStyleSheet(
        f"""
        * {{
            color: {COL['text_primary']};
            font-size: 13px;
        }}
        QWidget {{
            background: {COL['bg']};
        }}
        QLabel {{
            background: transparent;
        }}
        QCheckBox {{
            background: transparent;
        }}
        QRadioButton {{
            background: transparent;
        }}
        QWidget#contentOverlay {{
            background: rgba(247, 242, 236, 0.74);
        }}
        QMainWindow {{
            background: {COL['bg']};
        }}
        QMenuBar {{
            background: {COL['menubar']};
            border-bottom: 1px solid {COL['border']};
            spacing: 4px;
            padding: 4px 6px;
        }}
        QMenuBar::item {{
            padding: 7px 10px;
            border-radius: 10px;
            background: transparent;
            color: {COL['text_primary']};
        }}
        QMenuBar::item:selected {{
            background: {COL['surface_elevated']};
        }}
        QMenuBar::item:pressed {{
            background: {COL['surface_elevated']};
            border: 1px solid {COL['border']};
        }}
        QMenu {{
            background: {COL['surface_elevated']};
            border: 1px solid {COL['border']};
            padding: 6px;
        }}
        QMenu::item {{
            padding: 7px 10px;
            border-radius: 8px;
        }}
        QMenu::item:selected {{
            background: {COL['surface2']};
        }}

        QLabel#title {{
            font-size: 28px;
            font-weight: 800;
            color: {COL['text_primary']};
        }}
        QLabel#subtitle {{
            font-size: 15px;
            font-weight: 600;
            color: {COL['text_primary']};
        }}
        QLabel#muted {{
            color: {COL['text_muted']};
        }}

        QFrame#card {{
            background: {COL['surface_elevated']};
            border: 1px solid {COL['border']};
            border-radius: 16px;
        }}
        QFrame#softCard {{
            background: {COL['surface']};
            border: 1px solid {COL['border_soft']};
            border-radius: 14px;
        }}
        QFrame#contextBar {{
            background: rgba(239, 230, 218, 0.94);
            border: 1px solid {COL['border']};
            border-radius: 14px;
        }}
        QWidget#contextActions {{
            background: transparent;
        }}
        QFrame#authCard {{
            background: {COL['surface_elevated']};
            border: 1px solid {COL['border']};
            border-radius: 20px;
        }}
        QFrame#sidebar {{
            background: {COL['surface_glass']};
            border: 1px solid {COL['border']};
            border-radius: 16px;
        }}
        QFrame#form100Isolation {{
            background: rgba(244, 213, 141, 0.25);
            border: 1px solid {COL['border']};
            border-radius: 10px;
        }}
        QFrame#form100Isolation[active="true"] {{
            background: rgba(244, 213, 141, 0.78);
            border: 1px solid #D8AE52;
        }}

        QGroupBox#form100Lesion,
        QGroupBox#form100Tissue,
        QGroupBox#form100Help,
        QGroupBox#form100Bottom,
        QGroupBox#form100StubSection {{
            border: 1px solid {COL['border']};
            border-radius: 12px;
            margin-top: 8px;
            padding-top: 8px;
            background: {COL['surface_elevated']};
            font-weight: 700;
        }}
        QGroupBox#form100Lesion::title,
        QGroupBox#form100Tissue::title,
        QGroupBox#form100Help::title,
        QGroupBox#form100Bottom::title,
        QGroupBox#form100StubSection::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: {COL['text_primary']};
        }}

        QPushButton {{
            background: {COL['accent_primary']};
            border: 1px solid {COL['accent_border']};
            padding: 8px 12px;
            border-radius: 10px;
            color: {COL['text_primary']};
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: {COL['accent_hover']};
        }}
        QPushButton:pressed {{
            background: {COL['accent_pressed']};
        }}
        QPushButton:disabled {{
            background: {COL['surface']};
            border-color: {COL['border']};
            color: {COL['muted']};
        }}
        QPushButton#secondary {{
            background: {COL['surface2']};
            border: 1px solid {COL['accent_border']};
            color: {COL['text_primary']};
        }}
        QPushButton#secondary:hover {{
            background: {COL['surface']};
        }}
        QPushButton#ghost {{
            background: transparent;
            border: 1px solid {COL['border']};
        }}
        QPushButton#ghost:hover {{
            background: rgba(239, 230, 218, 0.65);
        }}
        QPushButton#danger {{
            background: {COL['error']};
            border-color: {COL['error']};
            color: #FFFFFF;
        }}
        QPushButton#danger:hover {{
            background: #DA807A;
        }}
        QPushButton#danger:pressed {{
            background: {COL['danger_pressed']};
            border-color: {COL['danger_pressed']};
        }}
        QPushButton#navButton {{
            text-align: left;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid transparent;
            background: transparent;
            font-weight: 600;
        }}
        QPushButton#navButton:hover {{
            background: rgba(239, 230, 218, 0.72);
            border-color: {COL['border']};
        }}
        QPushButton#navButton[active="true"] {{
            background: rgba(143, 220, 207, 0.25);
            border: 1px solid {COL['accent_border']};
            color: #22383A;
        }}
        QPushButton#lesionToggle {{
            background: {COL['surface']};
            border: 1px solid {COL['border']};
            border-radius: 10px;
            text-align: left;
            padding: 7px 10px;
            font-weight: 600;
        }}
        QPushButton#lesionToggle:hover {{
            background: {COL['surface2']};
            border-color: {COL['accent_border']};
        }}
        QPushButton#lesionToggle[active="true"] {{
            background: rgba(143, 220, 207, 0.23);
            border: 1px solid {COL['accent_border']};
            color: #22383A;
        }}
        QPushButton#iconSelectToggle {{
            background: {COL['surface']};
            border: 1px solid {COL['border']};
            border-radius: 10px;
            padding: 6px 10px;
            font-weight: 600;
        }}
        QPushButton#iconSelectToggle:hover {{
            background: {COL['surface2']};
            border-color: {COL['accent_border']};
        }}
        QPushButton#iconSelectToggle[active="true"] {{
            background: rgba(143, 220, 207, 0.23);
            border: 1px solid {COL['accent_border']};
            color: #22383A;
        }}

        QLineEdit, QDateEdit, QSpinBox, QComboBox, QTextEdit {{
            background: {COL['surface']};
            border: 1px solid {COL['border']};
            border-radius: 10px;
            padding: 7px 10px;
            color: {COL['text_primary']};
            selection-background-color: {COL['accent2']};
            selection-color: {COL['text_primary']};
        }}
        QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
            border: 1px solid {COL['accent_border']};
            background: {COL['surface2']};
        }}
        QLineEdit:disabled, QDateEdit:disabled, QSpinBox:disabled, QComboBox:disabled, QTextEdit:disabled {{
            background: {COL['surface2']};
            color: {COL['muted']};
        }}
        QLineEdit#form100Field, QTextEdit#form100FieldMultiline {{
            background: rgba(255, 252, 247, 0.50);
            border: 1px solid rgba(145, 132, 120, 0.35);
            border-radius: 3px;
            padding: 0px 2px;
            color: #1F2023;
        }}
        QLineEdit#form100Field:focus, QTextEdit#form100FieldMultiline:focus {{
            border: 1px solid rgba(111, 185, 173, 0.90);
            background: rgba(255, 252, 247, 0.82);
        }}
        QLineEdit#form100Field[readOnly="true"], QTextEdit#form100FieldMultiline[readOnly="true"] {{
            background: rgba(255, 252, 247, 0.25);
            border: 1px solid rgba(145, 132, 120, 0.25);
        }}

        QAbstractItemView {{
            selection-background-color: rgba(143, 220, 207, 0.32);
            selection-color: {COL['text_primary']};
            alternate-background-color: rgba(255, 249, 242, 0.88);
        }}
        QTableView, QTableWidget {{
            background: {COL['surface_elevated']};
            border: 1px solid {COL['border']};
            border-radius: 12px;
            gridline-color: {COL['border_soft']};
        }}
        QHeaderView::section {{
            background: {COL['menubar']};
            border: none;
            border-right: 1px solid {COL['border_soft']};
            border-bottom: 1px solid {COL['border_soft']};
            padding: 7px 8px;
            font-weight: 700;
        }}

        QCheckBox#form100FlagEmergency,
        QCheckBox#form100FlagRadiation,
        QCheckBox#form100FlagSanitation {{
            padding: 8px 12px;
            border-radius: 10px;
            border: 1px solid {COL['border']};
            font-weight: 700;
            background: {COL['surface']};
        }}
        QCheckBox#form100FlagEmergency::indicator,
        QCheckBox#form100FlagRadiation::indicator,
        QCheckBox#form100FlagSanitation::indicator {{
            width: 0px;
            height: 0px;
        }}
        QCheckBox#form100FlagEmergency:unchecked {{
            background: rgba(192, 57, 43, 0.22);
            border-color: rgba(192, 57, 43, 0.45);
        }}
        QCheckBox#form100FlagEmergency:checked {{
            background: rgba(192, 57, 43, 0.94);
            border-color: rgba(192, 57, 43, 1.0);
            color: #FFFFFF;
        }}
        QCheckBox#form100FlagRadiation:unchecked {{
            background: rgba(31, 119, 180, 0.22);
            border-color: rgba(31, 119, 180, 0.45);
        }}
        QCheckBox#form100FlagRadiation:checked {{
            background: rgba(31, 119, 180, 0.94);
            border-color: rgba(31, 119, 180, 1.0);
            color: #FFFFFF;
        }}
        QCheckBox#form100FlagSanitation:unchecked {{
            background: rgba(244, 213, 141, 0.36);
            border-color: rgba(190, 148, 63, 0.55);
        }}
        QCheckBox#form100FlagSanitation:checked {{
            background: rgba(244, 213, 141, 0.96);
            border-color: rgba(190, 148, 63, 0.88);
            color: {COL['text_primary']};
        }}

        QScrollBar:vertical, QScrollBar:horizontal {{
            background: transparent;
            border: none;
            margin: 0px;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {COL['border']};
            border-radius: 6px;
            min-height: 24px;
            min-width: 24px;
        }}
        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            border: none;
            background: transparent;
        }}
        """
    )
