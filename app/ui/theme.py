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
        outline: none;
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
        padding: 0 6px;
        background: {COL["bg"]};
        font-weight: 700;
    }}
    QLabel {{
        border: none;
        background: transparent;
    }}
    QCheckBox {{
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {COL["muted"]};
        border-radius: 4px;
        background: {COL["surface"]};
    }}
    QCheckBox::indicator:hover {{
        border-color: {COL["link"]};
        background: {COL["surface2"]};
    }}
    QCheckBox::indicator:checked {{
        border-color: {COL["link"]};
        background: {COL["surface"]};
        image: url("data:image/svg+xml;utf8,<svg width='14' height='14' viewBox='0 0 14 14' xmlns='http://www.w3.org/2000/svg'><path d='M5 10.5L2 7.5L3.4 6.1L5 7.7L10.6 2.1L12 3.5L5 10.5Z' fill='{COL["link"].replace("#", "%23")}'/></svg>");
    }}
    QCheckBox::indicator:disabled {{
        border-color: {COL["border"]};
        background: {COL["bg"]};
        image: none;
    }}
    QRadioButton {{
        spacing: 8px;
        background: transparent;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {COL["muted"]};
        border-radius: 10px;
        background: {COL["surface"]};
    }}
    QRadioButton::indicator:hover {{
        border-color: {COL["link"]};
        background: {COL["surface2"]};
    }}
    QRadioButton::indicator:checked {{
        border-color: {COL["link"]};
        background: {COL["surface"]};
        image: url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8Y2lyY2xlIGN4PSI1IiBjeT0iNSIgcj0iNCIgZmlsbD0iIzYxQzlCNiIvPgo8L3N2Zz4=");
    }}
    QRadioButton::indicator:disabled {{
        border-color: {COL["border"]};
        background: {COL["bg"]};
        image: none;
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
        border: none;
        border-radius: 6px;
        padding: 6px;
        color: #7A2424;
    }}
    QLabel#statusLabel {{
        color: {COL["text"]};
        background: transparent;
        border: none;
        border-radius: 10px;
        padding: 0;
        font-weight: 700;
    }}
    QLabel#statusLabel[statusLevel="info"] {{
        color: #2F4F58;
        background: #E8F4F2;
        border: 1px solid #9FCFC6;
        padding: 6px 12px;
    }}
    QLabel#statusLabel[statusLevel="success"] {{
        color: #2D5A40;
        background: #E8F7EE;
        border: 1px solid #9AD8A6;
        padding: 6px 12px;
    }}
    QLabel#statusLabel[statusLevel="warning"] {{
        color: #6E5525;
        background: #FFF4DB;
        border: 1px solid #E7C980;
        padding: 6px 12px;
    }}
    QLabel#statusLabel[statusLevel="error"] {{
        color: #7F2F2A;
        background: #FDE7E5;
        border: 1px solid #E3A39D;
        padding: 6px 12px;
    }}
    QLabel#chipLabel {{
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 1px 2px;
        color: {COL["text"]};
        font-weight: 600;
    }}
    QGroupBox#patientCard {{
        background: rgba(255, 249, 242, 0.72);
        border: 1px solid {COL["border"]};
        border-radius: 12px;
    }}
    QLabel#patientName {{
        color: {COL["text_primary"]};
        font-size: 18px;
        font-weight: 800;
        letter-spacing: 0.2px;
    }}
    QLabel#patientSubtitle {{
        color: {COL["text_muted"]};
        font-size: 11px;
        font-weight: 600;
    }}
    QWidget#patientIdCard {{
        background: rgba(161, 227, 216, 0.2);
        border: 1px solid {COL["border_soft"]};
        border-radius: 10px;
    }}
    QLabel#patientIdCaption {{
        color: {COL["text_muted"]};
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#patientIdBadge {{
        color: {COL["text_primary"]};
        font-size: 18px;
        font-weight: 800;
    }}
    QWidget#patientSeparator {{
        background: {COL["border_soft"]};
        border: none;
    }}
    QWidget#patientFieldCard {{
        background: rgba(255, 249, 242, 0.88);
        border: 1px solid {COL["border_soft"]};
        border-radius: 10px;
    }}
    QLabel#patientFieldTitle {{
        color: {COL["text_muted"]};
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#patientFieldValue {{
        color: {COL["text"]};
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#patientLabel {{
        color: {COL["text_muted"]};
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#patientValue {{
        color: {COL["text"]};
        font-size: 13px;
        font-weight: 700;
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
    QFrame#form100ListPreview {{
        background: #F7F4F0;
        border-left: 1px solid #E0DAD3;
        border-radius: 0;
    }}
    QLabel#form100ListBadge {{
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
        background: transparent;
        color: {COL["text_muted"]};
    }}
    QLabel#form100ListBadge[tone="draft"] {{
        background: #F4D58D;
        color: #7D5A00;
    }}
    QLabel#form100ListBadge[tone="signed"] {{
        background: #9AD8A6;
        color: #1D5030;
    }}
    QLabel#form100ListBadge[tone="archived"] {{
        background: #E3D9CF;
        color: #5A5A58;
    }}
    QLabel#form100ListName {{
        background: transparent;
        color: #1A252F;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#form100ListUnit {{
        background: transparent;
        color: #4A7A9B;
        font-size: 12px;
    }}
    QFrame#form100ListSeparator {{
        background: #D4CEC8;
        border: none;
    }}
    QLabel#form100ListDiagnosis {{
        background: transparent;
        color: {COL["text"]};
        font-size: 12px;
    }}
    QLabel#form100ListDate {{
        background: transparent;
        color: #8899AA;
        font-size: 11px;
    }}
    QGroupBox#form100Tissue QCheckBox#form100TissueCheck {{
        font-size: 12px;
        padding: 2px 0;
        spacing: 6px;
        color: {COL["text"]};
    }}
    QGroupBox#form100Tissue QCheckBox#form100TissueCheck::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {COL["accent_border"]};
        border-radius: 3px;
        background: {COL["surface"]};
    }}
    QGroupBox#form100Tissue QCheckBox#form100TissueCheck::indicator:hover {{
        background: #F2FBF9;
        border: 1px solid #58A99A;
    }}
    QGroupBox#form100Tissue QCheckBox#form100TissueCheck::indicator:checked {{
        border: 1px solid #4EAF9F;
        border-radius: 3px;
        background: #8FDCCF;
    }}
    QPushButton#iconSelectToggle {{
        background: #8FDCCF;
        border: 1px solid #6FB9AD;
        border-radius: 10px;
        color: {COL["text_primary"]};
        font-weight: 700;
        padding: 6px 12px;
        min-height: 34px;
    }}
    QPushButton#iconSelectToggle:hover {{
        background: #A7E8DD;
    }}
    QPushButton#iconSelectToggle:checked,
    QPushButton#iconSelectToggle[active="true"] {{
        background: #4EAF9F;
        border: 1px solid #2F7F73;
        color: #FFFFFF;
        font-weight: 800;
    }}
    QPushButton#iconSelectToggle:checked:hover,
    QPushButton#iconSelectToggle[active="true"]:hover {{
        background: #429A8C;
    }}
    QPushButton#lesionToggle {{
        background: #8FDCCF;
        border: 1px solid #6FB9AD;
        border-radius: 10px;
        color: {COL["text_primary"]};
        font-weight: 700;
        padding: 6px 10px;
    }}
    QPushButton#lesionToggle:hover {{
        background: #A7E8DD;
    }}
    QPushButton#lesionToggle:checked,
    QPushButton#lesionToggle[active="true"] {{
        background: #4EAF9F;
        border: 1px solid #2F7F73;
        color: #FFFFFF;
        font-weight: 800;
    }}
    QPushButton#lesionToggle:checked:hover,
    QPushButton#lesionToggle[active="true"]:hover {{
        background: #429A8C;
    }}
    QLabel#form100NotesHint {{
        color: #95A5A6;
        font-size: 11px;
        font-style: italic;
        padding: 2px 0;
    }}
    QWidget#form100NotesContainer {{
        background: transparent;
        border: none;
    }}
    QFrame#form100NoteRow {{
        background-color: #EBF5FB;
        border: 1px solid #AED6F1;
        border-radius: 4px;
    }}
    QLabel#form100NoteIndex {{
        color: #2E86C1;
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#form100NoteText {{
        color: #1A252F;
        font-size: 11px;
    }}
    QLabel#form100BottomRowLabel {{
        color: {COL["text_muted"]};
        font-size: 12px;
    }}
    QLabel#form100BottomSectionLabel {{
        color: {COL["accent_border"]};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.8px;
    }}
    QWidget#form100BottomInlineContainer {{
        background: transparent;
        border: none;
    }}
    QFrame#form100BottomSeparator {{
        background: #E0E6EA;
        border: none;
    }}
    QScrollArea#form100ReviewPanel {{
        background: {COL["surface2"]};
        border: none;
    }}
    QWidget#form100ReviewPanelInner {{
        background: transparent;
        border: none;
    }}
    QFrame#form100ReviewNameCard {{
        background: {COL["surface"]};
        border: 1px solid rgba(111, 185, 173, 0.28);
        border-radius: 8px;
        border-left: 5px solid {COL["accent_border"]};
    }}
    QLabel#form100ReviewName {{
        color: {COL["text_primary"]};
        font-size: 16px;
        font-weight: 800;
    }}
    QLabel#form100ReviewSub {{
        color: {COL["text_muted"]};
        font-size: 12px;
    }}
    QFrame#form100ReviewCard {{
        background: {COL["surface"]};
        border-radius: 4px;
        border-left: 4px solid {COL["accent_border"]};
    }}
    QFrame#form100ReviewCard[tone="id"] {{
        border-left: 4px solid {COL["accent_border"]};
    }}
    QFrame#form100ReviewCard[tone="injury"] {{
        border-left: 4px solid {COL["error"]};
    }}
    QFrame#form100ReviewCard[tone="lesion"] {{
        border-left: 4px solid {COL["warn"]};
    }}
    QFrame#form100ReviewCard[tone="med"] {{
        border-left: 4px solid {COL["success"]};
    }}
    QFrame#form100ReviewCard[tone="map"] {{
        border-left: 4px solid #8E6BAF;
    }}
    QFrame#form100ReviewCard[tone="evac"] {{
        border-left: 4px solid {COL["accent2"]};
    }}
    QFrame#form100ReviewCard[tone="flags"] {{
        border-left: 4px solid {COL["error"]};
    }}
    QFrame#form100ReviewCard[tone="diag"] {{
        border-left: 4px solid {COL["text_muted"]};
    }}
    QLabel#form100ReviewHeader {{
        background: transparent;
        color: {COL["accent_border"]};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.6px;
    }}
    QLabel#form100ReviewHeader[tone="injury"] {{
        color: {COL["error"]};
    }}
    QLabel#form100ReviewHeader[tone="lesion"] {{
        color: {COL["warn"]};
    }}
    QLabel#form100ReviewHeader[tone="med"] {{
        color: {COL["success"]};
    }}
    QLabel#form100ReviewHeader[tone="map"] {{
        color: #8E6BAF;
    }}
    QLabel#form100ReviewHeader[tone="evac"] {{
        color: {COL["accent_border"]};
    }}
    QLabel#form100ReviewHeader[tone="flags"] {{
        color: {COL["error"]};
    }}
    QLabel#form100ReviewHeader[tone="diag"] {{
        color: {COL["text_muted"]};
    }}
    QFrame#form100ReviewSeparator {{
        border: none;
        background: rgba(111, 185, 173, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="injury"] {{
        background: rgba(225, 138, 133, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="lesion"] {{
        background: rgba(244, 213, 141, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="med"] {{
        background: rgba(154, 216, 166, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="map"] {{
        background: rgba(142, 107, 175, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="evac"] {{
        background: rgba(111, 185, 173, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="flags"] {{
        background: rgba(225, 138, 133, 0.18);
    }}
    QFrame#form100ReviewSeparator[tone="diag"] {{
        background: rgba(122, 122, 120, 0.13);
    }}
    QWidget#form100ReviewRow {{
        background: transparent;
        border: none;
    }}
    QLabel#form100ReviewRow {{
        background: transparent;
        font-size: 12px;
    }}
    QLabel#form100ReviewRowLabel {{
        background: transparent;
        color: {COL["text_muted"]};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#form100ReviewRowValue {{
        background: transparent;
        color: {COL["text_primary"]};
        font-size: 12px;
    }}
    QLabel#form100ReviewBadge {{
        border-radius: 3px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        background: rgba(111, 185, 173, 0.15);
        color: {COL["accent_border"]};
        border: none;
    }}
    QLabel#form100ReviewBadge[tone="injury"] {{
        background: rgba(225, 138, 133, 0.15);
        color: {COL["error"]};
    }}
    QLabel#form100ReviewBadge[tone="lesion"] {{
        background: rgba(244, 213, 141, 0.15);
        color: #8B6914;
    }}
    QLabel#form100ReviewBadge[tone="med"] {{
        background: rgba(154, 216, 166, 0.15);
        color: #2D5A40;
    }}
    QLabel#form100ReviewBadge[tone="map"] {{
        background: rgba(142, 107, 175, 0.15);
        color: #6E4D8E;
    }}
    QLabel#form100ReviewBadge[tone="evac"] {{
        background: rgba(111, 185, 173, 0.15);
        color: {COL["accent_border"]};
    }}
    QLabel#form100ReviewBadge[tone="flags"] {{
        background: rgba(225, 138, 133, 0.15);
        color: {COL["error"]};
    }}
    QLabel#form100ReviewBadge[tone="diag"] {{
        background: rgba(122, 122, 120, 0.10);
        color: {COL["text_muted"]};
    }}
    QLabel#form100ReviewPlaceholder {{
        color: {COL["text_muted"]};
        font-size: 13px;
        font-style: italic;
    }}
    QFrame#wizardStepPanel {{
        background-color: #EDE8E1;
        border-right: 1px solid #D4CEC8;
    }}
    QLabel#wizardStepTitle {{
        background: transparent;
        color: #3A3A38;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QFrame#wizardStepSeparator {{
        background-color: #C8C2BC;
        border: none;
    }}
    QWidget#wizardStepRow {{
        background: transparent;
        border: none;
    }}
    QWidget#wizardStepConnectorWrap {{
        background: transparent;
        border: none;
    }}
    QFrame#wizardStepConnectorLine {{
        background-color: #C8C2BC;
        border: none;
    }}
    QLabel#wizardStepBadge {{
        border-radius: 15px;
        font-weight: 700;
        font-size: 11px;
        background-color: #D4CEC8;
        color: #7A7A78;
    }}
    QLabel#wizardStepBadge[stepState="done"] {{
        font-size: 12px;
        background-color: #27AE60;
        color: #FFFFFF;
    }}
    QLabel#wizardStepBadge[stepState="active"] {{
        font-size: 12px;
        background-color: #8FDCCF;
        color: #3A3A38;
    }}
    QLabel#wizardStepBadge[stepState="pending"] {{
        font-size: 11px;
        background-color: #D4CEC8;
        color: #7A7A78;
    }}
    QLabel#wizardStepName {{
        background: transparent;
        color: #7A7A78;
        font-size: 12px;
    }}
    QLabel#wizardStepName[stepState="done"] {{
        color: #27AE60;
        font-size: 12px;
    }}
    QLabel#wizardStepName[stepState="active"] {{
        color: #3A3A38;
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#wizardStepName[stepState="pending"] {{
        color: #7A7A78;
        font-size: 12px;
        font-weight: 400;
    }}
    QLabel#wizardStepLock {{
        background: transparent;
        color: #C0392B;
        font-size: 11px;
        padding: 6px 0 0 0;
    }}
    QFrame#wizardNavBar {{
        background-color: #FFF9F2;
        border-top: 1px solid #E0DAD3;
    }}
    QLabel#statBadge {{
        border-radius: 6px;
        padding: 2px 6px;
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
        border-radius: 10px;
        min-height: 58px;
    }}
    QLabel#metricValue {{
        font-size: 16px;
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
        border: none;
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
    QWidget#sectionActionBar {{
        background: rgba(255, 249, 242, 0.72);
        border: 1px solid {COL["border_soft"]};
        border-radius: 10px;
    }}
    QWidget#sectionActionGroup {{
        background: transparent;
        border: none;
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
        border: none;
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
        color: {COL["muted"]};
    }}
    QPushButton#secondaryButton {{
        background: {COL["surface"]};
        color: {COL["muted"]};
    }}
    QWidget#sectionActionBar QPushButton#primaryButton {{
        background: {COL["accent"]};
        font-weight: 800;
        padding: 6px 14px;
    }}
    QWidget#sectionActionBar QPushButton#primaryButton:hover {{
        background: {COL["accent_pressed"]};
    }}
    QWidget#sectionActionBar QPushButton#primaryButton:disabled {{
        background: {COL["surface"]};
        color: {COL["muted"]};
    }}
    QPushButton#logoutButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 4px 12px;
        color: {COL["text"]};
    }}
    QPushButton#logoutButton:hover {{
        background: {COL["error"]};
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
        font-size: 38px;
        font-weight: 900;
        letter-spacing: 0.5px;
    }}
    QDialog#loginDialog QFrame#loginTimePanel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 252, 248, 0.78), stop:1 rgba(245, 237, 228, 0.65));
        border: 1px solid rgba(198, 184, 168, 0.5);
        border-radius: 16px;
        min-width: 440px;
    }}
    QDialog#loginDialog QLabel#loginTimeCaption {{
        color: #6B6B66;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.4px;
    }}
    QDialog#loginDialog QLabel#loginTimeValue {{
        color: {COL["text_primary"]};
        font-size: 36px;
        font-weight: 800;
    }}
    QDialog#loginDialog QLabel#loginMedicalLine {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(161, 227, 216, 0.2), stop:0.5 rgba(161, 227, 216, 0.6),
            stop:1 rgba(161, 227, 216, 0.2));
        border-radius: 2px;
    }}
    QDialog#loginDialog QFrame#loginCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 250, 244, 0.92), stop:1 rgba(243, 235, 225, 0.78));
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: 16px;
    }}
    QDialog#loginDialog QLabel#loginCardAccent {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(111, 185, 173, 0.35), stop:0.5 rgba(111, 185, 173, 0.95),
            stop:1 rgba(111, 185, 173, 0.35));
        border: none;
        border-radius: 2px;
    }}
    QDialog#loginDialog QLabel#loginCardTitle {{
        color: {COL["text_primary"]};
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 0.2px;
    }}
    QDialog#loginDialog QLabel#loginCardHint {{
        color: {COL["muted"]};
        font-size: 12px;
        font-weight: 600;
        padding: 2px 0 6px 0;
    }}
    QDialog#loginDialog QLabel#loginFieldLabel {{
        color: #5A5955;
        font-size: 12px;
        font-weight: 700;
    }}
    QDialog#loginDialog QLineEdit#loginInput {{
        background: rgba(255, 253, 250, 0.95);
        border: 1px solid rgba(198, 184, 168, 0.65);
        border-radius: 10px;
        padding: 9px 12px;
        font-size: 13px;
    }}
    QDialog#loginDialog QLineEdit#loginInput:focus {{
        border: 1px solid rgba(111, 185, 173, 0.95);
        background: rgba(255, 255, 255, 0.98);
    }}
    QDialog#loginDialog QLabel#loginCardMeta {{
        color: #76726A;
        font-size: 11px;
        font-weight: 600;
        padding: 4px 0 2px 0;
    }}
    QDialog#loginDialog QPushButton#loginPrimaryButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {COL["accent"]}, stop:1 {COL["accent2"]});
        color: #183A35;
        border: 1px solid rgba(111, 185, 173, 0.8);
        border-radius: 11px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 800;
    }}
    QDialog#loginDialog QPushButton#loginPrimaryButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #B3ECE2, stop:1 #97DFD2);
    }}
    QDialog#loginDialog QPushButton#loginPrimaryButton:pressed {{
        background: #83D7C8;
    }}
    QDialog#loginDialog QPushButton#loginGhostButton {{
        background: rgba(255, 250, 244, 0.92);
        color: {COL["muted"]};
        border: 1px solid rgba(206, 196, 182, 0.8);
        border-radius: 11px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: 700;
    }}
    QDialog#loginDialog QPushButton#loginGhostButton:hover {{
        background: rgba(250, 241, 232, 0.95);
        color: {COL["text"]};
    }}
    QDialog#loginDialog QPushButton#loginGhostButton:pressed {{
        background: rgba(241, 231, 220, 0.95);
    }}
    QDialog#firstRunDialog QLabel#firstRunTitle {{
        color: {COL["text"]};
        font-size: 36px;
        font-weight: 900;
        letter-spacing: 0.45px;
    }}
    QDialog#firstRunDialog QLabel#firstRunSubtitle {{
        color: {COL["muted"]};
        font-size: 14px;
        font-weight: 600;
    }}
    QDialog#firstRunDialog QLabel#firstRunMedicalLine {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(161, 227, 216, 0.2), stop:0.5 rgba(161, 227, 216, 0.7),
            stop:1 rgba(161, 227, 216, 0.2));
        border-radius: 2px;
    }}
    QDialog#firstRunDialog QFrame#firstRunCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 250, 244, 0.92), stop:1 rgba(243, 235, 225, 0.78));
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: 16px;
    }}
    QDialog#firstRunDialog QLabel#firstRunCardAccent {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(111, 185, 173, 0.35), stop:0.5 rgba(111, 185, 173, 0.95),
            stop:1 rgba(111, 185, 173, 0.35));
        border: none;
        border-radius: 2px;
    }}
    QDialog#firstRunDialog QLabel#firstRunCardTitle {{
        color: {COL["text_primary"]};
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 0.2px;
    }}
    QDialog#firstRunDialog QLabel#firstRunCardHint {{
        color: {COL["muted"]};
        font-size: 12px;
        font-weight: 600;
        padding: 2px 0 6px 0;
    }}
    QDialog#firstRunDialog QLabel#firstRunFormLabel {{
        color: #5A5955;
        font-size: 12px;
        font-weight: 700;
    }}
    QDialog#firstRunDialog QLineEdit#firstRunInput {{
        background: rgba(255, 253, 250, 0.95);
        border: 1px solid rgba(198, 184, 168, 0.65);
        border-radius: 10px;
        padding: 9px 12px;
        font-size: 13px;
    }}
    QDialog#firstRunDialog QLineEdit#firstRunInput:focus {{
        border: 1px solid rgba(111, 185, 173, 0.95);
        background: rgba(255, 255, 255, 0.98);
    }}
    QDialog#firstRunDialog QLabel#firstRunCardMeta {{
        color: #76726A;
        font-size: 11px;
        font-weight: 600;
        padding: 4px 0 2px 0;
    }}
    QDialog#firstRunDialog QPushButton#firstRunPrimaryButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #8CDCCF, stop:1 #62C9B8);
        color: #11342F;
        border: 1px solid rgba(73, 163, 146, 0.95);
        border-radius: 11px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 800;
    }}
    QDialog#firstRunDialog QPushButton#firstRunPrimaryButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #9FE7DB, stop:1 #72D5C4);
    }}
    QDialog#firstRunDialog QPushButton#firstRunPrimaryButton:pressed {{
        background: #58BDAE;
    }}
    QDialog#firstRunDialog QPushButton#firstRunGhostButton {{
        background: rgba(255, 250, 244, 0.92);
        color: {COL["muted"]};
        border: 1px solid rgba(206, 196, 182, 0.8);
        border-radius: 11px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: 700;
    }}
    QDialog#firstRunDialog QPushButton#firstRunGhostButton:hover {{
        background: rgba(250, 241, 232, 0.95);
        color: {COL["text"]};
    }}
    QDialog#firstRunDialog QPushButton#firstRunGhostButton:pressed {{
        background: rgba(241, 231, 220, 0.95);
    }}
    QDialog#firstRunDialog QLabel#firstRunInfoBadge {{
        color: {COL["text"]};
        background: rgba(255, 249, 242, 0.66);
        border: 1px solid rgba(198, 184, 168, 0.4);
        border-radius: 12px;
        padding: 9px 14px;
        font-size: 12px;
        font-weight: 700;
    }}
    """

