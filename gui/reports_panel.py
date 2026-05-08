"""Reports 패널 — 리포트 생성/열기, JSON/CSV export"""
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from utils.constants import APP_VERSION, DISCLAIMER


class ReportsPanel(QWidget):
    """Reports 탭"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[Dict[str, Any]] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.setSpacing(16)

        title = QLabel("Reports & Export")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: 700;")
        outer.addWidget(title)

        # 현재 분석 정보
        info_group = QGroupBox("Current Analysis")
        info_lo = QVBoxLayout(info_group)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(160)
        self.info_text.setPlaceholderText(
            "No analysis result available.\nRun an analysis first."
        )
        info_lo.addWidget(self.info_text)
        outer.addWidget(info_group)

        # PDF 리포트
        pdf_group = QGroupBox("PDF Report")
        pdf_lo = QVBoxLayout(pdf_group)

        pdf_desc = QLabel(
            "The PDF report includes: case info, EF statistics, frame-wise EF curve,\n"
            "ED/ES snapshots, quality warnings, model metadata, and a research-use disclaimer."
        )
        pdf_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        pdf_desc.setWordWrap(True)
        pdf_lo.addWidget(pdf_desc)

        pdf_btns = QHBoxLayout()
        self.btn_open_pdf = QPushButton("Open PDF Report")
        self.btn_open_pdf.setProperty("class", "primary")
        self.btn_open_pdf.setFixedHeight(36)
        self.btn_open_pdf.setEnabled(False)
        self.btn_open_pdf.clicked.connect(self._open_pdf)
        pdf_btns.addWidget(self.btn_open_pdf)

        self.btn_regen_pdf = QPushButton("Re-generate PDF")
        self.btn_regen_pdf.setFixedHeight(36)
        self.btn_regen_pdf.setEnabled(False)
        self.btn_regen_pdf.clicked.connect(self._regen_pdf)
        pdf_btns.addWidget(self.btn_regen_pdf)
        pdf_btns.addStretch()
        pdf_lo.addLayout(pdf_btns)
        outer.addWidget(pdf_group)

        # JSON / CSV export
        export_group = QGroupBox("Data Export")
        export_lo = QVBoxLayout(export_group)

        exp_desc = QLabel(
            "JSON includes: full EF statistics, framewise_ef list, model metadata,\n"
            "unsupported_metrics, manual override status, and disclaimer.\n"
            "CSV contains per-case summary (framewise_ef excluded)."
        )
        exp_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        exp_desc.setWordWrap(True)
        export_lo.addWidget(exp_desc)

        exp_btns = QHBoxLayout()
        self.btn_open_json = QPushButton("Open JSON")
        self.btn_open_json.setFixedHeight(32)
        self.btn_open_json.setEnabled(False)
        self.btn_open_json.clicked.connect(self._open_json)
        exp_btns.addWidget(self.btn_open_json)

        self.btn_open_csv = QPushButton("Open CSV")
        self.btn_open_csv.setFixedHeight(32)
        self.btn_open_csv.setEnabled(False)
        self.btn_open_csv.clicked.connect(self._open_csv)
        exp_btns.addWidget(self.btn_open_csv)

        self.btn_export_all = QPushButton("Export All History CSV")
        self.btn_export_all.setFixedHeight(32)
        self.btn_export_all.clicked.connect(self._export_all_csv)
        exp_btns.addWidget(self.btn_export_all)
        exp_btns.addStretch()
        export_lo.addLayout(exp_btns)
        outer.addWidget(export_group)

        # EF Trend
        trend_group = QGroupBox("EF Trend")
        trend_lo = QVBoxLayout(trend_group)
        trend_desc = QLabel(
            "View the EF trend across all analyzed cases. "
            "Marker color indicates prediction stability (green=High, orange=Medium, red=Low)."
        )
        trend_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        trend_desc.setWordWrap(True)
        trend_lo.addWidget(trend_desc)
        btn_trend = QPushButton("Show EF Trend")
        btn_trend.setFixedHeight(32)
        btn_trend.setFixedWidth(160)
        btn_trend.clicked.connect(self._show_trend)
        trend_lo.addWidget(btn_trend)
        outer.addWidget(trend_group)

        # Disclaimer
        disc = QLabel(DISCLAIMER)
        disc.setStyleSheet(
            "color: #d29922; font-size: 11px; font-weight: 600;"
            "background-color: #1c1800; border: 1px solid #3d2e00;"
            "border-radius: 4px; padding: 8px;"
        )
        disc.setAlignment(Qt.AlignCenter)
        outer.addWidget(disc)

        outer.addStretch()

    # ── 데이터 업데이트 ───────────────────────────────────────────────────────

    def update_result(self, result: Dict[str, Any]):
        self._result = result
        model_info = result.get("model_info", {})
        meta = result.get("metadata", {})
        ef = result.get("ef")
        conf = result.get("confidence_level", "--")
        override = result.get("manual_override", False)

        info_lines = [
            f"App version:   {APP_VERSION}",
            f"Model:         {model_info.get('name','?')} {model_info.get('variant','?')} v{model_info.get('version','?')}",
            f"File:          {meta.get('file_path','?')}",
            f"Frames:        {meta.get('num_frames','?')}",
            f"EF (median):   {ef:.1f}%" if ef is not None else "EF:            --",
            f"Stability:     {conf}",
            f"Manual override: {'Yes' if override else 'No'}",
        ]
        self.info_text.setText("\n".join(info_lines))

        self.btn_open_pdf.setEnabled(bool(result.get("report_path")))
        self.btn_regen_pdf.setEnabled(True)
        self.btn_open_json.setEnabled(bool(result.get("json_path")))
        self.btn_open_csv.setEnabled(bool(result.get("csv_path")))

    # ── 파일 열기 ─────────────────────────────────────────────────────────────

    def _open_file(self, path):
        if not path or not Path(str(path)).exists():
            QMessageBox.warning(self, "Warning", "File not found.")
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(path)])

    def _open_pdf(self):
        self._open_file(self._result.get("report_path") if self._result else None)

    def _open_json(self):
        self._open_file(self._result.get("json_path") if self._result else None)

    def _open_csv(self):
        self._open_file(self._result.get("csv_path") if self._result else None)

    def _regen_pdf(self):
        if not self._result:
            return
        try:
            from datetime import datetime
            from pathlib import Path as P
            from utils.spec import PROJECT_ROOT
            from report.report_builder import build_pdf
            stem = Path(str(self._result.get("metadata", {}).get("file_path", "case"))).stem
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = PROJECT_ROOT / "output"
            out_dir.mkdir(exist_ok=True)
            rp = out_dir / f"{stem}_{ts}.pdf"
            build_pdf(report_path=rp, analysis_result=self._result)
            self._result["report_path"] = rp
            self.btn_open_pdf.setEnabled(True)
            QMessageBox.information(self, "Success", f"PDF generated:\n{rp}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"PDF generation failed:\n{e}")

    def _export_all_csv(self):
        from utils.history import export_all_csv
        path, _ = QFileDialog.getSaveFileName(
            self, "Export History CSV", "sonocube_history.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                export_all_csv(Path(path))
                QMessageBox.information(self, "Success", f"Saved:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _show_trend(self):
        from utils.history import load_history
        from gui.trend_dialog import TrendDialog
        dlg = TrendDialog(load_history(), parent=self)
        dlg.exec_()
