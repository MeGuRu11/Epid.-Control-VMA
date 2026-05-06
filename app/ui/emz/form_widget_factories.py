from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from PySide6.QtCore import QDate, QDateTime, QEvent, QModelIndex, QObject, QPoint, Qt
from PySide6.QtGui import QCursor, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QFrame,
    QListView,
    QVBoxLayout,
    QWidget,
)

from app.ui.emz.form_utils import OUTCOME_TYPE_OPTIONS, OUTCOME_TYPE_PLACEHOLDER
from app.ui.widgets.datetime_inputs import (
    configure_optional_date_edit,
    configure_optional_datetime_edit,
)

ABX_COMBO_MAX_VISIBLE_ITEMS = 6
ABX_COMBO_POPUP_MAX_HEIGHT = 216
ABX_COMBO_POPUP_MIN_WIDTH = 380


class IcdLike(Protocol):
    @property
    def code(self) -> object: ...

    @property
    def title(self) -> object: ...


class AntibioticLike(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def code(self) -> object: ...

    @property
    def name(self) -> object: ...


class IsmpAbbreviationLike(Protocol):
    @property
    def code(self) -> object: ...

    @property
    def name(self) -> object: ...

    @property
    def description(self) -> object: ...


class AntibioticPopupListView(QListView):
    """Список popup антибиотиков с явной прокруткой колесом мыши."""

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if self.scroll_from_wheel_delta(event.angleDelta().y()):
            event.accept()
            return
        super().wheelEvent(event)

    def scroll_from_wheel_delta(self, delta_y: int) -> bool:
        scrollbar = self.verticalScrollBar()
        if scrollbar.maximum() <= 0 or delta_y == 0:
            return False
        row_height = self.sizeHintForRow(0)
        if row_height <= 0:
            row_height = self.fontMetrics().height() + 10
        step = max(scrollbar.singleStep(), row_height)
        steps = max(1, abs(delta_y) // 120)
        direction = -1 if delta_y > 0 else 1
        value = scrollbar.value()
        target = max(scrollbar.minimum(), min(scrollbar.maximum(), value + direction * step * steps))
        scrollbar.setValue(target)
        return True


class LimitedPopupComboBox(QComboBox):
    """ComboBox с ограничением высоты внешнего popup-контейнера Qt."""

    def __init__(self, *, max_popup_height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._max_popup_height = max_popup_height
        self._popup_frame: QFrame | None = None
        self._popup_view: QListView | None = None
        self._global_wheel_filter_installed = False

    def showPopup(self) -> None:  # noqa: N802
        self.hidePopup()
        frame = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        frame.setObjectName("abxComboPopup")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        view = AntibioticPopupListView(frame)
        view.setObjectName("abxComboPopupView")
        view.setModel(self.model())
        view.setModelColumn(self.modelColumn())
        view.setRootIndex(self.rootModelIndex())
        view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        view.setUniformItemSizes(True)
        view.clicked.connect(self._select_popup_index)
        view.activated.connect(self._select_popup_index)
        frame.installEventFilter(self)
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        layout.addWidget(view)

        height = self._popup_height(view)
        width = self._popup_width(view)
        frame.setFixedSize(width, height)
        frame.move(self._popup_position(width, height))
        self._popup_frame = frame
        self._popup_view = view
        current = self.model().index(self.currentIndex(), self.modelColumn(), self.rootModelIndex())
        if current.isValid():
            view.setCurrentIndex(current)
            view.scrollTo(current, QAbstractItemView.ScrollHint.PositionAtCenter)
        frame.destroyed.connect(self._clear_popup_refs)
        self._install_global_wheel_filter()
        frame.show()
        view.setFocus(Qt.FocusReason.PopupFocusReason)

    def hidePopup(self) -> None:  # noqa: N802
        if self._popup_frame is not None:
            popup = self._popup_frame
            self._popup_frame = None
            self._popup_view = None
            popup.hide()
            popup.deleteLater()
        self._remove_global_wheel_filter()
        super().hidePopup()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if (
            event.type() == QEvent.Type.Wheel
            and isinstance(event, QWheelEvent)
            and isinstance(self._popup_view, AntibioticPopupListView)
            and self._should_handle_popup_wheel(watched)
        ):
            delta_y = event.angleDelta().y() or event.pixelDelta().y()
            self._popup_view.scroll_from_wheel_delta(delta_y)
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _should_handle_popup_wheel(self, watched: QObject) -> bool:
        if self._popup_frame is None or self._popup_view is None:
            return False
        if watched in {self._popup_frame, self._popup_view, self._popup_view.viewport()}:
            return True
        return self._popup_frame.geometry().contains(QCursor.pos())

    def _install_global_wheel_filter(self) -> None:
        if self._global_wheel_filter_installed:
            return
        app = QApplication.instance()
        if app is None:
            return
        app.installEventFilter(self)
        self._global_wheel_filter_installed = True

    def _remove_global_wheel_filter(self) -> None:
        if not self._global_wheel_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._global_wheel_filter_installed = False

    def _select_popup_index(self, index: QModelIndex) -> None:
        if index.isValid():
            self.setCurrentIndex(index.row())
        self.hidePopup()

    def _clear_popup_refs(self) -> None:
        self._popup_frame = None
        self._popup_view = None

    def _popup_height(self, view: QListView) -> int:
        if self.count() <= 0:
            return 1
        row_height = view.sizeHintForRow(0)
        if row_height <= 0:
            row_height = self.fontMetrics().height() + 10
        content_height = self.count() * row_height + 2
        return min(self._max_popup_height, max(row_height + 2, content_height))

    def _popup_width(self, view: QListView) -> int:
        content_width = view.sizeHintForColumn(self.modelColumn())
        if content_width <= 0:
            content_width = self.width()
        return max(self.width(), ABX_COMBO_POPUP_MIN_WIDTH, content_width + 42)

    def _popup_position(self, width: int, height: int) -> QPoint:
        below = self.mapToGlobal(QPoint(0, self.height()))
        screen = self.screen() or QApplication.screenAt(below)
        if screen is None:
            return below
        available = screen.availableGeometry()
        x = min(max(available.left(), below.x()), available.right() - width + 1)
        y = below.y()
        if y + height > available.bottom() + 1:
            above_y = self.mapToGlobal(QPoint(0, -height)).y()
            if above_y >= available.top():
                y = above_y
            else:
                y = max(available.top(), available.bottom() - height + 1)
        return QPoint(x, y)


def create_diag_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItems(["Поступление", "Перевод", "Выписка", "Осложнение"])
    return combo


def create_intervention_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItems(
        [
            "Центральный катетер",
            "ИВЛ",
            "Дренаж",
            "Перевязка",
            "Операция",
            "Другое (введите вручную)",
        ]
    )
    combo.setCurrentText("")
    combo.setToolTip("Можно выбрать из списка или ввести вручную.")
    return combo


def create_outcome_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.setObjectName("emzOutcomeTypeCombo")
    combo.addItem(OUTCOME_TYPE_PLACEHOLDER, None)
    for label, value in OUTCOME_TYPE_OPTIONS:
        combo.addItem(label, value)
    return combo


def create_datetime_cell(empty_dt: QDateTime) -> QDateTimeEdit:
    widget = QDateTimeEdit()
    return configure_optional_datetime_edit(widget, empty_datetime=empty_dt)


def create_date_cell(empty_date: QDate) -> QDateEdit:
    widget = QDateEdit()
    return configure_optional_date_edit(widget, empty_date=empty_date)


def create_icd_combo(*, icd_items: Sequence[IcdLike], wire_search: Callable[[QComboBox], None]) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.addItem("Выбрать", None)
    for icd in icd_items:
        combo.addItem(f"{icd.code} - {icd.title}", str(icd.code))
    wire_search(combo)
    return combo


def populate_icd_combo(
    *,
    combo: QComboBox,
    icd_items: Sequence[IcdLike],
    selected_data: object | None,
    edit_text: str | None = None,
) -> None:
    combo.clear()
    combo.addItem("Выбрать", None)
    for icd in icd_items:
        combo.addItem(f"{icd.code} - {icd.title}", str(icd.code))
    if selected_data is not None:
        idx = combo.findData(selected_data)
        if idx >= 0:
            combo.setCurrentIndex(idx)
    if edit_text is not None:
        combo.setEditText(edit_text)


def create_abx_combo(*, antibiotics: Sequence[AntibioticLike]) -> QComboBox:
    combo = LimitedPopupComboBox(max_popup_height=ABX_COMBO_POPUP_MAX_HEIGHT)
    combo.setMaxVisibleItems(ABX_COMBO_MAX_VISIBLE_ITEMS)
    combo.view().setMaximumHeight(ABX_COMBO_POPUP_MAX_HEIGHT)
    combo.addItem("Выбрать", None)
    for abx in antibiotics:
        combo.addItem(f"{abx.code} - {abx.name}", int(abx.id))
    return combo


def create_ismp_type_combo(
    *,
    abbreviations: Sequence[IsmpAbbreviationLike],
    tooltip_role: int,
) -> QComboBox:
    combo = QComboBox()
    combo.addItem("Выбрать", None)
    for item in abbreviations:
        code = str(item.code)
        name = str(item.name)
        label = f"{code} — {name}"
        combo.addItem(label, code)
        description = str(item.description or "")
        tooltip = description or name
        combo.setItemData(combo.count() - 1, tooltip, tooltip_role)
    return combo
