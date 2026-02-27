from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.services.analytics_service import AnalyticsService
from ...application.services.reference_service import ReferenceService
from ...application.services.reporting_service import ReportingService
from ..widgets.toast import show_toast

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover - optional dependency fallback
    pg = None


class _AntibiogramDialog(QDialog):
    """Сводная антибиотикограмма по периоду."""

    def __init__(self, svc, ref_svc, parent=None) -> None:
        super().__init__(parent)
        self._svc = svc
        self._ref_svc = ref_svc
        self.setWindowTitle("Антибиотикограмма")
        self.setMinimumSize(820, 540)
        self.resize(900, 580)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Фильтры
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Период:"))
        self._from = QDateEdit()
        self._from.setCalendarPopup(True)
        self._from.setDisplayFormat("dd.MM.yyyy")
        self._from.setDate(QDate.currentDate().addMonths(-6))
        self._to = QDateEdit()
        self._to.setCalendarPopup(True)
        self._to.setDisplayFormat("dd.MM.yyyy")
        self._to.setDate(QDate.currentDate())
        filter_row.addWidget(self._from)
        filter_row.addWidget(QLabel("—"))
        filter_row.addWidget(self._to)
        btn_apply = QPushButton("Применить")
        btn_apply.setObjectName("secondary")
        btn_apply.clicked.connect(self._load)
        filter_row.addWidget(btn_apply)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        hint = QLabel("Строки с %S < 50% выделены красным. N — число тестов.")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        # Таблица
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Микроорганизм", "Группа АБ", "%S", "%I", "%R", "N"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._load()

    def _load(self) -> None:
        qf, qt = self._from.date(), self._to.date()
        df = date(qf.year(), qf.month(), qf.day())
        dt = date(qt.year(), qt.month(), qt.day())
        try:
            rows = self._svc.antibiogram(date_from=df, date_to=dt)
        except Exception:
            rows = []
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(row["organism"]))
            self._table.setItem(r, 1, QTableWidgetItem(row["group"]))
            self._table.setItem(r, 2, QTableWidgetItem(f"{row['pct_S']}%"))
            self._table.setItem(r, 3, QTableWidgetItem(f"{row['pct_I']}%"))
            self._table.setItem(r, 4, QTableWidgetItem(f"{row['pct_R']}%"))
            self._table.setItem(r, 5, QTableWidgetItem(str(row["n_tests"])))
            if row["pct_S"] < 50:
                for col in range(6):
                    item = self._table.item(r, col)
                    if item:
                        item.setBackground(QColor("#FDEDEC"))
                        item.setForeground(QColor("#922B21"))


class AnalyticsView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self._svc = AnalyticsService(engine, session_ctx)
        self._reporting = ReportingService(engine, session_ctx)
        self._ref_svc = ReferenceService(engine, session_ctx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Аналитика")
        title.setObjectName("title")
        layout.addWidget(title)

        # ── Фильтры ───────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Период:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("—"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        filter_row.addWidget(self.date_to)

        filter_row.addWidget(QLabel("Отделение:"))
        self.filter_dep = QComboBox()
        self.filter_dep.setMinimumWidth(140)
        filter_row.addWidget(self.filter_dep)

        btn_apply = QPushButton("Применить")
        btn_apply.setObjectName("secondary")
        btn_apply.clicked.connect(self.refresh)
        btn_reset = QPushButton("Сброс")
        btn_reset.setObjectName("ghost")
        btn_reset.clicked.connect(self._reset_filters)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_reset)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # ── Кнопки экспорта ───────────────────────────────────────────────
        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить метрики")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_antibiogram = QPushButton("Антибиотикограмма")
        self.btn_antibiogram.setObjectName("secondary")
        self.btn_antibiogram.clicked.connect(self._open_antibiogram)
        self.btn_export_csv = QPushButton("CSV")
        self.btn_export_csv.setObjectName("secondary")
        self.btn_export_csv.clicked.connect(self.export_csv_report)
        self.btn_export_xlsx = QPushButton("XLSX")
        self.btn_export_xlsx.setObjectName("secondary")
        self.btn_export_xlsx.clicked.connect(self.export_xlsx_report)
        self.btn_export_pdf = QPushButton("PDF")
        self.btn_export_pdf.setObjectName("ghost")
        self.btn_export_pdf.clicked.connect(self.export_pdf_report)
        actions.addWidget(self.btn_refresh)
        actions.addWidget(self.btn_antibiogram)
        actions.addWidget(self.btn_export_csv)
        actions.addWidget(self.btn_export_xlsx)
        actions.addWidget(self.btn_export_pdf)
        actions.addStretch(1)
        layout.addLayout(actions)

        # ── Метрики + График ──────────────────────────────────────────────
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)

        self.card_summary = QFrame()
        self.card_summary.setObjectName("card")
        summary_l = QVBoxLayout(self.card_summary)
        summary_l.setContentsMargins(16, 14, 16, 14)
        summary_lbl = QLabel("Общая статистика")
        summary_lbl.setObjectName("subtitle")
        summary_l.addWidget(summary_lbl)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        summary_l.addWidget(self.summary)
        summary_l.addStretch(1)

        self.card_ismp = QFrame()
        self.card_ismp.setObjectName("card")
        ismp_l = QVBoxLayout(self.card_ismp)
        ismp_l.setContentsMargins(16, 14, 16, 14)
        ismp_lbl = QLabel("ИСМП-метрики")
        ismp_lbl.setObjectName("subtitle")
        ismp_l.addWidget(ismp_lbl)
        self.ismp_label = QLabel()
        self.ismp_label.setWordWrap(True)
        ismp_l.addWidget(self.ismp_label)
        ismp_l.addStretch(1)

        self.card_mortality = QFrame()
        self.card_mortality.setObjectName("card")
        mort_l = QVBoxLayout(self.card_mortality)
        mort_l.setContentsMargins(16, 14, 16, 14)
        mort_lbl = QLabel("Летальность / LOS")
        mort_lbl.setObjectName("subtitle")
        mort_l.addWidget(mort_lbl)
        self.mortality_label = QLabel()
        self.mortality_label.setWordWrap(True)
        mort_l.addWidget(self.mortality_label)
        mort_l.addStretch(1)

        metrics_row.addWidget(self.card_summary, 1)
        metrics_row.addWidget(self.card_ismp, 1)
        metrics_row.addWidget(self.card_mortality, 1)
        layout.addLayout(metrics_row)

        # ── Топ-10 микроорганизмов ────────────────────────────────────────
        top_card = QFrame()
        top_card.setObjectName("card")
        top_l = QVBoxLayout(top_card)
        top_l.setContentsMargins(12, 10, 12, 10)
        top_l.setSpacing(6)
        top_title = QLabel("Топ-10 микроорганизмов")
        top_title.setObjectName("subtitle")
        top_l.addWidget(top_title)
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["Микроорганизм", "Кол-во"])
        self.top_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setMaximumHeight(200)
        top_hdr = self.top_table.horizontalHeader()
        top_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        top_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        top_l.addWidget(self.top_table)
        layout.addWidget(top_card)

        # ── График ────────────────────────────────────────────────────────
        self.chart = None
        if pg is not None:
            chart_card = QFrame()
            chart_card.setObjectName("card")
            chart_l = QVBoxLayout(chart_card)
            chart_l.setContentsMargins(8, 8, 8, 8)
            self.chart = pg.PlotWidget()
            self.chart.setBackground("w")
            self.chart.showGrid(x=True, y=True, alpha=0.2)
            self.chart.getAxis("left").setPen("#3A3A38")
            self.chart.getAxis("bottom").setPen("#3A3A38")
            chart_l.addWidget(self.chart)
            layout.addWidget(chart_card, 2)

        # ── История отчётов ───────────────────────────────────────────────
        hist_card = QFrame()
        hist_card.setObjectName("card")
        hist_l = QVBoxLayout(hist_card)
        hist_l.setContentsMargins(12, 12, 12, 12)
        hist_l.setSpacing(6)
        hist_title = QLabel("История отчётов")
        hist_title.setObjectName("subtitle")
        hist_l.addWidget(hist_title)

        self.hist_table = QTableWidget(0, 4)
        self.hist_table.setHorizontalHeaderLabels(["ID", "Дата", "Тип отчёта", "Артефакт"])
        self.hist_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hist_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.hist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hist_table.setAlternatingRowColors(True)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setMaximumHeight(150)
        hhdr = self.hist_table.horizontalHeader()
        hhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hhdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hhdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hist_l.addWidget(self.hist_table)
        layout.addWidget(hist_card)

        self._load_departments()
        self.refresh()

    def _load_departments(self) -> None:
        self.filter_dep.clear()
        self.filter_dep.addItem("Все отделения", None)
        try:
            for dep in self._ref_svc.departments():
                self.filter_dep.addItem(dep.name, dep.id)
        except Exception:
            pass

    def _reset_filters(self) -> None:
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.filter_dep.setCurrentIndex(0)
        self.refresh()

    def _get_date_from(self):
        qd = self.date_from.date()
        from datetime import date
        return date(qd.year(), qd.month(), qd.day())

    def _get_date_to(self):
        qd = self.date_to.date()
        from datetime import date
        return date(qd.year(), qd.month(), qd.day())

    def refresh(self):
        date_from = self._get_date_from()
        date_to = self._get_date_to()
        dep_id = self.filter_dep.currentData()

        try:
            data = self._svc.summary(date_from=date_from, date_to=date_to, department_id=dep_id)
        except Exception:
            data = self._svc.summary()

        try:
            incidence = self._svc.incidence_density(date_from=date_from, date_to=date_to)
            prevalence = self._svc.prevalence(date_from=date_from, date_to=date_to)
        except Exception:
            incidence = self._svc.incidence_density()
            prevalence = self._svc.prevalence()

        self.summary.setText(
            "\n".join([
                f"Пациенты: {data['patients']}",
                f"Госпитализации: {data['cases']}",
                f"Версии ЭМЗ: {data['versions']}",
                f"Лаб-пробы: {data['lab_samples']}",
                f"Санитарные пробы: {data['sanitary_samples']}",
                f"Тяжелые версии: {data['severe_versions']}",
                f"Плотность инцидентности: {incidence}",
                f"Превалентность тяжелых: {prevalence}",
            ])
        )

        try:
            ismp = self._svc.ismp_metrics(date_from=date_from, date_to=date_to)
            self.ismp_label.setText(
                "\n".join([
                    f"ВАП (ИВЛ-события): {ismp['vap']}",
                    f"КА-ИК (ЦВК-события): {ismp['ca_bsi']}",
                    f"КА-ИМП (катетер-события): {ismp['ca_uti']}",
                ])
            )
        except Exception:
            self.ismp_label.setText("Нет данных")

        try:
            mort = self._svc.mortality_rate(date_from=date_from, date_to=date_to)
            los = self._svc.avg_los_days(date_from=date_from, date_to=date_to)
            self.mortality_label.setText(
                "\n".join([
                    f"Всего госпитализаций: {mort['total']}",
                    f"Умерло: {mort['died']}",
                    f"Летальность: {mort['rate_pct']}%",
                    f"Средний к/день: {los} дн.",
                ])
            )
        except Exception:
            self.mortality_label.setText("Нет данных")

        try:
            top = self._svc.top_organisms(limit=10, date_from=date_from, date_to=date_to)
        except Exception:
            top = []
        self.top_table.setRowCount(0)
        for item in top:
            r = self.top_table.rowCount()
            self.top_table.insertRow(r)
            self.top_table.setItem(r, 0, QTableWidgetItem(item["organism"]))
            self.top_table.setItem(r, 1, QTableWidgetItem(str(item["count"])))

        if self.chart is not None:
            values = [
                data["patients"],
                data["cases"],
                data["versions"],
                data["lab_samples"],
                data["sanitary_samples"],
                data["severe_versions"],
            ]
            x = list(range(len(values)))
            bars = pg.BarGraphItem(x=x, height=values, width=0.7, brush="#8FDCCF", pen="#6FB9AD")
            self.chart.clear()
            self.chart.addItem(bars)
            self.chart.getAxis("bottom").setTicks(
                [[(0, "Pat"), (1, "Case"), (2, "EMR"), (3, "Lab"), (4, "San"), (5, "Sev")]]
            )

        self._refresh_history()

    def _refresh_history(self) -> None:
        try:
            rows = self._reporting.history(limit=50)
        except Exception:
            return
        self.hist_table.setRowCount(0)
        for row in rows:
            r = self.hist_table.rowCount()
            self.hist_table.insertRow(r)
            ts = row.created_at.isoformat(timespec="seconds") if row.created_at else ""
            artifact = row.artifact_path or ""
            self.hist_table.setItem(r, 0, QTableWidgetItem(str(row.id)))
            self.hist_table.setItem(r, 1, QTableWidgetItem(ts))
            self.hist_table.setItem(r, 2, QTableWidgetItem(row.report_type or ""))
            self.hist_table.setItem(r, 3, QTableWidgetItem(artifact))

    def export_csv_report(self):
        try:
            path = self._reporting.export_summary_csv()
            show_toast(self.window(), f"CSV сохранен: {path.name}", "success")
            self._refresh_history()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка CSV: {exc}", "error")

    def export_xlsx_report(self):
        try:
            path = self._reporting.export_summary_xlsx()
            show_toast(self.window(), f"XLSX сохранен: {path.name}", "success")
            self._refresh_history()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка XLSX: {exc}", "error")

    def export_pdf_report(self):
        try:
            path = self._reporting.export_summary_pdf()
            show_toast(self.window(), f"PDF сохранен: {path.name}", "success")
            self._refresh_history()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка PDF: {exc}", "error")

    def _open_antibiogram(self) -> None:
        dlg = _AntibiogramDialog(self._svc, self._ref_svc, parent=self)
        dlg.exec()
