from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.config import Settings

COL = {
    "bg": "#F7F2EC",
    "surface": "#FFF9F2",
    "surface2": "#FFFDF8",
    "menubar": "#EFE6DA",
    "border": "#E3D9CF",
    "border_soft": "#EDE4D8",
    "text": "#3A3A38",
    "text_primary": "#2F3135",
    "text_muted": "#707070",
    "muted": "#7A7A78",
    "accent": "#A1E3D8",
    "accent2": "#8FDCCF",
    "accent_border": "#6FB9AD",
    "accent_pressed": "#76CABC",
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
}


def apply_theme(app: QApplication, settings: Settings) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COL["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COL["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COL["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COL["surface2"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COL["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COL["text"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COL["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COL["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COL["text"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(COL["error"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(COL["link"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COL["accent2"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COL["text_primary"]))
    app.setPalette(palette)
    app.setStyleSheet(_build_qss(settings))


def _build_qss(settings: Settings) -> str:
    compact = settings.ui_density == "compact"
    font_size = 11 if compact else 12
    control_py = "5px 8px" if compact else "7px 10px"
    button_py = "5px 10px" if compact else "6px 10px"
    return f"""
    * {{
        color: {COL["text_primary"]};
        font-size: {font_size}px;
    }}
    QWidget {{
        background: {COL["bg"]};
    }}
    QWidget[uiDensity="compact"] * {{
        font-size: 12px;
    }}
    QGroupBox {{
        border: 1px solid {COL["border"]};
        border-radius: 10px;
        margin-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        font-weight: 700;
    }}
    QLabel#pageTitle {{
        font-size: 22px;
        font-weight: 800;
        color: {COL["text_primary"]};
    }}
    QLabel#sectionTitle {{
        font-size: 16px;
        font-weight: 700;
    }}
    QLabel#muted, QLabel#helperText {{
        color: {COL["text_muted"]};
    }}
    QLabel#adminStatus, QLabel#homeUserInfo {{
        color: {COL["text"]};
    }}
    QLabel#validationBanner {{
        background: #FDECEC;
        border: 1px solid #E9B7B7;
        border-radius: 6px;
        padding: 6px;
        color: #7A2424;
    }}
    QLabel#statusLabel {{
        color: {COL["muted"]};
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0;
    }}
    QLabel#statusLabel[statusLevel="info"] {{
        color: {COL["info"]};
        background: {COL["info_bg"]};
        border: 1px solid #C9C6C1;
        padding: 6px 10px;
    }}
    QLabel#statusLabel[statusLevel="success"] {{
        color: {COL["success"]};
        background: {COL["success_bg"]};
        border: 1px solid {COL["success"]};
        padding: 6px 10px;
    }}
    QLabel#statusLabel[statusLevel="warning"] {{
        color: {COL["warn"]};
        background: {COL["warn_bg"]};
        border: 1px solid {COL["warn"]};
        padding: 6px 10px;
    }}
    QLabel#statusLabel[statusLevel="error"] {{
        color: {COL["error"]};
        background: {COL["error_bg"]};
        border: 1px solid {COL["error"]};
        padding: 6px 10px;
    }}
    QLabel#chipLabel {{
        background: {COL["surface2"]};
        border: 1px solid {COL["border"]};
        border-radius: 10px;
        padding: 2px 8px;
        color: {COL["text"]};
        font-weight: 600;
    }}
    QWidget#listCard {{
        background: {COL["surface"]};
        border: 1px solid {COL["border"]};
        border-radius: 8px;
    }}
    QLabel#cardStatusDot {{
        border-radius: 4px;
    }}
    QLabel#cardStatusDot[tone="danger"] {{
        background: {COL["error"]};
    }}
    QLabel#cardStatusDot[tone="ok"] {{
        background: {COL["success"]};
    }}
    QLabel#cardStatusDot[tone="warn"] {{
        background: {COL["warn"]};
    }}
    QLabel#cardStatusDot[tone="unknown"] {{
        background: {COL["muted"]};
    }}
    QLabel#cardTitle {{
        font-weight: 600;
    }}
    QLabel#cardMeta {{
        color: {COL["muted"]};
    }}
    QLabel#cardMeta[tone="danger"] {{
        color: {COL["error"]};
    }}
    QLabel#statBadge {{
        border-radius: 8px;
        padding: 4px 6px;
        font-weight: 700;
        color: {COL["text_primary"]};
    }}
    QLabel#statBadge[toneKey="patients"] {{
        background: {COL["accent2"]};
    }}
    QLabel#statBadge[toneKey="emr_cases"] {{
        background: {COL["warn"]};
    }}
    QLabel#statBadge[toneKey="lab_samples"] {{
        background: {COL["success"]};
    }}
    QLabel#statBadge[toneKey="sanitary_samples"] {{
        background: {COL["accent"]};
    }}
    QLabel#statBadge[toneKey="new_patients"] {{
        background: {COL["warn"]};
    }}
    QLabel#statBadge[toneKey="top_department"] {{
        background: {COL["accent"]};
    }}
    QLabel#statBadge[toneKey="default"] {{
        background: {COL["border"]};
    }}
    QWidget#statCard {{
        background: rgba(255, 249, 242, 0.78);
        border: 1px solid {COL["border"]};
        border-radius: 12px;
        min-height: 78px;
    }}
    QLabel#metricValue {{
        font-size: 18px;
        font-weight: 800;
        color: {COL["text_primary"]};
    }}
    QPushButton#chipClear {{
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        padding: 0;
        border-radius: 11px;
        font-weight: 700;
    }}
    QToolButton#contextToggle {{
        border: 1px solid {COL["border"]};
        border-radius: 6px;
        padding: 2px;
        background: transparent;
    }}
    QToolButton#contextToggle:hover {{
        background: {COL["menubar"]};
    }}
    QWidget#contextBar {{
        background: rgba(239, 230, 218, 0.88);
        border: 1px solid {COL["border"]};
        border-radius: 12px;
    }}
    QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
        background: {COL["surface"]};
        border: 1px solid {COL["border"]};
        border-radius: 10px;
        padding: {control_py};
        color: {COL["text"]};
        selection-background-color: {COL["accent2"]};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {COL["accent_border"]};
        background: {COL["surface2"]};
    }}
    QPushButton {{
        background: {COL["accent2"]};
        border: 1px solid {COL["accent_border"]};
        border-radius: 10px;
        padding: {button_py};
        color: {COL["text_primary"]};
        font-weight: 700;
        min-height: 28px;
    }}
    QPushButton:hover {{
        background: {COL["accent"]};
    }}
    QPushButton:pressed {{
        background: {COL["accent_pressed"]};
    }}
    QPushButton:disabled {{
        background: {COL["surface"]};
        border-color: {COL["border"]};
        color: {COL["muted"]};
    }}
    QPushButton#secondaryButton {{
        background: {COL["surface"]};
        border-color: {COL["border"]};
        color: {COL["muted"]};
    }}
    QPushButton#logoutButton {{
        background: transparent;
        border: 1px solid {COL["border"]};
        border-radius: 8px;
        padding: 4px 12px;
        color: {COL["text"]};
    }}
    QPushButton#logoutButton:hover {{
        background: {COL["error"]};
        border-color: {COL["error"]};
        color: {COL["surface2"]};
    }}
    QTableWidget, QTableView {{
        background: {COL["surface2"]};
        border: 1px solid {COL["border"]};
        border-radius: 12px;
        gridline-color: {COL["border_soft"]};
        alternate-background-color: rgba(255, 249, 242, 0.88);
        font-size: 10px;
    }}
    QHeaderView::section {{
        background: {COL["menubar"]};
        border: none;
        border-right: 1px solid {COL["border_soft"]};
        border-bottom: 1px solid {COL["border_soft"]};
        padding: 5px 6px;
        font-size: 10px;
        font-weight: 700;
    }}
    QWidget#contextActions QPushButton {{
        min-height: 26px;
        padding: 4px 8px;
    }}
    QMenuBar {{
        background: {COL["menubar"]};
        border-bottom: 1px solid {COL["border"]};
        spacing: 4px;
        padding: 4px 6px;
    }}
    QMenuBar::item {{
        padding: 7px 10px;
        border-radius: 10px;
        background: transparent;
    }}
    QMenuBar[compactNav="true"] {{
        spacing: 2px;
        padding: 3px 5px;
    }}
    QMenuBar[compactNav="true"]::item {{
        padding: 5px 7px;
        border-radius: 8px;
    }}
    QMenuBar[compactNav="true"][miniNav="true"]::item {{
        padding: 4px 5px;
        border-radius: 7px;
    }}
    QMenuBar::item:selected {{
        background: {COL["surface2"]};
    }}
    QMenu {{
        background: {COL["surface2"]};
        border: 1px solid {COL["border"]};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 8px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background: {COL["surface"]};
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        border-radius: 5px;
        background: rgba(143, 220, 207, 0.75);
        min-height: 24px;
    }}
    QToolTip {{
        background-color: {COL["surface"]};
        color: {COL["text"]};
        border: 1px solid {COL["border"]};
    }}
    QWidget#toast {{
        border-radius: 12px;
    }}
    QWidget#toast[toastLevel="success"] {{
        background: {COL["success_bg"]};
        border: 1px solid {COL["success"]};
    }}
    QWidget#toast[toastLevel="warning"] {{
        background: {COL["warn_bg"]};
        border: 1px solid {COL["warn"]};
    }}
    QWidget#toast[toastLevel="error"] {{
        background: {COL["error_bg"]};
        border: 1px solid {COL["error"]};
    }}
    QWidget#toast[toastLevel="info"] {{
        background: {COL["info_bg"]};
        border: 1px solid #C9C6C1;
    }}
    QWidget#toast QLabel {{
        background: transparent;
        color: {COL["text"]};
    }}
    QDialog#loginDialog QLabel {{
        background: transparent;
    }}
    QDialog#loginDialog QLabel#loginAppTitle {{
        color: {COL["text"]};
        font-size: 34px;
        font-weight: 800;
        letter-spacing: 0.4px;
    }}
    QDialog#loginDialog QFrame#loginTimePanel {{
        background: rgba(255, 249, 242, 0.42);
        border: 1px solid rgba(225, 217, 207, 0.6);
        border-radius: 14px;
        min-width: 420px;
    }}
    QDialog#loginDialog QLabel#loginTimeCaption {{
        color: {COL["muted"]};
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}
    QDialog#loginDialog QLabel#loginTimeValue {{
        color: {COL["text"]};
        font-size: 24px;
        font-weight: 700;
    }}
    QDialog#loginDialog QLabel#loginMedicalLine {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(161, 227, 216, 0.2), stop:0.5 rgba(161, 227, 216, 0.6),
            stop:1 rgba(161, 227, 216, 0.2));
        border-radius: 2px;
    }}
    QDialog#loginDialog QFrame#loginCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 249, 242, 0.7), stop:1 rgba(239, 230, 218, 0.6));
        border: 1px solid rgba(255, 255, 255, 0.65);
        outline: 1px solid rgba(225, 217, 207, 0.8);
        border-radius: 14px;
    }}
    QDialog#loginDialog QLabel#loginCardTitle {{
        color: {COL["text"]};
        font-size: 14px;
        font-weight: 700;
    }}
    QDialog#loginDialog QLabel#loginCardHint {{
        color: {COL["muted"]};
        font-size: 11px;
    }}
    QDialog#loginDialog QLineEdit {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QDialog#loginDialog QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
    }}
    QDialog#firstRunDialog QLabel#firstRunTitle {{
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 0.3px;
        color: {COL["text"]};
    }}
    QDialog#firstRunDialog QLabel#firstRunSubtitle {{
        color: {COL["muted"]};
        font-size: 13px;
    }}
    QDialog#firstRunDialog QLabel#firstRunMedicalLine {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(161, 227, 216, 0.15), stop:0.5 rgba(161, 227, 216, 0.55),
            stop:1 rgba(161, 227, 216, 0.15));
        border-radius: 2px;
    }}
    QDialog#firstRunDialog QFrame#firstRunCard {{
        background: rgba(255, 249, 242, 0.95);
        border: 1px solid rgba(225, 217, 207, 0.7);
        border-radius: 14px;
    }}
    QDialog#firstRunDialog QLabel#firstRunInfoBadge {{
        color: {COL["text"]};
        background: rgba(255, 249, 242, 0.6);
        border: 1px solid rgba(225, 217, 207, 0.6);
        border-radius: 10px;
        padding: 8px 12px;
        font-weight: 600;
    }}
    QDialog#firstRunDialog QLabel#firstRunFormLabel {{
        color: {COL["text"]};
    }}
    """
