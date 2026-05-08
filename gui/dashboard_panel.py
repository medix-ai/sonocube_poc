"""Dashboard 패널 — 케이스 통계, 최근 케이스 테이블, EF trend 요약"""
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QGroupBox,
)

from utils.constants import APP_NAME, APP_VERSION, CONFIDENCE_COLORS


class StatCard(QWidget):
    """단일 통계 카드 위젯"""

    def __init__(self, label: str, value: str = "--", color: str = "#58a6ff", parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet(
            "background-color: #1c2128; border: 1px solid #30363d; border-radius: 8px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._val_label = QLabel(value)
        self._val_label.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 700; border: none;"
        )
        layout.addWidget(self._val_label)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 600;"
            "text-transform: uppercase; letter-spacing: 0.3px; border: none;"
        )
        layout.addWidget(lbl)

    def set_value(self, value: str, color: str = None):
        self._val_label.setText(value)
        if color:
            self._val_label.setStyleSheet(
                f"color: {color}; font-size: 28px; font-weight: 700; border: none;"
            )


class DashboardPanel(QWidget):
    """Dashboard 탭"""

    open_file_requested = pyqtSignal()
    start_analysis_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: List[Dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(16)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel(f"{APP_NAME}")
        title.setStyleSheet(
            "color: #e6edf3; font-size: 22px; font-weight: 700;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        ver = QLabel(f"v{APP_VERSION}  ·  Research use only")
        ver.setStyleSheet("color: #8b949e; font-size: 12px;")
        hdr.addWidget(ver)

        btn_new = QPushButton("+ New Analysis")
        btn_new.setProperty("class", "primary")
        btn_new.setFixedHeight(32)
        btn_new.clicked.connect(self.open_file_requested)
        hdr.addWidget(btn_new)
        outer.addLayout(hdr)

        # Disclaimer
        disc = QLabel(
            "NOT FOR DIAGNOSTIC USE — Research and educational purposes only."
        )
        disc.setProperty("class", "disclaimer")
        disc.setAlignment(Qt.AlignCenter)
        disc.setStyleSheet(
            "color: #d29922; font-size: 11px; font-weight: 600;"
            "background-color: #1c1800; border: 1px solid #3d2e00;"
            "border-radius: 4px; padding: 6px;"
        )
        outer.addWidget(disc)

        # 통계 카드
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.card_total   = StatCard("Total Cases",        "--")
        self.card_recent  = StatCard("Last 7 Days",        "--", "#3fb950")
        self.card_avg_ef  = StatCard("Average EF",         "--", "#58a6ff")
        self.card_low     = StatCard("Low Stability Cases","--", "#f85149")
        for c in (self.card_total, self.card_recent, self.card_avg_ef, self.card_low):
            cards_row.addWidget(c)
        outer.addLayout(cards_row)

        # 검색 + 정렬
        ctrl_row = QHBoxLayout()
        search_lbl = QLabel("Search:")
        search_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        ctrl_row.addWidget(search_lbl)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Case ID, file name, view type…")
        self.search_box.setFixedWidth(280)
        self.search_box.textChanged.connect(self._apply_filter)
        ctrl_row.addWidget(self.search_box)
        ctrl_row.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedHeight(28)
        self.btn_refresh.clicked.connect(self.refresh)
        ctrl_row.addWidget(self.btn_refresh)

        self.btn_export_all = QPushButton("Export All CSV")
        self.btn_export_all.setFixedHeight(28)
        self.btn_export_all.clicked.connect(self._export_all_csv)
        ctrl_row.addWidget(self.btn_export_all)
        outer.addLayout(ctrl_row)

        # 케이스 테이블
        self.table = QTableWidget()
        self._setup_table()
        outer.addWidget(self.table)

    def _setup_table(self):
        cols = ["Case ID", "File", "Timestamp", "EF (median)", "Stability", "View", "Status", "Report"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in (0, 3, 4, 5, 6, 7):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.setSortingEnabled(True)

    # ── 데이터 갱신 ──────────────────────────────────────────────────────────

    def refresh(self):
        from utils.history import load_history
        self._history = list(reversed(load_history()))
        self._update_stat_cards()
        self._populate_table(self._history)

    def _update_stat_cards(self):
        h = self._history
        self.card_total.set_value(str(len(h)))

        cutoff = datetime.now() - timedelta(days=7)
        recent = []
        for e in h:
            try:
                d = e.get("date", "")
                dt = datetime.fromisoformat(d[:19].replace("_", "T"))
                if dt >= cutoff:
                    recent.append(e)
            except Exception:
                pass
        self.card_recent.set_value(str(len(recent)))

        efs = [e["ef"] for e in h if isinstance(e.get("ef"), (int, float))]
        self.card_avg_ef.set_value(
            f"{sum(efs)/len(efs):.1f}%" if efs else "--"
        )

        low_count = sum(1 for e in h if e.get("confidence_level") == "Low")
        self.card_low.set_value(
            str(low_count),
            "#f85149" if low_count > 0 else "#3fb950"
        )

    def _populate_table(self, entries: List[Dict[str, Any]]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            ef = e.get("ef")
            conf = e.get("confidence_level", "?")
            conf_color = CONFIDENCE_COLORS.get(conf, "#8b949e")

            self._set_cell(row, 0, e.get("case_id", "?"))
            self._set_cell(row, 1, e.get("file", "?"))
            date_str = e.get("date", "")[:16].replace("T", " ").replace("_", " ")
            self._set_cell(row, 2, date_str)
            ef_text = f"{ef:.1f}%" if isinstance(ef, (int, float)) else "--"
            self._set_cell(row, 3, ef_text)

            conf_item = QTableWidgetItem(conf)
            conf_item.setForeground(
                __import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(conf_color)
            )
            conf_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, conf_item)

            self._set_cell(row, 5, e.get("view_type", "?"))
            self._set_cell(row, 6, e.get("status", "success"))

            btn = QPushButton("Open PDF")
            btn.setFixedHeight(24)
            btn.setProperty("class", "primary")
            rp = e.get("report_path", "")
            btn.setEnabled(bool(rp))
            btn.clicked.connect(lambda _, p=rp: self._open_file(p))
            self.table.setCellWidget(row, 7, btn)

        self.table.setSortingEnabled(True)

    def _set_cell(self, row, col, text, align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(align)
        self.table.setItem(row, col, item)

    # ── 필터 ─────────────────────────────────────────────────────────────────

    def _apply_filter(self, text: str):
        txt = text.lower().strip()
        filtered = [
            e for e in self._history
            if not txt
            or txt in e.get("case_id", "").lower()
            or txt in e.get("file", "").lower()
            or txt in e.get("view_type", "").lower()
            or txt in e.get("confidence_level", "").lower()
        ]
        self._populate_table(filtered)

    # ── Context menu ──────────────────────────────────────────────────────────

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self._history):
            return
        e = self._history[row]
        menu = QMenu(self)
        menu.addAction("Open PDF", lambda: self._open_file(e.get("report_path", "")))
        menu.addAction("Open JSON", lambda: self._open_file(e.get("json_path", "")))
        menu.addSeparator()
        menu.addAction("Delete Entry", lambda: self._delete_entry(row))
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _delete_entry(self, row: int):
        reply = QMessageBox.question(self, "Delete Entry", "Delete this history entry?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        from utils.history import load_history, save_history
        history = load_history()
        actual_idx = len(history) - 1 - row
        if 0 <= actual_idx < len(history):
            history.pop(actual_idx)
            save_history(history)
        self.refresh()

    def _export_all_csv(self):
        from PyQt5.QtWidgets import QFileDialog
        from utils.history import export_all_csv
        path, _ = QFileDialog.getSaveFileName(
            self, "Export All History", "sonocube_history.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                export_all_csv(__import__("pathlib").Path(path))
                QMessageBox.information(self, "Export", f"Saved:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_file(self, path: str):
        import platform, subprocess
        if not path or not __import__("pathlib").Path(str(path)).exists():
            QMessageBox.warning(self, "Warning", "File not found.")
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(path)])
