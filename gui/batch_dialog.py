"""Batch 분석 다이얼로그"""
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from gui.batch_worker import BatchWorker


class BatchDialog(QDialog):
    """Batch 분석 다이얼로그"""

    def __init__(self, default_output_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Analysis")
        self.setMinimumSize(640, 520)
        self._worker: Optional[BatchWorker] = None
        self._output_dir = default_output_dir
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Batch Analysis")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        desc = QLabel(
            "Select a folder containing echo video files.\n"
            "All supported files (MP4, AVI, MOV, MKV, DICOM) will be analyzed sequentially."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 폴더 선택
        folder_group = QGroupBox("Input Folder")
        folder_lo = QVBoxLayout(folder_group)
        folder_row = QHBoxLayout()
        self.lbl_folder = QLabel("No folder selected")
        self.lbl_folder.setStyleSheet("color: #8b949e; font-size: 12px;")
        folder_row.addWidget(self.lbl_folder, 1)
        btn_folder = QPushButton("Select Folder")
        btn_folder.clicked.connect(self._select_folder)
        folder_row.addWidget(btn_folder)
        folder_lo.addLayout(folder_row)

        self.lbl_file_count = QLabel("")
        self.lbl_file_count.setStyleSheet("color: #58a6ff; font-size: 11px;")
        folder_lo.addWidget(self.lbl_file_count)
        layout.addWidget(folder_group)

        # 출력 폴더
        out_group = QGroupBox("Output Directory")
        out_lo = QVBoxLayout(out_group)
        out_row = QHBoxLayout()
        self.lbl_output = QLabel(str(self._output_dir) if self._output_dir else "Same as project output/")
        self.lbl_output.setStyleSheet("color: #8b949e; font-size: 12px;")
        out_row.addWidget(self.lbl_output, 1)
        btn_out = QPushButton("Change…")
        btn_out.clicked.connect(self._select_output)
        out_row.addWidget(btn_out)
        out_lo.addLayout(out_row)
        layout.addWidget(out_group)

        # View type
        vt_row = QHBoxLayout()
        vt_row.addWidget(QLabel("View type (applied to all files):"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["A4C", "A2C", "PLAX", "Unknown"])
        self.view_combo.setFixedWidth(120)
        vt_row.addWidget(self.view_combo)
        vt_row.addStretch()
        layout.addLayout(vt_row)

        # 진행 상황
        prog_group = QGroupBox("Progress")
        prog_lo = QVBoxLayout(prog_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        prog_lo.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        prog_lo.addWidget(self.lbl_status)

        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(160)
        prog_lo.addWidget(self.result_list)
        layout.addWidget(prog_group)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_start = QPushButton("Start Batch")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.setFixedHeight(36)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._folder: Optional[Path] = None
        self._total_files = 0

    # ── 폴더 선택 ─────────────────────────────────────────────────────────────

    def _select_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if d:
            self._folder = Path(d)
            self.lbl_folder.setText(str(self._folder))
            _EXT = {".mp4", ".avi", ".mov", ".mkv", ".dcm", ".dicom"}
            files = [p for p in self._folder.rglob("*") if p.suffix.lower() in _EXT]
            self._total_files = len(files)
            self.lbl_file_count.setText(f"{self._total_files} supported file(s) found")
            self.btn_start.setEnabled(self._total_files > 0)

    def _select_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self._output_dir = Path(d)
            self.lbl_output.setText(str(self._output_dir))

    # ── 분석 ─────────────────────────────────────────────────────────────────

    def _start(self):
        if not self._folder:
            return
        if not self._output_dir:
            from utils.spec import PROJECT_ROOT
            self._output_dir = PROJECT_ROOT / "output" / "batch"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self.result_list.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self._total_files)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        view_type = self.view_combo.currentText()
        self._worker = BatchWorker(self._folder, self._output_dir, view_type)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.batch_finished.connect(self._on_finished)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.btn_cancel.setEnabled(False)

    @pyqtSlot(str)
    def _on_progress(self, msg: str):
        self.lbl_status.setText(msg)

    @pyqtSlot(str, int, int)
    def _on_file_started(self, name: str, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current - 1)

    @pyqtSlot(str, bool, str)
    def _on_file_done(self, name: str, success: bool, reason: str):
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        if success:
            item = QListWidgetItem(f"✓  {name}")
            item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor("#3fb950"))
        else:
            item = QListWidgetItem(f"✗  {name}  —  {reason}")
            item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor("#f85149"))
        self.result_list.addItem(item)
        self.result_list.scrollToBottom()

    @pyqtSlot(list)
    def _on_finished(self, results: list):
        success = sum(1 for r in results if r.get("status") == "success")
        total = len(results)
        self.lbl_status.setText(f"Done — {success}/{total} succeeded. Results saved to: {self._output_dir}")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.information(
            self, "Batch Complete",
            f"Batch analysis finished.\n{success}/{total} files succeeded.\nOutput: {self._output_dir}"
        )
