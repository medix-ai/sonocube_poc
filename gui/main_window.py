"""메인 윈도우 — SonoCube v1.2  QTabWidget 6탭 구조"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QTabWidget, QToolBar, QWidget,
)

from gui.analysis_panel import AnalysisPanel
from gui.dashboard_panel import DashboardPanel
from gui.import_panel import ImportPanel
from gui.reports_panel import ReportsPanel
from gui.results_panel import ResultsPanel
from gui.settings_panel import SettingsPanel
from gui.styles import load_style_sheet
from gui.worker import AnalysisWorker
from utils.constants import APP_NAME, APP_VERSION

# 탭 인덱스 상수
TAB_DASHBOARD = 0
TAB_IMPORT    = 1
TAB_ANALYSIS  = 2
TAB_RESULTS   = 3
TAB_REPORTS   = 4
TAB_SETTINGS  = 5


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.current_result: Optional[Dict[str, Any]] = None
        self.worker: Optional[AnalysisWorker] = None
        self.video_path: Optional[Path] = None
        self._settings: Dict[str, Any] = {}
        self._init_ui()
        self.apply_style()

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle(f"{APP_NAME} — Cardiac Echo Analysis  v{APP_VERSION}")
        self.setGeometry(80, 80, 1440, 920)
        self._create_menu_bar()
        self._create_toolbar()
        self._create_tabs()
        self.statusBar().showMessage("Ready — import an echo video to begin")

    def apply_style(self):
        self.setStyleSheet(load_style_sheet())

    # ── 메뉴바 ───────────────────────────────────────────────────────────────

    def _create_menu_bar(self):
        mb = self.menuBar()

        file_m = mb.addMenu("File")
        file_m.addAction(QAction("Open Video…", self, shortcut="Ctrl+O",
                                  triggered=self._go_import))
        file_m.addSeparator()
        file_m.addAction(QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close))

        analysis_m = mb.addMenu("Analysis")
        analysis_m.addAction(QAction("Start Analysis", self, shortcut="Ctrl+R",
                                      triggered=self._trigger_analysis_from_menu))
        analysis_m.addAction(QAction("Stop Analysis", self, triggered=self._stop_analysis))
        analysis_m.addSeparator()
        analysis_m.addAction(QAction("Batch Analysis…", self,
                                      triggered=self._open_batch))

        export_m = mb.addMenu("Export")
        export_m.addAction(QAction("Open PDF Report", self, shortcut="Ctrl+P",
                                    triggered=self._open_pdf))
        export_m.addAction(QAction("Open JSON", self, triggered=self._open_json))
        export_m.addAction(QAction("Open CSV", self, triggered=self._open_csv))
        export_m.addSeparator()
        export_m.addAction(QAction("Export All History CSV…", self,
                                    triggered=self._export_all_csv))

        tools_m = mb.addMenu("Tools")
        tools_m.addAction(QAction("EF Trend…", self, triggered=self._show_trend))
        tools_m.addAction(QAction("Batch Analysis…", self, triggered=self._open_batch))
        tools_m.addAction(QAction("Save Screenshot", self, shortcut="Ctrl+Shift+S",
                                   triggered=self._save_screenshot))

        help_m = mb.addMenu("Help")
        help_m.addAction(QAction("About", self, triggered=self._show_about))

    # ── 툴바 ─────────────────────────────────────────────────────────────────

    def _create_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        title = QLabel(f"  {APP_NAME}  ")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #58a6ff;")
        tb.addWidget(title)
        tb.addSeparator()

        self.btn_import = QPushButton("Import File")
        self.btn_import.setProperty("class", "primary")
        self.btn_import.setFixedHeight(30)
        self.btn_import.clicked.connect(self._go_import)
        tb.addWidget(self.btn_import)

        self.btn_analyze = QPushButton("Start Analysis")
        self.btn_analyze.setProperty("class", "primary")
        self.btn_analyze.setFixedHeight(30)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._trigger_analysis_from_menu)
        tb.addWidget(self.btn_analyze)

        tb.addSeparator()

        self.btn_pdf = QPushButton("Open PDF")
        self.btn_pdf.setFixedHeight(30)
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self._open_pdf)
        tb.addWidget(self.btn_pdf)

        self.btn_batch = QPushButton("Batch Analysis")
        self.btn_batch.setFixedHeight(30)
        self.btn_batch.clicked.connect(self._open_batch)
        tb.addWidget(self.btn_batch)

        tb.addSeparator()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(160)
        self.progress_bar.setFixedHeight(18)
        tb.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color: #8b949e; font-size: 11px;")
        tb.addWidget(self.lbl_progress)

    # ── 탭 ───────────────────────────────────────────────────────────────────

    def _create_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        # Dashboard
        self.dashboard = DashboardPanel()
        self.dashboard.open_file_requested.connect(self._go_import)
        self.tabs.addTab(self.dashboard, "Dashboard")

        # Import
        self.import_panel = ImportPanel()
        self.import_panel.analysis_requested.connect(self._on_analysis_requested)
        self.tabs.addTab(self.import_panel, "Import")

        # Analysis
        self.analysis_panel = AnalysisPanel()
        self.analysis_panel.ed_override.connect(self._on_ed_override)
        self.analysis_panel.es_override.connect(self._on_es_override)
        self.analysis_panel.snapshot_saved.connect(
            lambda p: self.statusBar().showMessage(f"Snapshot saved: {p}")
        )
        self.tabs.addTab(self.analysis_panel, "Analysis")

        # Results
        self.results_panel = ResultsPanel()
        self.tabs.addTab(self.results_panel, "Results")

        # Reports
        self.reports_panel = ReportsPanel()
        self.tabs.addTab(self.reports_panel, "Reports")

        # Settings
        self.settings_panel = SettingsPanel()
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self._settings = self.settings_panel.get_settings()
        self.tabs.addTab(self.settings_panel, "Settings")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Dashboard 초기 로드
        self.dashboard.refresh()

    # ── 탭 전환 ──────────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int):
        if idx == TAB_DASHBOARD:
            self.dashboard.refresh()

    def _go_import(self):
        self.tabs.setCurrentIndex(TAB_IMPORT)

    # ── 분석 시작 (Import 패널에서 호출) ────────────────────────────────────

    @pyqtSlot(Path, str, str)
    def _on_analysis_requested(self, video_path: Path, case_id: str, view_type: str):
        self.video_path = video_path
        self._start_analysis(video_path, case_id, view_type)

    def _trigger_analysis_from_menu(self):
        """메뉴바 / 툴바에서 분석 시작 — Import 탭에 파일이 있어야 함"""
        if not self.video_path:
            self._go_import()
            return
        view_type = self.import_panel.view_combo.currentText()
        case_id = self.import_panel.case_id_edit.text().strip() or \
                  self.video_path.stem[:8].upper().ljust(8, "0")
        self._start_analysis(self.video_path, case_id, view_type)

    def _start_analysis(self, video_path: Path, case_id: str, view_type: str):
        self.btn_analyze.setEnabled(False)
        self.btn_import.setEnabled(False)
        self.import_panel.set_enabled_start(False)
        self.progress_bar.setVisible(True)
        self.lbl_progress.setText("Starting…")
        self.tabs.setCurrentIndex(TAB_ANALYSIS)

        s = self._settings
        output_dir_str = s.get("output_dir", "")
        output_dir = Path(output_dir_str) if output_dir_str else None

        self.worker = AnalysisWorker(
            video_path=video_path,
            view_type=view_type,
            case_id=case_id,
            output_dir=output_dir,
            auto_pdf=s.get("auto_pdf", True),
            auto_json=s.get("auto_json", True),
            auto_csv=s.get("auto_csv", True),
        )
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.analysis_finished.connect(self._on_analysis_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _stop_analysis(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        self._reset_toolbar()

    # ── 워커 시그널 ──────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_progress(self, msg: str):
        self.lbl_progress.setText(msg)
        self.statusBar().showMessage(msg)

    @pyqtSlot(dict)
    def _on_analysis_finished(self, result: Dict[str, Any]):
        self.current_result = result
        self._reset_toolbar()
        self.btn_pdf.setEnabled(bool(result.get("report_path")))
        self.btn_analyze.setEnabled(True)

        # 각 패널 업데이트
        self.analysis_panel.load_result(result)
        self.results_panel.update_result(result)
        self.reports_panel.update_result(result)
        self.dashboard.refresh()

        # Results 탭으로 자동 이동
        self.tabs.setCurrentIndex(TAB_RESULTS)
        self.statusBar().showMessage("Analysis complete!")

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._reset_toolbar()
        QMessageBox.critical(self, "Analysis Error", msg)
        self.statusBar().showMessage("Error occurred")
        self.import_panel.set_enabled_start(True)
        self.tabs.setCurrentIndex(TAB_IMPORT)

    def _reset_toolbar(self):
        self.progress_bar.setVisible(False)
        self.lbl_progress.setText("")
        self.btn_analyze.setEnabled(True)
        self.btn_import.setEnabled(True)
        self.import_panel.set_enabled_start(True)

    # ── Manual override ───────────────────────────────────────────────────────

    @pyqtSlot(int)
    def _on_ed_override(self, idx: int):
        if self.current_result:
            self.current_result["ed_frame_index_final"] = idx
            self.current_result["manual_override"] = True
            self.results_panel.update_result(self.current_result)

    @pyqtSlot(int)
    def _on_es_override(self, idx: int):
        if self.current_result:
            self.current_result["es_frame_index_final"] = idx
            self.current_result["manual_override"] = True
            self.results_panel.update_result(self.current_result)

    # ── 파일 열기 ─────────────────────────────────────────────────────────────

    def _open_pdf(self):
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No analysis result available.")
            return
        self._open_file(self.current_result.get("report_path"))

    def _open_json(self):
        self._open_file(self.current_result.get("json_path") if self.current_result else None)

    def _open_csv(self):
        self._open_file(self.current_result.get("csv_path") if self.current_result else None)

    def _open_file(self, path):
        import platform, subprocess
        if not path or not Path(str(path)).exists():
            QMessageBox.warning(self, "Warning", "File not found.")
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(path)])

    # ── 기타 액션 ─────────────────────────────────────────────────────────────

    def _open_batch(self):
        from gui.batch_dialog import BatchDialog
        s = self._settings
        out_str = s.get("output_dir", "")
        out = Path(out_str) / "batch" if out_str else None
        dlg = BatchDialog(default_output_dir=out, parent=self)
        dlg.exec_()
        self.dashboard.refresh()

    def _export_all_csv(self):
        from PyQt5.QtWidgets import QFileDialog
        from utils.history import export_all_csv
        path, _ = QFileDialog.getSaveFileName(
            self, "Export All History", "sonocube_history.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                export_all_csv(Path(path))
                QMessageBox.information(self, "Export", f"Saved:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _show_trend(self):
        from utils.history import load_history
        from gui.trend_dialog import TrendDialog
        dlg = TrendDialog(load_history(), parent=self)
        dlg.exec_()

    def _save_screenshot(self):
        from utils.spec import PROJECT_ROOT
        ss_dir = PROJECT_ROOT / "output" / "screenshots"
        ss_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        p = ss_dir / f"screenshot_{ts}.png"
        self.grab().save(str(p))
        QMessageBox.information(self, "Screenshot", f"Saved:\n{p}")

    def _on_settings_changed(self, settings: Dict[str, Any]):
        self._settings = settings

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            "Research-use echocardiography EF analysis desktop application.\n"
            "Estimates frame-wise EF, visualizes prediction stability,\n"
            "identifies ED/ES candidate frames, and generates structured reports.\n\n"
            "NOT FOR DIAGNOSTIC USE.\n"
            "For research and educational purposes only."
        )
