from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ..widgets.toast import show_toast


class PlaceholderView(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        card = QFrame()
        card.setObjectName("softCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setObjectName("muted")
        card_layout.addWidget(subtitle_label)

        hint_btn = QPushButton("Показать уведомление")
        hint_btn.setObjectName("secondary")
        hint_btn.clicked.connect(lambda: show_toast(self.window(), f"Раздел «{title}» пока в разработке.", "info"))
        card_layout.addWidget(hint_btn)

        layout.addWidget(card)
        layout.addStretch(1)
