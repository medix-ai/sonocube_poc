"""Case history panel — simplified 3-tab workstation (replaces DashboardPanel)"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QSortFilterProxyModel, pyqtSlot
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QTableView,
    QVBoxLayout, QWidget,
)

from gui.styles import ACCENT, BG_PANEL, EF_LOW, EF_MID, EF_NORMAL, TEXT_PRI, TEXT_SEC
from utils.history import delete_entry, export_all_csv, load_history


_COLS = ["Case ID", "File", "EF (%)", "Stability", "View", "Date", ""]


class HistoryPanel(QWidget):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._history: List[Dict[str, Any]] = []
        self._init_ui()
        self.refresh()

    # ── layout ───────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # header row
        hdr = QHBoxLayout()
        lbl = QLabel("Case History")
        lbl.setStyleSheet(f"color:{TEXT_PRI}; font-size:15px; font-weight:600;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search case ID / file / view…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._on_search)
        hdr.addWidget(self._search)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedHeight(28)
        btn_refresh.clicked.connect(self.refresh)
        hdr.addWidget(btn_refresh)

        btn_export = QPushButton("Export CSV")
        btn_export.setFixedHeight(28)
        btn_export.clicked.connect(self._export_csv)
        hdr.addWidget(btn_export)

        btn_clear = QPushButton("Clear All")
        btn_clear.setProperty("class", "danger")
        btn_clear.setFixedHeight(28)
        btn_clear.clicked.connect(self._clear_all)
        hdr.addWidget(btn_clear)

        root.addLayout(hdr)

        # table
        self._model = QStandardItemModel(0, len(_COLS))
        self._model.setHorizontalHeaderLabels(_COLS)

        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)  # search all columns

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.doubleClicked.connect(self._on_double_click)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        root.addWidget(self._table)

        # footer
        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet(f"color:{TEXT_SEC}; font-size:11px;")
        root.addWidget(self._lbl_count)

    # ── public ───────────────────────────────────────────────────────────────

    def refresh(self):
        self._history = load_history()
        self._rebuild_table()

    # ── internal ─────────────────────────────────────────────────────────────

    def _rebuild_table(self):
        self._model.setRowCount(0)
        for entry in reversed(self._history):
            row = self._make_row(entry)
            self._model.appendRow(row)
        visible = self._proxy.rowCount()
        total = len(self._history)
        self._lbl_count.setText(f"{total} case(s) total")

    def _make_row(self, e: Dict[str, Any]) -> List[QStandardItem]:
        ef = e.get("ef") or e.get("estimated_ef_median") or e.get("ef_median")
        ef_str = f"{ef:.1f}" if ef is not None else "—"
        ef_color = _ef_color(ef) if ef is not None else TEXT_SEC

        stability = e.get("confidence_level", e.get("stability", "—"))
        view = e.get("view_type", "—")

        # worker.py → "date", batch_worker.py → "date" (구버전 호환: "analysis_timestamp")
        ts_raw = e.get("date", e.get("analysis_timestamp", ""))
        date_str = ts_raw[:16].replace("T", " ") if ts_raw else "—"

        # worker.py → "file", batch_worker.py → "file" (구버전 호환: "input_file")
        file_name = e.get("file") or Path(e.get("input_file", "")).name or "—"

        items = [
            _item(e.get("case_id", "—")),
            _item(file_name, tooltip=e.get("file", e.get("input_file", ""))),
            _item(ef_str, fg=ef_color, align=Qt.AlignCenter),
            _item(stability, fg=_stability_color(stability), align=Qt.AlignCenter),
            _item(view, align=Qt.AlignCenter),
            _item(date_str),
            _item("PDF", fg=ACCENT, align=Qt.AlignCenter),
        ]
        # store full entry in first column for retrieval
        items[0].setData(e, Qt.UserRole)
        return items

    def _entry_at_proxy_row(self, proxy_row: int) -> Optional[Dict[str, Any]]:
        src_idx = self._proxy.mapToSource(self._proxy.index(proxy_row, 0))
        item = self._model.item(src_idx.row(), 0)
        return item.data(Qt.UserRole) if item else None

    def _history_index_for_entry(self, entry: Dict[str, Any]) -> int:
        """Return index in self._history (as loaded) matching entry by case_id+timestamp."""
        key = (entry.get("case_id"), entry.get("date", entry.get("analysis_timestamp")))
        for i, e in enumerate(self._history):
            if (e.get("case_id"), e.get("date", e.get("analysis_timestamp"))) == key:
                return i
        return -1

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._proxy.setFilterFixedString(text)

    def _on_double_click(self, index):
        entry = self._entry_at_proxy_row(index.row())
        if entry:
            self._open_pdf(entry)

    def _context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        entry = self._entry_at_proxy_row(idx.row())
        if not entry:
            return

        menu = QMenu(self)
        menu.addAction("Open PDF Report", lambda: self._open_pdf(entry))
        menu.addAction("Open JSON", lambda: self._open_json(entry))
        menu.addSeparator()
        menu.addAction("Copy Case ID", lambda: QApplication.clipboard().setText(
            entry.get("case_id", "")))
        menu.addSeparator()
        act_del = menu.addAction("Delete Entry")
        act_del.triggered.connect(lambda: self._delete_entry(entry))
        menu.exec_(self._table.viewport().mapToGlobal(pos))

    def _open_pdf(self, entry: Dict[str, Any]):
        _open_file(entry.get("report_path"), self)

    def _open_json(self, entry: Dict[str, Any]):
        _open_file(entry.get("json_path"), self)

    def _delete_entry(self, entry: Dict[str, Any]):
        idx = self._history_index_for_entry(entry)
        if idx < 0:
            return
        reply = QMessageBox.question(
            self, "Delete", f"Delete entry for case {entry.get('case_id', '?')}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            delete_entry(idx)
            self.refresh()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export History CSV", "sonocube_history.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                export_all_csv(Path(path))
                QMessageBox.information(self, "Export", f"Saved:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _clear_all(self):
        if not self._history:
            return
        reply = QMessageBox.question(
            self, "Clear All", "Delete all history entries? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        # delete from last to first to avoid index shifting
        for i in reversed(range(len(self._history))):
            delete_entry(i)
        self.refresh()


# ── helpers ───────────────────────────────────────────────────────────────────

def _item(text: str, fg: str = TEXT_PRI, align: Qt.AlignmentFlag = Qt.AlignLeft,
          tooltip: str = "") -> QStandardItem:
    it = QStandardItem(str(text))
    it.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(fg))
    it.setTextAlignment(align | Qt.AlignVCenter)
    if tooltip:
        it.setToolTip(tooltip)
    it.setEditable(False)
    return it


def _ef_color(ef: float) -> str:
    if ef >= 55:
        return EF_NORMAL
    elif ef >= 40:
        return EF_MID
    return EF_LOW


def _stability_color(level: str) -> str:
    from gui.styles import HIGH_CLR, MED_CLR, LOW_CLR
    return {"High": HIGH_CLR, "Medium": MED_CLR, "Low": LOW_CLR}.get(level, TEXT_SEC)


def _open_file(path, parent: QWidget):
    import platform, subprocess
    if not path or not Path(str(path)).exists():
        QMessageBox.warning(parent, "File Not Found", f"File not found:\n{path}")
        return
    sys_ = platform.system()
    if sys_ == "Darwin":
        subprocess.run(["open", str(path)])
    elif sys_ == "Windows":
        subprocess.run(["start", str(path)], shell=True)
    else:
        subprocess.run(["xdg-open", str(path)])
